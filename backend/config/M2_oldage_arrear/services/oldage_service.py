"""
Old-age additional pension (DoPPW / CCS slabs).

Base for % = (M2 − M1) benefit at the CPI in force for each period.

% chart:
  80–<85 → 20%
  85–<90 → 30%
  90–<95 → 40%
  95–<100 → 50%
  100+   → 100%

Payable from the 1st of the calendar month in which the age is completed.

Period split example (age-80 WEF = Mar 2017):
  Mar-2017 … Dec-2021 → (M2−M1)@277 × 20%
  Jan-2022 … day before age-85 WEF → (M2−M1)@359 × 20%
  from age-85 WEF → (M2−M1)@359 × 30%
Display / arrear horizon stops at 31-Dec-2026 (no years after 2026).
"""

from __future__ import annotations

from calendar import monthrange
from datetime import date, datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP
from typing import Any

# (min_age_inclusive, max_age_exclusive_or_None, percent_of_basic)
OLDAGE_SLABS = (
    (80, 85, Decimal("20")),
    (85, 90, Decimal("30")),
    (90, 95, Decimal("40")),
    (95, 100, Decimal("50")),
    (100, None, Decimal("100")),
)

CPI_277_FROM = date(2017, 1, 1)
CPI_359_FROM = date(2022, 1, 1)
DISPLAY_HORIZON_END = date(2026, 12, 31)


def _as_date(value) -> date | None:
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    text = str(value).strip()[:10]
    for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y"):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    try:
        return datetime.fromisoformat(str(value).replace("Z", "")[:19]).date()
    except ValueError:
        return None


def _as_decimal(value) -> Decimal | None:
    if value is None or value == "":
        return None
    try:
        return Decimal(str(value))
    except Exception:
        return None


def _money(value: Decimal | None) -> float | None:
    if value is None:
        return None
    return float(value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def _benefit(m2, m1) -> Decimal | None:
    a = _as_decimal(m2)
    b = _as_decimal(m1)
    if a is None or b is None:
        return None
    diff = a - b
    return diff if diff > 0 else Decimal("0")


def age_completed_on(dob: date, as_on: date) -> int:
    years = as_on.year - dob.year
    if (as_on.month, as_on.day) < (dob.month, dob.day):
        years -= 1
    return max(years, 0)


def wef_for_age(dob: date, age_years: int) -> date:
    try:
        anniversary = date(dob.year + age_years, dob.month, dob.day)
    except ValueError:
        last = monthrange(dob.year + age_years, 2)[1]
        anniversary = date(dob.year + age_years, 2, last)
    return date(anniversary.year, anniversary.month, 1)


def percent_for_age(age_years: int) -> Decimal:
    if age_years < 80:
        return Decimal("0")
    for lo, hi, pct in OLDAGE_SLABS:
        if age_years >= lo and (hi is None or age_years < hi):
            return pct
    return Decimal("0")


def percent_on_wef_date(dob: date, on_date: date) -> Decimal:
    """Slab % in force on on_date (based on age WEF milestones, not birthday day)."""
    pct = Decimal("0")
    for lo, _hi, slab_pct in OLDAGE_SLABS:
        if on_date >= wef_for_age(dob, lo):
            pct = slab_pct
    return pct


def slab_age_on_wef_date(dob: date, on_date: date) -> int | None:
    age = None
    for lo, _hi, _pct in OLDAGE_SLABS:
        if on_date >= wef_for_age(dob, lo):
            age = lo
    return age


def slab_label(lo: int, hi: int | None) -> str:
    if hi is None:
        return f"{lo} years or more"
    return f"From {lo} years to less than {hi} years"


def cpi_period_for_date(wef: date | None) -> str | None:
    if wef is None:
        return None
    if wef >= CPI_359_FROM:
        return "359"
    if wef >= CPI_277_FROM:
        return "277"
    return None


def months_inclusive(start: date, end: date) -> int:
    if end < start:
        return 0
    return (end.year - start.year) * 12 + (end.month - start.month) + 1


def _benefit_for_cpi(
    cpi: str | None, b277: Decimal | None, b359: Decimal | None
) -> Decimal | None:
    if cpi == "359":
        return b359
    if cpi == "277":
        return b277
    return b359 if b359 is not None else b277


def build_oldage_periods(
    dob: date,
    *,
    b277: Decimal | None,
    b359: Decimal | None,
    as_on: date,
    horizon_end: date = DISPLAY_HORIZON_END,
    class_grp: int = 3,
) -> list[dict[str, Any]]:
    """
    Split [age-80 WEF … min(as_on, horizon_end)] at CPI, age-slab, and DA% changes.
    Each period pays enhancement + DA on that enhancement at the period DA%.
    """
    from M2_oldage_arrear.services.da_service import (
        da_on_amount,
        da_wef_dates,
        lookup_da_pct,
    )

    start = wef_for_age(dob, 80)
    end = min(as_on, horizon_end)
    if start > end:
        return []

    if end < CPI_277_FROM:
        return []
    if start < CPI_277_FROM:
        start = CPI_277_FROM

    breaks: set[date] = {start}
    for lo, _hi, _pct in OLDAGE_SLABS:
        w = wef_for_age(dob, lo)
        if start < w <= end:
            breaks.add(w)
    if start < CPI_359_FROM <= end:
        breaks.add(CPI_359_FROM)
    if start < CPI_277_FROM <= end:
        breaks.add(CPI_277_FROM)
    for wef in da_wef_dates(class_grp, start, end):
        breaks.add(wef)

    points = sorted(breaks)
    sentinel = end + timedelta(days=1)
    points = [p for p in points if p < sentinel]
    points.append(sentinel)

    periods: list[dict[str, Any]] = []
    for i in range(len(points) - 1):
        p_from = points[i]
        p_to = points[i + 1] - timedelta(days=1)
        if p_to > end:
            p_to = end
        if p_from > p_to:
            continue

        cpi = cpi_period_for_date(p_from)
        if cpi is None:
            continue

        benefit = _benefit_for_cpi(cpi, b277, b359)
        pct = percent_on_wef_date(dob, p_from)
        slab_age = slab_age_on_wef_date(dob, p_from)
        monthly = None
        if benefit is not None and pct > 0:
            monthly = (benefit * pct / Decimal("100")).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            )

        da_pct = lookup_da_pct(class_grp, cpi, p_from)
        monthly_da = da_on_amount(monthly, da_pct) if monthly is not None else Decimal("0")
        monthly_total = None
        if monthly is not None:
            monthly_total = (monthly + monthly_da).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            )

        months = months_inclusive(p_from, p_to)
        arrear_basic = None
        arrear_da = None
        arrear = None
        if monthly is not None:
            arrear_basic = (monthly * Decimal(months)).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            )
            arrear_da = (monthly_da * Decimal(months)).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            )
            arrear = (arrear_basic + arrear_da).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            )

        periods.append(
            {
                "period_from": p_from.isoformat(),
                "period_to": p_to.isoformat(),
                "months": months,
                "cpi_period": cpi,
                "age_slab": slab_age,
                "percent": float(pct),
                "benefit_base": _money(benefit),
                "da_pct": float(da_pct),
                "monthly_additional": _money(monthly),
                "monthly_da": _money(monthly_da),
                "monthly_total": _money(monthly_total),
                "period_arrear_basic": _money(arrear_basic),
                "period_arrear_da": _money(arrear_da),
                "period_arrear": _money(arrear),
            }
        )

    return periods


def compute_oldage_benefit(
    *,
    dob,
    basic_pension=None,
    as_on_date=None,
    pension_277=None,
    pension_359=None,
    m1_pension_277=None,
    m1_pension_359=None,
    benefit_277=None,
    benefit_359=None,
    horizon_end=None,
    category=None,
    class_grp=None,
) -> dict[str, Any]:
    """
    Build current entitlement + period-wise schedule up to Dec-2026
    (enhancement + DA on enhancement for each period).
    """
    from M2_oldage_arrear.services.da_service import (
        class_grp_from_category,
        da_on_amount,
        lookup_da_pct,
    )

    dob_d = _as_date(dob)
    as_on = _as_date(as_on_date) or date.today()
    horizon = _as_date(horizon_end) or DISPLAY_HORIZON_END
    grp = int(class_grp) if class_grp not in (None, "") else class_grp_from_category(category)

    m2_359 = _as_decimal(pension_359)
    m1_359 = _as_decimal(m1_pension_359)
    m2_277 = _as_decimal(pension_277)
    m1_277 = _as_decimal(m1_pension_277)

    b359 = _as_decimal(benefit_359)
    if b359 is None and m2_359 is not None and m1_359 is not None:
        b359 = _benefit(m2_359, m1_359)

    b277 = _as_decimal(benefit_277)
    if b277 is None and m2_277 is not None and m1_277 is not None:
        b277 = _benefit(m2_277, m1_277)

    explicit_basic = _as_decimal(basic_pension)

    if not dob_d:
        return {
            "error": "Date of birth is required for old-age benefit",
            "dob": None,
            "as_on_date": as_on.isoformat(),
            "age_completed": None,
            "applicable_percent": 0,
            "additional_pension": None,
            "slabs": [],
            "milestones": [],
            "periods": [],
        }

    age = age_completed_on(dob_d, as_on)
    pct = percent_on_wef_date(dob_d, as_on)

    current_wef = None
    for lo, hi, _pct in OLDAGE_SLABS:
        if age >= lo and (hi is None or age < hi):
            current_wef = wef_for_age(dob_d, lo)
            break
    if current_wef is None and pct > 0:
        current_wef = wef_for_age(dob_d, 80)

    applicable_cpi = cpi_period_for_date(as_on)
    basic = _benefit_for_cpi(applicable_cpi, b277, b359)
    if basic is None:
        basic = explicit_basic

    additional = None
    da_pct_now = lookup_da_pct(grp, applicable_cpi, as_on)
    monthly_da_now = Decimal("0")
    monthly_total_now = None
    if basic is not None and pct > 0:
        additional = (basic * pct / Decimal("100")).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
        monthly_da_now = da_on_amount(additional, da_pct_now)
        monthly_total_now = (additional + monthly_da_now).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )

    periods = build_oldage_periods(
        dob_d,
        b277=b277,
        b359=b359,
        as_on=as_on,
        horizon_end=horizon,
        class_grp=grp,
    )

    milestones = []
    for lo, _hi, slab_pct in OLDAGE_SLABS:
        wef = wef_for_age(dob_d, lo)
        if wef > horizon:
            continue
        cpi = cpi_period_for_date(wef)
        base = _benefit_for_cpi(cpi, b277, b359)
        milestones.append(
            {
                "age": lo,
                "percent": float(slab_pct),
                "wef": wef.isoformat(),
                "eligible": as_on >= wef,
                "cpi_period": cpi,
                "benefit_base": _money(base),
                "additional_on_basic": _money(
                    (base * slab_pct / Decimal("100")) if base is not None else None
                ),
            }
        )

    total_arrear = None
    total_arrear_basic = None
    total_arrear_da = None
    if periods:
        total_arrear = _money(
            sum(
                (
                    Decimal(str(p["period_arrear"]))
                    for p in periods
                    if p.get("period_arrear") is not None
                ),
                Decimal("0"),
            )
        )
        total_arrear_basic = _money(
            sum(
                (
                    Decimal(str(p["period_arrear_basic"]))
                    for p in periods
                    if p.get("period_arrear_basic") is not None
                ),
                Decimal("0"),
            )
        )
        total_arrear_da = _money(
            sum(
                (
                    Decimal(str(p["period_arrear_da"]))
                    for p in periods
                    if p.get("period_arrear_da") is not None
                ),
                Decimal("0"),
            )
        )

    slabs = [
        {
            "label": slab_label(lo, hi),
            "age_from": lo,
            "age_to": hi,
            "percent": float(pct_slab),
        }
        for lo, hi, pct_slab in OLDAGE_SLABS
    ]

    return {
        "dob": dob_d.isoformat(),
        "as_on_date": as_on.isoformat(),
        "horizon_end": horizon.isoformat(),
        "age_completed": age,
        "class_grp": grp,
        "applicable_percent": float(pct),
        "applicable_cpi": applicable_cpi,
        "da_pct": float(da_pct_now),
        "m2_pension_359": _money(m2_359),
        "m1_pension_359": _money(m1_359),
        "m2_pension_277": _money(m2_277),
        "m1_pension_277": _money(m1_277),
        "benefit_359": _money(b359),
        "benefit_277": _money(b277),
        "basic_pension": _money(basic),
        "pension_277": _money(b277),
        "pension_359": _money(b359),
        "additional_pension": _money(additional),
        "monthly_da": _money(monthly_da_now),
        "monthly_total": _money(monthly_total_now),
        "current_slab_wef": current_wef.isoformat() if current_wef else None,
        "eligible": pct > 0 and as_on >= wef_for_age(dob_d, 80),
        "slabs": slabs,
        "milestones": milestones,
        "periods": periods,
        "total_arrear": total_arrear,
        "total_arrear_basic": total_arrear_basic,
        "total_arrear_da": total_arrear_da,
        "note": (
            "Period-wise: age-% × (M2 − M1) at CPI in force, plus DA on that "
            "enhancement at fi_pr_mh_calc_da rate for the period. "
            "Splits also when DA% changes. Schedule stops at 31.12.2026."
        ),
    }
