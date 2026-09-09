"""
Unified Methodology I family pension calculation.

Returns family pension for category 1/2 (30% of 277 CPI basic)
and notional basic pay for category 3/4 at 277 / 359 CPI.

Scale input by category:
- Category 1/2: executive grade (E-1, E-2, … E-25)
- Category 3/4: full pay-scale string (1030 CPI period only); null/0 otherwise
- Old class 3/4 with no scale: ``equiv_pay_at_base_cpi`` (607 pay) can replace
  the scale mapping (Oracle EQUIV_PAY_AT_BASE_CPI / “Base CPI Pay when not matched”).
"""

from methodology1.services.cpi_chain_service import (
    CPI_359_REVISION,
    _already_on_359_scale,
    compute_277,
    compute_359,
)
from methodology1.services.parallel_cpi_service import CPI_1030_REVISION
from methodology1.services.revision_resolver import (
    get_calculation_start_revision,
    get_revision_column,
    is_1030_direct_607_period,
    is_pre_1988_separation,
)
from methodology1.services.scale_service import (
    get_equivalent_scales_by_scale,
    resolve_full_scale,
)
from methodology2.services.class1_2_service import (
    calculate_class12,
    validate_executive_grade,
)


def _normalize_category(value):
    if value in (None, ""):
        return None
    text = str(value).strip().upper()
    mapping = {"I": "1", "II": "2", "III": "3", "IV": "4"}
    text = mapping.get(text, text)
    if text not in {"1", "2", "3", "4"}:
        return None
    return text


def _normalize_scale(value):
    if value in (None, "", 0, "0"):
        return None
    text = str(value).strip()
    return text or None


def _parse_pay(value):
    if value in (None, ""):
        return None
    pay = float(value)
    if pay <= 0:
        return None
    return pay


def _fp_output(fp_277, fp_359):
    return {
        "FP_277_cpi": fp_277,
        "FP_359_cpi": fp_359,
    }


def _apply_scale_or_equiv_607(separation_date, last_pay, scale, equiv_pay, error_msg):
    """
    Resolve Excel scale map, or use entered 607 equivalent when scale is missing.

    Returns (last_pay, equivalent_scales, pay_source, error_dict).
    """
    if scale:
        equivalent_scales = get_equivalent_scales_by_scale(separation_date, scale)
        if equivalent_scales:
            return last_pay, equivalent_scales, "last_basic", None
        if equiv_pay:
            return equiv_pay, None, "equiv_pay_at_base_cpi", None
        return (
            last_pay,
            None,
            None,
            {"error": f"Could not resolve pay scale '{scale}' in PayScale table"},
        )
    if equiv_pay:
        return equiv_pay, None, "equiv_pay_at_base_cpi", None
    return last_pay, None, None, {"error": error_msg}


def _fp_result(fp_277, fp_359, *, calc_pay, pay_source):
    out = _fp_output(fp_277, fp_359)
    out["calc_pay"] = calc_pay
    out["pay_source"] = pay_source
    return out


def _calculate_class_34(
    separation_date, last_pay, scale, equiv_pay_at_base_cpi=None
):
    scale_revision = get_revision_column(separation_date)
    start_revision = get_calculation_start_revision(separation_date)
    equivalent_scales = None
    pay_source = "last_basic"
    equiv_pay = _parse_pay(equiv_pay_at_base_cpi)

    if is_pre_1988_separation(separation_date):
        last_pay, equivalent_scales, pay_source, err = _apply_scale_or_equiv_607(
            separation_date,
            last_pay,
            scale,
            equiv_pay,
            (
                "scale is required when separation date is before "
                "01/01/1988 (or enter Base CPI Pay when not matched)"
            ),
        )
        if err:
            return err

    if scale_revision == CPI_1030_REVISION and not is_1030_direct_607_period(
        separation_date
    ):
        last_pay, equivalent_scales, pay_source, err = _apply_scale_or_equiv_607(
            separation_date,
            last_pay,
            scale,
            equiv_pay,
            (
                "scale is required when separation date falls in "
                "1030 CPI period (1993-1994) "
                "(or enter Base CPI Pay when not matched)"
            ),
        )
        if err:
            return err

    cpi_359 = compute_359(
        last_pay,
        scale_revision,
        start_revision,
        equivalent_scales,
        separation_date,
    )
    if not cpi_359:
        return {"error": "Could not compute CPI revision chain for given inputs"}

    # Already on 359 CPI (e.g. separation year 2022+): 30% of last pay only.
    if _already_on_359_scale(scale_revision, separation_date):
        return _fp_result(
            None, cpi_359["notional"], calc_pay=last_pay, pay_source=pay_source
        )

    # Start at 359 from an earlier scale: 359 result only (no 277 rebuild).
    if start_revision == CPI_359_REVISION:
        return _fp_result(
            None, cpi_359["notional"], calc_pay=last_pay, pay_source=pay_source
        )

    cpi_277 = compute_277(
        last_pay,
        scale_revision,
        start_revision,
        equivalent_scales,
        separation_date,
    )
    if not cpi_277:
        return {"error": "Could not compute CPI revision chain for given inputs"}

    return _fp_result(
        cpi_277["notional"],
        cpi_359["notional"],
        calc_pay=last_pay,
        pay_source=pay_source,
    )


def _calculate_class_12(separation_date, grade, last_pay):
    result = calculate_class12(separation_date, grade, last_pay)
    if result.get("error"):
        return result

    family_pension = result.get("family_pension")
    if family_pension is None:
        return {"error": "Could not compute class 1/2 pension for given inputs"}

    return _fp_output(family_pension, None)


def calculate_family_pension(
    separation_date,
    category,
    pay,
    scale=None,
    grade=None,
    equiv_pay_at_base_cpi=None,
):
    """
    Methodology I unified calculation.

    ``equiv_pay_at_base_cpi``: 607 equivalent when last basic is not a scale
    stage / salary scale is missing (family pension claim field).

    Returns ``{"FP_277_cpi": ..., "FP_359_cpi": ...}`` on success
    or ``{"error": "..."}``.
    """
    if not separation_date:
        return {"error": "separation_date is required"}

    cat = _normalize_category(category)
    if cat is None:
        return {"error": "category must be 1, 2, 3, or 4"}

    equiv_pay = _parse_pay(equiv_pay_at_base_cpi)
    last_pay = _parse_pay(pay)
    if last_pay is None:
        last_pay = equiv_pay
    if last_pay is None:
        return {"error": "pay must be a positive number"}

    if cat in {"1", "2"}:
        raw_scale = _normalize_scale(scale) or _normalize_scale(grade)
        grade_value = validate_executive_grade(raw_scale)
        if not grade_value:
            return {
                "error": (
                    "For category 1/2, scale must be executive grade "
                    "(e.g. E-1, E-9), not pay band value"
                )
            }
        return _calculate_class_12(separation_date, grade_value, last_pay)

    scale_value = _normalize_scale(scale)
    if scale_value:
        scale_value = resolve_full_scale(separation_date, scale_value)

    return _calculate_class_34(
        separation_date,
        last_pay,
        scale_value,
        equiv_pay_at_base_cpi=equiv_pay,
    )
