"""Decimal helpers for consistent accounting calculations across databases."""

from decimal import ROUND_HALF_UP, Decimal

CURRENCY_QUANTUM = Decimal("0.01")


def as_decimal(value=0) -> Decimal:
	return Decimal(str(value or 0))


def rounded(value) -> Decimal:
	return as_decimal(value).quantize(CURRENCY_QUANTUM, rounding=ROUND_HALF_UP)
