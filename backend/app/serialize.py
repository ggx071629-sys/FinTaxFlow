from __future__ import annotations

from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core import clock
from app.models import BillingEvent, BillingTask, Company, Invoice, User


def money(value: Decimal | str) -> str:
    return f"{Decimal(value).quantize(Decimal('0.01')):.2f}"


def user_out(user: User) -> dict:
    return {"id": str(user.id), "username": user.username, "name": user.name}


def company_out(company: Company) -> dict:
    return {
        "id": str(company.id),
        "name": company.name,
        "tax_id": company.tax_id,
        "service_status": company.service_status,
    }


def invoice_out(invoice: Invoice) -> dict:
    payload = {
        "id": str(invoice.id),
        "company_id": str(invoice.company_id),
        "number": invoice.number,
        "invoice_type": invoice.invoice_type,
        "direction": invoice.direction,
        "issued_at": clock.iso(invoice.issued_at),
        "buyer": {"name": invoice.buyer_name, "tax_id": invoice.buyer_tax_id},
        "seller": {"name": invoice.seller_name, "tax_id": invoice.seller_tax_id},
        "item_name": invoice.item_name,
        "net_amount": money(invoice.net_amount),
        "tax_amount": money(invoice.tax_amount),
        "total_amount": money(invoice.total_amount),
        "tax_rate": invoice.tax_rate,
        "verification_status": invoice.verification_status,
        "verification_note": invoice.verification_note,
        "pdf_available": invoice.pdf_available,
    }
    if invoice.source_task_id:
        payload["source_task_id"] = str(invoice.source_task_id)
    return payload


def event_out(event: BillingEvent) -> dict:
    item = {"label": event.label, "status": event.status}
    if event.time is not None:
        item["time"] = clock.iso(event.time)
    if event.note:
        item["note"] = event.note
    return item


def task_out(db: Session, task: BillingTask) -> dict:
    from app.models.extension import BatchAttempt, BatchLine

    followups = db.scalars(
        select(BillingTask.id)
        .where(BillingTask.source_task_id == task.id)
        .order_by(BillingTask.created_at)
    ).all()
    payload = {
        "id": str(task.id),
        "company_id": str(task.company_id),
        "number": task.number,
        "status": task.status,
        "input": task.input_snapshot,
        "seller": {"name": task.seller_name, "tax_id": task.seller_tax_id},
        "net_amount": money(task.net_amount),
        "tax_amount": money(task.tax_amount),
        "total_amount": money(task.total_amount),
        "tax_rate": task.tax_rate,
        "created_at": clock.iso(task.created_at),
        "followup_task_ids": [str(item) for item in followups],
        "events": [event_out(event) for event in task.events],
    }
    if task.completed_at:
        payload["completed_at"] = clock.iso(task.completed_at)
    if task.failure_reason:
        payload["failure_reason"] = task.failure_reason
    if task.invoice_id:
        payload["invoice_id"] = str(task.invoice_id)
    if task.invoice_number:
        payload["invoice_number"] = task.invoice_number
    if task.source_task_id:
        payload["source_task_id"] = str(task.source_task_id)
    attempt = db.get(BatchAttempt, task.id)
    if attempt:
        payload["batch_id"] = str(db.get(BatchLine, attempt.line_id).batch_id)
    return payload
