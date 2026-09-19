from typing import Annotated

from fastapi import APIRouter, Depends, Header
from sqlalchemy.orm import Session

from app.api.deps import get_reset_run, require_company
from app.core.security import get_current_user
from app.db import get_db
from app.models import DemoSetting, User
from app.schemas import DemoSettingsIn, ResetRequest
from app.services.reset import start_reset

router = APIRouter(tags=["demo"])


@router.get("/demo/settings")
def read_demo_settings(
    company_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    company = require_company(db, user, company_id)
    row = db.get(DemoSetting, (user.id, company.id))
    return {"next_result": row.next_result if row else "SUCCESS", "declaration_fault": row.declaration_fault if row else "NONE"}


@router.put("/demo/settings")
def save_demo_settings(
    body: DemoSettingsIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    company = require_company(db, user, body.company_id)
    from app.services.automation import lock
    lock(db, company)
    row = db.get(DemoSetting, (user.id, company.id))
    if row is None:
        row = DemoSetting(user_id=user.id, company_id=company.id, next_result=body.next_result)
        db.add(row)
    else:
        row.next_result = body.next_result
    if body.declaration_fault is not None:
        row.declaration_fault = body.declaration_fault
    db.flush()
    return {"next_result": row.next_result, "declaration_fault": row.declaration_fault}


@router.post("/demo/reset")
def reset_company(
    body: ResetRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
):
    company = require_company(db, user, body.company_id)
    return start_reset(db, user, company, body.confirmed, idempotency_key)


@router.get("/demo/resets/{run_id}")
def reset_status(
    run_id: str,
    company_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    company = require_company(db, user, company_id)
    run = get_reset_run(db, company, run_id)
    return {"id": str(run.id), "status": run.status, "message": run.message}
