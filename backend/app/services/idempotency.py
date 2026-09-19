from __future__ import annotations

import hashlib
import json
import uuid

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.core import clock
from app.core.errors import ApiError
from app.models import IdempotencyKey, User


def request_hash(payload: dict) -> str:
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()
    ).hexdigest()


def lookup(
    db: Session,
    user: User,
    company_id: uuid.UUID,
    operation: str,
    key: str | None,
    payload: dict,
) -> IdempotencyKey | None:
    from app.core.config import get_settings
    db.execute(text("SELECT pg_advisory_xact_lock(:k)"), {"k": get_settings().processor_lock_key})
    if not key or len(key) > 120:
        raise ApiError(400, "IDEMPOTENCY_REQUIRED", "缺少幂等请求标识")
    existing = db.scalar(
        select(IdempotencyKey).where(
            IdempotencyKey.user_id == user.id,
            IdempotencyKey.company_id == company_id,
            IdempotencyKey.operation == operation,
            IdempotencyKey.key == key,
        )
    )
    if existing is None:
        return None
    digest = request_hash(payload)
    if existing.request_hash != digest and operation != "company_reset":
        raise ApiError(409, "IDEMPOTENCY_CONFLICT", "同一请求标识不能用于不同内容")
    return existing


def store(
    db: Session,
    user: User,
    company_id: uuid.UUID,
    operation: str,
    key: str,
    payload: dict,
    object_id: uuid.UUID,
) -> IdempotencyKey:
    record = IdempotencyKey(
        user_id=user.id,
        company_id=company_id,
        operation=operation,
        key=key,
        request_hash=request_hash(payload),
        object_id=object_id,
        created_at=clock.now(),
    )
    db.add(record)
    db.flush()
    return record
