from __future__ import annotations

import logging
import uuid
from datetime import timedelta
from decimal import Decimal

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.core import clock
from app.core.config import get_settings
from app.db import SessionLocal
from app.models import Activity, BillingTask, Company, Invoice
from app.services.billing import add_event
from app.services.pdf import write_invoice_pdf

log = logging.getLogger("fintaxflow.processor")


def acquire_lock(db: Session) -> bool:
    return bool(
        db.execute(
            text("SELECT pg_try_advisory_xact_lock(:k)"), {"k": get_settings().processor_lock_key}
        ).scalar()
    )


def next_invoice_number(db: Session, at) -> str:
    prefix = f"26{at.strftime('%y%m%d')}"
    numbers = db.scalars(select(Invoice.number).where(Invoice.number.like(f"{prefix}%"))).all()
    highest = 0
    for number in numbers:
        tail = number[len(prefix) :]
        if tail.isdigit():
            highest = max(highest, int(tail))
    return f"{prefix}{highest + 1:012d}"


def complete_task(db: Session, task: BillingTask) -> None:
    now = clock.now()
    company = db.get(Company, task.company_id)
    if company is None or company.generation != task.generation:
        if db.get(BillingTask, task.id) is None:
            return
        task.status = "FAILED"
        task.failure_reason = "企业数据已恢复，本次处理已失效"
        task.completed_at = now
        add_event(task, "处理已取消", "FAILED", now, "恢复后旧任务不能回写")
        return
    existing = db.scalar(select(Invoice).where(Invoice.source_task_id == task.id))
    if existing is not None:
        task.status = "SUCCESS"
        task.invoice_id = existing.id
        task.invoice_number = existing.number
        task.completed_at = task.completed_at or now
        return
    if task.bound_result == "FAILED":
        task.status = "FAILED"
        task.failure_reason = "开票处理失败，请核对资料后重新提交"
        task.completed_at = now
        add_event(task, "模拟处理失败", "FAILED", now, task.failure_reason)
        db.add(
            Activity(
                company_id=company.id,
                title=f"{task.input_snapshot.get('item_name')} · 模拟开票失败",
                time=now,
                object_type="billing",
                object_id=str(task.id),
            )
        )
        return
    snapshot = task.input_snapshot
    invoice = Invoice(
        id=uuid.uuid4(),
        company_id=company.id,
        generation=company.generation,
        number=next_invoice_number(db, now),
        invoice_type=snapshot["invoice_type"],
        direction="OUTPUT",
        issued_at=now,
        buyer_name=snapshot["buyer_name"],
        buyer_tax_id=snapshot["buyer_tax_id"],
        seller_name=task.seller_name,
        seller_tax_id=task.seller_tax_id,
        item_name=snapshot["item_name"],
        net_amount=Decimal(str(task.net_amount)),
        tax_amount=Decimal(str(task.tax_amount)),
        total_amount=Decimal(str(task.total_amount)),
        tax_rate=task.tax_rate,
        verification_status="VERIFIED",
        verification_note="演示数据：模拟验真通过，未连接外部税务平台",
        source_task_id=task.id,
        pdf_available=False,
    )
    try:
        path = write_invoice_pdf(invoice)
    except Exception:
        log.exception("pdf generation failed for task %s", task.id)
        task.status = "FAILED"
        task.failure_reason = "演示文件生成失败，请稍后重试"
        task.completed_at = now
        add_event(task, "文件准备失败", "FAILED", now, task.failure_reason)
        return
    invoice.pdf_path = str(path)
    invoice.pdf_available = True
    db.add(invoice)
    db.flush()
    task.status = "SUCCESS"
    task.invoice_id = invoice.id
    task.invoice_number = invoice.number
    task.completed_at = now
    add_event(task, "模拟处理完成", "SUCCESS", now, "演示文件已生成")
    db.add(
        Activity(
            company_id=company.id,
            title=f"{invoice.item_name} · 模拟开票成功",
            time=now,
            object_type="billing",
            object_id=str(task.id),
        )
    )
    db.add(
        Activity(
            company_id=company.id,
            title="新增一张销项票据",
            time=now,
            object_type="invoice",
            object_id=str(invoice.id),
        )
    )


def recover_orphans(db: Session) -> None:
    now = clock.now()
    stuck = db.scalars(
        select(BillingTask).where(
            BillingTask.status == "PROCESSING",
            BillingTask.processing_started_at.is_not(None),
            BillingTask.processing_started_at < now - timedelta(minutes=5),
        )
    ).all()
    for task in stuck:
        task.status = "PENDING"
        task.processing_started_at = None


def tick(db: Session) -> None:
    if not acquire_lock(db):
        return
    recover_orphans(db)
    now = clock.now()
    delay = timedelta(seconds=get_settings().billing_process_delay_seconds)
    pending = db.scalars(
        select(BillingTask)
        .where(BillingTask.status == "PENDING", BillingTask.created_at <= now)
        .order_by(BillingTask.created_at)
        .limit(20)
        .with_for_update(skip_locked=True)
    ).all()
    for task in pending:
        task.status = "PROCESSING"
        task.processing_started_at = now
        add_event(task, "模拟处理开始", "PROCESSING", now)
        if delay.total_seconds() <= 0:
            complete_task(db, task)
    if delay.total_seconds() <= 0:
        return
    db.flush()
    ready = db.scalars(
        select(BillingTask)
        .where(
            BillingTask.status == "PROCESSING",
            BillingTask.processing_started_at.is_not(None),
            BillingTask.processing_started_at <= now - delay,
        )
        .order_by(BillingTask.processing_started_at)
        .limit(20)
        .with_for_update(skip_locked=True)
    ).all()
    for task in ready:
        complete_task(db, task)


def run_tick() -> None:
    db = SessionLocal()
    try:
        tick(db)
        from app.services.automation import sync_batches
        sync_batches(db)
        db.commit()
    except Exception:
        db.rollback()
        log.exception("processor tick failed")
    finally:
        db.close()
    from app.workers.declaration import run_one
    run_one()
