from __future__ import annotations

import logging
import shutil
from pathlib import Path

from sqlalchemy import delete, select, text
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


def _folders(company: Company) -> list[Path]:
    from app.core.config import get_settings
    return [company_pdf_dir(company.id), get_settings().rpa_evidence_dir / str(company.id)]


def _backup(folder: Path, run: ResetRun) -> Path:
    return folder.with_name(f".{folder.name}.reset-{run.id}")


def _finish_cleanup(db: Session, run: ResetRun, company: Company) -> ResetRun:
    from app.core.config import get_settings
    db.execute(text("SELECT pg_advisory_xact_lock(:k)"), {"k": get_settings().processor_lock_key})
    db.refresh(run)
    if run.status == "SUCCESS":
        return run
    try:
        for folder in _folders(company):
            backup = _backup(folder, run)
            if backup.exists():
                shutil.rmtree(backup)
    except OSError:
        run.status = "FAILED"
        run.message = "样例已重建，文件清理未完成，请重试恢复"
    else:
        run.status = "SUCCESS"
        run.message = "当前企业演示数据已恢复"
    run.updated_at = clock.now()
    db.commit()
    return run


def execute_reset(db: Session, run: ResetRun, company: Company) -> ResetRun:
    """Keep original artifacts recoverable until the replacement DB is committed."""
    run.status = "PROCESSING"
    run.updated_at = clock.now()
    db.flush()
    folders = _folders(company)
    staged: list[tuple[Path, Path]] = []
    prepared: list[Path] = []

    def restore_files() -> None:
        for folder in reversed(prepared):
            if folder.exists():
                shutil.rmtree(folder)
        for folder, backup in reversed(staged):
            backup.rename(folder)

    try:
        with db.begin_nested():
            # Rename on the same volume, without deleting the only copy of any file.
            for folder in folders:
                if folder.exists():
                    backup = _backup(folder, run)
                    if backup.exists():
                        raise OSError("A previous reset backup requires recovery")
                    folder.rename(backup)
                    staged.append((folder, backup))
                prepared.append(folder)
            company.generation += 1
            _clear_company(db, company)
            seed_company_data(db, company)
            db.flush()
    except Exception:
        logging.getLogger(__name__).exception("Reset rebuild failed; restoring original artifacts")
        restore_files()
        run.status = "FAILED"
        run.message = "演示恢复未完成，原数据和文件已保留，请重试恢复"
        run.updated_at = clock.now()
        db.flush()
        return run

    run.message = "样例已重建，正在清理原文件"
    run.updated_at = clock.now()
    try:
        # Confirm durability before returning success or discarding original artifacts.
        db.commit()
    except Exception:
        db.rollback()
        restore_files()
        raise ApiError(503, "RESET_NOT_COMMITTED", "恢复尚未提交，原文件已保留，请使用原请求重试")
    return _finish_cleanup(db, run, company)


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
        if run.status == "PROCESSING" or (run.status == "FAILED" and any(
            _backup(folder, run).exists() for folder in _folders(company)
        )):
            _finish_cleanup(db, run, company)
            return {"id": str(run.id), "status": run.status, "message": run.message}
        if run.status in ("SUCCESS", "PENDING"):
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
