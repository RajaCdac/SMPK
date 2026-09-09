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


def _cpi_number_from_revision(revision):
    """Extract CPI points from a revision label, e.g. '2017(277 CPI)' → 277."""
    import re

    match = re.search(r"\((\d+)\s*CPI\)", str(revision or ""), re.I)
    if not match:
        return None
    try:
        return int(match.group(1))
    except (TypeError, ValueError):
        return None


def _resolve_retirement_cpi(claim, fp, pensioner, retirement_dt):
    """
    CPI at retirement / separation — for sanction header "On CPI".

    Prefer claim RETIREMENT_CPI; else derive from retirement date.
    Do not use process/current CPI (e.g. 359 after upgrade).
    """
    n = _num(claim.get("retirement_cpi"))
    if n is not None and n > 0:
        return float(int(n)) if float(n).is_integer() else float(n)

    if retirement_dt:
        try:
            from methodology1.services.revision_resolver import get_revision_column

            dt = retirement_dt
            if isinstance(dt, date) and not isinstance(dt, datetime):
                dt = datetime(dt.year, dt.month, dt.day)
            cpi = _cpi_number_from_revision(get_revision_column(dt))
            if cpi is not None:
                return float(cpi)
        except Exception:
            pass

    # Last resort only — these fields may already reflect a later upgrade.
    for src in (fp.get("base_cpi"), pensioner.get("base_cpi")):
        n = _num(src)
        if n is not None and n > 0:
            return float(int(n)) if float(n).is_integer() else float(n)
    return None


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
                SELECT CLMCA_ID, CLM_CA_TYPE, CA_NO, EMP_CD, APPCN_NO, APPCN_DATE,
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
                SELECT CLMCA_ID, CLM_CA_TYPE, CA_NO, EMP_CD, APPCN_NO, APPCN_DATE,
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


def _fetch_fin(emp_cd):
    with connection.cursor() as cur:
        cur.execute(
            """
            SELECT EMP_CLASS, SCALE_SL
            FROM fi_xx_mh_emp_fin
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
                       ORIGINAL_DOUBLE_FPENSION_AMT, DOUBLE_FPENSION_UPTO,
                       BASE_CPI, WEF_DT, APP_CLASS,
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
                   ORIGINAL_DOUBLE_FPENSION_AMT, DOUBLE_FPENSION_UPTO,
                   BASE_CPI, WEF_DT, APP_CLASS,
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


def _wef_date(claim, fp):
    wef = _as_date(fp.get("wef_dt"))
    if wef:
        return wef
    dod = _as_date(claim.get("dod_emp_pensioner"))
    if dod:
        return dod + timedelta(days=1)
    m = claim.get("fpen_start_mnth")
    y = claim.get("fprn_start_yr")
    try:
        if m and y:
            return date(int(y), int(m), 1)
    except (TypeError, ValueError):
        pass
    return None


def _pick_fp_amount_and_cpi(m1_result, preferred_cpi=None):
    """
    Same band selection as First FP generation (_m1_amount_and_cpi):
    honour claim RETIREMENT_CPI (277/359) when set; else latest band.
    """
    if not m1_result or m1_result.get("error"):
        return None, None
    fp_359 = _num(m1_result.get("FP_359_cpi"))
    fp_277 = _num(m1_result.get("FP_277_cpi"))
    pref = None
    if preferred_cpi not in (None, ""):
        try:
            pref = int(float(preferred_cpi))
        except (TypeError, ValueError):
            pref = None
    if pref == 277 and fp_277 is not None and fp_277 > 0:
        return float(int(round(fp_277))), 277
    if pref == 359 and fp_359 is not None and fp_359 > 0:
        return float(int(round(fp_359))), 359
    if fp_359 is not None and fp_359 > 0:
        return float(int(round(fp_359))), 359
    if fp_277 is not None and fp_277 > 0:
        return float(int(round(fp_277))), 277
    return None, None


def _recompute_fp_single_rate(claim, fp, pensioner, adm, emp, sep_dt, last_pay):
    """
    Mirror First FP generate: class 1/2 → officer chain; class 3/4 → M1 CPI chain.
    """
    from family_pension.services.class12_fp_service import (
        calculate_class12_family_pension_for_fp,
        load_familypensioner_app_class,
        resolve_category_for_fp,
    )
    from methodology1.services.family_pension_calculation_service import (
        calculate_family_pension,
    )

    fin = _fetch_fin(emp)
    familypensioner_app_class = fp.get("app_class") or load_familypensioner_app_class(emp)
    category = resolve_category_for_fp(
        claim,
        fin,
        pensioner,
        familypensioner_app_class=familypensioner_app_class,
    )
    scale = _clip(claim.get("scale_cd")) or _clip(fin.get("scale_sl")) or None
    preferred_cpi = (
        _num(claim.get("retirement_cpi"))
        or _num(fp.get("base_cpi"))
        or _num(pensioner.get("base_cpi"))
    )
    if not sep_dt or not last_pay or last_pay <= 0:
        return None, None, category, scale

    try:
        if category in ("1", "2"):
            m1 = calculate_class12_family_pension_for_fp(
                separation_date=sep_dt.isoformat(),
                last_pay=last_pay,
                scale=scale,
            )
        else:
            m1 = calculate_family_pension(
                separation_date=sep_dt.isoformat(),
                category=category,
                pay=last_pay,
                scale=scale,
            )
    except Exception:
        return None, None, category, scale

    amt, cpi = _pick_fp_amount_and_cpi(m1, preferred_cpi=preferred_cpi)
    return amt, cpi, category, scale


def _family_pension_amounts(claim, fp, pensioner, adm, per, emp):
    """
    Resolve single / double monthly rates and double upto for the print text.

    Recomputes using the same class + Methodology path as First FP generation
    (class 1/2 officer chain; class 3/4 generic M1), with RETIREMENT_CPI band pick.
    """
    from family_pension.services.double_fpension_service import (
        compute_double_family_pension,
        resolve_double_fpen_upto,
        _truthy_eligibility,
    )

    eligible = _truthy_eligibility(claim.get("double_fpen_eligibility"))
    single = _num(fp.get("original_single_fpension_amt"))
    if single is None:
        single = _num(fp.get("original_family_pension_amt"))
    double = _num(fp.get("original_double_fpension_amt"))
    double_upto = _as_date(fp.get("double_fpension_upto")) or _as_date(
        claim.get("double_fpen_upto")
    )
    wef = _wef_date(claim, fp)

    last_pay = (
        _num(claim.get("last_basic_at_ret"))
        or _num(pensioner.get("pension_emoluments"))
        or 0
    )
    sep_dt = (
        _as_date(adm.get("separation_dt"))
        or _as_date(pensioner.get("emp_ret_dt"))
        or _as_date(fp.get("emp_ret_dt"))
    )
    ret_dt = sep_dt
    dod = _as_date(claim.get("dod_emp_pensioner"))
    emp_dob = _as_date(per.get("birth_dt"))

    m1_single, process_cpi, category, scale = _recompute_fp_single_rate(
        claim, fp, pensioner, adm, emp, sep_dt, last_pay
    )
    if m1_single is not None:
        single = m1_single

    if eligible and dod and wef and (last_pay > 0) and single:
        try:
            bill_m = wef.month
            bill_y = wef.year
            dbl = compute_double_family_pension(
                claim=claim,
                emp_dob=emp_dob,
                single_fp_rate=float(single),
                last_basic=float(last_pay),
                dod=dod,
                retirement_dt=ret_dt,
                original_pension_amt=_num(pensioner.get("original_pension_amt")),
                wef=wef,
                bill_month=bill_m,
                bill_year=bill_y,
                separation_date=sep_dt,
                category=category,
                scale=scale,
                separation_type=adm.get("separation_type"),
                exp_ret_dt=_as_date(adm.get("exp_ret_dt")),
            )
            double = dbl.double_rate
            double_upto = dbl.double_fpen_upto
        except Exception:
            if not double_upto and emp_dob and (sep_dt or dod):
                try:
                    double_upto = resolve_double_fpen_upto(
                        separation_dt=sep_dt,
                        emp_dob=emp_dob,
                        emp_class=category,
                        claim_upto=None,
                        dod=dod,
                        separation_type=adm.get("separation_type"),
                        exp_ret_dt=_as_date(adm.get("exp_ret_dt")),
                    )
                except Exception:
                    pass

    return {
        "eligible": eligible,
        "single": single,
        "double": double,
        "double_upto": double_upto,
        "wef": wef,
        "process_cpi": process_cpi,
        "emp_class": category,
    }


def _build_notes(claim, fp, base_cpi, amounts=None):
    """
    Print notes matching FI_PN_MH_FPENSION_PROPOSAL / sample sanction:

    Double / full-pension case:
      Family pension to be paid @ <full> P.M. w.e.f. <wef> to <double_upto>
      and thereafter @ <single> P.M. w.e.f. <double_upto+1>
      till Death or Re-Marriage whichever is earlier.

    Normal:
      Family pension to be paid @ <single> P.M. w.e.f. <wef>
      till Death or Re-Marriage whichever is earlier.
    """
    notes = []
    amounts = amounts or {}
    eligible = amounts.get("eligible")
    if eligible is None:
        eligible = claim.get("double_fpen_eligibility") in (1, "1", True)

    single = amounts.get("single")
    if single is None:
        single = _num(fp.get("original_single_fpension_amt")) or _num(
            fp.get("original_family_pension_amt")
        )
    double = amounts.get("double")
    if double is None:
        double = _num(fp.get("original_double_fpension_amt"))
    wef = amounts.get("wef") or _wef_date(claim, fp)
    double_upto = amounts.get("double_upto") or _as_date(
        claim.get("double_fpen_upto")
    ) or _as_date(fp.get("double_fpension_upto"))

    wef_s = _fmt_dd_mm_yyyy(wef)
    if (
        eligible
        and double is not None
        and single is not None
        and wef
        and double_upto
    ):
        thereafter = double_upto + timedelta(days=1)
        notes.append(
            f"Family pension to be paid @ {_fmt_amount_int(double)} P.M. "
            f"w.e.f. {wef_s} to {_fmt_dd_mm_yyyy(double_upto)} "
            f"and thereafter @ {_fmt_amount_int(single)} P.M. "
            f"w.e.f. {_fmt_dd_mm_yyyy(thereafter)} "
            f"till Death or Re-Marriage whichever is earlier."
        )
    elif single is not None:
        notes.append(
            f"Family pension to be paid @ {_fmt_amount_int(single)} P.M. "
            f"w.e.f. {wef_s} till Death or Re-Marriage whichever is earlier."
        )
    elif double is not None:
        notes.append(
            f"Family pension to be paid @ {_fmt_amount_int(double)} P.M. "
            f"w.e.f. {wef_s} till Death or Re-Marriage whichever is earlier."
        )

    notes.append("Submitted to the FA & CAO for sanction.")

    # Relief line uses calculated pension CPI (process band), not retirement CPI.
    cpi = amounts.get("process_cpi")
    if cpi is None:
        cpi = _num(base_cpi)
    if cpi is not None:
        notes.append(f"Relief to be given over {int(cpi)} CPI.")

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

    amounts = _family_pension_amounts(
        claim, fp, pensioner, adm, per, emp
    )

    # Header "On CPI" = CPI at retirement, not process/current band (often 359).
    retirement_cpi = _resolve_retirement_cpi(
        claim, fp, pensioner, retirement_dt
    )
    # Notes / relief line use calculated (process) CPI when available.
    process_cpi = amounts.get("process_cpi")
    base_cpi = (
        process_cpi
        or retirement_cpi
        or fp.get("base_cpi")
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
        "last_pension_basic": _fmt_amount_int(
            pensioner.get("original_pension_amt")
            or pensioner.get("payable_pension")
        ),
        "on_cpi": (
            str(int(retirement_cpi))
            if _num(retirement_cpi) is not None
            else ""
        ),
        "entered_service": _fmt_dd_mm_yyyy(join_dt),
        "retired_from": _fmt_dd_mm_yyyy(retirement_dt),
        "retirement_reason": _retirement_reason_and_age(
            adm, per, retirement_dt
        ),
        "notes": _build_notes(claim, fp, base_cpi, amounts=amounts),
        "remarks": _build_remarks(emp_name, join_dt, retirement_dt, dod),
        # detail fields for frontend if needed later
        "family_pension_single": _fmt_amount_int(amounts.get("single")),
        "family_pension_double": _fmt_amount_int(amounts.get("double")),
        "double_fpen_upto": _fmt_dd_mm_yyyy(amounts.get("double_upto")),
        "wef_dt": _fmt_dd_mm_yyyy(amounts.get("wef")),
        "double_eligible": bool(amounts.get("eligible")),
    }

    return {
        "org_name": ORG_NAME,
        "report_title": REPORT_TITLE,
        "run_date": _fmt_run_date(),
        "pages": [page],
    }
