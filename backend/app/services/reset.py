from __future__ import annotations

import shutil

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.core import clock
from app.core.errors import ApiError
from app.models import (
    AccountingSummary,
    Activity,
    BillingEvent,
    BillingTask,
    Company,
    DemoSetting,
    IdempotencyKey,
    Invoice,
    ResetRun,
    TaxFiling,
    User,
)
from app.services.pdf import company_pdf_dir
from app.services import idempotency
from app.services.seed import seed_company_data


def _clear_company(db: Session, company: Company) -> None:
    from app.models import (FileAsset, ImportRecord, ImportLine, AutomationTask, BillingBatch, BatchLine, BatchAttempt, Reconciliation, Declaration)
    line_ids = select(BatchLine.id).where(BatchLine.company_id == company.id)
    db.execute(delete(BatchAttempt).where(BatchAttempt.line_id.in_(line_ids)))
    for model in [Declaration, Reconciliation, BatchLine, BillingBatch, ImportLine, ImportRecord, AutomationTask, FileAsset]:
        db.execute(delete(model).where(model.company_id == company.id))
    task_ids = db.scalars(select(BillingTask.id).where(BillingTask.company_id == company.id)).all()
    if task_ids:
        db.execute(delete(BillingEvent).where(BillingEvent.task_id.in_(task_ids)))
    db.execute(delete(Invoice).where(Invoice.company_id == company.id))
    db.execute(delete(BillingTask).where(BillingTask.company_id == company.id))
    db.execute(delete(TaxFiling).where(TaxFiling.company_id == company.id))
    db.execute(delete(AccountingSummary).where(AccountingSummary.company_id == company.id))
    db.execute(delete(Activity).where(Activity.company_id == company.id))
    db.execute(delete(DemoSetting).where(DemoSetting.company_id == company.id))
    db.execute(
        delete(IdempotencyKey).where(
            IdempotencyKey.company_id == company.id, IdempotencyKey.operation != "company_reset"
        )
    )
    db.flush()


def execute_reset(db: Session, run: ResetRun, company: Company) -> ResetRun:
    now = clock.now()
    run.status = "PROCESSING"
    run.updated_at = now
    db.flush()
    company.generation += 1
    _clear_company(db, company)
    folder = company_pdf_dir(company.id)
    try:
        if folder.exists():
            shutil.rmtree(folder)
        from app.core.config import get_settings
        rpa_folder = get_settings().rpa_evidence_dir / str(company.id)
        if rpa_folder.exists():
            shutil.rmtree(rpa_folder)
    except OSError:
        run.status = "FAILED"
        run.message = "文件清理未完成，请重试恢复"
        run.updated_at = clock.now()
        return run
    try:
        seed_company_data(db, company)
    except Exception:
        run.status = "FAILED"
        run.message = "样例重建失败，请重试恢复"
        run.updated_at = clock.now()
        return run
    if folder.exists() is False:
        # PDFs are written under the company dir during seed; absence is OK only if no invoices.
        pass
    run.status = "SUCCESS"
    run.message = "当前企业演示数据已恢复"
    run.updated_at = clock.now()
    return run


def start_reset(
    db: Session, user: User, company: Company, confirmed: bool, key: str | None
) -> dict:
    if not confirmed:
        raise ApiError(400, "CONFIRM_REQUIRED", "请确认后恢复当前企业")
    payload = {"company_id": str(company.id), "confirmed": True}
    existing = idempotency.lookup(db, user, company.id, "company_reset", key, payload)
    db.refresh(company)  # A concurrent reset may have advanced the generation while waiting.
    if existing:
        run = db.get(ResetRun, existing.object_id)
        if run is None:
            raise ApiError(409, "IDEMPOTENCY_CONFLICT", "原恢复记录已不存在")
        if run.status in ("SUCCESS", "PROCESSING", "PENDING"):
            return {"id": str(run.id), "status": run.status, "message": run.message}
        execute_reset(db, run, company)
        return {"id": str(run.id), "status": run.status, "message": run.message}
    unfinished = db.scalar(select(ResetRun).where(
        ResetRun.company_id == company.id,
        ResetRun.status.in_(["PENDING", "PROCESSING", "FAILED"]),
    ))
    if unfinished is not None:
        raise ApiError(409, "RESET_IN_PROGRESS", "已有未完成恢复，请沿用原请求标识继续恢复")
    now = clock.now()
    run = ResetRun(
        user_id=user.id,
        company_id=company.id,
        status="PENDING",
        created_at=now,
        updated_at=now,
    )
    db.add(run)
    db.flush()
    idempotency.store(db, user, company.id, "company_reset", key or "", payload, run.id)
    execute_reset(db, run, company)
    return {"id": str(run.id), "status": run.status, "message": run.message}
