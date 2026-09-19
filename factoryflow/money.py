"""Small money helpers.

Money is handled as :class:`decimal.Decimal` everywhere in this project — never
``float`` — so allocation splits are cent-accurate and re-sum exactly to the
deduction total.
"""

from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal

CENTS = Decimal("0.01")


def to_decimal(value: object) -> Decimal:
    """Coerce strings/ints/floats to :class:`Decimal` safely.

    ``float`` inputs are routed through ``str`` first to avoid binary-float
    artifacts like ``Decimal(0.1) == 0.1000000000000000055…``.
    """
    if isinstance(value, Decimal):
        return value
    if isinstance(value, float):
        return Decimal(str(value))
    if value is None or value == "":
        return Decimal("0")
    return Decimal(str(value).replace(",", "").replace("$", "").strip())


def quantize(value: Decimal) -> Decimal:
    """Round to whole cents, half-up."""
    return to_decimal(value).quantize(CENTS, rounding=ROUND_HALF_UP)
