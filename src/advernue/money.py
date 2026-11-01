"""Money helpers: `Decimal` <-> `{micros, currency}`. Floats are rejected on purpose."""
from __future__ import annotations

from decimal import ROUND_HALF_EVEN, Decimal
from typing import Union

from ._generated.models import Money

MICROS = Decimal(1_000_000)


def to_money(amount: Union[Decimal, int, str], currency: str) -> Money:
    """`to_money(Decimal("12.34"), "USD")` -> `{"micros": 12340000, "currency": "USD"}`."""
    if isinstance(amount, (float, bool)):
        raise TypeError("money amounts must be Decimal, int or str, never float")
    micros = (Decimal(amount) * MICROS).quantize(Decimal(1), rounding=ROUND_HALF_EVEN)
    return {"micros": int(micros), "currency": currency.upper()}


def from_money(money: Money) -> Decimal:
    """`{"micros": 12340000, ...}` -> `Decimal("12.34")`."""
    return Decimal(money["micros"]) / MICROS
