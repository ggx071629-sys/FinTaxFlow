from __future__ import annotations

import os
from datetime import datetime
from zoneinfo import ZoneInfo

SHANGHAI = ZoneInfo("Asia/Shanghai")


def now() -> datetime:
    override = os.environ.get("FINTAX_CLOCK")
    if override:
        value = datetime.fromisoformat(override)
        if value.tzinfo is None:
            value = value.replace(tzinfo=SHANGHAI)
        return value.astimezone(SHANGHAI)
    return datetime.now(SHANGHAI)


def iso(value: datetime | None) -> str | None:
    if value is None:
        return None
    return value.astimezone(SHANGHAI).isoformat(timespec="seconds")


def current_period(at: datetime | None = None) -> str:
    return (at or now()).strftime("%Y-%m")


def period_start(period: str) -> datetime:
    year, month = (int(part) for part in period.split("-"))
    return datetime(year, month, 1, tzinfo=SHANGHAI)


def shift_period(period: str, months: int) -> str:
    year, month = (int(part) for part in period.split("-"))
    total = year * 12 + (month - 1) + months
    year, month0 = divmod(total, 12)
    return f"{year:04d}-{month0 + 1:02d}"


def last_three_periods(at: datetime | None = None) -> list[str]:
    current = current_period(at)
    return [shift_period(current, offset) for offset in range(0, -3, -1)]
