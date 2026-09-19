from __future__ import annotations

import re

AMOUNT_RE = re.compile(r"^\d{1,10}(\.\d{1,2})?$")
TAX_ID_RE = re.compile(r"^[A-Z0-9]{18}$")
EMAIL_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
RATES = ("0", "0.01", "0.03", "0.06", "0.09", "0.13")
CREATE_TYPES = ("DIGITAL_NORMAL", "DIGITAL_SPECIAL")


def parse_cents(amount: str) -> int:
    whole, _, fraction = amount.partition(".")
    return int(whole) * 100 + int((fraction or "").ljust(2, "0")[:2] or 0)


def format_cents(cents: int) -> str:
    sign = "-" if cents < 0 else ""
    value = abs(cents)
    return f"{sign}{value // 100}.{value % 100:02d}"


def split_amount(amount: str, rate: str) -> dict[str, str]:
    cents = parse_cents(amount)
    rate_units = int(round(float(rate) * 10000))
    denominator = 10000 + rate_units
    net = (cents * 10000 + denominator // 2) // denominator
    return {
        "net_amount": format_cents(net),
        "tax_amount": format_cents(cents - net),
        "total_amount": format_cents(cents),
        "tax_rate": rate,
    }
