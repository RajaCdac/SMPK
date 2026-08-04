"""Load employee master / separation from MySQL Oracle mirror tables."""

from datetime import date, datetime

from employee.oracle_mirror import FiXxMdFinscale, FiXxMhEmpAdm, FiXxMhEmpFin, FiXxMhEmpPer
from employee.utils.age import calculate_age
from employee.services.emp_data_service import (
    fetch_emp_data_posting,
    resolve_posting_designation_display,
)
from employee.utils.display_format import normalize_department_name
from methodology2.services.oracle_employee_service import resolve_scale_display


def _emp_key(emp_code):
    return str(emp_code).strip()[:5]


def _format_dd_mm_yyyy(value):
    if not value:
        return None
    if isinstance(value, datetime):
        value = value.date()
    if isinstance(value, date):
        return value.strftime("%d-%m-%Y")
    return str(value)[:10]


def _format_iso_date(value):
    if not value:
        return ""
    if isinstance(value, datetime):
        value = value.date()
    if isinstance(value, date):
        return value.strftime("%Y-%m-%d")
    return str(value)[:10]


def _full_name(per):
    if not per:
        return ""
    parts = [per.title, per.first_name, per.middle_name, per.last_name]
    return " ".join(str(p).strip() for p in parts if p and str(p).strip()).strip()


def _map_emp_class(value):
    if value is None or value == "":
        return ""
    text = str(value).strip().upper()
    if text in {"I", "II", "III", "IV"}:
        return text
    mapping = {1: "I", 2: "II", 3: "III", 4: "IV"}
    try:
        return mapping.get(int(value), text)
    except (TypeError, ValueError):
        return text


def _latest_finscale(emp_cd):
    return (
        FiXxMdFinscale.objects.filter(emp_cd=emp_cd)
        .order_by("-wef_dt", "-sl_no")
        .first()
    )


def fetch_emp_adm_separation_from_mirror(emp_code):
    adm = FiXxMhEmpAdm.objects.filter(emp_cd=_emp_key(emp_code)).first()
    if not adm:
        return None
    if not (adm.separation_type or "").strip() and not adm.separation_dt:
        return None
    return {
        "separation_type": (adm.separation_type or "").strip(),
        "separation_date": _format_iso_date(adm.separation_dt),
        "remarks": (adm.termin_remark or "").strip(),
    }


def load_employee_from_mirror(emp_code):
    """
    Build employee-search shaped dict from fi_xx_mh_emp_* mirror tables.
    Returns None when PER row is missing.
    """
    emp_key = _emp_key(emp_code)
    per = FiXxMhEmpPer.objects.filter(emp_cd=emp_key).first()
    if not per:
        return None

    adm = FiXxMhEmpAdm.objects.filter(emp_cd=emp_key).first()
    fin = FiXxMhEmpFin.objects.filter(emp_cd=emp_key).first()
    finscale = _latest_finscale(emp_key)

    join_dt = adm.join_dt if adm else None
    exp_ret_dt = (adm.exp_ret_dt if adm else None) or (
        adm.separation_dt if adm else None
    )
    birth_dt = per.birth_dt
    scale_sl = (fin.scale_sl if fin and fin.scale_sl else "") or (
        finscale.scale_sl if finscale else ""
    )
    basic_amt = None
    if finscale and finscale.basic_amt is not None:
        basic_amt = float(finscale.basic_amt)
    elif finscale and finscale.stag_pay_amt is not None:
        basic_amt = float(finscale.stag_pay_amt)

    scale_display = ""
    if scale_sl:
        try:
            scale_display = resolve_scale_display(scale_sl, exp_ret_dt) or str(scale_sl)
        except Exception:
            scale_display = str(scale_sl).strip()

    emp_class = _map_emp_class(fin.emp_class if fin else "")
    name = _full_name(per)

    posting = fetch_emp_data_posting(emp_key)
    desig_desc = ""
    if adm and adm.desig_cd is not None:
        from master_data.models import FiXxMhDesig

        desig_row = FiXxMhDesig.objects.filter(desig_cd=adm.desig_cd).first()
        if desig_row and desig_row.desig_desc:
            desig_desc = desig_row.desig_desc
        elif posting and posting.get("desig"):
            desig_desc = posting["desig"]

    department = ""
    designation = str(adm.desig_cd) if adm and adm.desig_cd is not None else ""
    if posting:
        department = normalize_department_name(posting.get("dept_desc"))
        designation = resolve_posting_designation_display(
            dept_desc=posting.get("dept_desc"),
            desig_desc=desig_desc or posting.get("desig"),
            alloc_desc=posting.get("alloc_desc"),
        )
    elif desig_desc:
        designation = resolve_posting_designation_display(desig_desc=desig_desc)

    return {
        "emp_id": emp_key,
        "name": name,
        "join_date": _format_dd_mm_yyyy(join_dt),
        "expected_retirement_date": _format_dd_mm_yyyy(exp_ret_dt),
        "birth_date": _format_dd_mm_yyyy(birth_dt),
        "department": department,
        "designation": designation,
        "scale": scale_display,
        "scale_code": str(scale_sl).strip() if scale_sl else "",
        "basic_amount": basic_amt,
        "class": emp_class,
        "age_on_appointment": (
            calculate_age(birth_dt, join_dt) if birth_dt and join_dt else None
        ),
        "age_on_retirement": (
            calculate_age(birth_dt, exp_ret_dt) if birth_dt and exp_ret_dt else None
        ),
        "partial": False,
        "data_source": "mirror",
    }


def resolve_pension_case_snapshot(emp_code, payload=None):
    """
    Fill PensionCase create/update fields from request payload + mirror tables.
    """
    payload = dict(payload or {})
    mirror = load_employee_from_mirror(emp_code) or {}

    def pick(*keys):
        for key in keys:
            val = payload.get(key)
            if val is not None and str(val).strip() != "":
                return val
        for key in keys:
            val = mirror.get(key)
            if val is not None and str(val).strip() != "":
                return val
        return None

    name = pick("name") or mirror.get("name") or f"Employee {_emp_key(emp_code)}"
    emp_class = pick("class") or mirror.get("class") or ""
    birth_date = pick("birth_date") or mirror.get("birth_date")
    joining_date = pick("joining_date", "join_date") or mirror.get("join_date")
    retirement_date = (
        pick("retirement_date", "expected_retirement_date")
        or mirror.get("expected_retirement_date")
    )
    designation = pick("designation") or mirror.get("designation") or ""
    scale = pick("scale") or mirror.get("scale") or ""
    last_basic = pick("last_basic", "basic_amount")
    if last_basic is None:
        last_basic = mirror.get("basic_amount")
    if last_basic is None:
        last_basic = 0

    sep_date = payload.get("separation_date")
    fallback_date = sep_date or retirement_date or joining_date or birth_date

    def parse_date(value):
        if not value:
            return None
        if hasattr(value, "strftime") and not isinstance(value, str):
            return value.date() if hasattr(value, "date") else value
        text = str(value).strip()
        for fmt in ("%Y-%m-%d", "%d-%m-%Y"):
            try:
                return datetime.strptime(text, fmt).date()
            except ValueError:
                continue
        return None

    birth_parsed = parse_date(birth_date) or parse_date(fallback_date)
    join_parsed = parse_date(joining_date) or parse_date(fallback_date)
    retire_parsed = parse_date(retirement_date) or parse_date(fallback_date)

    return {
        "name": str(name).strip()[:200],
        "emp_class": str(emp_class).strip()[:20],
        "birth_date": birth_parsed,
        "joining_date": join_parsed,
        "retirement_date": retire_parsed,
        "designation": str(designation).strip()[:200],
        "scale": str(scale).strip()[:100],
        "last_basic": last_basic,
    }
