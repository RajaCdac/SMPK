"""
Consolidation save/load for M2 Old Age Arrear.

Reuses Methodology-2 consolidation math by temporarily pointing its model
at M2OldageArrearConsolidation — methodology2_consolidation is never written.
"""

from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime

from M2_oldage_arrear.models import M2OldageArrearConsolidation
from M2_oldage_arrear.services.oldage_service import _as_date, compute_oldage_benefit
import methodology2.services.consolidation_service as m2_cs


@contextmanager
def _use_oldage_model():
    original = m2_cs.Methodology2Consolidation
    m2_cs.Methodology2Consolidation = M2OldageArrearConsolidation
    try:
        yield
    finally:
        m2_cs.Methodology2Consolidation = original


def _column_m1(comparison: dict, cpi: int):
    """Employee Methodology-1 on the print column. Not the family scalar."""
    for col in (comparison or {}).get("columns") or []:
        if not isinstance(col, dict):
            continue
        try:
            col_cpi = int(col.get("cpi") or 0)
        except (TypeError, ValueError):
            continue
        if col_cpi == cpi and col.get("m1") is not None:
            return col.get("m1")
    return None


def _as_bool_employee(value, default=True) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in ("1", "true", "yes", "y")


def resolve_oldage_dob(payload: dict | None = None, result: dict | None = None, emp_id: str | None = None):
    """
    Age for old-age benefit.

    A family-pension case uses the family pensioner's date of birth.
    The employee date of birth is not used for that age.
    """
    payload = payload or {}
    result = result or {}
    explicit = _as_date(payload.get("oldage_dob"))
    if explicit is not None:
        return explicit

    is_emp = _as_bool_employee(
        payload.get("is_employee_pension")
        if "is_employee_pension" in payload
        else result.get("is_employee_pension"),
        default=True,
    )
    if not is_emp:
        comparison = result.get("pension_comparison") or {}
        if not isinstance(comparison, dict):
            comparison = {}
        family_dob = _as_date(
            payload.get("family_pensioner_dob")
            or comparison.get("family_pensioner_dob")
            or result.get("family_pensioner_dob")
        )
        if family_dob is None and emp_id:
            from methodology2.services.consolidation_service import (
                fetch_family_pensioner_dob,
            )

            family_dob = fetch_family_pensioner_dob(emp_id)
        return family_dob

    return _as_date(
        payload.get("date_of_birth")
        or payload.get("dob")
        or result.get("date_of_birth")
    )


def _apply_oldage_print_columns(result: dict, payload: dict | None = None) -> dict:
    """
    Attach old-age mid-CPI print columns.

    When Met2 already built a death/enhanced split (50% then 30%), keep those
    columns — do not replace with a single family/employee rate (that drops
    enhanced 18250 to only 10950 for cases like 42788).
    """
    from M2_oldage_arrear.services.oldage_print_columns import (
        build_oldage_pension_comparison,
    )

    payload = payload or {}
    existing = dict(result.get("pension_comparison") or {})
    existing_cols = [
        c for c in (existing.get("columns") or []) if isinstance(c, dict)
    ]
    kinds = {c.get("kind") for c in existing_cols}
    # Met2 death/enhanced segregation — keep those columns (do not flatten to 30%).
    if existing.get("has_death_split") or (
        len(kinds & {"enhanced", "employee", "family"}) >= 2 and existing_cols
    ):
        merged = dict(existing)
        merged["has_death_split"] = True
        is_emp = bool(
            result.get("is_employee_pension", existing.get("is_employee_pension"))
        )
        if not is_emp:
            merged["has_oldage_calc_table"] = False
            merged["has_oldage_split"] = False
            merged["section_title"] = existing.get("section_title") or "FAMILY PENSION"
            merged["is_employee_pension"] = False
        result["pension_comparison"] = merged
        emp = str(result.get("emp_cd") or "").strip()[:5]
        if emp:
            M2OldageArrearConsolidation.objects.filter(emp_cd=emp).update(
                pension_comparison=merged
            )
        return result

    dob = resolve_oldage_dob(
        payload,
        result,
        str(result.get("emp_cd") or "").strip()[:5],
    )
    if not dob:
        return result

    is_emp = bool(result.get("is_employee_pension"))
    excel_m1_277 = payload.get("m1_pension_277")
    excel_m1_359 = payload.get("m1_pension_359")
    if is_emp:
        m2_277 = result.get("m2_pension_277")
        m2_359 = result.get("m2_pension_359")
        # Living employee: m1_family_pension_* is null. Employee M1 is on the columns.
        # Manual Excel M-I_277 / M-I_359 wins over the wage header.
        m1_277 = excel_m1_277 if excel_m1_277 is not None else _column_m1(existing, 277)
        m1_359 = excel_m1_359 if excel_m1_359 is not None else _column_m1(existing, 359)
    else:
        m2_277 = result.get("m2_family_pension_277")
        m2_359 = result.get("m2_family_pension_359")
        m1_277 = (
            excel_m1_277
            if excel_m1_277 is not None
            else result.get("m1_family_pension_277")
        )
        m1_359 = (
            excel_m1_359
            if excel_m1_359 is not None
            else result.get("m1_family_pension_359")
        )

    oa_cmp = build_oldage_pension_comparison(
        dob=dob,
        m2_277=m2_277,
        m1_277=m1_277,
        m2_359=m2_359,
        m1_359=m1_359,
        is_employee_pension=is_emp,
        as_on_date=payload.get("as_on_date"),
    )
    if not oa_cmp.get("columns"):
        return result

    merged = {**existing, **oa_cmp}
    if existing.get("stagnation_amount") is not None:
        merged["stagnation_amount"] = existing["stagnation_amount"]
    if existing.get("npa_amount") is not None:
        merged["npa_amount"] = existing["npa_amount"]
    if existing.get("date_of_death_display"):
        merged["date_of_death_display"] = existing["date_of_death_display"]
        merged["date_of_death"] = existing.get("date_of_death")
    if existing.get("double_fpension_upto_display"):
        merged["double_fpension_upto_display"] = existing[
            "double_fpension_upto_display"
        ]
        merged["double_fpension_upto"] = existing.get("double_fpension_upto")
    if existing.get("family_pensioner_dob_display"):
        merged["family_pensioner_dob_display"] = existing[
            "family_pensioner_dob_display"
        ]
        merged["family_pensioner_dob"] = existing.get("family_pensioner_dob")
    if existing.get("family_pensioner_name"):
        merged["family_pensioner_name"] = existing["family_pensioner_name"]

    result["pension_comparison"] = merged
    emp = str(result.get("emp_cd") or "").strip()[:5]
    if emp:
        M2OldageArrearConsolidation.objects.filter(emp_cd=emp).update(
            pension_comparison=merged
        )
    return result


def _attach_oldage(result: dict | None, payload: dict | None = None) -> dict | None:
    if not result:
        return result
    payload = payload or {}
    emp = str(result.get("emp_cd") or "").strip()[:5]
    obj = (
        M2OldageArrearConsolidation.objects.filter(emp_cd=emp).first() if emp else None
    )

    oldage = payload.get("oldage_benefit")
    # Stored DATE_OF_BIRTH stays the employee. Family old-age uses the
    # family pensioner's date of birth and must not overwrite that field.
    dob = _as_date(payload.get("date_of_birth") or payload.get("dob"))
    oldage_dob = resolve_oldage_dob(payload, result, emp)
    if oldage is None and oldage_dob is not None:
        pension = payload.get("pension") or {}
        m2_359 = (
            result.get("m2_pension_359")
            or pension.get("pension_359_cpi")
        )
        m2_277 = (
            result.get("m2_pension_277")
            or pension.get("pension_277_cpi")
        )
        m1_359 = (
            payload.get("m1_pension_359")
            or result.get("m1_family_pension_359")
            or pension.get("m1_pension_359")
        )
        m1_277 = (
            payload.get("m1_pension_277")
            or result.get("m1_family_pension_277")
            or pension.get("m1_pension_277")
        )
        oldage = compute_oldage_benefit(
            dob=oldage_dob,
            as_on_date=payload.get("as_on_date"),
            pension_277=m2_277,
            pension_359=m2_359,
            m1_pension_277=m1_277,
            m1_pension_359=m1_359,
            benefit_359=payload.get("benefit_359") or payload.get("basic_pension"),
            benefit_277=payload.get("benefit_277"),
            category=payload.get("category") or result.get("category"),
        )

    if obj is not None:
        updates = {}
        if oldage is not None:
            updates["oldage_benefit"] = oldage
        if dob is not None:
            updates["date_of_birth"] = dob
        if updates:
            for key, value in updates.items():
                setattr(obj, key, value)
            obj.save(update_fields=list(updates.keys()) + ["updated_at"])
            obj.refresh_from_db()

        result["oldage_benefit"] = obj.oldage_benefit or oldage or {}
        result["date_of_birth"] = (
            obj.date_of_birth.isoformat() if obj.date_of_birth else None
        )
    elif oldage is not None:
        result["oldage_benefit"] = oldage
        result["date_of_birth"] = dob.isoformat() if dob else None

    return _apply_oldage_print_columns(result, payload)

def save_consolidation_snapshot(payload):
    with _use_oldage_model():
        result = m2_cs.save_consolidation_snapshot(payload)
    if result.get("error"):
        return result
    result = _attach_oldage(result, payload)
    try:
        from methodology2.models import M2ConsolCase
        from methodology2.services.consol_store_service import (
            sync_consol_store_from_snapshot,
        )

        emp = str(result.get("emp_cd") or "").strip()[:5]
        oa_pk = None
        if emp:
            oa_row = M2OldageArrearConsolidation.objects.filter(emp_cd=emp).first()
            oa_pk = oa_row.pk if oa_row else None
        sync_consol_store_from_snapshot(
            result,
            source_app=M2ConsolCase.SOURCE_OA,
            snapshot_pk=oa_pk,
        )
    except Exception:
        import logging

        logging.getLogger(__name__).exception(
            "m2_consol_store OA sync failed for emp_cd=%s",
            result.get("emp_cd"),
        )
    return result


def get_consolidation_snapshot(emp_id):
    with _use_oldage_model():
        result = m2_cs.get_consolidation_snapshot(emp_id)
    return _attach_oldage(result)


def fetch_employee_dob(emp_id: str):
    """DOB from pensioner master, else emp_per.BIRTH_DT."""
    from django.db import connection

    emp = str(emp_id or "").strip()[:5]
    if not emp:
        return None
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT DOB FROM fi_pn_mh_pensioner
            WHERE EMP_CD = %s AND DOB IS NOT NULL
            LIMIT 1
            """,
            [emp],
        )
        row = cursor.fetchone()
        if row and row[0]:
            return _as_date(row[0])

        cursor.execute(
            """
            SELECT BIRTH_DT FROM fi_xx_mh_emp_per
            WHERE EMP_CD = %s AND BIRTH_DT IS NOT NULL
            LIMIT 1
            """,
            [emp],
        )
        row = cursor.fetchone()
        if row and row[0]:
            return _as_date(row[0])
    return None
