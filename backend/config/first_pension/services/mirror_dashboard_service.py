"""Dashboard retirement list from MySQL Oracle mirror tables."""

import calendar

from employee.oracle_mirror import (
    FiXxMdFinscale,
    FiXxMhEmpAdm,
    FiXxMhEmpData,
    FiXxMhEmpFin,
    FiXxMhEmpPer,
)
from employee.services.emp_data_service import (
    fetch_emp_data_posting,
    resolve_posting_designation_display,
)
from employee.services.employee_mirror_service import _full_name, _map_emp_class
from employee.services.scale_desc_service import batch_fetch_scale_desc_map
from employee.utils.age import calculate_age
from employee.utils.display_format import normalize_department_name
from master_data.models import FiXxMhDesig
from methodology1.services.oracle_employee_service import extract_scale_cd
from methodology2.services.oracle_employee_service import resolve_scale_display

_RETIREMENT_ADM_WHERE = """
    exp_ret_dt IS NOT NULL
    AND (separation_type IS NULL OR UPPER(TRIM(separation_type)) NOT IN ('VR', 'DT'))
    AND MONTH(DATE_SUB(exp_ret_dt, INTERVAL 1 DAY)) = %s
    AND YEAR(DATE_SUB(exp_ret_dt, INTERVAL 1 DAY)) = %s
"""


def _month_shift(month, year, delta):
    month += delta
    while month < 1:
        month += 12
        year -= 1
    while month > 12:
        month -= 12
        year += 1
    return month, year


def _format_dd_mm_yyyy(value):
    if not value:
        return None
    if hasattr(value, "strftime"):
        return value.strftime("%d-%m-%Y")
    return str(value)[:10]


def _count_retirements(month, year):
    return FiXxMhEmpAdm.objects.extra(
        where=[_RETIREMENT_ADM_WHERE],
        params=[month, year],
    ).count()


def _latest_finscale_map(emp_codes):
    rows = (
        FiXxMdFinscale.objects.filter(emp_cd__in=emp_codes)
        .order_by("emp_cd", "-wef_dt", "-sl_no")
    )
    result = {}
    for row in rows:
        if row.emp_cd not in result:
            result[row.emp_cd] = row
    return result


def _basic_amount(finscale):
    if not finscale:
        return None
    if finscale.basic_amt is not None:
        return float(finscale.basic_amt)
    if finscale.stag_pay_amt is not None:
        return float(finscale.stag_pay_amt)
    return None


def _build_row(adm, per, fin, finscale, emp_data, *, scale_desc_map=None):
    scale_sl = ""
    if fin and str(fin.scale_sl or "").strip():
        scale_sl = str(fin.scale_sl).strip()
    elif finscale and str(finscale.scale_sl or "").strip():
        scale_sl = str(finscale.scale_sl).strip()

    posting = fetch_emp_data_posting(adm.emp_cd)
    desig_desc = ""
    if adm.desig_cd is not None:
        desig_row = FiXxMhDesig.objects.filter(desig_cd=adm.desig_cd).first()
        if desig_row and desig_row.desig_desc:
            desig_desc = desig_row.desig_desc
        elif posting and posting.get("desig"):
            desig_desc = posting["desig"]

    dept_desc = posting.get("dept_desc") if posting else ""
    designation = resolve_posting_designation_display(
        dept_desc=dept_desc,
        desig_desc=desig_desc,
        alloc_desc=posting.get("alloc_desc") if posting else "",
    )

    emp_class = ""
    if emp_data and str(emp_data.emp_class or "").strip():
        emp_class = _map_emp_class(emp_data.emp_class)
    elif fin and fin.emp_class is not None:
        emp_class = _map_emp_class(fin.emp_class)

    return {
        "emp_code": adm.emp_cd,
        "name": _full_name(per) if per else "",
        "joining_date": _format_dd_mm_yyyy(adm.join_dt),
        "retirement_date": _format_dd_mm_yyyy(adm.exp_ret_dt),
        "birth_date": _format_dd_mm_yyyy(per.birth_dt if per else None),
        "age_on_appointment": (
            calculate_age(per.birth_dt, adm.join_dt)
            if per and per.birth_dt and adm.join_dt
            else None
        ),
        "age_on_retirement": (
            calculate_age(per.birth_dt, adm.exp_ret_dt)
            if per and per.birth_dt and adm.exp_ret_dt
            else None
        ),
        "department": normalize_department_name(dept_desc),
        "designation": designation,
        "scale": (
            resolve_scale_display(
                scale_sl,
                adm.exp_ret_dt,
                scale_desc_map=scale_desc_map,
            )
            or scale_sl
        ),
        "scale_code": scale_sl,
        "last_basic": _basic_amount(finscale),
        "class": emp_class,
    }


def fetch_dashboard_from_mirror(month, year):
    """Same response shape as oracle_dashboard_service.fetch_dashboard_payload."""
    month = int(month)
    year = int(year)
    prev_month, prev_year = _month_shift(month, year, -1)
    next_month, next_year = _month_shift(month, year, 1)

    adms = list(
        FiXxMhEmpAdm.objects.extra(
            where=[_RETIREMENT_ADM_WHERE],
            params=[month, year],
        ).order_by("emp_cd")
    )
    emp_codes = [adm.emp_cd for adm in adms]

    per_map = {
        row.emp_cd: row
        for row in FiXxMhEmpPer.objects.filter(emp_cd__in=emp_codes)
    }
    fin_map = {
        row.emp_cd: row
        for row in FiXxMhEmpFin.objects.filter(emp_cd__in=emp_codes)
    }
    finscale_map = _latest_finscale_map(emp_codes)
    emp_data_map = {
        row.emp_cd: row
        for row in FiXxMhEmpData.objects.filter(emp_cd__in=emp_codes)
    }

    scale_cds = set()
    for adm in adms:
        fin = fin_map.get(adm.emp_cd)
        finscale = finscale_map.get(adm.emp_cd)
        scale_sl = ""
        if fin and str(fin.scale_sl or "").strip():
            scale_sl = str(fin.scale_sl).strip()
        elif finscale and str(finscale.scale_sl or "").strip():
            scale_sl = str(finscale.scale_sl).strip()
        scale_cd = extract_scale_cd(scale_sl)
        if scale_cd:
            scale_cds.add(scale_cd)
    scale_desc_map = batch_fetch_scale_desc_map(scale_cds)

    retirement_list = []
    for adm in adms:
        per = per_map.get(adm.emp_cd)
        if not per:
            continue
        retirement_list.append(
            _build_row(
                adm,
                per,
                fin_map.get(adm.emp_cd),
                finscale_map.get(adm.emp_cd),
                emp_data_map.get(adm.emp_cd),
                scale_desc_map=scale_desc_map,
            )
        )

    def month_label(m, y):
        return f"{calendar.month_name[m]} {y}"

    return {
        "total_employees": FiXxMhEmpPer.objects.count(),
        "retirement_count": len(retirement_list),
        "retirement_list": retirement_list,
        "prev_month_count": _count_retirements(prev_month, prev_year),
        "next_month_count": _count_retirements(next_month, next_year),
        "prev_month_label": month_label(prev_month, prev_year),
        "this_month_label": month_label(month, year),
        "next_month_label": month_label(next_month, next_year),
        "retirement_month": month,
        "retirement_year": year,
    }
