"""Consolidation dashboard: analytics + date-filtered row list.

Also: mark payment done, delete emp consolidation from m2* tables only
(never touches fi_* / Oracle wage masters).
"""

from __future__ import annotations

from datetime import date, datetime, time, timedelta
from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from M2_oldage_arrear.models import M2OldageArrearConsolidation
from methodology2.models import (
    M2ConsolCase,
    M2ConsolReleaseLog,
    Methodology2Consolidation,
)


def _parse_date(value: str | None, field: str) -> date | None:
    text = str(value or "").strip()[:10]
    if not text:
        return None
    try:
        return datetime.strptime(text, "%Y-%m-%d").date()
    except ValueError as exc:
        raise ValueError(f"{field} must be YYYY-MM-DD") from exc


def _money(value) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(Decimal(str(value)))
    except Exception:
        return None


def _local_today() -> date:
    return timezone.localdate()


def _day_bounds(d: date):
    start = timezone.make_aware(datetime.combine(d, time.min))
    end = timezone.make_aware(datetime.combine(d, time.max))
    return start, end


def _range_bounds(from_d: date | None, to_d: date | None):
    start = (
        timezone.make_aware(datetime.combine(from_d, time.min)) if from_d else None
    )
    end = timezone.make_aware(datetime.combine(to_d, time.max)) if to_d else None
    return start, end


def _category_bucket(category) -> str:
    c = str(category or "").strip()
    if c in ("1", "2"):
        return "12"
    if c in ("3", "4"):
        return "34"
    return "other"


def _matches_category(category, category_filter: str) -> bool:
    cat = str(category_filter or "all").strip().lower()
    if cat in ("", "all"):
        return True
    bucket = _category_bucket(category)
    if cat == "12":
        return bucket == "12"
    if cat == "34":
        return bucket == "34"
    return True


def _oa_benefits_from_obj(obj) -> tuple[float | None, float | None]:
    """
    Old-age benefit @277 / @359 from pension_comparison columns (print values).
    Falls back to oldage_benefit JSON when columns are absent.
    """
    oa_277 = None
    oa_359 = None
    comparison = getattr(obj, "pension_comparison", None) or {}
    if isinstance(comparison, dict):
        for col in comparison.get("columns") or []:
            if not isinstance(col, dict):
                continue
            cpi = col.get("cpi")
            if cpi is None:
                key = str(col.get("key") or "")
                if key.startswith("277"):
                    cpi = 277
                elif key.startswith("359"):
                    cpi = 359
            try:
                cpi_i = int(cpi)
            except (TypeError, ValueError):
                continue
            val = col.get("oa_benefit")
            if val is None and col.get("oldage_addl") is not None:
                val = col.get("oldage_addl")
            money = _money(val)
            if money is None:
                continue
            if cpi_i == 277:
                oa_277 = money
            elif cpi_i == 359:
                oa_359 = money

    ob = getattr(obj, "oldage_benefit", None) or {}
    if isinstance(ob, dict):
        addl = _money(ob.get("additional_pension"))
        applicable = ob.get("applicable_cpi")
        try:
            applicable_i = int(applicable) if applicable is not None else None
        except (TypeError, ValueError):
            applicable_i = None
        if addl is not None and applicable_i == 277 and oa_277 is None:
            oa_277 = addl
        if addl is not None and applicable_i == 359 and oa_359 is None:
            oa_359 = addl

    return oa_277, oa_359


def _benefit_dob(obj):
    """Age-80 date. Family pension uses the family pensioner's date of birth."""
    from M2_oldage_arrear.services.oldage_service import _as_date

    comparison = getattr(obj, "pension_comparison", None) or {}
    if not isinstance(comparison, dict):
        comparison = {}
    is_emp = getattr(obj, "is_employee_pension", None)
    if is_emp is None:
        is_emp = comparison.get("is_employee_pension", True)
    if is_emp is False or str(is_emp).strip().lower() in ("0", "false", "no"):
        return _as_date(comparison.get("family_pensioner_dob"))

    dob = _as_date(getattr(obj, "date_of_birth", None))
    if dob:
        return dob
    return _as_date(comparison.get("date_of_birth") or comparison.get("dob"))


def _has_oldage_benefit(obj, as_on: date) -> bool:
    """True when age 80 is reached on or before as_on (1st of that month)."""
    from M2_oldage_arrear.services.oldage_service import wef_for_age

    dob = _benefit_dob(obj)
    if not dob or not as_on:
        return False
    return as_on >= wef_for_age(dob, 80)


def _has_enhanced_benefit(obj, start: date | None, end: date | None) -> bool:
    """Enhanced / double family pension overlaps the search dates."""
    from M2_oldage_arrear.services.oldage_service import _as_date

    comparison = getattr(obj, "pension_comparison", None) or {}
    if not isinstance(comparison, dict):
        comparison = {}
    kinds = {
        c.get("kind")
        for c in (comparison.get("columns") or [])
        if isinstance(c, dict)
    }
    # rate_cutover is the employee-to-family switch (often the date of death)
    # even when enhanced family pension does not apply. Do not treat it as enhanced.
    upto = _as_date(comparison.get("double_fpension_upto"))
    flagged = (
        bool(comparison.get("enhanced_family_pension"))
        or "enhanced" in kinds
        or bool(upto)
    )
    if not flagged:
        return False
    dod = _as_date(getattr(obj, "date_of_death", None)) or _as_date(
        comparison.get("date_of_death")
    )
    enh_from = dod + timedelta(days=1) if dod else None
    if upto and start and upto < start:
        return False
    if enh_from and end and enh_from > end:
        return False
    return True


def _matches_benefit(obj, benefit: str, start: date | None, as_on: date) -> bool:
    if benefit == "oldage":
        return _has_oldage_benefit(obj, as_on)
    if benefit == "without_oldage":
        return not _has_oldage_benefit(obj, as_on)
    if benefit == "enhanced":
        return _has_enhanced_benefit(obj, start, as_on)
    return True


def _cpi_probe(cpi: int, as_on: date) -> date:
    """Date used to pick the print column for this CPI."""
    if cpi == 277:
        start, end = date(2017, 1, 1), date(2021, 12, 31)
    else:
        start, end = date(2022, 1, 1), None
    if as_on < start:
        return start
    if end and as_on > end:
        return end
    return as_on


def _print_pair(obj, cpi: int, as_on: date):
    """
    M2 and M1 from the same pension-comparison column the print shows.

    277 uses the pension in force on 31/12/2021 (or earlier, if the search
    ends sooner). 359 uses the pension in force on as_on. A death-split
    case therefore does not pair a family M2 with an employee M1.
    """
    from methodology2.services.arrear_payment_service import (
        _column_for,
        _comparison,
        _pension_kind_on,
    )

    comparison = _comparison(obj)
    enhanced = bool(comparison.get("enhanced_family_pension"))
    enhanced_upto = comparison.get("double_fpension_upto")
    if enhanced and not enhanced_upto:
        enhanced_upto = comparison.get("rate_cutover")
    info = {
        "date_of_death": getattr(obj, "date_of_death", None)
        or comparison.get("date_of_death"),
        "double_fpension_upto": enhanced_upto,
        "enhanced_family_pension": enhanced,
        "die_in_harness": comparison.get("die_in_harness"),
        "is_employee_pension": bool(getattr(obj, "is_employee_pension", False)),
        "columns": comparison.get("columns") or [],
    }
    kind = _pension_kind_on(info, _cpi_probe(cpi, as_on))
    column = _column_for(info["columns"], cpi, kind)
    if column is None and kind != "employee":
        column = _column_for(info["columns"], cpi, "employee")
    if column is not None and column.get("m2") is not None:
        return _money(column.get("m2")), _money(column.get("m1"))

    if kind == "family":
        m2 = _money(getattr(obj, f"m2_family_pension_{cpi}", None)) or _money(
            getattr(obj, f"m2_pension_{cpi}", None)
        )
    else:
        m2 = _money(getattr(obj, f"m2_pension_{cpi}", None))
    m1 = _money(getattr(obj, f"m1_family_pension_{cpi}", None))
    return m2, m1


def _serialize_row(obj, *, source: str, as_on: date) -> dict:
    updated = getattr(obj, "updated_at", None)
    created = getattr(obj, "created_at", None)
    is_emp = bool(getattr(obj, "is_employee_pension", False))
    m2_277, m1_277 = _print_pair(obj, 277, as_on)
    m2_359, m1_359 = _print_pair(obj, 359, as_on)
    oa_277, oa_359 = _oa_benefits_from_obj(obj)
    paid_at = getattr(obj, "payment_done_at", None)

    return {
        "source": source,
        "emp_cd": str(getattr(obj, "emp_cd", "") or ""),
        "name": str(getattr(obj, "name", "") or ""),
        "pensioner_name": str(getattr(obj, "pensioner_name", "") or ""),
        "case_no": str(getattr(obj, "case_no", "") or ""),
        "roll_no": str(getattr(obj, "roll_no", "") or ""),
        "category": str(getattr(obj, "category", "") or ""),
        "designation": str(getattr(obj, "designation", "") or ""),
        "is_employee_pension": is_emp,
        "pension_type": "Employee" if is_emp else "Family",
        "retirement_date": (
            obj.retirement_date.isoformat()
            if getattr(obj, "retirement_date", None)
            else None
        ),
        "date_of_death": (
            obj.date_of_death.isoformat()
            if getattr(obj, "date_of_death", None)
            else None
        ),
        "m2_277": m2_277,
        "m2_359": m2_359,
        "m1_277": m1_277,
        "m1_359": m1_359,
        "oa_277": oa_277,
        "oa_359": oa_359,
        "payment_done": bool(getattr(obj, "payment_done", False)),
        "payment_done_at": paid_at.isoformat() if paid_at else None,
        "payment_done_by": str(getattr(obj, "payment_done_by", "") or ""),
        "payment_phase": str(getattr(obj, "payment_phase", "") or ""),
        "payment_abstract_no": str(getattr(obj, "payment_abstract_no", "") or ""),
        "payment_ref_date": (
            obj.payment_ref_date.isoformat()
            if getattr(obj, "payment_ref_date", None)
            else None
        ),
        "consolidated_by": str(getattr(obj, "consolidated_by", "") or ""),
        "updated_at": updated.isoformat() if updated else None,
        "updated_date": updated.date().isoformat() if updated else None,
        "created_at": created.isoformat() if created else None,
    }


def _filter_qs(qs, from_dt, to_dt, payment: str | None = None):
    if from_dt:
        qs = qs.filter(updated_at__gte=from_dt)
    if to_dt:
        qs = qs.filter(updated_at__lte=to_dt)
    pay = str(payment or "").strip().lower()
    if pay in ("1", "true", "yes", "done", "paid"):
        qs = qs.filter(payment_done=True)
    elif pay in ("0", "false", "no", "pending", "unpaid"):
        qs = qs.filter(payment_done=False)
    return qs


def _empty_summary() -> dict:
    return {
        "total": 0,
        "employee_pension": 0,
        "family_pension": 0,
        "class_12": 0,
        "class_34": 0,
        "today": 0,
        "this_week": 0,
        "this_month": 0,
        "oa_count": 0,
        "enhanced_count": 0,
        "payment_done": 0,
        "payment_pending": 0,
        "from_date": None,
        "to_date": None,
        "source": "all",
        "category": "all",
        "limit": None,
        "total_matched": 0,
    }


def build_consolidation_dashboard(
    *,
    from_date: str | None = None,
    to_date: str | None = None,
    source: str = "all",
    category: str = "all",
    limit: int | None = None,
    payment: str | None = None,
) -> dict:
    """
    List Met2 + OA consolidation snapshots with summary cards.

    source: all | oldage | without_oldage | enhanced
    category: all | 12 | 34
    payment: all | done | pending (optional filter)
    limit: last N rows by updated_at desc (None / 0 = no cap)
    Date filter applies to updated_at (inclusive).
    """
    from_d = _parse_date(from_date, "from_date")
    to_d = _parse_date(to_date, "to_date")
    if from_d and to_d and from_d > to_d:
        raise ValueError("from_date cannot be after to_date")

    src = str(source or "all").strip().lower()
    if src not in ("all", "oldage", "without_oldage", "enhanced"):
        src = "all"
    cat = str(category or "all").strip().lower()
    if cat not in ("all", "12", "34"):
        cat = "all"

    lim = limit
    if lim is not None:
        try:
            lim = int(lim)
        except (TypeError, ValueError):
            lim = 100
        if lim <= 0:
            lim = None

    from_dt, to_dt = _range_bounds(from_d, to_d)
    today = _local_today()
    week_start = today - timedelta(days=today.weekday())
    month_start = today.replace(day=1)

    rows: list[dict] = []

    as_on = to_d or today
    oa_qs = _filter_qs(
        M2OldageArrearConsolidation.objects.all(),
        from_dt,
        to_dt,
        payment=payment,
    ).order_by("-updated_at")
    for obj in oa_qs.iterator(chunk_size=500):
        if _matches_benefit(obj, src, from_d, as_on) and _matches_category(
            getattr(obj, "category", ""), cat
        ):
            row = _serialize_row(obj, source="oa", as_on=as_on)
            row["oldage_benefit"] = _has_oldage_benefit(obj, as_on)
            row["enhanced_benefit"] = _has_enhanced_benefit(obj, from_d, as_on)
            rows.append(row)

    met2_qs = _filter_qs(
        Methodology2Consolidation.objects.all(),
        from_dt,
        to_dt,
        payment=payment,
    ).order_by("-updated_at")
    for obj in met2_qs.iterator(chunk_size=500):
        if _matches_benefit(obj, src, from_d, as_on) and _matches_category(
            getattr(obj, "category", ""), cat
        ):
            row = _serialize_row(obj, source="met2", as_on=as_on)
            row["oldage_benefit"] = _has_oldage_benefit(obj, as_on)
            row["enhanced_benefit"] = _has_enhanced_benefit(obj, from_d, as_on)
            rows.append(row)

    # Newest first (last N show mode)
    rows.sort(key=lambda r: r.get("updated_at") or "", reverse=True)
    total_matched = len(rows)
    if lim is not None:
        rows = rows[:lim]

    summary = _empty_summary()
    summary["from_date"] = from_d.isoformat() if from_d else None
    summary["to_date"] = to_d.isoformat() if to_d else None
    summary["source"] = src
    summary["category"] = cat
    summary["limit"] = lim
    summary["total_matched"] = total_matched
    summary["total"] = len(rows)

    for r in rows:
        if r.get("oldage_benefit"):
            summary["oa_count"] += 1
        if r.get("enhanced_benefit"):
            summary["enhanced_count"] += 1
        if r["is_employee_pension"]:
            summary["employee_pension"] += 1
        else:
            summary["family_pension"] += 1
        if r.get("payment_done"):
            summary["payment_done"] += 1
        else:
            summary["payment_pending"] += 1
        bucket = _category_bucket(r.get("category"))
        if bucket == "12":
            summary["class_12"] += 1
        elif bucket == "34":
            summary["class_34"] += 1

        ud = r.get("updated_date")
        if not ud:
            continue
        try:
            d = date.fromisoformat(ud)
        except ValueError:
            continue
        if d == today:
            summary["today"] += 1
        if d >= week_start:
            summary["this_week"] += 1
        if d >= month_start:
            summary["this_month"] += 1

    return {"summary": summary, "rows": rows, "count": len(rows)}


def _snapshot_model(source: str):
    src = str(source or "").strip().lower()
    if src in ("oa", "oldage", "old_age"):
        return M2OldageArrearConsolidation, M2ConsolCase.SOURCE_OA, "oa"
    if src in ("met2", "m2", "methodology2"):
        return Methodology2Consolidation, M2ConsolCase.SOURCE_MET2, "met2"
    raise ValueError("source must be oa or met2")


def set_consolidation_payment(
    *,
    emp_cd: str,
    source: str,
    payment_done: bool,
    by_user: str = "",
) -> dict:
    """Mark / unmark payment done on the consolidation snapshot (m2* only)."""
    emp = str(emp_cd or "").strip()[:5]
    if not emp:
        raise ValueError("emp_cd is required")

    Model, _case_src, src_norm = _snapshot_model(source)
    obj = Model.objects.filter(emp_cd=emp).first()
    if not obj:
        raise ValueError(f"No {src_norm} consolidation for emp_cd={emp}")

    done = bool(payment_done)
    obj.payment_done = done
    if done:
        obj.payment_done_at = timezone.now()
        obj.payment_done_by = str(by_user or "").strip()[:80]
    else:
        obj.payment_done_at = None
        obj.payment_done_by = ""
        obj.payment_phase = ""
        obj.payment_abstract_no = ""
        obj.payment_ref_date = None
    obj.save(
        update_fields=[
            "payment_done",
            "payment_done_at",
            "payment_done_by",
            "payment_phase",
            "payment_abstract_no",
            "payment_ref_date",
            "updated_at",
        ]
    )
    return _serialize_row(obj, source=src_norm, as_on=_local_today())


@transaction.atomic
def delete_consolidation_m2_only(*, emp_cd: str, source: str) -> dict:
    """
    Delete this emp's consolidation from m2* tables only.

    Removes:
      - methodology2_consolidation OR m2_oldage_arrear_consolidation
      - m2_consol_case (+ cascaded rate/check/event)
      - m2_consol_release_log rows for that case

    Does NOT touch fi_* / Oracle wage or pension master tables.
    """
    emp = str(emp_cd or "").strip()[:5]
    if not emp:
        raise ValueError("emp_cd is required")

    Model, case_src, src_norm = _snapshot_model(source)
    snap = Model.objects.filter(emp_cd=emp).first()
    if not snap:
        raise ValueError(f"No {src_norm} consolidation for emp_cd={emp}")

    if bool(getattr(snap, "payment_done", False)):
        raise ValueError(
            f"Cannot delete {src_norm} consolidation for emp_cd={emp}: "
            "payment is marked done. Unmark paid first, then delete."
        )

    deleted = {
        "emp_cd": emp,
        "source": src_norm,
        "snapshot": 0,
        "consol_case": 0,
        "release_log": 0,
    }

    cases = list(M2ConsolCase.objects.filter(emp_cd=emp, source_app=case_src))
    case_ids = [c.pk for c in cases]
    if case_ids:
        deleted["release_log"] = M2ConsolReleaseLog.objects.filter(
            case_id__in=case_ids
        ).delete()[0]
        deleted["consol_case"] = M2ConsolCase.objects.filter(
            pk__in=case_ids
        ).delete()[0]

    snap.delete()
    deleted["snapshot"] = 1
    deleted["fi_tables_touched"] = False
    return deleted


def _action_items(items) -> list[dict]:
    if not isinstance(items, list) or not items:
        raise ValueError("Select at least one row")
    if len(items) > 500:
        raise ValueError("Select at most 500 rows at a time")
    out = []
    for item in items:
        if not isinstance(item, dict):
            raise ValueError("Each item must include emp_cd and source")
        out.append(
            {
                "emp_cd": str(item.get("emp_cd") or item.get("emp_id") or ""),
                "source": str(item.get("source") or ""),
            }
        )
    return out


def set_consolidation_payment_many(
    items, *, payment_done: bool, by_user: str = ""
) -> dict:
    """Mark or unmark payment for many dashboard rows. No bill tag."""
    ok = []
    errors = []
    for item in _action_items(items):
        try:
            row = set_consolidation_payment(
                emp_cd=item["emp_cd"],
                source=item["source"],
                payment_done=payment_done,
                by_user=by_user,
            )
            ok.append({"emp_cd": row["emp_cd"], "source": row["source"]})
        except ValueError as exc:
            errors.append({**item, "error": str(exc)})
    return {
        "ok_count": len(ok),
        "error_count": len(errors),
        "ok": ok,
        "errors": errors,
        "payment_done": bool(payment_done),
    }


def delete_consolidation_m2_many(items) -> dict:
    """Delete many m2* consolidations. Paid rows are rejected individually."""
    ok = []
    errors = []
    for item in _action_items(items):
        try:
            deleted = delete_consolidation_m2_only(
                emp_cd=item["emp_cd"], source=item["source"]
            )
            ok.append(
                {"emp_cd": deleted["emp_cd"], "source": deleted["source"]}
            )
        except ValueError as exc:
            errors.append({**item, "error": str(exc)})
    return {
        "ok_count": len(ok),
        "error_count": len(errors),
        "ok": ok,
        "errors": errors,
        "fi_tables_touched": False,
    }
