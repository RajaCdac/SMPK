"""
Recommendation & Sanction of Family Pension report
(FI_PN_MH_FPENSION_PROPOSAL_RPT.fmb → fi_pn_mh_Fpension_Appl).
"""

from __future__ import annotations

from datetime import date, datetime, timedelta
from decimal import Decimal

from django.db import connection
from django.utils import timezone

from employee.utils.age import calculate_age


class FamilyPensionProposalReportError(Exception):
    pass


ORG_NAME = "SYAMA PRASAD MOOKERJEE PORT, KOLKATA"
REPORT_TITLE = "RECOMENDATION AND SANCTION OF FAMILY PENSION (NORMAL)"


def _clip(value, max_len=None, default=""):
    if value is None:
        return default
    text = str(value).strip()
    if not text:
        return default
    if max_len:
        return text[:max_len]
    return text


def _as_date(value):
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    text = str(value).strip()[:10]
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    return None


def _fmt_dd_mm_yyyy(value):
    dt = _as_date(value)
    if not dt:
        return ""
    return dt.strftime("%d/%m/%Y")


def _fmt_run_date(value=None):
    dt = value or timezone.localdate()
    if hasattr(dt, "strftime"):
        return dt.strftime("%d/%m/%y")
    return str(dt)


def _num(value):
    if value is None or value == "":
        return None
    if isinstance(value, Decimal):
        return float(value)
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _fmt_amount_int(value):
    n = _num(value)
    if n is None:
        return ""
    return str(int(round(n)))


def _emp_key(emp_cd):
    text = _clip(emp_cd, 5)
    if text.isdigit() and len(text) < 5:
        return text.zfill(5)
    return text


def _clean_name(name):
    text = " ".join(str(name or "").split()).upper()
    for prefix in ("MRS.", "MR.", "MS.", "MISS.", "SHRI.", "SMT.", "LT."):
        if text.startswith(prefix + " "):
            return text[len(prefix) :].strip()
    return text


def _pension_scheme_label(option):
    opt = (option or "G").strip().upper()
    if opt.startswith("P"):
        return "Port line"
    return "Government Line"


def _relation_label(relation_cd, fallback=""):
    if relation_cd in (None, ""):
        return _clip(fallback).upper()
    try:
        code = int(relation_cd)
    except (TypeError, ValueError):
        return _clip(fallback).upper() or _clip(relation_cd).upper()

    with connection.cursor() as cur:
        cur.execute(
            """
            SELECT RELATION_DESC
            FROM fi_pm_mh_relation
            WHERE RELATION_CD = %s
            LIMIT 1
            """,
            [code],
        )
        row = cur.fetchone()
    if row and row[0]:
        return str(row[0]).strip().upper()
    return _clip(fallback).upper() or str(code)


def _desig_desc(desig_cd):
    if desig_cd in (None, ""):
        return ""
    try:
        code = int(desig_cd)
    except (TypeError, ValueError):
        return ""
    with connection.cursor() as cur:
        cur.execute(
            "SELECT DESIG_DESC FROM fi_xx_mh_desig WHERE DESIG_CD = %s LIMIT 1",
            [code],
        )
        row = cur.fetchone()
    return str(row[0]).strip().upper() if row and row[0] else ""


def _fetch_claim(clmca_id=None, emp_cd=None):
    with connection.cursor() as cur:
        if clmca_id:
            cur.execute(
                """
                SELECT CLMCA_ID, CLM_CA_TYPE, CA_NO, EMP_CD, APPCN_NO,
                       APPLICANT_NAME, APPLICANT_TYPE, DOD_EMP_PENSIONER,
                       GURDIAN_RELATION_CD, SERVICE_PENSION_AMT,
                       FPEN_START_MNTH, FPRN_START_YR, RETIREMENT_CPI,
                       PENSION_OPT, LAST_BASIC_AT_RET, EQUIV_PAY_AT_BASE_CPI,
                       DOUBLE_FPEN_ELIGIBILITY, DOUBLE_FPEN_UPTO, REMARKS
                FROM fi_pn_mh_fpen_caclaim
                WHERE CLMCA_ID = %s
                LIMIT 1
                """,
                [_clip(clmca_id, 20)],
            )
        elif emp_cd:
            cur.execute(
                """
                SELECT CLMCA_ID, CLM_CA_TYPE, CA_NO, EMP_CD, APPCN_NO,
                       APPLICANT_NAME, APPLICANT_TYPE, DOD_EMP_PENSIONER,
                       GURDIAN_RELATION_CD, SERVICE_PENSION_AMT,
                       FPEN_START_MNTH, FPRN_START_YR, RETIREMENT_CPI,
                       PENSION_OPT, LAST_BASIC_AT_RET, EQUIV_PAY_AT_BASE_CPI,
                       DOUBLE_FPEN_ELIGIBILITY, DOUBLE_FPEN_UPTO, REMARKS
                FROM fi_pn_mh_fpen_caclaim
                WHERE EMP_CD = %s
                ORDER BY DATE_MODIFIED DESC, DATE_CREATED DESC
                LIMIT 1
                """,
                [_emp_key(emp_cd)],
            )
        else:
            return None
        row = cur.fetchone()
        if not row:
            return None
        cols = [d[0].lower() for d in cur.description]
        return dict(zip(cols, row))


def _fetch_pensioner(emp_cd):
    with connection.cursor() as cur:
        cur.execute(
            """
            SELECT EMP_CD, NAME, CA_NUMBER, ORIGINAL_PENSION_AMT, PAYABLE_PENSION,
                   PENSION_EMOLUMENTS, BASE_CPI, DESIG_CD, EMP_RET_DT,
                   SINGLE_FPEN_AMT, DOUBLE_FPEN_AMT, PENSION_OPTION
            FROM fi_pn_mh_pensioner
            WHERE EMP_CD = %s
            LIMIT 1
            """,
            [_emp_key(emp_cd)],
        )
        row = cur.fetchone()
        if not row:
            return {}
        cols = [d[0].lower() for d in cur.description]
        return dict(zip(cols, row))


def _fetch_familypensioner(clmca_id, emp_cd):
    with connection.cursor() as cur:
        if clmca_id:
            cur.execute(
                """
                SELECT ORIGINAL_FAMILY_PENSION_AMT, ORIGINAL_SINGLE_FPENSION_AMT,
                       ORIGINAL_DOUBLE_FPENSION_AMT, BASE_CPI, WEF_DT,
                       EMP_RET_DT, DESIG_CD, FPENSION_ROLL_NO, PENSION_OPTION
                FROM fi_pn_mh_familypensioner
                WHERE CLMCA_ID = %s
                ORDER BY SL_NO
                LIMIT 1
                """,
                [_clip(clmca_id, 20)],
            )
            row = cur.fetchone()
            if row:
                cols = [d[0].lower() for d in cur.description]
                return dict(zip(cols, row))
        cur.execute(
            """
            SELECT ORIGINAL_FAMILY_PENSION_AMT, ORIGINAL_SINGLE_FPENSION_AMT,
                   ORIGINAL_DOUBLE_FPENSION_AMT, BASE_CPI, WEF_DT,
                   EMP_RET_DT, DESIG_CD, FPENSION_ROLL_NO, PENSION_OPTION
            FROM fi_pn_mh_familypensioner
            WHERE EMP_CD = %s
            ORDER BY SL_NO
            LIMIT 1
            """,
            [_emp_key(emp_cd)],
        )
        row = cur.fetchone()
        if not row:
            return {}
        cols = [d[0].lower() for d in cur.description]
        return dict(zip(cols, row))


def _fetch_adm(emp_cd):
    with connection.cursor() as cur:
        cur.execute(
            """
            SELECT JOIN_DT, SEPARATION_DT, SEPARATION_TYPE, DESIG_CD, EXP_RET_DT
            FROM fi_xx_mh_emp_adm
            WHERE EMP_CD = %s
            LIMIT 1
            """,
            [_emp_key(emp_cd)],
        )
        row = cur.fetchone()
        if not row:
            return {}
        cols = [d[0].lower() for d in cur.description]
        return dict(zip(cols, row))


def _fetch_per(emp_cd):
    with connection.cursor() as cur:
        cur.execute(
            """
            SELECT TITLE, FIRST_NAME, MIDDLE_NAME, LAST_NAME, BIRTH_DT, SEX
            FROM fi_xx_mh_emp_per
            WHERE EMP_CD = %s
            LIMIT 1
            """,
            [_emp_key(emp_cd)],
        )
        row = cur.fetchone()
        if not row:
            return {}
        cols = [d[0].lower() for d in cur.description]
        return dict(zip(cols, row))


def _employee_name(pensioner, per):
    if pensioner.get("name"):
        return _clean_name(pensioner["name"])
    parts = [
        per.get("first_name"),
        per.get("middle_name"),
        per.get("last_name"),
    ]
    return _clean_name(" ".join(p for p in parts if p and str(p).strip()))


def _beneficiary_name(claim, relation, emp_name):
    applicant = _clean_name(claim.get("applicant_name"))
    rel = _clip(relation).upper() or "WIFE"
    deceased = _clip(emp_name).upper()
    if applicant and deceased:
        return f"{applicant} {rel} of LT. {deceased}"
    if applicant:
        return applicant
    return deceased


def _retirement_reason_and_age(adm, per, retirement_dt):
    sep_type = _clip(adm.get("separation_type")).upper()
    reason = "Retired"
    if sep_type in ("DE", "D"):
        reason = "Died"
    elif sep_type in ("VR",):
        reason = "Voluntarily Retired"
    elif sep_type in ("RE",):
        reason = "Resigned"

    age = calculate_age(_as_date(per.get("birth_dt")), _as_date(retirement_dt))
    if not age:
        return reason
    return (
        f"{reason} {age['years']}years {age['months']}months {age['days']}days"
    )


def _family_pension_amount(claim, fp):
    double_eligible = claim.get("double_fpen_eligibility") in (1, "1", True)
    if double_eligible and _num(fp.get("original_double_fpension_amt")) is not None:
        return _num(fp.get("original_double_fpension_amt"))
    if _num(fp.get("original_single_fpension_amt")) is not None:
        return _num(fp.get("original_single_fpension_amt"))
    if _num(fp.get("original_family_pension_amt")) is not None:
        return _num(fp.get("original_family_pension_amt"))
    return None


def _wef_date(claim, fp):
    wef = _as_date(fp.get("wef_dt"))
    if wef:
        return wef
    dod = _as_date(claim.get("dod_emp_pensioner"))
    if dod:
        return dod + timedelta(days=1)
    # start month/year from claim
    m = claim.get("fpen_start_mnth")
    y = claim.get("fprn_start_yr")
    try:
        if m and y:
            return date(int(y), int(m), 1)
    except (TypeError, ValueError):
        pass
    return None


def _build_notes(claim, fp, base_cpi):
    notes = []
    amt = _family_pension_amount(claim, fp)
    wef = _fmt_dd_mm_yyyy(_wef_date(claim, fp))
    if amt is not None:
        notes.append(
            f"Family pension to be paid @ {_fmt_amount_int(amt)} P.M. "
            f"w.e.f. {wef} till Death or Re-Marriage whichever is earlier."
        )
    notes.append("Submitted to the FA & CAO for sanction.")
    cpi = _num(base_cpi)
    if cpi is not None:
        notes.append(f"Relief to be given over {int(cpi)}")
    return notes


def _build_remarks(emp_name, join_dt, retirement_dt, dod):
    name = _clip(emp_name).upper() or "Employee"
    parts = [
        f"{name} entered in C.P.T service on & from {_fmt_dd_mm_yyyy(join_dt)} "
        f"and retired on {_fmt_dd_mm_yyyy(retirement_dt)}"
    ]
    if dod:
        parts.append(f"and subsequently Died On {_fmt_dd_mm_yyyy(dod)}")
    narrative = " ".join(parts) + "."
    boilerplate = (
        "as per 'E Form attached.\n"
        "In terms of lib . Pension rules and family pension Scheme."
    )
    return f"{narrative}\n{boilerplate}"


def build_family_pension_proposal_report(*, clmca_id=None, emp_cd=None):
    claim = _fetch_claim(clmca_id=clmca_id, emp_cd=emp_cd)
    if not claim:
        raise FamilyPensionProposalReportError(
            "Family pension claim not found. Save the claim first."
        )

    emp = _emp_key(claim.get("emp_cd") or emp_cd)
    pensioner = _fetch_pensioner(emp)
    fp = _fetch_familypensioner(claim.get("clmca_id"), emp)
    adm = _fetch_adm(emp)
    per = _fetch_per(emp)

    emp_name = _employee_name(pensioner, per)
    relation = _relation_label(
        claim.get("gurdian_relation_cd"),
        fallback="",
    )
    # Oracle sample uses WIFE for relation_cd 1
    if not relation and str(claim.get("gurdian_relation_cd") or "") == "1":
        relation = "WIFE"

    desig_cd = (
        fp.get("desig_cd")
        or pensioner.get("desig_cd")
        or adm.get("desig_cd")
    )
    designation = _desig_desc(desig_cd)

    pension_opt = (
        claim.get("pension_opt")
        or fp.get("pension_option")
        or pensioner.get("pension_option")
        or "G"
    )
    department = _pension_scheme_label(pension_opt)

    join_dt = adm.get("join_dt")
    retirement_dt = (
        fp.get("emp_ret_dt")
        or pensioner.get("emp_ret_dt")
        or adm.get("separation_dt")
        or adm.get("exp_ret_dt")
    )
    dod = claim.get("dod_emp_pensioner")

    base_cpi = (
        fp.get("base_cpi")
        or claim.get("retirement_cpi")
        or pensioner.get("base_cpi")
    )

    pay = claim.get("last_basic_at_ret")
    report_no = _clip(claim.get("ca_no")) or _clip(pensioner.get("ca_number"))

    page = {
        "page_no": 1,
        "total_pages": 1,
        "report_no": report_no,
        "clmca_id": _clip(claim.get("clmca_id")),
        "name": _beneficiary_name(claim, relation, emp_name),
        "emp_cd": emp,
        "designation": designation,
        "department": department,
        "pay": _fmt_amount_int(pay),
        "last_pension_basic": "",
        "on_cpi": "",
        "entered_service": _fmt_dd_mm_yyyy(join_dt),
        "retired_from": _fmt_dd_mm_yyyy(retirement_dt),
        "retirement_reason": _retirement_reason_and_age(
            adm, per, retirement_dt
        ),
        "notes": _build_notes(claim, fp, base_cpi),
        "remarks": _build_remarks(emp_name, join_dt, retirement_dt, dod),
    }

    return {
        "org_name": ORG_NAME,
        "report_title": REPORT_TITLE,
        "run_date": _fmt_run_date(),
        "pages": [page],
    }
