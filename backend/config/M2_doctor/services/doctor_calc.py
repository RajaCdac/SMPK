"""
Doctor Methodology-2: last pay = basic + NPA, shown separately at every step.

Basic and NPA each go through the same DA % and fitment %. On a notional pay
line, Pay and NPA stay in decimals and only the Total (Pay + NPA) is rounded
up to the next 10; the next stage continues from the decimal Pay and NPA.
M2 pension (50% / 30%) is on the rounded Total at 277 CPI.

Only class 1/2 from the 1997 scale onward has percentage-only steps. Earlier
class 1/2 stages (fixed DA, fit into scale) and class 3/4 (pay matrix) cannot
be applied to NPA alone, so those are calculated on the combined pay.
"""

from methodology2.services.class1_2_service import (
    _get_scale_row,
    calculate_class12,
    format_class12_scale_display,
    get_class12_equivalent_scales,
    get_class12_start_revision,
    SCALE_COLUMNS,
)
from methodology2.services.proportionate_pension import apply_proportionate_pension
from methodology2.services.rounding_helpers import round2, round_up_to_10

SPLIT_START_REVISIONS = ("1997", "2007", "2017")

# Same rates and labels as _block_2007 / _block_2017 in class1_2_service.
STAGES = {
    "2007": (
        0.782,
        0.30,
        "DA @ 78.2% on Basic",
        "Fitment @ 30% on (Basic+DA)",
        "Basic Pay Over 126 CPI Points (01.01.2007) (Rounded to the next 10 Rupees)",
    ),
    "2017": (
        1.198,
        0.15,
        "DA @ 119.8% on Basic",
        "Fitment @ 15% on (Basic+DA)",
        "Basic Pay Over 277 CPI Points (01.01.2017) (Rounded to the next 10 Rupees)",
    ),
}
STAGES_AFTER = {"1997": ("2007", "2017"), "2007": ("2017",), "2017": ()}

NO_SPLIT_NOTE = (
    "Pay and NPA cannot be shown separately for this case (retired before the "
    "1997 scale, or class 3/4). Calculated on basic + NPA together."
)


def _number(value, *, allow_zero=False):
    try:
        out = float(value)
    except (TypeError, ValueError):
        return None
    if out < 0 or (out == 0 and not allow_zero):
        return None
    return out


def _line(description, pay, npa, total=None):
    return {
        "description": description,
        "pay": pay,
        "npa": npa,
        "value": round2(pay + npa) if total is None else total,
    }


def _split_chain(start, basic, npa):
    """
    Rows from the start scale to 01.01.2017 with Pay | NPA | Total.

    Returns (rows, pay_2017, npa_2017, total_2017).
    """
    rows = [_line(
        f"Basic Pay in the existing scale ({start} revised pay scale)", basic, npa
    )]
    pay, npa_amt, total = basic, npa, round2(basic + npa)
    for key in STAGES_AFTER[start]:
        da_rate, fit_rate, da_label, fit_label, basic_label = STAGES[key]
        pay_da, npa_da = round2(pay * da_rate), round2(npa_amt * da_rate)
        pay_fit = round2((pay + pay_da) * fit_rate)
        npa_fit = round2((npa_amt + npa_da) * fit_rate)
        pay = round2(pay + pay_da + pay_fit)
        npa_amt = round2(npa_amt + npa_da + npa_fit)
        total = round_up_to_10(pay + npa_amt)
        rows.append(_line(da_label, pay_da, npa_da))
        rows.append(_line(fit_label, pay_fit, npa_fit))
        rows.append(_line(basic_label, pay, npa_amt, total))
    rows.append(_line("Basic Pay as on 01.01.2017", pay, npa_amt, total))
    return rows, pay, npa_amt, total


def calculate_doctor_class12(
    separation_date,
    grade,
    basic,
    npa,
    *,
    tqs_yr=None,
    tqs_month=None,
    tqs_days=None,
):
    basic = _number(basic)
    npa = _number(npa, allow_zero=True) or 0.0
    if basic is None:
        return {"error": "Basic pay must be a positive number"}
    scale_row = _get_scale_row(grade)
    if scale_row is None:
        return {"error": f"Scale '{grade}' not found in class 1/2 pay scales"}

    start = get_class12_start_revision(separation_date)
    if start not in SPLIT_START_REVISIONS:
        result = calculate_class12(
            separation_date,
            grade,
            basic + npa,
            tqs_yr=tqs_yr,
            tqs_month=tqs_month,
            tqs_days=tqs_days,
        )
        if not result.get("error"):
            result.update(npa_split=False, note=NO_SPLIT_NOTE)
        return result

    rows, pay_2017, npa_2017, basic_2017 = _split_chain(start, basic, npa)

    pension_payload = apply_proportionate_pension(
        {
            "basic_pay_2017": basic_2017,
            "basic_pay_2022": None,
            "pension_277_cpi": round2(basic_2017 / 2),
            "pension_359_cpi": None,
            "family_pension_277_cpi": round2(basic_2017 * 0.30),
            "family_pension_359_cpi": None,
            "pension": round2(basic_2017 / 2),
            "family_pension": round2(basic_2017 * 0.30),
        },
        retirement_date=separation_date,
        tqs_yr=tqs_yr,
        tqs_month=tqs_month,
        tqs_days=tqs_days,
    )

    start_scale = scale_row.get(SCALE_COLUMNS[start])
    scale_at_separation = (
        str(start_scale).strip()
        if start_scale is not None and str(start_scale) != "nan"
        else ""
    )
    return {
        "start_revision": start,
        "grade": str(grade),
        "scale_at_separation": scale_at_separation,
        "scale_display": format_class12_scale_display(scale_at_separation),
        "equivalent_scales": get_class12_equivalent_scales(grade),
        "rows": rows,
        "basic_pay_2017": basic_2017,
        "pay_2017": pay_2017,
        "npa_2017": npa_2017,
        "pension": pension_payload.get("pension"),
        "family_pension": pension_payload.get("family_pension"),
        "proportionate": pension_payload.get("proportionate"),
        "npa_split": True,
    }


def calculate_doctor_class34(
    retirement_date,
    scale,
    basic,
    npa,
    *,
    sda=0,
    tqs_yr=None,
    tqs_month=None,
    tqs_days=None,
):
    """Class 3/4: pay matrix steps — combined pay, as before."""
    from methodology2.services.calculation_service import calculate_revision
    from methodology2.services.revision_resolver import get_revision_column
    from methodology2.services.scale_service import get_equivalent_scales_by_scale

    basic = _number(basic)
    npa = _number(npa, allow_zero=True) or 0.0
    if basic is None:
        return {"error": "Basic pay must be a positive number"}
    scales = get_equivalent_scales_by_scale(retirement_date, scale)
    current_revision = get_revision_column(retirement_date)
    result = calculate_revision(
        scales,
        current_revision,
        basic + npa,
        _number(sda, allow_zero=True) or 0,
        retirement_date=retirement_date,
        tqs_yr=tqs_yr,
        tqs_month=tqs_month,
        tqs_days=tqs_days,
    )
    return {
        "rows": result.get("rows", []),
        "pension": result.get("pension", {}),
        "start_revision": current_revision,
        "equivalent_scales": scales,
        "npa_split": False,
        "note": NO_SPLIT_NOTE,
    }
