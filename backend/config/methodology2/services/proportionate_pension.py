"""
Methodology-2 proportionate pension.

Rule (all classes 1/2/3/4):
  - TQS rounded like Oracle FFunc_TQS_Round_2:
      < 3 months  → whole years
      3–8 months  → years + 0.5
      9–11 months → years + 1
  - The date tested is the calculation date, one day before retirement /
    separation (same as the pay revision): retiring on 01-Jan-2007 is
    calculated as on 31-Dec-2006.
  - Calculation date up to 31-Dec-2006:
      rounded TQS >= 20 (e.g. 19y 9m → 20) → full pension factor 1.0
      (employee 50% of basic, family 30% of basic);
      rounded TQS < 20 → factor = rounded_TQS / 20.
  - Calculation date from 01-Jan-2007 (retiring on/after 02-Jan-2007):
      rounded TQS >= 10 (e.g. 9y 9m → 10) → full pension;
      rounded TQS < 10 → not eligible for pension (factor 0).
    Death in harness (retirement_type DEATH / DT ...) from 01-Jan-2007:
      rounded TQS >= 10 → full; rounded TQS < 10 → proportionate
      factor = rounded_TQS / 10 (never "not eligible").
  - Final pension amounts: any fraction rounds UP to next whole rupee
    (39346.88 → 39347).

Kept in this file so Met2 calc services stay readable; call sites only
pass retirement_date + TQS Y/M/D into apply_proportionate_pension().
"""

from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any

from methodology2.services.rounding_helpers import round_up_whole_rupee

# Full (non-proportionate) qualifying service after Oracle month rounding.
FULL_PENSION_TQS_YEARS = 20
# Calculation date (day before retirement) on/after this: full pension from
# 10 years; below it, no pension.
POST_2007_FROM = date(2007, 1, 1)
POST_2007_MIN_TQS_YEARS = 10

# CR 10-11-2026 (emp 45654): the post-2007 "TQS < 10 = not eligible" rule is
# only for retirement / VR etc.; a death-in-harness case gets TQS/10 instead.
DEATH_IN_HARNESS_TYPES = frozenset(
    {"DEATH", "DT", "DH", "D", "DE", "DIED IN HARNESS", "DEATH IN HARNESS"}
)


def is_death_in_harness(retirement_type) -> bool:
    return str(retirement_type or "").strip().upper() in DEATH_IN_HARNESS_TYPES


EMPLOYEE_PENSION_RATE = 0.5
FAMILY_PENSION_RATE = 0.3


def _as_date(value) -> date | None:
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    text = str(value).strip()[:10]
    try:
        return datetime.strptime(text, "%Y-%m-%d").date()
    except ValueError:
        return None


def round_tqs_years_oracle(tqs_years, tqs_months, tqs_days=0) -> float:
    """
    Oracle FFunc_TQS_Round_2 month bands (days ignored for the fraction).
    19y 9m → 20.0; 19y 8m → 19.5; 19y 2m → 19.0.
    """
    years = int(tqs_years or 0)
    months = int(tqs_months or 0)
    if months < 3:
        return float(years)
    if months < 9:
        return years + 0.5
    return float(years + 1)


def resolve_service_factor(
    *,
    retirement_date,
    tqs_yr=None,
    tqs_month=None,
    tqs_days=None,
    retirement_type=None,
) -> dict[str, Any]:
    """
    Resolve Met2 pension service factor for a case.

    Returns a dict always (safe to attach on pension payload):
      applied, full_pension, factor, rounded_tqs, divisor, cutoff, note, ...
    """
    base = {
        "rule": "tqs_20",
        "divisor": FULL_PENSION_TQS_YEARS,
        "applied": False,
        "full_pension": True,
        "eligible": True,
        "factor": 1.0,
        "rounded_tqs": None,
        "tqs_yr": tqs_yr,
        "tqs_month": tqs_month,
        "tqs_days": tqs_days,
        "retirement_date": None,
        "note": "",
    }

    d = _as_date(retirement_date)
    base["retirement_date"] = d.isoformat() if d else None

    if tqs_yr is None and tqs_month is None and tqs_days is None:
        base["note"] = "TQS not supplied — pension left at full rates."
        return base
    if d is None:
        base["note"] = "Retirement date not supplied — pension left at full rates."
        return base

    rounded = round_tqs_years_oracle(tqs_yr, tqs_month, tqs_days)
    base["rounded_tqs"] = rounded
    base["applied"] = True
    as_on = d - timedelta(days=1)
    base["calc_as_on"] = as_on.isoformat()
    as_on_text = as_on.strftime("%d-%m-%Y")

    if as_on >= POST_2007_FROM:
        base["rule"] = "post_2007_tqs_10"
        base["divisor"] = POST_2007_MIN_TQS_YEARS
        if rounded >= POST_2007_MIN_TQS_YEARS:
            base["note"] = (
                f"Calculated as on {as_on_text} (from 01-01-2007): rounded TQS "
                f"{rounded:g} >= {POST_2007_MIN_TQS_YEARS} -> full pension (50% / 30%)."
            )
            return base
        # CR 10-11-2026 (emp 45654): death in harness is not cut off at TQS 10;
        # it is proportionate TQS/10 instead of "not eligible".
        if is_death_in_harness(retirement_type):
            base["rule"] = "post_2007_death_tqs_10"
            base["full_pension"] = False
            base["factor"] = float(rounded) / float(POST_2007_MIN_TQS_YEARS)
            base["note"] = (
                f"Calculated as on {as_on_text} (from 01-01-2007, death in harness): "
                f"rounded TQS {rounded:g} < {POST_2007_MIN_TQS_YEARS} -> proportionate x "
                f"({rounded:g}/{POST_2007_MIN_TQS_YEARS})."
            )
            return base
        base["full_pension"] = False
        base["eligible"] = False
        base["factor"] = 0.0
        base["note"] = (
            f"Calculated as on {as_on_text} (from 01-01-2007): rounded TQS "
            f"{rounded:g} < {POST_2007_MIN_TQS_YEARS} years -> not eligible for pension."
        )
        return base

    base["rule"] = "pre_2007_tqs_20"
    if rounded >= FULL_PENSION_TQS_YEARS:
        base["full_pension"] = True
        base["factor"] = 1.0
        base["note"] = (
            f"Calculated as on {as_on_text} (up to 31-12-2006): rounded TQS "
            f"{rounded:g} >= {FULL_PENSION_TQS_YEARS} -> full pension (50% / 30%)."
        )
        return base

    factor = float(rounded) / float(FULL_PENSION_TQS_YEARS)
    base["full_pension"] = False
    base["factor"] = factor
    base["note"] = (
        f"Calculated as on {as_on_text} (up to 31-12-2006): rounded TQS "
        f"{rounded:g} < {FULL_PENSION_TQS_YEARS} -> proportionate x "
        f"({rounded:g}/{FULL_PENSION_TQS_YEARS})."
    )
    return base


def amount_from_basic(basic, *, employee: bool, factor: float = 1.0) -> float:
    """basic × rate × service factor (employee 50%, family 30%).

    Any paise/fraction is rounded UP to the next whole rupee
    (e.g. 39346.88 → 39347).
    """
    rate = EMPLOYEE_PENSION_RATE if employee else FAMILY_PENSION_RATE
    return float(round_up_whole_rupee(float(basic or 0) * rate * float(factor)))


def _ceil_pension_fields(out: dict) -> dict:
    """Ceil Met2 pension amount fields to whole rupees when any fraction exists."""
    for key in (
        "pension_277_cpi",
        "pension_359_cpi",
        "family_pension_277_cpi",
        "family_pension_359_cpi",
        "pension",
        "family_pension",
    ):
        if key in out and out[key] is not None and out[key] != "":
            out[key] = float(round_up_whole_rupee(out[key]))
    return out


def apply_proportionate_pension(
    pension: dict | None,
    *,
    retirement_date,
    tqs_yr=None,
    tqs_month=None,
    tqs_days=None,
    retirement_type=None,
) -> dict:
    """
    Adjust a Met2 pension dict in place (and return it).

    Supports both class 3/4 keys (pension_*_cpi / family_pension_*_cpi /
    basic_pay_*) and class 1/2 keys (pension / family_pension / basic_pay_2017).
    """
    out = dict(pension or {})
    meta = resolve_service_factor(
        retirement_date=retirement_date,
        tqs_yr=tqs_yr,
        tqs_month=tqs_month,
        tqs_days=tqs_days,
        # CR 10-11-2026 (emp 45654): death in harness → TQS/10, not cut off.
        retirement_type=retirement_type,
    )
    out["proportionate"] = meta

    raw_factor = meta.get("factor")
    factor = 1.0 if raw_factor is None else float(raw_factor)
    # Only rescale when TQS gives a reduced factor (0 = not eligible).
    if not meta.get("applied") or factor >= 1.0:
        return _ceil_pension_fields(out)

    basic_2017 = out.get("basic_pay_2017")
    basic_2022 = out.get("basic_pay_2022")

    if basic_2017 is not None:
        out["pension_277_cpi"] = amount_from_basic(
            basic_2017, employee=True, factor=factor
        )
        out["family_pension_277_cpi"] = amount_from_basic(
            basic_2017, employee=False, factor=factor
        )
        # Class 1/2 aliases
        if "pension" in out:
            out["pension"] = out["pension_277_cpi"]
        if "family_pension" in out:
            out["family_pension"] = out["family_pension_277_cpi"]

    if basic_2022 is not None:
        out["pension_359_cpi"] = amount_from_basic(
            basic_2022, employee=True, factor=factor
        )
        out["family_pension_359_cpi"] = amount_from_basic(
            basic_2022, employee=False, factor=factor
        )

    return _ceil_pension_fields(out)
