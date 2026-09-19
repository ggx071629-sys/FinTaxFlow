from __future__ import annotations

from datetime import timedelta
from decimal import Decimal

from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import Session

from app.core import clock
from app.models import (
    AccountingSummary,
    Activity,
    BillingTask,
    Company,
    Invoice,
    TaxFiling,
)
from app.serialize import invoice_out, money


def _blank(value: str | None) -> str | None:
    if not value:
        return None
    stripped = value.strip()
    # Mini program GET may stringify missing fields as "undefined"/"null".
    if stripped.lower() in {"undefined", "null"}:
        return None
    return stripped


def dashboard(db: Session, company: Company) -> dict:
    period = clock.current_period()
    start = clock.period_start(period)
    end = clock.period_start(clock.shift_period(period, 1))

    def wrap(builder):
        try:
            return {"data": builder()}
        except Exception:
            return {"data": None, "error": {"code": "QUERY_FAILED", "message": "该分区加载失败，请重试"}}

    def services():
        invoices = db.scalars(
            select(Invoice).where(
                Invoice.company_id == company.id, Invoice.issued_at >= start, Invoice.issued_at < end
            )
        ).all()
        taxes = db.scalars(
            select(TaxFiling).where(TaxFiling.company_id == company.id, TaxFiling.period == period)
        ).all()
        open_tasks = db.scalars(
            select(BillingTask).where(
                BillingTask.company_id == company.id,
                BillingTask.status.in_(("PENDING", "PROCESSING", "FAILED")),
            )
        ).all()
        latest_invoice = max((item.issued_at for item in invoices), default=clock.now())
        latest_tax = max((item.updated_at for item in taxes), default=clock.now())
        latest_billing = max(
            (item.completed_at or item.created_at for item in db.scalars(
                select(BillingTask).where(BillingTask.company_id == company.id)
            ).all()),
            default=clock.now(),
        )
        pending_verify = sum(1 for item in invoices if item.verification_status == "PENDING")
        completed_tax = sum(1 for item in taxes if item.status == "COMPLETED")
        processing_billing = sum(1 for item in open_tasks if item.status == "PROCESSING")
        failed_billing = sum(1 for item in open_tasks if item.status == "FAILED")
        return [
            {
                "kind": "invoice",
                "title": "票据处理",
                "status": "核对中" if pending_verify else "已归集",
                "summary": f"{len(invoices)} 张归集，{pending_verify} 张待处理",
                "count": len(invoices),
                "updated_at": clock.iso(latest_invoice),
            },
            {
                "kind": "tax",
                "title": "报税进度",
                "status": "进行中" if taxes and completed_tax < len(taxes) else "可查询",
                "summary": f"{len(taxes)} 个税种，{completed_tax} 项已完成",
                "count": len(taxes),
                "updated_at": clock.iso(latest_tax),
            },
            {
                "kind": "billing",
                "title": "开票任务",
                "status": "跟进中" if open_tasks else "已完成",
                "summary": f"{processing_billing} 项处理中，{failed_billing} 项需重提",
                "count": len(open_tasks),
                "updated_at": clock.iso(latest_billing),
            },
        ]

    def statistics():
        invoices = db.scalars(
            select(Invoice).where(
                Invoice.company_id == company.id, Invoice.issued_at >= start, Invoice.issued_at < end
            )
        ).all()
        input_amount = sum((item.total_amount for item in invoices if item.direction == "INPUT"), Decimal("0"))
        output_amount = sum((item.total_amount for item in invoices if item.direction == "OUTPUT"), Decimal("0"))
        pending = sum(1 for item in invoices if item.verification_status == "PENDING")
        return {
            "input_amount": money(input_amount),
            "output_amount": money(output_amount),
            "pending_invoices": pending,
        }

    def activities():
        rows = db.scalars(
            select(Activity)
            .where(Activity.company_id == company.id)
            .order_by(Activity.time.desc())
            .limit(8)
        ).all()
        return [
            {
                "id": str(row.id),
                "title": row.title,
                "time": clock.iso(row.time),
                "object_type": row.object_type,
                "object_id": row.object_id,
                **({"period": row.period} if row.period else {}),
            }
            for row in rows
        ]

    return {
        "period": period,
        "services": wrap(services),
        "statistics": wrap(statistics),
        "activities": wrap(activities),
    }


def list_invoices(
    db: Session,
    company: Company,
    *,
    keyword: str | None,
    direction: str | None,
    date_from: str | None,
    date_to: str | None,
    invoice_type: str | None,
    verification_status: str | None,
    page: int,
    page_size: int,
) -> dict:
    page = max(1, page)
    page_size = min(max(1, page_size), 100)
    filters = [Invoice.company_id == company.id]
    keyword = _blank(keyword)
    direction = _blank(direction)
    invoice_type = _blank(invoice_type)
    verification_status = _blank(verification_status)
    date_from = _blank(date_from)
    date_to = _blank(date_to)
    if keyword:
        like = f"%{keyword}%"
        filters.append(
            or_(
                Invoice.buyer_name.ilike(like),
                Invoice.seller_name.ilike(like),
                Invoice.number.ilike(like),
            )
        )
    if direction in ("INPUT", "OUTPUT"):
        filters.append(Invoice.direction == direction)
    if invoice_type:
        filters.append(Invoice.invoice_type == invoice_type)
    if verification_status:
        filters.append(Invoice.verification_status == verification_status)
    if date_from and len(date_from) >= 10:
        start_day = clock.period_start(date_from[:7]).replace(day=int(date_from[8:10]))
        filters.append(Invoice.issued_at >= start_day)
    if date_to and len(date_to) >= 10:
        end_day = clock.period_start(date_to[:7]).replace(day=int(date_to[8:10])) + timedelta(days=1)
        filters.append(Invoice.issued_at < end_day)
    where = and_(*filters)
    total = db.scalar(select(func.count()).select_from(Invoice).where(where)) or 0
    amount = db.scalar(select(func.coalesce(func.sum(Invoice.total_amount), 0)).where(where)) or Decimal("0")
    rows = db.scalars(
        select(Invoice)
        .where(where)
        .order_by(Invoice.issued_at.desc(), Invoice.number.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    return {
        "items": [invoice_out(item) for item in rows],
        "page": page,
        "page_size": page_size,
        "total": total,
        "total_amount": money(amount),
    }


def _periods(db: Session, company: Company, table) -> list[str]:
    rows = db.scalars(
        select(table.period).where(table.company_id == company.id).distinct()
    ).all()
    return sorted(set(rows), reverse=True)


def tax_response(db: Session, company: Company, period: str | None) -> dict:
    from app.services.declarations import declaration_for_filing
    periods = _periods(db, company, TaxFiling)
    requested = _blank(period)
    current = clock.current_period()
    selected = requested or (current if current in periods else (periods[0] if periods else current))
    items = db.scalars(
        select(TaxFiling)
        .where(TaxFiling.company_id == company.id, TaxFiling.period == selected)
        .order_by(TaxFiling.name)
    ).all()
    completed = sum(1 for item in items if item.status == "COMPLETED")
    summary = (
        f"{completed} / {len(items)} 个税种已完成"
        if items
        else "该月份暂无报税样例，可查询已有期间或在演示设置恢复样例"
    )
    return {
        "period": selected,
        "periods": periods,
        "summary": summary,
        "items": [
            {
                "id": str(item.id),
                "name": item.name,
                "period": item.period,
                "status": item.status,
                "updated_at": clock.iso(item.updated_at),
                "nodes": item.nodes or [],
                **declaration_for_filing(db, item),
                **({"failure_reason": item.failure_reason} if item.failure_reason else {}),
            }
            for item in items
        ],
    }


def accounting_response(db: Session, company: Company, period: str | None) -> dict:
    periods = _periods(db, company, AccountingSummary)
    requested = _blank(period)
    current = clock.current_period()
    selected = requested or (current if current in periods else (periods[0] if periods else current))
    rows = {
        item.period: item
        for item in db.scalars(
            select(AccountingSummary).where(AccountingSummary.company_id == company.id)
        ).all()
    }
    summary = rows.get(selected)
    trend_periods = periods[:3] or clock.last_three_periods()
    return {
        "period": selected,
        "periods": periods,
        "summary": None
        if summary is None
        else {
            "income": money(summary.income),
            "expense": money(summary.expense),
            "profit": money(summary.profit),
            "receivable": money(summary.receivable),
            "payable": money(summary.payable),
        },
        "trend": [
            {
                "period": item,
                "income": money(rows[item].income) if item in rows else "0.00",
                "expense": money(rows[item].expense) if item in rows else "0.00",
            }
            for item in sorted(trend_periods)
        ],
    }


def list_billing(
    db: Session, company: Company, status: str | None, page: int, page_size: int
) -> dict:
    from app.serialize import task_out

    page = max(1, page)
    page_size = min(max(1, page_size), 100)
    filters = [BillingTask.company_id == company.id]
    status = _blank(status)
    if status:
        filters.append(BillingTask.status == status)
    where = and_(*filters)
    total = db.scalar(select(func.count()).select_from(BillingTask).where(where)) or 0
    rows = db.scalars(
        select(BillingTask)
        .where(where)
        .order_by(BillingTask.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    return {
        "items": [task_out(db, item) for item in rows],
        "page": page,
        "page_size": page_size,
        "total": total,
    }
