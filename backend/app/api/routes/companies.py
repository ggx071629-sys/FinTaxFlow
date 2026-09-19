from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import require_company
from app.core.security import get_current_user
from app.db import get_db
from app.models import Company, User, UserCompany
from app.serialize import company_out

router = APIRouter(tags=["companies"])


@router.get("/companies")
def companies(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = db.scalars(
        select(Company)
        .join(UserCompany, UserCompany.company_id == Company.id)
        .where(UserCompany.user_id == user.id)
        .order_by(Company.name)
    ).all()
    return [company_out(item) for item in rows]


@router.get("/companies/{company_id}")
def company_detail(
    company_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    return company_out(require_company(db, user, company_id))
