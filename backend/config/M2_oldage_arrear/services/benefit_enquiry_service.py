"""
Old-age benefit enquiry: Emp + From/To month-year → calculate + month-wise save.

Tables:
  m2_oa_th_oldage_benefit     — header (fi_pn_th_* style)
  m2_oa_td_oldage_benefit_mth — one row per bill month (pens_cal_* style)
"""

from __future__ import annotations

import calendar
from datetime import date
from decimal import Decimal, InvalidOperation

from django.db import transaction
from django.utils import timezone

from M2_oldage_arrear.models import (
    M2OaTdOldageBenefitMth,
    M2OaThOldageBenefit,
    M2OldageArrearConsolidation,
)
from M2_oldage_arrear.services.oldage_service import (
    _as_date,
    compute_oldage_benefit,
)

MONTH_ABBR = (
    "",
    "JAN",
    "FEB",
    "MAR",
    "APR",
    "MAY",
    "JUN",
    "JUL",
    "AUG",
    "SEP",
    "OCT",
    "NOV",
    "DEC",
)


def _as_decimal(value):
    if value is None or value == "":
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return None


def _money(value):
    d = _as_decimal(value)
    return float(d) if d is not None else None


def month_start(year: int, month: int) -> date:
    return date(int(year), int(month), 1)


def month_end(year: int, month: int) -> date:
    last = calendar.monthrange(int(year), int(month))[1]
    return date(int(year), int(month), last)


def parse_month_year(month, year, *, field: str) -> tuple[int, int]:
    try:
        y = int(year)
        m = int(month)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field} month/year must be numbers") from exc
    if m < 1 or m > 12:
        raise ValueError(f"{field} month must be 1–12")
    if y < 1900 or y > 2100:
        raise ValueError(f"{field} year out of range")
    return m, y


def iter_months(from_start: date, to_end: date):
    y, m = from_start.year, from_start.month
    while (y, m) <= (to_end.year, to_end.month):
        yield y, m
        if m == 12:
            y, m = y + 1, 1
        else:
            m += 1


def expand_periods_to_months(
    periods: list[dict],
    *,
    from_start: date,
    to_end: date,
    m1_277=None,
    m1_359=None,
    m2_277=None,
    m2_359=None,
) -> list[dict]:
    """Expand engine periods into one row per calendar month in From–To."""
    m1_277 = _as_decimal(m1_277)
    m1_359 = _as_decimal(m1_359)
    m2_277 = _as_decimal(m2_277)
    m2_359 = _as_decimal(m2_359)

    by_month: dict[tuple[int, int], dict] = {}
    for p in periods or []:
        if not isinstance(p, dict):
            continue
        p_from = _as_date(p.get("period_from"))
        p_to = _as_date(p.get("period_to"))
        if not p_from or not p_to:
            continue
        clip_from = max(p_from, from_start)
        clip_to = min(p_to, to_end)
        if clip_from > clip_to:
            continue
        cpi = p.get("cpi_period")
        try:
            cpi_point = int(cpi) if cpi is not None else None
        except (TypeError, ValueError):
            cpi_point = None
        if cpi_point == 277:
            m1_amt, m2_amt = m1_277, m2_277
        else:
            m1_amt, m2_amt = m1_359, m2_359
        for y, m in iter_months(clip_from, clip_to):
            ms = month_start(y, m)
            me = month_end(y, m)
            if me < clip_from or ms > clip_to:
                continue
            by_month[(y, m)] = {
                "bill_year": y,
                "bill_month": m,
                "bill_mth": MONTH_ABBR[m],
                "month_start": ms,
                "month_end": me,
                "cpi_point": cpi_point,
                "oa_percent": _as_decimal(p.get("percent")),
                "age_slab": p.get("age_slab"),
                "m1_pension": m1_amt,
                "m2_pension": m2_amt,
                "benefit_base": _as_decimal(p.get("benefit_base")),
                "oa_basic": _as_decimal(p.get("monthly_additional")),
                "da_pct": _as_decimal(p.get("da_pct")),
                "oa_da": _as_decimal(p.get("monthly_da")),
                "month_total": _as_decimal(p.get("monthly_total")),
            }

    rows = [by_month[k] for k in sorted(by_month.keys())]
    return rows


def _filter_periods(
    periods: list,
    from_start: date,
    to_end: date,
    *,
    m1_277=None,
    m1_359=None,
    m2_277=None,
    m2_359=None,
) -> list[dict]:
    out = []
    m1_277 = _as_decimal(m1_277)
    m1_359 = _as_decimal(m1_359)
    m2_277 = _as_decimal(m2_277)
    m2_359 = _as_decimal(m2_359)
    for p in periods or []:
        if not isinstance(p, dict):
            continue
        p_from = _as_date(p.get("period_from"))
        p_to = _as_date(p.get("period_to"))
        if not p_from or not p_to:
            continue
        if p_to < from_start or p_from > to_end:
            continue
        clip_from = max(p_from, from_start)
        clip_to = min(p_to, to_end)
        row = dict(p)
        row["period_from"] = clip_from.isoformat()
        row["period_to"] = clip_to.isoformat()
        cpi = str(p.get("cpi_period") or "")
        if cpi == "277":
            row["m1_pension"] = _money(m1_277)
            row["m2_pension"] = _money(m2_277)
        else:
            row["m1_pension"] = _money(m1_359)
            row["m2_pension"] = _money(m2_359)
        # Recompute months / arrears for clipped window.
        from M2_oldage_arrear.services.oldage_service import months_inclusive

        months = months_inclusive(clip_from, clip_to)
        row["months"] = months
        monthly = _as_decimal(p.get("monthly_additional"))
        monthly_da = _as_decimal(p.get("monthly_da")) or Decimal("0")
        if monthly is not None:
            basic = (monthly * Decimal(months)).quantize(Decimal("0.01"))
            da = (monthly_da * Decimal(months)).quantize(Decimal("0.01"))
            row["period_arrear_basic"] = float(basic)
            row["period_arrear_da"] = float(da)
            row["period_arrear"] = float(basic + da)
        out.append(row)
    return out


def resolve_bases_from_snapshots(emp_cd: str) -> dict:
    """Prefer OA consolidation snapshot, else Met2 consolidation."""
    emp = str(emp_cd or "").strip()[:5]
    out = {
        "name": "",
        "roll_no": "",
        "case_no": "",
        "category": "",
        "dob": None,
        "family_dob": None,
        "is_employee_pension": True,
        "m1_277": None,
        "m1_359": None,
        "m2_277": None,
        "m2_359": None,
        "source": None,
    }
    if not emp:
        return out

    oa = M2OldageArrearConsolidation.objects.filter(emp_cd=emp).first()
    if oa:
        is_emp = bool(oa.is_employee_pension)
        out.update(
            {
                "name": oa.name or oa.wage_emp_name or oa.pensioner_name or "",
                "roll_no": oa.roll_no or "",
                "case_no": oa.case_no or "",
                "category": oa.category or "",
                "dob": oa.date_of_birth,
                "family_dob": (oa.pension_comparison or {}).get("family_pensioner_dob")
                if isinstance(oa.pension_comparison, dict)
                else None,
                "is_employee_pension": is_emp,
                "m1_277": oa.m1_family_pension_277,
                "m1_359": oa.m1_family_pension_359,
                "m2_277": oa.m2_pension_277 if is_emp else oa.m2_family_pension_277,
                "m2_359": oa.m2_pension_359 if is_emp else oa.m2_family_pension_359,
                "source": "m2_oldage_arrear_consolidation",
            }
        )
        return out

    try:
        from methodology2.models import Methodology2Consolidation

        m2 = Methodology2Consolidation.objects.filter(emp_cd=emp).first()
    except Exception:
        m2 = None
    if m2:
        is_emp = bool(m2.is_employee_pension)
        out.update(
            {
                "name": m2.name or m2.wage_emp_name or m2.pensioner_name or "",
                "roll_no": m2.roll_no or "",
                "case_no": m2.case_no or "",
                "category": m2.category or "",
                "dob": None,
                "family_dob": (m2.pension_comparison or {}).get("family_pensioner_dob")
                if isinstance(getattr(m2, "pension_comparison", None), dict)
                else None,
                "is_employee_pension": is_emp,
                "m1_277": m2.m1_family_pension_277,
                "m1_359": m2.m1_family_pension_359,
                "m2_277": m2.m2_pension_277 if is_emp else m2.m2_family_pension_277,
                "m2_359": m2.m2_pension_359 if is_emp else m2.m2_family_pension_359,
                "source": "methodology2_consolidation",
            }
        )
    return out


def run_oldage_benefit_enquiry(
    *,
    emp_cd: str,
    from_month: int,
    from_year: int,
    to_month: int,
    to_year: int,
    dob=None,
    category=None,
    m1_277=None,
    m1_359=None,
    m2_277=None,
    m2_359=None,
    is_employee_pension=None,
    name: str = "",
    roll_no: str = "",
    case_no: str = "",
) -> dict:
    emp = str(emp_cd or "").strip()[:5]
    if not emp:
        return {"error": "emp_cd is required"}

    fm, fy = parse_month_year(from_month, from_year, field="from")
    tm, ty = parse_month_year(to_month, to_year, field="to")
    from_start = month_start(fy, fm)
    to_end = month_end(ty, tm)
    if from_start > to_end:
        return {"error": "From month/year cannot be after To month/year"}

    bases = resolve_bases_from_snapshots(emp)
    is_emp = (
        bool(is_employee_pension)
        if is_employee_pension is not None
        else bool(bases.get("is_employee_pension", True))
    )
    if not is_emp:
        dob_d = _as_date(bases.get("family_dob"))
        if dob_d is None:
            from methodology2.services.consolidation_service import (
                fetch_family_pensioner_dob,
            )

            dob_d = fetch_family_pensioner_dob(emp)
    else:
        dob_d = _as_date(dob) or _as_date(bases.get("dob"))
        if dob_d is None:
            from M2_oldage_arrear.services.consolidation_bridge import fetch_employee_dob

            dob_d = fetch_employee_dob(emp)

    m1_277 = _as_decimal(m1_277 if m1_277 is not None else bases.get("m1_277"))
    m1_359 = _as_decimal(m1_359 if m1_359 is not None else bases.get("m1_359"))
    m2_277 = _as_decimal(m2_277 if m2_277 is not None else bases.get("m2_277"))
    m2_359 = _as_decimal(m2_359 if m2_359 is not None else bases.get("m2_359"))
    cat = category or bases.get("category") or ""

    if not dob_d:
        return {
            "error": (
                "Family pensioner date of birth not found"
                if not is_emp
                else "Date of birth not found for employee"
            )
        }
    if m2_277 is None and m2_359 is None:
        return {
            "error": (
                "Met2 pension amounts not found. "
                "Save OA/Met2 consolidation for this emp first, or pass pension amounts."
            )
        }

    result = compute_oldage_benefit(
        dob=dob_d,
        as_on_date=to_end,
        horizon_end=to_end,
        pension_277=m2_277,
        pension_359=m2_359,
        m1_pension_277=m1_277,
        m1_pension_359=m1_359,
        category=cat,
    )
    if result.get("error") and not result.get("dob"):
        return result

    periods = _filter_periods(
        result.get("periods") or [],
        from_start,
        to_end,
        m1_277=m1_277,
        m1_359=m1_359,
        m2_277=m2_277,
        m2_359=m2_359,
    )
    months = expand_periods_to_months(
        result.get("periods") or [],
        from_start=from_start,
        to_end=to_end,
        m1_277=m1_277,
        m1_359=m1_359,
        m2_277=m2_277,
        m2_359=m2_359,
    )

    total_basic = Decimal("0")
    total_da = Decimal("0")
    for r in months:
        if r.get("oa_basic") is not None:
            total_basic += r["oa_basic"]
        if r.get("oa_da") is not None:
            total_da += r["oa_da"]
    total = total_basic + total_da

    result["periods"] = periods
    result["months"] = [
        {
            **{
                k: (float(v) if isinstance(v, Decimal) else v)
                for k, v in row.items()
                if k
                not in (
                    "month_start",
                    "month_end",
                    "oa_percent",
                    "benefit_base",
                    "m1_pension",
                    "m2_pension",
                    "oa_basic",
                    "da_pct",
                    "oa_da",
                    "month_total",
                )
            },
            "month_start": row["month_start"].isoformat(),
            "month_end": row["month_end"].isoformat(),
            "oa_percent": _money(row.get("oa_percent")),
            "m1_pension": _money(row.get("m1_pension")),
            "m2_pension": _money(row.get("m2_pension")),
            "benefit_base": _money(row.get("benefit_base")),
            "oa_basic": _money(row.get("oa_basic")),
            "da_pct": _money(row.get("da_pct")),
            "oa_da": _money(row.get("oa_da")),
            "month_total": _money(row.get("month_total")),
        }
        for row in months
    ]
    result["total_arrear_basic"] = float(total_basic.quantize(Decimal("0.01")))
    result["total_arrear_da"] = float(total_da.quantize(Decimal("0.01")))
    result["total_arrear"] = float(total.quantize(Decimal("0.01")))
    result["from_month"] = fm
    result["from_year"] = fy
    result["to_month"] = tm
    result["to_year"] = ty
    result["from_date"] = from_start.isoformat()
    result["to_date"] = to_end.isoformat()
    result["emp_cd"] = emp
    result["name"] = name or bases.get("name") or ""
    result["roll_no"] = roll_no or bases.get("roll_no") or ""
    result["case_no"] = case_no or bases.get("case_no") or ""
    result["category"] = cat
    result["is_employee_pension"] = is_emp
    result["bases_source"] = bases.get("source")
    result["m1_pension_277"] = _money(m1_277)
    result["m1_pension_359"] = _money(m1_359)
    result["m2_pension_277"] = _money(m2_277)
    result["m2_pension_359"] = _money(m2_359)
    return result


@transaction.atomic
def save_oldage_benefit_enquiry(payload: dict, *, user: str = "") -> dict:
    """Upsert header + replace month rows for Emp + From–To range."""
    if payload.get("error"):
        return payload

    emp = str(payload.get("emp_cd") or "").strip()[:5]
    fm = int(payload["from_month"])
    fy = int(payload["from_year"])
    tm = int(payload["to_month"])
    ty = int(payload["to_year"])

    hdr, created = M2OaThOldageBenefit.objects.select_for_update().get_or_create(
        emp_cd=emp,
        from_year=fy,
        from_month=fm,
        to_year=ty,
        to_month=tm,
        defaults={"version_no": 1},
    )
    if not created:
        hdr.version_no = (hdr.version_no or 1) + 1

    hdr.name = str(payload.get("name") or "")[:200]
    hdr.roll_no = str(payload.get("roll_no") or "")[:30]
    hdr.case_no = str(payload.get("case_no") or "")[:20]
    hdr.category = str(payload.get("category") or "")[:20]
    hdr.is_employee_pension = bool(payload.get("is_employee_pension", True))
    hdr.dob = _as_date(payload.get("dob") or payload.get("date_of_birth"))
    hdr.as_on_date = _as_date(payload.get("as_on_date") or payload.get("to_date"))
    hdr.m1_pension_277 = _as_decimal(payload.get("m1_pension_277"))
    hdr.m2_pension_277 = _as_decimal(payload.get("m2_pension_277"))
    hdr.m1_pension_359 = _as_decimal(payload.get("m1_pension_359"))
    hdr.m2_pension_359 = _as_decimal(payload.get("m2_pension_359"))
    hdr.benefit_277 = _as_decimal(payload.get("benefit_277"))
    hdr.benefit_359 = _as_decimal(payload.get("benefit_359"))
    hdr.age_completed = payload.get("age_completed")
    hdr.applicable_percent = _as_decimal(payload.get("applicable_percent"))
    hdr.additional_pension = _as_decimal(payload.get("additional_pension"))
    hdr.monthly_da = _as_decimal(payload.get("monthly_da"))
    hdr.monthly_total = _as_decimal(payload.get("monthly_total"))
    hdr.da_pct = _as_decimal(payload.get("da_pct"))
    hdr.total_arrear = _as_decimal(payload.get("total_arrear"))
    hdr.total_arrear_basic = _as_decimal(payload.get("total_arrear_basic"))
    hdr.total_arrear_da = _as_decimal(payload.get("total_arrear_da"))
    hdr.calculated_at = timezone.now()
    hdr.calculated_by = (user or "")[:80]
    hdr.payload_json = {
        "periods": payload.get("periods") or [],
        "slabs": payload.get("slabs") or [],
        "milestones": payload.get("milestones") or [],
        "note": payload.get("note") or "",
        "bases_source": payload.get("bases_source"),
    }
    hdr.save()

    hdr.months.all().delete()
    month_rows = []
    for row in payload.get("months") or []:
        by = int(row["bill_year"])
        bm = int(row["bill_month"])
        month_rows.append(
            M2OaTdOldageBenefitMth(
                hdr=hdr,
                emp_cd=emp,
                bill_year=by,
                bill_month=bm,
                bill_mth=str(row.get("bill_mth") or MONTH_ABBR[bm])[:3],
                month_start=_as_date(row.get("month_start")) or month_start(by, bm),
                month_end=_as_date(row.get("month_end")) or month_end(by, bm),
                cpi_point=row.get("cpi_point"),
                oa_percent=_as_decimal(row.get("oa_percent")),
                age_slab=row.get("age_slab"),
                benefit_base=_as_decimal(row.get("benefit_base")),
                m1_pension=_as_decimal(row.get("m1_pension")),
                m2_pension=_as_decimal(row.get("m2_pension")),
                oa_basic=_as_decimal(row.get("oa_basic")),
                da_pct=_as_decimal(row.get("da_pct")),
                oa_da=_as_decimal(row.get("oa_da")),
                month_total=_as_decimal(row.get("month_total")),
            )
        )
    if month_rows:
        M2OaTdOldageBenefitMth.objects.bulk_create(month_rows)

    payload["hdr_id"] = hdr.id
    payload["version_no"] = hdr.version_no
    payload["saved"] = True
    payload["month_count"] = len(month_rows)
    return payload


def load_oldage_benefit_enquiry(
    emp_cd: str,
    from_month: int,
    from_year: int,
    to_month: int,
    to_year: int,
) -> dict | None:
    emp = str(emp_cd or "").strip()[:5]
    fm, fy = parse_month_year(from_month, from_year, field="from")
    tm, ty = parse_month_year(to_month, to_year, field="to")
    hdr = (
        M2OaThOldageBenefit.objects.filter(
            emp_cd=emp,
            from_year=fy,
            from_month=fm,
            to_year=ty,
            to_month=tm,
        )
        .prefetch_related("months")
        .first()
    )
    if not hdr:
        return None

    months = []
    for row in hdr.months.all():
        months.append(
            {
                "bill_year": row.bill_year,
                "bill_month": row.bill_month,
                "bill_mth": row.bill_mth,
                "month_start": row.month_start.isoformat() if row.month_start else None,
                "month_end": row.month_end.isoformat() if row.month_end else None,
                "cpi_point": row.cpi_point,
                "oa_percent": _money(row.oa_percent),
                "age_slab": row.age_slab,
                "benefit_base": _money(row.benefit_base),
                "m1_pension": _money(row.m1_pension),
                "m2_pension": _money(row.m2_pension),
                "oa_basic": _money(row.oa_basic),
                "da_pct": _money(row.da_pct),
                "oa_da": _money(row.oa_da),
                "month_total": _money(row.month_total),
            }
        )

    payload = dict(hdr.payload_json or {})
    return {
        **payload,
        "hdr_id": hdr.id,
        "emp_cd": hdr.emp_cd,
        "name": hdr.name,
        "roll_no": hdr.roll_no,
        "case_no": hdr.case_no,
        "category": hdr.category,
        "is_employee_pension": hdr.is_employee_pension,
        "dob": hdr.dob.isoformat() if hdr.dob else None,
        "date_of_birth": hdr.dob.isoformat() if hdr.dob else None,
        "as_on_date": hdr.as_on_date.isoformat() if hdr.as_on_date else None,
        "from_month": hdr.from_month,
        "from_year": hdr.from_year,
        "to_month": hdr.to_month,
        "to_year": hdr.to_year,
        "m1_pension_277": _money(hdr.m1_pension_277),
        "m2_pension_277": _money(hdr.m2_pension_277),
        "m1_pension_359": _money(hdr.m1_pension_359),
        "m2_pension_359": _money(hdr.m2_pension_359),
        "benefit_277": _money(hdr.benefit_277),
        "benefit_359": _money(hdr.benefit_359),
        "age_completed": hdr.age_completed,
        "applicable_percent": _money(hdr.applicable_percent),
        "additional_pension": _money(hdr.additional_pension),
        "monthly_da": _money(hdr.monthly_da),
        "monthly_total": _money(hdr.monthly_total),
        "da_pct": _money(hdr.da_pct),
        "total_arrear": _money(hdr.total_arrear),
        "total_arrear_basic": _money(hdr.total_arrear_basic),
        "total_arrear_da": _money(hdr.total_arrear_da),
        "version_no": hdr.version_no,
        "months": months,
        "saved": True,
    }
