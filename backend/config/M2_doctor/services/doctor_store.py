"""
Doctor consolidation save / load into m2_doctor_consolidation only.

Same consolidation logic as the Old Age app (comparison columns, difference,
old-age benefit and print columns), pointed at the doctor table. The
structured consolidation store is not synced for doctors.
"""

from __future__ import annotations

from contextlib import contextmanager
from decimal import Decimal, InvalidOperation

import methodology2.services.consolidation_service as m2_cs
import M2_oldage_arrear.services.consolidation_bridge as oa_bridge
from M2_doctor.models import M2DoctorConsolidation


@contextmanager
def _use_doctor_model():
    original_cs = m2_cs.Methodology2Consolidation
    original_bridge = oa_bridge.M2OldageArrearConsolidation
    m2_cs.Methodology2Consolidation = M2DoctorConsolidation
    oa_bridge.M2OldageArrearConsolidation = M2DoctorConsolidation
    try:
        yield
    finally:
        m2_cs.Methodology2Consolidation = original_cs
        oa_bridge.M2OldageArrearConsolidation = original_bridge


def _decimal(value):
    if value is None or str(value).strip() == "":
        return None
    try:
        return Decimal(str(value).replace(",", ""))
    except (InvalidOperation, ValueError):
        return None


def _with_pay_split(result: dict | None) -> dict | None:
    if not result:
        return result
    emp = str(result.get("emp_cd") or "").strip()[:5]
    obj = M2DoctorConsolidation.objects.filter(emp_cd=emp).first() if emp else None
    if obj is not None:
        result["last_basic"] = float(obj.last_basic) if obj.last_basic is not None else None
        result["last_npa"] = float(obj.last_npa) if obj.last_npa is not None else None
    return result


def save_doctor_consolidation(payload: dict) -> dict:
    with _use_doctor_model():
        result = m2_cs.save_consolidation_snapshot(payload)
        if result.get("error"):
            return result
        result = oa_bridge._attach_oldage(result, payload)

    emp = str(result.get("emp_cd") or "").strip()[:5]
    last_pay = _decimal(payload.get("last_pay"))
    last_npa = _decimal(payload.get("npa_amount")) or Decimal("0")
    last_basic = _decimal(payload.get("last_basic"))
    if last_basic is None and last_pay is not None:
        last_basic = last_pay - last_npa
    if emp:
        M2DoctorConsolidation.objects.filter(emp_cd=emp).update(
            last_basic=last_basic, last_npa=last_npa
        )
    return _with_pay_split(result)


def get_doctor_consolidation(emp_id: str) -> dict | None:
    with _use_doctor_model():
        result = m2_cs.get_consolidation_snapshot(emp_id)
        result = oa_bridge._attach_oldage(result)
    return _with_pay_split(result)
