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


def _apply_oldage_print_columns(result: dict, payload: dict | None = None) -> dict:
    """Replace comparison columns with old-age mid-CPI splits for print."""
    from M2_oldage_arrear.services.oldage_print_columns import (
        build_oldage_pension_comparison,
    )

    payload = payload or {}
    dob = _as_date(
        result.get("date_of_birth")
        or payload.get("date_of_birth")
        or payload.get("dob")
    )
    if not dob:
        return result

    is_emp = bool(result.get("is_employee_pension"))
    if is_emp:
        m2_277 = result.get("m2_pension_277")
        m2_359 = result.get("m2_pension_359")
    else:
        m2_277 = result.get("m2_family_pension_277")
        m2_359 = result.get("m2_family_pension_359")
    m1_277 = result.get("m1_family_pension_277")
    m1_359 = result.get("m1_family_pension_359")

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

    # Keep useful extras (stagnation, DOD display) from existing comparison.
    existing = dict(result.get("pension_comparison") or {})
    merged = {**existing, **oa_cmp}
    # Preserve death/enhanced notes if present and no OA columns built — already replaced.
    if existing.get("stagnation_amount") is not None:
        merged["stagnation_amount"] = existing["stagnation_amount"]
    if existing.get("date_of_death_display"):
        merged["date_of_death_display"] = existing["date_of_death_display"]
        merged["date_of_death"] = existing.get("date_of_death")
    if existing.get("double_fpension_upto_display"):
        merged["double_fpension_upto_display"] = existing[
            "double_fpension_upto_display"
        ]

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
    dob = _as_date(payload.get("date_of_birth") or payload.get("dob"))
    if oldage is None and dob is not None:
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
            dob=dob,
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
    return _attach_oldage(result, payload)


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
