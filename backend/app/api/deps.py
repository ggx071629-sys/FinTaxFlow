from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import ApiError
from app.models import BillingTask, Company, Invoice, ResetRun, User, UserCompany


def parse_uuid(value: str | None, field: str = "id") -> uuid.UUID:
    if not value:
        raise ApiError(400, "VALIDATION_ERROR", "缺少必要参数", {field: "不能为空"})
    try:
        return uuid.UUID(value)
    except ValueError:
        raise ApiError(400, "VALIDATION_ERROR", "标识格式不正确", {field: "不是有效标识"}) from None


def require_company(db: Session, user: User, company_id: str | uuid.UUID | None) -> Company:
    cid = company_id if isinstance(company_id, uuid.UUID) else parse_uuid(company_id, "company_id")
    link = db.scalar(
        select(UserCompany).where(UserCompany.user_id == user.id, UserCompany.company_id == cid)
    )
    company = db.get(Company, cid)
    if link is None or company is None:
        raise ApiError(403, "COMPANY_FORBIDDEN", "无权访问该企业")
    return company


def get_invoice(db: Session, company: Company, invoice_id: str) -> Invoice:
    invoice = db.get(Invoice, parse_uuid(invoice_id, "id"))
    if invoice is None or invoice.company_id != company.id:
        raise ApiError(404, "NOT_FOUND", "对象不存在")
    return invoice


def get_task(db: Session, company: Company, task_id: str) -> BillingTask:
    task = db.get(BillingTask, parse_uuid(task_id, "id"))
    if task is None or task.company_id != company.id:
        raise ApiError(404, "NOT_FOUND", "对象不存在")
    return task


def get_reset_run(db: Session, company: Company, run_id: str) -> ResetRun:
    run = db.get(ResetRun, parse_uuid(run_id, "id"))
    if run is None or run.company_id != company.id:
        raise ApiError(404, "NOT_FOUND", "对象不存在")
    return run


def normalize_page(value: int | None) -> int:
    return value or 1


def normalize_page_size(value: int | None) -> int:
    return value or 20
