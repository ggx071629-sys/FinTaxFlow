from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import require_company
from app.core.security import get_current_user
from app.db import get_db
from app.models import User
from app.services import queries

router = APIRouter(tags=["dashboard"])


@router.get("/dashboard")
def dashboard(
    company_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    return queries.dashboard(db, require_company(db, user, company_id))
