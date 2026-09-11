"""Soft employee load for Old Age when Met2 mirror lacks class/scale."""

from __future__ import annotations

from employee.oracle_mirror import FiXxMhEmpAdm, FiXxMhEmpFin, FiXxMhEmpPer
from employee.services.methodology_employee_lookup import (
    _format_date_for_input,
    _full_name,
    category_from_emp_class,
    _employee_class,
    _emp_key,
)
from methodology2.services.oracle_employee_service import (
    fetch_employee_for_methodology2,
)

from M2_oldage_arrear.services.consolidation_bridge import fetch_employee_dob


def _pensioner_name(emp_key: str) -> str:
    from django.db import connection

    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT NAME FROM fi_pn_mh_pensioner WHERE EMP_CD = %s LIMIT 1",
            [emp_key],
        )
        row = cursor.fetchone()
        if row and row[0]:
            return str(row[0]).strip()
    return ""


def fetch_employee_for_oldage(emp_id: str) -> dict | None:
    """
    Prefer full Met2 lookup. If that returns None (e.g. missing emp_class),
    still return identity + DOB + separation so the Old Age screen can open
    and the user can enter scale / last pay manually.
    """
    emp_key = _emp_key(emp_id)
    if not emp_key:
        return None

    data = fetch_employee_for_methodology2(emp_key)
    if data:
        dob = fetch_employee_dob(emp_key)
        data["date_of_birth"] = dob.isoformat() if dob else None
        data["dob"] = data["date_of_birth"]
        return data

    per = FiXxMhEmpPer.objects.filter(emp_cd=emp_key).first()
    if not per:
        # Try pensioner-only existence
        name = _pensioner_name(emp_key)
        dob = fetch_employee_dob(emp_key)
        if not name and not dob:
            return None
        return {
            "emp_id": emp_key,
            "name": name or emp_key,
            "separation_date": None,
            "scale": "",
            "last_pay": None,
            "category": "3",
            "date_of_birth": dob.isoformat() if dob else None,
            "dob": dob.isoformat() if dob else None,
            "data_source": "soft_oldage",
            "warning": (
                "Employee found for old-age (limited master). "
                "Enter separation date, scale and last pay manually for Met2 calc."
            ),
        }

    adm = FiXxMhEmpAdm.objects.filter(emp_cd=emp_key).first()
    fin = FiXxMhEmpFin.objects.filter(emp_cd=emp_key).first()
    sep = None
    if adm:
        sep = adm.separation_dt or adm.exp_ret_dt
    dob = fetch_employee_dob(emp_key)
    emp_class = _employee_class(fin, None)
    category = category_from_emp_class(emp_class) or "3"
    name = _full_name(per) or _pensioner_name(emp_key)

    return {
        "emp_id": emp_key,
        "name": name,
        "separation_date": _format_date_for_input(sep),
        "scale": "",
        "last_pay": None,
        "oracle_scale_sl": str(getattr(fin, "scale_sl", "") or "").strip(),
        "emp_class": emp_class or "",
        "category": category,
        "date_of_birth": dob.isoformat() if dob else None,
        "dob": dob.isoformat() if dob else None,
        "data_source": "soft_oldage",
        "warning": (
            "Met2 auto-scale/pay not available for this employee "
            "(missing class/scale/finscale). "
            "DOB and separation loaded — enter scale and last pay to calculate, "
            "or old-age periods still work once Met2 pension & M1 amounts are known."
        ),
    }
