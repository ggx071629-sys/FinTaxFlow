from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import ApiError
from app.core.security import create_token, get_current_user, verify_password
from app.db import get_db
from app.models import User
from app.schemas import LoginRequest
from app.serialize import user_out

router = APIRouter(tags=["auth"])


@router.post("/auth/login")
def login(body: LoginRequest, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.username == body.username.strip()))
    if user is None or not verify_password(body.password, user.password_hash):
        raise ApiError(401, "INVALID_CREDENTIALS", "账号或密码错误")
    return {"access_token": create_token(user), "user": user_out(user)}


@router.get("/auth/profile")
def profile(user: User = Depends(get_current_user)):
    return user_out(user)
