"""
Arrear for an employee who already has a Methodology-2 consolidation.

Separate from the consolidation engine.

Class 3/4:
  Jan 2017–Dec 2021 → 277 CPI pension difference
  Jan 2022 onward   → 359 CPI pension difference
Class 1/2: 277 CPI difference for every month (2017 is the last CPI).

Each month uses the consolidation column that covers that month:
  pension difference and old-age difference are the stored amounts
  (old age is not worked out as a percent of the difference again)
  monthly amount  = pension difference + old-age difference
  pension arrear  = monthly amount × months
  DA relief       = DA% × monthly amount × months
The month in which enhanced family pension ends mid-month is paid by days
(actual days of that month): enhanced diff × days up to the enhanced-upto
date + family diff × remaining days, e.g. 980 × 12/30 + 588 × 18/30.
"""

from __future__ import annotations

from calendar import monthrange
from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP

from M2_oldage_arrear.services.da_service import (
    class_grp_from_category,
    lookup_da_pct,
)
ARREAR_FROM = date(2017, 1, 1)
CPI_359_FROM = date(2022, 1, 1)


def _money(value) -> float:
    return float(Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def _as_float(value):
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _month_start(year: int, month: int) -> date:
    return date(int(year), int(month), 1)


def _month_end(d: date) -> date:
    return date(d.year, d.month, monthrange(d.year, d.month)[1])


def _add_month(d: date) -> date:
    if d.month == 12:
        return date(d.year + 1, 1, 1)
    return date(d.year, d.month + 1, 1)


def _month_label(d: date) -> str:
    names = (
        "Jan", "Feb", "Mar", "Apr", "May", "Jun",
        "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
    )
    return f"{names[d.month - 1]} {d.year}"


def _is_class12(category) -> bool:
    return str(category or "").strip() in {"1", "2"}


def _comparison(obj) -> dict:
    raw = getattr(obj, "pension_comparison", None) or {}
    return raw if isinstance(raw, dict) else {}


def _as_date(value):
    from M2_oldage_arrear.services.oldage_service import _as_date as parse_date

    return parse_date(value)


def _pension_kind_on(info: dict, day: date) -> str:
    """
    Pension in force on this day.

    Employee (50%) through the date of death. Enhanced family pension (50%)
    through the enhanced-upto date. Family pension (30%) after that.
    """
    dod = _as_date(info.get("date_of_death"))
    enhanced_upto = _as_date(info.get("double_fpension_upto")) or _as_date(
        info.get("rate_cutover")
    )
    enhanced = bool(info.get("enhanced_family_pension"))
    if info.get("die_in_harness") and enhanced_upto:
        return "enhanced" if day <= enhanced_upto else "family"
    if enhanced and dod and enhanced_upto and enhanced_upto > dod:
        if day <= dod:
            return "employee"
        if day <= enhanced_upto:
            return "enhanced"
        return "family"
    if dod:
        return "employee" if day <= dod else "family"
    if enhanced and enhanced_upto:
        return "enhanced" if day <= enhanced_upto else "family"
    return "employee" if info.get("is_employee_pension") else "family"


def _column_covers(col: dict, on_date: date | None) -> bool:
    """True when the column has no dates, or on_date falls inside its period."""
    if on_date is None:
        return True
    start = _as_date(col.get("period_from"))
    end = _as_date(col.get("period_to"))
    if start is None and end is None:
        return True
    if start is not None and on_date < start:
        return False
    if end is not None and on_date > end:
        return False
    return True


def _column_for(columns, cpi: int, kind: str, on_date: date | None = None):
    same = []
    for col in columns or []:
        if not isinstance(col, dict):
            continue
        try:
            col_cpi = int(col.get("cpi") or 0)
        except (TypeError, ValueError):
            continue
        if col_cpi == cpi:
            same.append(col)
    exact = [c for c in same if c.get("kind") == kind and _column_covers(c, on_date)]
    if on_date is not None and exact:
        exact.sort(key=lambda c: _as_date(c.get("period_from")) or date.min)
        return exact[-1]
    if exact:
        return exact[0]
    # Some saved rows label the 50% enhanced period as employee.
    if kind == "enhanced":
        employee_cols = [
            c for c in same if c.get("kind") == "employee" and _column_covers(c, on_date)
        ]
        if on_date is not None and employee_cols:
            employee_cols.sort(key=lambda c: _as_date(c.get("period_from")) or date.min)
            return employee_cols[-1]
        if employee_cols:
            return employee_cols[0]
    return None


def _family_pension_diff(info: dict, cpi: int, picked):
    """
    Family-pension difference for one CPI: the family column's M2 − M1.

    CR 12-11-2026 (emp 46913): the family M1 is never worked out from the
    employee pension (it was employee × 0.6 when blank or equal). A blank
    family M1 gives None, so the arrear stops for that employee; an M1 equal
    to the employee pension is the family pension (42390) and is used as is.
    """
    from methodology2.services.consolidation_service import family_m1_problem

    m2 = _as_float(picked.get("m2")) if picked else None
    fam_m1 = _as_float(picked.get("m1")) if picked else None
    if fam_m1 is None or m2 is None:
        return None
    # Same as the employee / enhanced M1 at this CPI = copied employee pension
    # (user choice): treated as missing, not paid as a negative difference.
    if family_m1_problem(info.get("columns"), picked):
        return None
    return m2 - fam_m1


_KIND_LABEL = {
    "employee": "Employee pension",
    "enhanced": "Enhanced family pension",
    "family": "Family pension",
}


def _comparison_m1(obj, cpi: int):
    """Employee Methodology-1 from the print comparison. Not the family column."""
    comparison = getattr(obj, "pension_comparison", None) or {}
    if not isinstance(comparison, dict):
        return None
    for col in comparison.get("columns") or []:
        if not isinstance(col, dict):
            continue
        try:
            col_cpi = int(col.get("cpi") or 0)
        except (TypeError, ValueError):
            continue
        if col_cpi == cpi and col.get("m1") is not None:
            return _as_float(col.get("m1"))
    return None


def _stored_diffs(obj) -> tuple[float | None, float | None]:
    """
    Signed pension difference on the consolidation print: M2 − M1.

    A living employee uses the 50% pension and the employee Methodology-1
    on the print columns. m1_family_pension_* stays empty for that case.

    A family pensioner uses the 30% pension. The Methodology-1 family
    pension (m1_family_pension_*) is required. It is not taken from the
    employee comparison columns.
    """
    if getattr(obj, "is_employee_pension", False):
        m2_277 = _as_float(getattr(obj, "m2_pension_277", None))
        m2_359 = _as_float(getattr(obj, "m2_pension_359", None))
        m1_277 = _comparison_m1(obj, 277)
        m1_359 = _comparison_m1(obj, 359)
        # Older saves kept the employee Methodology-1 in m1_family_pension_*
        # and left the print comparison empty.
        if m1_277 is None:
            m1_277 = _as_float(getattr(obj, "m1_family_pension_277", None))
        if m1_359 is None:
            m1_359 = _as_float(getattr(obj, "m1_family_pension_359", None))
    else:
        m2_277 = _as_float(getattr(obj, "m2_family_pension_277", None))
        m2_359 = _as_float(getattr(obj, "m2_family_pension_359", None))
        m1_277 = _as_float(getattr(obj, "m1_family_pension_277", None))
        m1_359 = _as_float(getattr(obj, "m1_family_pension_359", None))
    d277 = (
        m2_277 - m1_277
        if m2_277 is not None and m1_277 is not None
        else None
    )
    d359 = (
        m2_359 - m1_359
        if m2_359 is not None and m1_359 is not None
        else None
    )
    return d277, d359


def _dob_from_obj(obj):
    from M2_oldage_arrear.services.oldage_service import _as_date

    dob = _as_date(getattr(obj, "date_of_birth", None))
    if dob:
        return dob
    comparison = getattr(obj, "pension_comparison", None) or {}
    if isinstance(comparison, dict):
        dob = _as_date(comparison.get("date_of_birth") or comparison.get("dob"))
        if dob:
            return dob
    return None


def _sheet_pension_pair(obj):
    """
    M-I and M-II behind the stored difference.

    Same sources as the difference itself. 359 is unused for class 1/2.
    """
    if getattr(obj, "is_employee_pension", False):
        m2_277 = _as_float(getattr(obj, "m2_pension_277", None))
        m2_359 = _as_float(getattr(obj, "m2_pension_359", None))
        m1_277 = _comparison_m1(obj, 277)
        m1_359 = _comparison_m1(obj, 359)
        if m1_277 is None:
            m1_277 = _as_float(getattr(obj, "m1_family_pension_277", None))
        if m1_359 is None:
            m1_359 = _as_float(getattr(obj, "m1_family_pension_359", None))
    else:
        m2_277 = _as_float(getattr(obj, "m2_family_pension_277", None))
        m2_359 = _as_float(getattr(obj, "m2_family_pension_359", None))
        m1_277 = _as_float(getattr(obj, "m1_family_pension_277", None))
        m1_359 = _as_float(getattr(obj, "m1_family_pension_359", None))
    if _is_class12(getattr(obj, "category", None)):
        m1_359 = None
        m2_359 = None
    return m1_277, m2_277, m1_359, m2_359


def _describe_consolidation(obj) -> dict:
    d277, d359 = _stored_diffs(obj)
    m1_277, m2_277, m1_359, m2_359 = _sheet_pension_pair(obj)
    cat = str(obj.category or "").strip()
    is_emp = bool(obj.is_employee_pension)
    cmp_ = _comparison(obj)
    dod = _as_date(getattr(obj, "date_of_death", None)) or _as_date(
        cmp_.get("date_of_death")
    )
    dob = _dob_from_obj(obj)
    return {
        "emp_cd": obj.emp_cd,
        "name": obj.name or "",
        "category": cat,
        "class12": _is_class12(cat),
        "is_employee_pension": is_emp,
        "has_death_split": bool(cmp_.get("has_death_split") or dod),
        "date_of_death": dod.isoformat() if dod else None,
        "double_fpension_upto": (
            _as_date(cmp_.get("double_fpension_upto")).isoformat()
            if _as_date(cmp_.get("double_fpension_upto"))
            else None
        ),
        "rate_cutover": (
            _as_date(cmp_.get("rate_cutover")).isoformat()
            if _as_date(cmp_.get("rate_cutover"))
            else None
        ),
        "enhanced_family_pension": bool(cmp_.get("enhanced_family_pension")),
        "die_in_harness": bool(cmp_.get("die_in_harness")),
        "columns": [c for c in (cmp_.get("columns") or []) if isinstance(c, dict)],
        "m1_family_277": (
            None
            if is_emp
            else _as_float(getattr(obj, "m1_family_pension_277", None))
        ),
        "m1_family_359": (
            None
            if is_emp or _is_class12(cat)
            else _as_float(getattr(obj, "m1_family_pension_359", None))
        ),
        "diff_277": d277,
        "diff_359": None if _is_class12(cat) else d359,
        "sheet_m1_277": m1_277,
        "sheet_m2_277": m2_277,
        "sheet_m1_359": m1_359,
        "sheet_m2_359": m2_359,
        "date_of_birth": dob.isoformat() if dob else None,
    }


def _oldage_summary(oa_obj) -> dict:
    """Current old-age benefit. Missing or not eligible is 0."""
    raw = getattr(oa_obj, "oldage_benefit", None) if oa_obj is not None else None
    oa = raw if isinstance(raw, dict) else {}
    percent = _as_float(oa.get("applicable_percent")) or 0.0
    amount = _as_float(oa.get("additional_pension")) or 0.0
    has = bool(oa.get("eligible")) and percent > 0
    return {
        "has_oldage_benefit": has,
        "oldage_percent": percent if has else 0.0,
        "oldage_benefit": amount if has else 0.0,
    }


def resolve_consolidation(emp_cd: str) -> dict | None:
    """
    One consolidation for arrear. No Methodology 2 / Old Age choice.

    Pension figures come from the saved consolidation. Old-age benefit is
    taken from the Old Age row when the employee has one; otherwise it is 0.
    """
    from M2_oldage_arrear.models import M2OldageArrearConsolidation
    from methodology2.models import Methodology2Consolidation

    emp = str(emp_cd or "").strip()[:5]
    if not emp:
        return None
    met2 = Methodology2Consolidation.objects.filter(emp_cd=emp).first()
    oa = M2OldageArrearConsolidation.objects.filter(emp_cd=emp).first()
    if not met2 and not oa:
        return None

    # CR 12-11-2026 (emp 46913): with both saved, use the one saved last (was
    # always Methodology-2, even when the Old Age row was re-saved later).
    def _saved_at(obj):
        return getattr(obj, "updated_at", None) or getattr(obj, "created_at", None)

    if met2 is not None and oa is not None:
        m2_at, oa_at = _saved_at(met2), _saved_at(oa)
        latest, other = (oa, met2) if (oa_at and (not m2_at or oa_at > m2_at)) else (met2, oa)
    else:
        latest, other = (met2 or oa), None
    row = _describe_consolidation(latest)
    if other is not None and not row.get("columns"):
        row = _describe_consolidation(other)
    if oa is not None:
        dob = _dob_from_obj(oa)
        if dob:
            row["date_of_birth"] = dob.isoformat()
    row.update(_oldage_summary(oa))
    return row


def _load(emp_cd: str, source: str | None = None):
    row = resolve_consolidation(emp_cd)
    if not row:
        return None, {"error": "No consolidation saved for this employee."}
    return row, None


def _cpi_for_month(month_start: date, class12: bool) -> str:
    if class12 or month_start < CPI_359_FROM:
        return "277"
    return "359"


def validate_arrear_period(from_month, from_year, to_month, to_year) -> str | None:
    """None when the window is usable. Arrear months start at January 2017."""
    try:
        start = _month_start(int(from_year), int(from_month))
        end = _month_end(_month_start(int(to_year), int(to_month)))
    except (TypeError, ValueError):
        return "Enter a from month/year and a to month/year."
    if start < ARREAR_FROM:
        return "Arrear can start from January 2017."
    if end < start:
        return "The to month is before the from month."
    return None


def _month_part(info: dict, cpi: str, kind: str, on_date: date, diff_277, diff_359) -> dict:
    """Pension and old-age difference of one pension kind in force on on_date."""
    picked = _column_for(info.get("columns"), int(cpi), kind, on_date)
    diff = _as_float(picked.get("diff")) if picked else None
    if kind == "family":
        diff = _family_pension_diff(info, int(cpi), picked)
        if diff is None:
            # CR 12-11-2026 (emp 46913): no derived family M1 — re-save asks it.
            return {
                "error": (
                    f"Family pension M1@{cpi} (30%) from {_month_label(on_date)} "
                    "is not on the consolidation, or is the same as the "
                    "employee pension. Re-save the consolidation with the "
                    "family M1."
                )
            }
    elif diff is None:
        diff = diff_277 if cpi == "277" else diff_359
    if diff is None:
        return {
            "error": (
                f"{_KIND_LABEL.get(kind, 'Pension')} difference at {cpi} CPI "
                f"is not on this consolidation for {_month_label(on_date)}."
            )
        }
    # Stored old-age difference (M2 OA − M1 OA). Not diff × age %.
    pct = (_as_float(picked.get("oldage_percent")) if picked else 0.0) or 0.0
    oa = _as_float(picked.get("oa_diff")) if picked else None
    return {"picked": picked, "diff": diff, "pct": pct, "oa": _money(oa or 0.0)}


def _part_amounts(diff, oa, weight: float) -> tuple[float, float]:
    """(pension + old-age, old-age) for a fraction of a month; 0 when the
    benefit is negative (CR 03-11-2026 not payable)."""
    if diff is None or diff < 0:
        return 0.0, 0.0
    return _money((diff + oa) * weight), _money(oa * weight)


def calculate_consolidation_arrear(
    emp_cd: str,
    from_month: int,
    from_year: int,
    to_month: int,
    to_year: int,
    source: str | None = None,
) -> dict:
    info, err = _load(emp_cd, source)
    if err:
        return err

    period_error = validate_arrear_period(from_month, from_year, to_month, to_year)
    if period_error:
        return {"error": period_error}
    start = _month_start(int(from_year), int(from_month))
    end = _month_end(_month_start(int(to_year), int(to_month)))

    class12 = info["class12"]
    diff_277 = info["diff_277"]
    diff_359 = info["diff_359"]

    from M2_oldage_arrear.services.oldage_service import _as_date

    dob = _as_date(info.get("date_of_birth"))
    class_grp = class_grp_from_category(info["category"])
    lines = []
    month_cursor = start
    last_m = date(end.year, end.month, 1)
    while month_cursor <= last_m:
        cpi = _cpi_for_month(month_cursor, class12)
        kind = _pension_kind_on(info, month_cursor)
        part = _month_part(info, cpi, kind, month_cursor, diff_277, diff_359)
        if part.get("error"):
            return part
        picked = part["picked"]
        diff = part["diff"]
        pct = part["pct"]
        oa = part["oa"]
        monthly = _money(diff + oa)
        # CR 12-11-2026 (emp 45936): enhanced up to 12-09-2026 paid the whole of
        # September at the enhanced rate. Split that month by days instead.
        weight = 1.0
        family_part = None
        month_last = _month_end(month_cursor)
        if kind == "enhanced" and _pension_kind_on(info, month_last) == "family":
            enhanced_upto = _as_date(info.get("double_fpension_upto")) or _as_date(
                info.get("rate_cutover")
            )
            if enhanced_upto and month_cursor <= enhanced_upto < month_last:
                weight = enhanced_upto.day / month_last.day
                family_day = enhanced_upto + timedelta(days=1)
                family_part = _month_part(
                    info, cpi, "family", family_day, diff_277, diff_359
                )
                if family_part.get("error"):
                    return family_part
        month_pen, month_oa = _part_amounts(diff, oa, weight)
        if family_part:
            fam_pen, fam_oa = _part_amounts(
                family_part["diff"], family_part["oa"], 1.0 - weight
            )
            month_pen = _money(month_pen + fam_pen)
            month_oa = _money(month_oa + fam_oa)
        da_pct = lookup_da_pct(class_grp, cpi, month_cursor)
        diff_r = _money(diff)
        m2_raw = _as_float(picked.get("m2")) if picked else None
        if m2_raw is not None:
            m2_r = _money(m2_raw)
            m1_r = _money(m2_raw - diff)
        elif kind != "family":
            if cpi == "277":
                m1_r = info.get("sheet_m1_277")
                m2_r = info.get("sheet_m2_277")
            else:
                m1_r = info.get("sheet_m1_359")
                m2_r = info.get("sheet_m2_359")
            m1_r = _money(m1_r) if m1_r is not None else None
            m2_r = _money(m2_r) if m2_r is not None else None
        else:
            m1_r = None
            m2_r = None
        bucket = {
            "cpi": cpi,
            "pension_kind": kind,
            "pension_label": _KIND_LABEL.get(kind, kind),
            "pension_diff": diff_r,
            "m1": m1_r,
            "m2": m2_r,
            "oldage_percent": pct,
            "oldage_benefit": oa,
            "monthly_amount": monthly,
            "da_pct": da_pct,
            "from": month_cursor,
        }
        month_entry = {"month": month_cursor.isoformat(), "amount": month_pen, "oa": month_oa}
        if (
            lines
            and _same_rate(lines[-1], bucket)
            and _next_month(lines[-1]["to"]) == month_cursor
        ):
            lines[-1]["to"] = month_cursor
            lines[-1]["months"] += 1
            lines[-1]["pen_sum"] = _money(lines[-1]["pen_sum"] + month_pen)
            lines[-1]["oa_sum"] = _money(lines[-1]["oa_sum"] + month_oa)
            lines[-1]["month_amounts"].append(month_entry)
        else:
            bucket["to"] = month_cursor
            bucket["months"] = 1
            bucket["pen_sum"] = month_pen
            bucket["oa_sum"] = month_oa
            bucket["month_amounts"] = [month_entry]
            lines.append(bucket)
        month_cursor = _add_month(month_cursor)

    pension_arrear = 0.0
    da_relief = 0.0
    out_lines = []
    for line in lines:
        months = line["months"]
        # CR 03-11-2026: M-I above M-II (negative benefit) is not paid — old-age,
        # basic + old-age, DA, months and total are 0 for those months. The
        # negative difference itself is still shown.
        if line["pension_diff"] is not None and line["pension_diff"] < 0:
            line["oldage_benefit"] = 0.0
            line["monthly_amount"] = 0.0
            line["not_payable"] = True
            months = 0
        # CR 12-11-2026: amounts are summed month by month (pen_sum) so a
        # day-split change-over month is paid by days; full months are
        # monthly amount × 1 as before, negative parts are 0.
        pen = _money(line["pen_sum"])
        da = _money(pen * line["da_pct"] / 100.0)
        total = _money(pen + da)
        pension_arrear = _money(pension_arrear + pen)
        da_relief = _money(da_relief + da)
        out_lines.append(
            {
                "from_label": _month_label(line["from"]),
                "to_label": _month_label(line["to"]),
                "from_iso": line["from"].isoformat(),
                "to_iso": line["to"].isoformat(),
                "months": months,
                "cpi": line["cpi"],
                "pension_kind": line["pension_kind"],
                "pension_label": line["pension_label"],
                "pension_diff": line["pension_diff"],
                "m1": line.get("m1"),
                "m2": line.get("m2"),
                "oldage_percent": line["oldage_percent"],
                "oldage_benefit": line["oldage_benefit"],
                "monthly_amount": line["monthly_amount"],
                "da_pct": line["da_pct"],
                "pension_arrear": pen,
                "da_relief": da,
                "total": total,
                "not_payable": bool(line.get("not_payable")),
                # CR 12-11-2026: old-age paid in this line and per-month amounts
                # (a day-split month is not old-age × months).
                "oldage_arrear": _money(line["oa_sum"]),
                "month_amounts": line["month_amounts"],
            }
        )

    return {
        "emp_cd": info["emp_cd"],
        "name": info["name"],
        "category": info["category"],
        "class12": class12,
        "has_death_split": bool(info.get("has_death_split")),
        "date_of_death": info.get("date_of_death"),
        "diff_277": diff_277,
        "diff_359": diff_359,
        "date_of_birth": info.get("date_of_birth"),
        "dob_missing": dob is None,
        "from_label": _month_label(start),
        "to_label": _month_label(date(end.year, end.month, 1)),
        "lines": out_lines,
        "pension_arrear": pension_arrear,
        "da_relief": da_relief,
        "total": _money(pension_arrear + da_relief),
    }


def _same_rate(prev: dict, nxt: dict) -> bool:
    return (
        prev["cpi"] == nxt["cpi"]
        and prev["pension_kind"] == nxt["pension_kind"]
        and prev["pension_diff"] == nxt["pension_diff"]
        and prev["oldage_percent"] == nxt["oldage_percent"]
        and prev["oldage_benefit"] == nxt["oldage_benefit"]
        and prev["da_pct"] == nxt["da_pct"]
    )


def _next_month(d: date) -> date:
    return _add_month(d)
