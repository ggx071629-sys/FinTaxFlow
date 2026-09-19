from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import require_company
from app.core.security import get_current_user
from app.db import get_db
from app.models import User
from app.services import queries

router = APIRouter(tags=["tax"])


@router.get("/tax-filings")
def tax_filings(
    company_id: str,
    period: str | None = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return queries.tax_response(db, require_company(db, user, company_id), period)
