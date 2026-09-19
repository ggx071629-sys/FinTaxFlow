from __future__ import annotations

import uuid
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core import clock
from app.core.errors import ApiError
from app.core.money import AMOUNT_RE, CREATE_TYPES, EMAIL_RE, RATES, TAX_ID_RE, split_amount
from app.models import BillingEvent, BillingTask, Company, DemoSetting, User
from app.serialize import task_out
from app.services import idempotency


def validate_input(body: dict) -> dict[str, str]:
    errors: dict[str, str] = {}
    if body.get("invoice_type") not in CREATE_TYPES:
        errors["invoice_type"] = "仅支持数电普票或数电专票"
    if not str(body.get("buyer_name") or "").strip():
        errors["buyer_name"] = "请输入购买方名称"
    if not TAX_ID_RE.match(str(body.get("buyer_tax_id") or "")):
        errors["buyer_tax_id"] = "请输入 18 位大写字母或数字的演示税号"
    if not str(body.get("item_name") or "").strip():
        errors["item_name"] = "请输入开票项目"
    amount = str(body.get("total_amount") or "")
    if not AMOUNT_RE.match(amount) or Decimal(amount or "0") <= 0:
        errors["total_amount"] = "请输入大于 0 的金额，最多两位小数、十位整数"
    if body.get("tax_rate") not in RATES:
        errors["tax_rate"] = "请选择演示税率"
    email = str(body.get("email") or "")
    if email and not EMAIL_RE.match(email):
        errors["email"] = "请输入有效邮箱，或留空"
    return errors


def _snapshot(body: dict) -> dict:
    return {
        "invoice_type": body["invoice_type"],
        "buyer_name": str(body["buyer_name"]).strip(),
        "buyer_tax_id": str(body["buyer_tax_id"]).strip(),
        "item_name": str(body["item_name"]).strip(),
        "total_amount": split_amount(str(body["total_amount"]), str(body["tax_rate"]))["total_amount"],
        "tax_rate": body["tax_rate"],
        "email": str(body.get("email") or "").strip(),
        "remark": str(body.get("remark") or "").strip(),
        **(
            {"source_task_id": body["source_task_id"]}
            if body.get("source_task_id")
            else {}
        ),
    }


def _next_number(db: Session, at) -> str:
    prefix = f"KP{at.strftime('%Y%m%d')}"
    numbers = db.scalars(select(BillingTask.number).where(BillingTask.number.like(f"{prefix}%"))).all()
    highest = 0
    for number in numbers:
        tail = number[len(prefix) :]
        if tail.isdigit():
            highest = max(highest, int(tail))
    return f"{prefix}{highest + 1:04d}"


def add_event(task: BillingTask, label: str, status: str, at, note: str | None = None) -> None:
    task.events.append(
        BillingEvent(label=label, status=status, time=at, note=note, sort=len(task.events))
    )


def create_task(
    db: Session,
    user: User,
    company: Company,
    body: dict,
    idempotency_key: str | None,
    allow_batch: bool = False,
) -> dict:
    from app.services.automation import lock
    from app.models import BatchAttempt
    lock(db, company)
    errors = validate_input(body)
    if errors:
        raise ApiError(400, "VALIDATION_ERROR", "请核对开票资料", errors)
    snapshot = _snapshot(body)
    existing = idempotency.lookup(db, user, company.id, "billing_create", idempotency_key, snapshot)
    if existing:
        task = db.get(BillingTask, existing.object_id)
        if task is None:
            raise ApiError(409, "IDEMPOTENCY_CONFLICT", "原申请已不存在，请使用新的请求标识")
        return task_out(db, task)
    source = None
    if snapshot.get("source_task_id"):
        try:
            source_id = uuid.UUID(snapshot["source_task_id"])
        except ValueError:
            raise ApiError(
                400, "VALIDATION_ERROR", "原申请标识不正确", {"source_task_id": "不是有效标识"}
            ) from None
        source = db.get(BillingTask, source_id)
        if source is None or source.company_id != company.id:
            raise ApiError(404, "NOT_FOUND", "原申请不存在")
        if not allow_batch and db.get(BatchAttempt, source.id):
            raise ApiError(409, "IMPORT_NOT_SUBMITTABLE", "批量开票请在原批次中仅重试失败项")
        if source.status != "FAILED":
            raise ApiError(400, "INVALID_SOURCE", "仅失败申请可以修改后重新提交")
    amounts = split_amount(snapshot["total_amount"], snapshot["tax_rate"])
    setting = db.scalar(
        select(DemoSetting)
        .where(DemoSetting.user_id == user.id, DemoSetting.company_id == company.id)
        .with_for_update()
    )
    bound = setting.next_result if setting else "SUCCESS"
    if setting:
        setting.next_result = "SUCCESS"
    now = clock.now()
    task = BillingTask(
        company_id=company.id,
        generation=company.generation,
        number=_next_number(db, now),
        status="PENDING",
        input_snapshot=snapshot,
        net_amount=Decimal(amounts["net_amount"]),
        tax_amount=Decimal(amounts["tax_amount"]),
        total_amount=Decimal(amounts["total_amount"]),
        tax_rate=amounts["tax_rate"],
        seller_name=company.name,
        seller_tax_id=company.tax_id,
        created_at=now,
        source_task_id=source.id if source else None,
        bound_result=bound,
    )
    add_event(task, "申请已受理", "SUCCESS", now)
    db.add(task)
    db.flush()
    idempotency.store(db, user, company.id, "billing_create", idempotency_key or "", snapshot, task.id)
    return task_out(db, task)
