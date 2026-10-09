"""
Persist systematic consolidation case + dated rate periods.

Print snapshots remain on methodology2_consolidation /
m2_oldage_arrear_consolidation. This store is for validity windows
(enhanced 50% upto … then family 30%), old-age, checklist, and day-wise events.
"""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal, InvalidOperation

from django.db import transaction
from django.utils import timezone

from methodology2.models import (
    M2ConsolCase,
    M2ConsolCheck,
    M2ConsolEvent,
    M2ConsolRate,
)
from methodology2.services.consolidation_service import (
    CPI_277_START,
    CPI_359_START,
)

CHECK_STEPS = [
    ("DOB", "Date of birth", 10),
    ("DOD", "Date of death", 20),
    ("FP_DOB", "Family pensioner DOB", 30),
    ("SCALE", "Pay scale / notional", 40),
    ("MATRIX", "Matrix / Met2 basic", 50),
    ("M2_277", "Met2 amount @ 277 CPI", 60),
    ("M2_359", "Met2 amount @ 359 CPI", 70),
    ("M1_277", "Met1 amount @ 277 CPI", 80),
    ("M1_359", "Met1 amount @ 359 CPI", 90),
    ("ENHANCED", "Enhanced / DIH split & upto date", 100),
    ("PAYABLE", "Payable (higher of M1 & M2)", 110),
    ("OA", "Old age % / benefit", 120),
    ("ROLL_BANK", "Roll / bank / LIC link", 130),
]

KIND_MAP = {
    "employee": M2ConsolRate.KIND_EMPLOYEE,
    "enhanced": M2ConsolRate.KIND_ENHANCED,
    "family": M2ConsolRate.KIND_FAMILY,
}

PCT_MAP = {
    M2ConsolRate.KIND_EMPLOYEE: Decimal("50"),
    M2ConsolRate.KIND_ENHANCED: Decimal("50"),
    M2ConsolRate.KIND_FAMILY: Decimal("30"),
}


def _as_date(value):
    if value is None or value == "":
        return None
    if isinstance(value, date):
        return value
    text = str(value).strip()[:10]
    if not text:
        return None
    try:
        return date.fromisoformat(text)
    except ValueError:
        return None


def _as_decimal(value):
    if value is None or value == "":
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return None


def _beneficial(m1, m2):
    if m1 is None and m2 is None:
        return "", None, None
    if m1 is None:
        return "M-II", m2, None
    if m2 is None:
        return "M-I", m1, None
    if m2 > m1:
        return "M-II", m2, (m2 - m1)
    if m1 > m2:
        return "M-I", m1, (m1 - m2)
    return "Equal", m1, Decimal("0")


def _map_case_type(comparison: dict, is_employee_pension: bool) -> str:
    raw = str(comparison.get("case_type") or "").strip().lower()
    if comparison.get("die_in_harness") or raw in ("die_in_harness", "dih"):
        return M2ConsolCase.CASE_DIH
    if raw in ("died_after_retirement", "died_after_ret", "dar"):
        return M2ConsolCase.CASE_DIED_AFTER_RET
    if comparison.get("date_of_death") or comparison.get("has_death_split"):
        return M2ConsolCase.CASE_DIED_AFTER_RET
    if is_employee_pension:
        return M2ConsolCase.CASE_RETIRED
    return M2ConsolCase.CASE_FAMILY


def _default_window(cpi: int):
    if int(cpi) == 277:
        return CPI_277_START, CPI_359_START - timedelta(days=1)
    return CPI_359_START, None


def _assign_split_validity(
    cols: list[dict],
    *,
    enhanced_upto: date | None,
    dod: date | None,
) -> list[dict]:
    """
    Fill missing period_from/to for death-split columns using enhanced_upto / DOD.

    Within each CPI window, order kinds employee → enhanced → family.
    """
    by_cpi: dict[int, list[dict]] = {}
    for col in cols:
        by_cpi.setdefault(int(col.get("cpi") or 359), []).append(col)

    cut = enhanced_upto or dod
    out = []
    for cpi, group in by_cpi.items():
        win_from, win_to = _default_window(cpi)
        # Preserve original order but compute dates if missing.
        cursor = win_from
        for col in group:
            kind = str(col.get("kind") or "").lower()
            vf = _as_date(col.get("period_from") or col.get("valid_from"))
            vt = _as_date(col.get("period_to") or col.get("valid_to"))
            if vf is None:
                vf = cursor
            if vt is None:
                if kind in ("employee", "enhanced") and cut:
                    # Clip cutover to this CPI window.
                    last = cut
                    if win_to and last > win_to:
                        last = win_to
                    if last < vf:
                        last = vf
                    # If cut is before this CPI window, this kind shouldn't apply;
                    # keep window end as fallback.
                    if cut < win_from:
                        vt = win_to
                    else:
                        vt = last if last >= vf else win_to
                    # Open within CPI if enhanced continues past window.
                    if win_to and cut >= win_to and kind in ("employee", "enhanced"):
                        vt = win_to
                elif kind == "family":
                    vt = win_to
                else:
                    vt = win_to
            col = dict(col)
            col["period_from"] = vf.isoformat() if isinstance(vf, date) else vf
            col["period_to"] = vt.isoformat() if isinstance(vt, date) else vt
            out.append(col)
            if isinstance(vt, date):
                cursor = vt + timedelta(days=1)
            elif vf:
                cursor = vf
        # Fix family start after enhanced when still missing logic for open 359:
        # re-pass: if family follows enhanced and enhanced has valid_to, family from+1
        fixed = []
        prev_to = None
        for col in out[-len(group) :]:
            kind = str(col.get("kind") or "").lower()
            vf = _as_date(col.get("period_from"))
            vt = _as_date(col.get("period_to"))
            if kind == "family" and prev_to and (vf is None or vf <= prev_to):
                vf = prev_to + timedelta(days=1)
                col = dict(col)
                col["period_from"] = vf.isoformat()
                if vt and vf > vt:
                    col["period_to"] = None if win_to is None else win_to.isoformat()
            fixed.append(col)
            prev_to = _as_date(col.get("period_to")) or prev_to
        # Replace last group in out
        out = out[: -len(group)] + fixed
    return out


def _rate_rows_from_columns(
    columns: list,
    as_on: date,
    *,
    enhanced_upto: date | None = None,
    dod: date | None = None,
) -> list[dict]:
    raw_cols = [c for c in (columns or []) if isinstance(c, dict)]
    needs_dates = any(
        not (c.get("period_from") or c.get("valid_from")) for c in raw_cols
    )
    if needs_dates and (enhanced_upto or dod):
        raw_cols = _assign_split_validity(
            raw_cols, enhanced_upto=enhanced_upto, dod=dod
        )

    rows = []
    for idx, col in enumerate(raw_cols, start=1):
        kind_raw = str(col.get("kind") or "employee").strip().lower()
        rate_kind = KIND_MAP.get(kind_raw, M2ConsolRate.KIND_EMPLOYEE)
        cpi = int(col.get("cpi") or 359)
        vf = _as_date(col.get("period_from") or col.get("valid_from"))
        vt = _as_date(col.get("period_to") or col.get("valid_to"))
        if vf is None:
            vf, default_to = _default_window(cpi)
            if vt is None:
                vt = default_to

        m2 = _as_decimal(col.get("m2_base", col.get("m2")))
        m1 = _as_decimal(col.get("m1"))
        beneficial, payable, diff = _beneficial(m1, m2)
        if col.get("payable_basic") is not None:
            payable = _as_decimal(col.get("payable_basic"))
        if col.get("diff") is not None and diff is None:
            diff = _as_decimal(col.get("diff"))

        oa_pct = _as_decimal(col.get("oldage_percent"))
        oa_ben = _as_decimal(col.get("oa_benefit"))
        with_oa = _as_decimal(
            col.get("revised_total_basic") or col.get("payable_with_oa")
        )
        if with_oa is None and payable is not None and oa_ben is not None:
            with_oa = payable + oa_ben
        elif with_oa is None and payable is not None:
            with_oa = payable

        is_current = vf <= as_on and (vt is None or vt >= as_on)
        rows.append(
            {
                "seq_no": idx,
                "cpi_point": cpi,
                "rate_kind": rate_kind,
                "rate_pct": PCT_MAP.get(rate_kind, Decimal("50")),
                "valid_from": vf,
                "valid_to": vt,
                "m2_amount": m2,
                "m1_amount": m1,
                "payable_amount": payable,
                "beneficial": beneficial,
                "diff_amount": diff,
                "oa_percent": oa_pct,
                "oa_benefit": oa_ben,
                "payable_with_oa": with_oa,
                "period_note": str(col.get("period_note") or "")[:255],
                "is_current": is_current,
            }
        )
    return rows


def _seed_checks(case: M2ConsolCase, *, reset: bool):
    existing = {c.step_code: c for c in case.checks.all()}
    for code, label, order in CHECK_STEPS:
        row = existing.get(code)
        if row is None:
            M2ConsolCheck.objects.create(
                case=case,
                step_code=code,
                step_label=label,
                sort_order=order,
                result=M2ConsolCheck.RESULT_PENDING,
            )
        elif reset:
            row.result = M2ConsolCheck.RESULT_PENDING
            row.remark = ""
            row.checked_by = ""
            row.checked_at = None
            row.step_label = label
            row.sort_order = order
            row.save(
                update_fields=[
                    "result",
                    "remark",
                    "checked_by",
                    "checked_at",
                    "step_label",
                    "sort_order",
                ]
            )


def _add_event(
    case: M2ConsolCase,
    *,
    event_type: str,
    from_status: str = "",
    to_status: str = "",
    event_by: str = "",
    note: str = "",
    payload: dict | None = None,
):
    M2ConsolEvent.objects.create(
        case=case,
        emp_cd=case.emp_cd,
        source_app=case.source_app,
        event_type=event_type,
        from_status=from_status or "",
        to_status=to_status or "",
        event_at=timezone.now(),
        event_by=(event_by or "")[:80],
        note=(note or "")[:255],
        payload_json=payload or {},
    )


@transaction.atomic
def sync_consol_store_from_snapshot(
    snapshot: dict,
    *,
    source_app: str = M2ConsolCase.SOURCE_MET2,
    user: str = "",
    snapshot_pk: int | None = None,
) -> M2ConsolCase | None:
    """
    Upsert m2_consol_case + replace m2_consol_rate from a consolidation snapshot dict
    (same shape as snapshot_to_dict / OA attach result).
    """
    if not snapshot or snapshot.get("error"):
        return None

    emp = str(snapshot.get("emp_cd") or "").strip()[:5]
    if not emp:
        return None

    source = (
        M2ConsolCase.SOURCE_OA
        if source_app == M2ConsolCase.SOURCE_OA
        else M2ConsolCase.SOURCE_MET2
    )
    comparison = snapshot.get("pension_comparison") or {}
    if not isinstance(comparison, dict):
        comparison = {}

    is_emp = bool(snapshot.get("is_employee_pension", comparison.get("is_employee_pension")))
    dod = _as_date(snapshot.get("date_of_death") or comparison.get("date_of_death"))
    enhanced_upto = _as_date(
        comparison.get("double_fpension_upto")
        or comparison.get("rate_cutover")
        or snapshot.get("double_fpension_upto")
    )
    family_from = (enhanced_upto + timedelta(days=1)) if enhanced_upto else None
    dob = _as_date(
        snapshot.get("date_of_birth")
        or comparison.get("date_of_birth")
    )
    fp_dob = _as_date(
        comparison.get("family_pensioner_dob")
        or snapshot.get("family_pensioner_dob")
    )
    dor = _as_date(snapshot.get("retirement_date"))

    as_on = _as_date(comparison.get("as_on_date")) or date.today()
    rate_defs = _rate_rows_from_columns(
        comparison.get("columns") or [],
        as_on,
        enhanced_upto=enhanced_upto,
        dod=dod,
    )

    current_rates = [r for r in rate_defs if r["is_current"]]
    if not current_rates and rate_defs:
        # Prefer highest CPI open/current-ish row.
        current_rates = sorted(rate_defs, key=lambda r: r["cpi_point"])[-1:]
        for r in rate_defs:
            r["is_current"] = False
        if current_rates:
            current_rates[0]["is_current"] = True

    payable = current_rates[0]["payable_amount"] if current_rates else None
    with_oa = current_rates[0]["payable_with_oa"] if current_rates else None
    cpi = current_rates[0]["cpi_point"] if current_rates else None

    now = timezone.now()
    case, created = M2ConsolCase.objects.select_for_update().get_or_create(
        emp_cd=emp,
        source_app=source,
        defaults={
            "status": M2ConsolCase.STATUS_CALCULATED,
            "version_no": 1,
            "calculated_at": now,
            "calculated_by": (user or "")[:80],
            "status_at": now,
            "status_by": (user or "")[:80],
        },
    )

    from_status = case.status
    if not created:
        case.version_no = (case.version_no or 1) + 1
        # Recalc returns case to CALCULATED (needs re-verify) unless already ERROR/DISPUTED.
        if case.status in (
            M2ConsolCase.STATUS_APPROVED,
            M2ConsolCase.STATUS_RELEASED,
            M2ConsolCase.STATUS_VERIFIED,
            M2ConsolCase.STATUS_IN_REVIEW,
            M2ConsolCase.STATUS_SUPERSEDED,
            M2ConsolCase.STATUS_HELD,
        ):
            case.status = M2ConsolCase.STATUS_CALCULATED
        elif case.status not in (
            M2ConsolCase.STATUS_ERROR,
            M2ConsolCase.STATUS_DISPUTED,
        ):
            case.status = M2ConsolCase.STATUS_CALCULATED

    case.case_type = _map_case_type(comparison, is_emp)
    case.pensioner_type = "P" if is_emp else "F"
    case.roll_no = str(snapshot.get("roll_no") or "")[:30]
    case.case_no = str(snapshot.get("case_no") or "")[:20]
    case.name = str(snapshot.get("name") or snapshot.get("wage_emp_name") or "")[:200]
    case.fp_name = str(
        snapshot.get("pensioner_name")
        or comparison.get("family_pensioner_name")
        or ""
    )[:200]
    case.category = str(snapshot.get("category") or "")[:20]
    case.designation = str(snapshot.get("designation") or "")[:200]
    case.scale = str(snapshot.get("scale") or "")[:100]
    case.dob = dob
    case.dod = dod
    case.fp_dob = fp_dob
    case.dor = dor
    case.enhanced_upto = enhanced_upto
    case.family_from = family_from
    case.die_in_harness = bool(comparison.get("die_in_harness"))
    case.payable_basic = payable
    case.payable_with_oa = with_oa
    case.cpi_point = cpi
    case.calculated_at = now
    case.calculated_by = (user or case.calculated_by or "")[:80]
    case.status_at = now
    case.status_by = (user or "")[:80]
    case.status_reason = ""

    if source == M2ConsolCase.SOURCE_OA:
        case.snapshot_oa_id = snapshot_pk or case.snapshot_oa_id
    else:
        case.snapshot_met2_id = snapshot_pk or case.snapshot_met2_id

    case.save()

    case.rates.all().delete()
    M2ConsolRate.objects.bulk_create(
        [M2ConsolRate(case=case, **row) for row in rate_defs]
    )

    # New case: seed PENDING steps. Recalc: reset all steps (must re-verify).
    _seed_checks(case, reset=not created)

    _add_event(
        case,
        event_type="CALCULATED" if created else "RECALC",
        from_status=from_status,
        to_status=case.status,
        event_by=user,
        note=f"v{case.version_no}; {len(rate_defs)} rate period(s)",
        payload={
            "version_no": case.version_no,
            "rate_count": len(rate_defs),
            "enhanced_upto": enhanced_upto.isoformat() if enhanced_upto else None,
            "has_death_split": bool(comparison.get("has_death_split")),
            "has_oldage_split": bool(comparison.get("has_oldage_split")),
        },
    )
    return case
