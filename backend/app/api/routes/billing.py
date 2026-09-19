from typing import Annotated

from fastapi import APIRouter, Depends, Header
from sqlalchemy.orm import Session

from app.api.deps import get_task, normalize_page, normalize_page_size, require_company
from app.core.security import get_current_user
from app.db import get_db
from app.models import User
from app.schemas import BillingInput
from app.serialize import task_out
from app.services import billing as billing_service
from app.services import queries

router = APIRouter(tags=["billing"])


@router.get("/billing")
def list_billing(
    company_id: str,
    status: str | None = None,
    page: int = 1,
    page_size: int = 20,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return queries.list_billing(
        db,
        require_company(db, user, company_id),
        status,
        normalize_page(page),
        normalize_page_size(page_size),
   
    )


@router.post("/billing")
def create_billing(
    body: BillingInput,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
):
    company = require_company(db, user, body.company_id)
    payload = body.model_dump()
    return billing_service.create_task(db, user, company, payload, idempotency_key)


@router.get("/billing/{task_id}")
def billing_detail(
    task_id: str,
    company_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    company = require_company(db, user, company_id)
    return task_out(db, get_task(db, company, task_id))
