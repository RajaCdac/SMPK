import math
from decimal import Decimal, ROUND_HALF_UP


def round2(amount):
    return round(float(amount), 2)


def round_up_to_10(amount):
    """Excel ROUNDUP(value, -1) — next higher multiple of 10."""
    value = float(amount)
    if value <= 0:
        return 0
    return int(math.ceil(value / 10.0) * 10)


def round_up_to_100(amount):
    """Round up to next higher multiple of 100 (2017 basic from 2012 notional)."""
    value = float(amount)
    if value <= 0:
        return 0
    return int(math.ceil(value / 100.0) * 100)


def round_up_whole_rupee(amount):
    """Excel ROUNDUP(value, 0) — e.g. special allowance row 43."""
    return int(math.ceil(float(amount)))


def round_nearest_rupee(amount):
    """Round to nearest whole rupee (0.40 → down, 0.60 → up; half-up at .50)."""
    return int(
        Decimal(str(float(amount))).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
    )
