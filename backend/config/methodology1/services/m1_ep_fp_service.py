"""
M2 "M1 calculation": Methodology-1 employee pension and family pension.

CR 06-11-2026. Class 3/4 uses the Methodology-1 CPI chain on the full last pay
(no starting 30% / 607 slab), every later step unchanged (DA, fitment, 1708 DA
cap, pay-protect minimums). Employee pension = 50% and family pension = 30% of
the 277 / 359 CPI notional. Class 1/2 uses the class 1/2 engine, which already
gives both at 277 CPI.
"""

import math

from methodology1.services.cpi_chain_service import full_pay_chain
from methodology1.services.family_pension_calculation_service import (
    _calculate_class_34,
    _normalize_category,
    _normalize_scale,
    _parse_pay,
)
from methodology1.services.revision_resolver import (
    get_calculation_start_revision,
    get_revision_column,
)
from methodology1.services.scale_service import resolve_full_scale
from methodology2.services.class1_2_service import (
    calculate_class12,
    validate_executive_grade,
)

EP_SHARE = 0.50
FP_SHARE = 0.30


def _share(value, share):
    """Pension from a notional amount, rounded up to the next rupee."""
    if value is None:
        return None
    return math.ceil(round(float(value) * share, 2))


def _class_12(separation_date, scale, grade, last_pay):
    raw = _normalize_scale(scale) or _normalize_scale(grade)
    grade_value = validate_executive_grade(raw)
    if not grade_value:
        return {
            "error": "For category 1/2, scale must be executive grade (e.g. E-1, E-9), not pay band value"
        }
    result = calculate_class12(separation_date, grade_value, last_pay)
    if result.get("error"):
        return result
    basic_2017 = result.get("basic_pay_2017")
    return {
        "category_group": "1/2",
        "notional_277": basic_2017,
        "notional_359": None,
        "EP_277_cpi": result.get("pension"),
        "EP_359_cpi": None,
        "FP_277_cpi": result.get("family_pension"),
        "FP_359_cpi": None,
        "steps": [
            {
                "stage": row.get("description"),
                "pay": None,
                "da": None,
                "fitment": None,
                "notional": row.get("value"),
            }
            for row in (result.get("rows") or [])
        ],
        "note": "Class 1/2: 50% / 30% of the 2017 (277 CPI) notional basic; no 359 CPI revision.",
    }


def _class_34(separation_date, last_pay, scale, equiv_pay):
    scale_value = _normalize_scale(scale)
    if scale_value:
        scale_value = resolve_full_scale(separation_date, scale_value)
    trace = []
    with full_pay_chain(trace):
        result = _calculate_class_34(
            separation_date, last_pay, scale_value, equiv_pay_at_base_cpi=equiv_pay
        )
    if result.get("error"):
        return result
    # compute_359 rebuilds 277 internally — keep each stage once.
    steps, seen = [], set()
    for row in trace:
        if row["stage"] in seen:
            continue
        seen.add(row["stage"])
        steps.append(row)
    n277 = result.get("FP_277_cpi")
    n359 = result.get("FP_359_cpi")
    return {
        "category_group": "3/4",
        "notional_277": n277,
        "notional_359": n359,
        "EP_277_cpi": _share(n277, EP_SHARE),
        "EP_359_cpi": _share(n359, EP_SHARE),
        "FP_277_cpi": _share(n277, FP_SHARE),
        "FP_359_cpi": _share(n359, FP_SHARE),
        "calc_pay": result.get("calc_pay"),
        "pay_source": result.get("pay_source"),
        "steps": steps,
        "note": (
            "Class 3/4: Methodology-1 chain on the full last pay (no starting 30% / 607 slab); "
            "employee pension 50% and family pension 30% of the 277 / 359 CPI notional, rounded up."
        ),
    }


def calculate_m1_employee_and_family(
    separation_date, category, pay, scale=None, grade=None, equiv_pay_at_base_cpi=None
):
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
        out = _class_12(separation_date, scale, grade, last_pay)
    else:
        out = _class_34(separation_date, last_pay, scale, equiv_pay)
    if out.get("error"):
        return out
    out.update(
        {
            "separation_date": separation_date,
            "category": cat,
            "last_pay": last_pay,
            "scale_revision": get_revision_column(separation_date),
            "start_revision": get_calculation_start_revision(separation_date),
        }
    )
    return out
