"""
Family Pension Claim form — FI_PN_MH_FPENSION_CLAIM_E.fmb

Master: smpk_pension.fi_pn_mh_fpen_caclaim
Detail: smpk_pension.fi_pn_md_fpen_appcn
"""

from __future__ import annotations

from datetime import date, datetime, timedelta
from decimal import Decimal

from django.db import connections


def _fmt_date(value):
    if value is None:
        return ""
    if isinstance(value, datetime):
        return value.date().isoformat()
    if isinstance(value, date):
        return value.isoformat()
    text = str(value).strip()
    return text[:10] if text else ""


def _num(value):
    if value is None:
        return None
    if isinstance(value, Decimal):
        return float(value)
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _str(value):
    if value is None:
        return ""
    return str(value).strip()


def _normalize_emp_class(value):
    """Map APP_CLASS / CLASS to 1–4; blank if unknown."""
    if value in (None, ""):
        return ""
    text = str(value).strip().upper()
    mapping = {
        "I": "1",
        "II": "2",
        "III": "3",
        "IV": "4",
        "O": "1",
        "E": "3",
        "1": "1",
        "2": "2",
        "3": "3",
        "4": "4",
    }
    if text in mapping:
        return mapping[text]
    try:
        n = int(float(text))
    except (TypeError, ValueError):
        return ""
    return str(n) if n in (1, 2, 3, 4) else ""


def _lookup_familypensioner_app_class(cur, emp_cd: str):
    """APP_CLASS from fi_pn_mh_familypensioner (claim Class of emp)."""
    code = _str(emp_cd)[:5]
    if not code:
        return ""
    sql = """
        SELECT APP_CLASS
        FROM fi_pn_mh_familypensioner
        WHERE EMP_CD = %s
          AND APP_CLASS IS NOT NULL
          AND CAST(APP_CLASS AS CHAR) <> ''
        ORDER BY DATE_CREATED DESC
        LIMIT 1
    """
    try:
        cur.execute(sql, [code])
        row = cur.fetchone()
        if row and row[0] not in (None, ""):
            return _normalize_emp_class(row[0])
    except Exception:
        pass
    return ""


def empty_claim_form():
    now = datetime.now()
    return {
        "clmca_id": "",
        "clm_ca_type": "CA",
        "ca_no": "",
        "emp_cd": "",
        "disp_name": "",
        "appcn_no": "",
        "appcn_date": "",
        "appcn_status": "",
        "double_fpen_eligibility": 0,
        "double_fpen_upto": "",
        "emp_birth_dt": "",
        "separation_dt": "",
        "exp_ret_dt": "",
        "separation_type": "",
        "applicant_type": "",
        "applicant_name": "",
        "applicant_address": "",
        "dod_emp_pensioner": "",
        "gurdian_relation_cd": "",
        "disp_relation": "",
        "dob_guardian": "",
        "service_pension_amt": "",
        "fpen_start_mnth": now.month,
        "fprn_start_yr": now.year,
        "retirement_cpi": "",
        "pension_opt": "",
        "last_fpen_mth": now.month,
        "last_fpen_yr": now.year,
        "scale_cd": "",
        "last_basic_at_ret": "",
        "fpension_roll_no": "",
        "incentive_holder_flg": "",
        "consolid_cpi_scl_stamt": "",
        "equiv_pay_at_base_cpi": "",
        "class_cd": "",
        "emp_dod": "",
        "remarks": "",
        "applicants": [],
    }


def empty_applicant():
    return {
        "sl_no": None,
        "name": "",
        "dob": "",
        "sex": "",
        "relation_cd": "",
        "relation_desc": "",
        "fpen_active": 1,
        "fpen_start_mnth": "",
        "fprn_start_yr": "",
        "impl_mnth": "",
        "impl_yr": "",
        "bank_cd": "",
        "account_no": "",
        "lic_bank_cd": "",
        "status_flg": "",
        "fpen_inactive_from_dt": "",
        "fpen_clos_reason": "",
        "handicap_flg": "N",
        "pan_no": "",
    }


def list_relations():
    sql = """
        SELECT RELATION_CD, RELATION_DESC, SEX
        FROM fi_pm_mh_relation
        ORDER BY RELATION_CD
    """
    conn = connections["default"]
    rows = []
    with conn.cursor() as cur:
        cur.execute(sql)
        for code, desc, sex in cur.fetchall():
            rows.append(
                {
                    "relation_cd": code,
                    "relation_desc": _str(desc),
                    "sex": _str(sex),
                }
            )
    return rows


def _lookup_emp_name(cur, emp_cd):
    if not emp_cd:
        return ""
    cur.execute(
        """
        SELECT TRIM(CONCAT_WS(' ',
            NULLIF(TRIM(FIRST_NAME), ''),
            NULLIF(TRIM(MIDDLE_NAME), ''),
            NULLIF(TRIM(LAST_NAME), '')
        ))
        FROM fi_xx_mh_emp_per
        WHERE EMP_CD = %s
        LIMIT 1
        """,
        [emp_cd],
    )
    row = cur.fetchone()
    return _str(row[0]) if row and row[0] else ""


def _lookup_emp_birth_dt(cur, emp_cd):
    if not emp_cd:
        return ""
    cur.execute(
        """
        SELECT BIRTH_DT FROM fi_xx_mh_emp_per
        WHERE EMP_CD = %s
        LIMIT 1
        """,
        [emp_cd],
    )
    row = cur.fetchone()
    return _fmt_date(row[0]) if row else ""


def _as_plain_date(value):
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    parsed = _parse_date(value)
    if isinstance(parsed, datetime):
        return parsed.date()
    return parsed


def _lookup_separation_info(cur, emp_cd):
    """
    Returns dict: separation_dt, exp_ret_dt, separation_type (ISO/str blanks).
    Prefers emp_adm; falls back to pensioner EMP_RET_DT for separation only.
    """
    code = _str(emp_cd)[:5]
    info = {"separation_dt": "", "exp_ret_dt": "", "separation_type": ""}
    if not code:
        return info
    cur.execute(
        """
        SELECT SEPARATION_DT, EXP_RET_DT, SEPARATION_TYPE
        FROM fi_xx_mh_emp_adm
        WHERE EMP_CD = %s
        LIMIT 1
        """,
        [code],
    )
    row = cur.fetchone()
    if row:
        info["separation_dt"] = _fmt_date(row[0]) if row[0] else ""
        info["exp_ret_dt"] = _fmt_date(row[1]) if row[1] else ""
        info["separation_type"] = _str(row[2]) if row[2] is not None else ""
    if not info["separation_dt"]:
        cur.execute(
            """
            SELECT EMP_RET_DT
            FROM fi_pn_mh_pensioner
            WHERE EMP_CD = %s
            LIMIT 1
            """,
            [code],
        )
        prow = cur.fetchone()
        if prow and prow[0]:
            info["separation_dt"] = _fmt_date(prow[0])
    return info


def _lookup_separation_dt(cur, emp_cd):
    """Separation preferred; fall back to expected retirement / pensioner ret date."""
    info = _lookup_separation_info(cur, emp_cd)
    return info["separation_dt"] or info["exp_ret_dt"] or ""


def _is_death_separation(sep_type) -> bool:
    return _str(sep_type).upper() in {"DT", "DE", "D", "DEATH"}


def _minus_one_day(value) -> str:
    d = _as_plain_date(value)
    if not d:
        return ""
    return _fmt_date(d - timedelta(days=1))


def _lookup_emp_dod(cur, emp_cd: str) -> str:
    """
    Employee date of death (EMP_DOD).
    Prefer a value already stored on a claim; else original (non-CE) pensioner
    death; else death-in-service separation minus one day (KoPT sep = DOD+1).
    """
    code = _str(emp_cd)[:5]
    if not code:
        return ""
    cur.execute(
        """
        SELECT EMP_DOD
        FROM fi_pn_mh_fpen_caclaim
        WHERE EMP_CD = %s AND EMP_DOD IS NOT NULL
        ORDER BY CASE
            WHEN UPPER(LEFT(IFNULL(CLM_CA_TYPE, ''), 2)) = 'CE' THEN 0
            ELSE 1
        END, CLMCA_ID
        LIMIT 1
        """,
        [code],
    )
    row = cur.fetchone()
    if row and row[0]:
        return _fmt_date(row[0])
    cur.execute(
        """
        SELECT DOD_EMP_PENSIONER
        FROM fi_pn_mh_fpen_caclaim
        WHERE EMP_CD = %s
          AND DOD_EMP_PENSIONER IS NOT NULL
          AND UPPER(LEFT(IFNULL(CLM_CA_TYPE, ''), 2)) <> 'CE'
        ORDER BY CLMCA_ID
        LIMIT 1
        """,
        [code],
    )
    row = cur.fetchone()
    if row and row[0]:
        return _fmt_date(row[0])
    info = _lookup_separation_info(cur, code)
    if _is_death_separation(info.get("separation_type")) and info.get(
        "separation_dt"
    ):
        return _minus_one_day(info["separation_dt"])
    return ""


def _compute_double_fpen_upto(
    separation_value,
    emp_birth_value,
    emp_class=None,
    dod_value=None,
    separation_type=None,
    exp_ret_value=None,
):
    """
    Normal: MIN(sep/ret + 7y, DOB + age) − 1 day.
    Die-in-harness (type DT and sep < exp ret): straight sep + 10y − 1 day
    (no age cap; sep is next day after death).
    Returns date or None.
    """
    from family_pension.services.double_fpension_service import (
        resolve_double_fpen_upto,
    )

    separation_dt = _as_plain_date(separation_value)
    emp_dob = _as_plain_date(emp_birth_value)
    dod = _as_plain_date(dod_value)
    exp_ret = _as_plain_date(exp_ret_value)

    if not separation_dt and not dod:
        return None
    try:
        return resolve_double_fpen_upto(
            separation_dt=separation_dt,
            emp_dob=emp_dob,
            emp_class=emp_class,
            claim_upto=None,
            dod=dod,
            separation_type=separation_type,
            exp_ret_dt=exp_ret,
        )
    except Exception:
        return None


def _lookup_relation_desc(cur, relation_cd):
    if relation_cd in (None, ""):
        return ""
    cur.execute(
        """
        SELECT RELATION_DESC FROM fi_pm_mh_relation
        WHERE RELATION_CD = %s LIMIT 1
        """,
        [relation_cd],
    )
    row = cur.fetchone()
    return _str(row[0]) if row else ""


def lookup_bank(bank_cd: str) -> dict:
    """
    Oracle LOV_BANK style: bank name + branch (desc) for a bank code.

    fi_pm_mh_bank.BANK_DESC  -> branch description
    fi_pm_mh_bankabbr.BANK_NAME (via type = first 2 of bank_cd) -> bank name
    """
    code = _str(bank_cd)[:6]
    empty = {
        "bank_cd": code,
        "bank_name": "",
        "bank_branch": "",
        "bank_id": "",
        "bank_short_name": "",
        "found": False,
    }
    if not code:
        return empty

    conn = connections["default"]
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT
                a.BANK_CD,
                a.BANK_DESC,
                a.BANK_ID,
                b.BANK_NAME,
                b.BANK_SHORT_NAME
            FROM fi_pm_mh_bank a
            LEFT JOIN fi_pm_mh_bankabbr b
              ON SUBSTR(a.BANK_CD, 1, 2) = b.BANK_TYPE
            WHERE a.BANK_CD = %s
            LIMIT 1
            """,
            [code],
        )
        row = cur.fetchone()
    if not row:
        return empty
    return {
        "bank_cd": _str(row[0]),
        "bank_branch": _str(row[1]),
        "bank_id": _str(row[2]),
        "bank_name": _str(row[3]),
        "bank_short_name": _str(row[4]),
        "found": True,
    }


def _enrich_applicant_bank(app: dict) -> dict:
    """Attach display bank name / branch for code on the applicant row."""
    bank = lookup_bank(app.get("bank_cd"))
    app["bank_name"] = bank.get("bank_name") or ""
    app["bank_branch"] = bank.get("bank_branch") or ""
    app["bank_id"] = bank.get("bank_id") or ""
    app["bank_short_name"] = bank.get("bank_short_name") or ""
    lic = lookup_bank(app.get("lic_bank_cd"))
    app["lic_bank_name"] = lic.get("bank_name") or ""
    app["lic_bank_branch"] = lic.get("bank_branch") or ""
    return app


def _fetch_applicants(cur, clmca_id):
    cur.execute(
        """
        SELECT
            a.SL_NO, a.NAME, a.DOB, a.SEX, a.RELATION_CD, r.RELATION_DESC,
            a.FPEN_ACTIVE, a.FPEN_START_MNTH, a.FPRN_START_YR,
            a.IMPL_MNTH, a.IMPL_YR, a.BANK_CD, a.ACCOUNT_NO, a.LIC_BANK_CD,
            a.STATUS_FLG, a.FPEN_INACTIVE_FROM_DT, a.FPEN_CLOS_REASON,
            a.HANDICAP_FLG, a.PAN_NO, a.RELIEF_TAG
        FROM fi_pn_md_fpen_appcn a
        LEFT JOIN fi_pm_mh_relation r ON r.RELATION_CD = a.RELATION_CD
        WHERE a.CLMCA_ID = %s
        ORDER BY a.SL_NO
        """,
        [clmca_id],
    )
    out = []
    for row in cur.fetchall():
        app = {
            "sl_no": row[0],
            "name": _str(row[1]),
            "dob": _fmt_date(row[2]),
            "sex": _str(row[3]),
            "relation_cd": row[4] if row[4] is not None else "",
            "relation_desc": _str(row[5]),
            "fpen_active": row[6],
            "fpen_start_mnth": row[7] if row[7] is not None else "",
            "fprn_start_yr": row[8] if row[8] is not None else "",
            "impl_mnth": row[9] if row[9] is not None else "",
            "impl_yr": row[10] if row[10] is not None else "",
            "bank_cd": _str(row[11]),
            "account_no": _str(row[12]),
            "lic_bank_cd": _str(row[13]),
            "status_flg": _str(row[14]),
            "fpen_inactive_from_dt": _fmt_date(row[15]),
            "fpen_clos_reason": _str(row[16]),
            "handicap_flg": _str(row[17]) or "N",
            "pan_no": _str(row[18]),
            "relief_tag": _str(row[19]),
        }
        out.append(_enrich_applicant_bank(app))
    return out


def get_claim_by_id(clmca_id: str):
    claim_id = _str(clmca_id)
    if not claim_id:
        return None

    conn = connections["default"]
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT
                CLMCA_ID, CLM_CA_TYPE, CA_NO, EMP_CD,
                APPCN_NO, APPCN_DATE, APPCN_STATUS,
                DOUBLE_FPEN_ELIGIBILITY, DOUBLE_FPEN_UPTO,
                APPLICANT_TYPE, APPLICANT_NAME, APPLICANT_ADDRESS,
                DOD_EMP_PENSIONER, GURDIAN_RELATION_CD, DOB_GUARDIAN,
                SERVICE_PENSION_AMT,
                FPEN_START_MNTH, FPRN_START_YR, RETIREMENT_CPI, PENSION_OPT,
                LAST_FPEN_MTH, LAST_FPEN_YR, SCALE_CD, LAST_BASIC_AT_RET,
                FPENSION_ROLL_NO, INCENTIVE_HOLDER_FLG,
                CONSOLID_CPI_SCL_STAMT, EQUIV_PAY_AT_BASE_CPI,
                CLASS, EMP_DOD, REMARKS
            FROM fi_pn_mh_fpen_caclaim
            WHERE CLMCA_ID = %s
            LIMIT 1
            """,
            [claim_id],
        )
        row = cur.fetchone()
        if not row:
            return None

        emp_cd = _str(row[3])
        gurdian_cd = row[13]
        form = {
            "clmca_id": _str(row[0]),
            "clm_ca_type": _str(row[1]) or "CA",
            "ca_no": _str(row[2]),
            "emp_cd": emp_cd,
            "disp_name": _lookup_emp_name(cur, emp_cd),
            "appcn_no": _str(row[4]),
            "appcn_date": _fmt_date(row[5]),
            "appcn_status": row[6] if row[6] is not None else "",
            "double_fpen_eligibility": 1 if row[7] in (1, "1", True) else 0,
            "double_fpen_upto": _fmt_date(row[8]),
            "applicant_type": row[9] if row[9] is not None else "",
            "applicant_name": _str(row[10]),
            "applicant_address": _str(row[11]),
            "dod_emp_pensioner": _fmt_date(row[12]),
            "gurdian_relation_cd": gurdian_cd if gurdian_cd is not None else "",
            "disp_relation": _lookup_relation_desc(cur, gurdian_cd),
            "dob_guardian": _fmt_date(row[14]),
            "service_pension_amt": _num(row[15]),
            "fpen_start_mnth": row[16] if row[16] is not None else "",
            "fprn_start_yr": row[17] if row[17] is not None else "",
            "retirement_cpi": _num(row[18]),
            "pension_opt": _str(row[19]),
            "last_fpen_mth": row[20] if row[20] is not None else "",
            "last_fpen_yr": row[21] if row[21] is not None else "",
            "scale_cd": _str(row[22]),
            "last_basic_at_ret": _num(row[23]),
            "fpension_roll_no": _str(row[24]),
            "incentive_holder_flg": _str(row[25]),
            "consolid_cpi_scl_stamt": _num(row[26]),
            "equiv_pay_at_base_cpi": _num(row[27]),
            "class_cd": (
                _normalize_emp_class(row[28])
                or _lookup_familypensioner_app_class(cur, emp_cd)
            ),
            "emp_dod": _fmt_date(row[29]),
            "remarks": _str(row[30]),
            "emp_birth_dt": _lookup_emp_birth_dt(cur, emp_cd),
            "applicants": _fetch_applicants(cur, claim_id),
        }
        sep_info = _lookup_separation_info(cur, emp_cd)
        form["separation_dt"] = sep_info["separation_dt"] or form.get("separation_dt")
        form["exp_ret_dt"] = sep_info["exp_ret_dt"]
        form["separation_type"] = sep_info["separation_type"]
        if not form.get("emp_dod"):
            form["emp_dod"] = _lookup_emp_dod(cur, emp_cd)
        # Refresh upto from rule when eligible + separation/DOB available
        if form["double_fpen_eligibility"] == 1 and (
            form.get("separation_dt") or form.get("dod_emp_pensioner")
        ):
            computed = _compute_double_fpen_upto(
                form.get("separation_dt"),
                form.get("emp_birth_dt"),
                emp_class=form.get("class_cd"),
                dod_value=form.get("dod_emp_pensioner"),
                separation_type=form.get("separation_type"),
                exp_ret_value=form.get("exp_ret_dt"),
            )
            if computed:
                form["double_fpen_upto"] = _fmt_date(computed)
        return form


def find_claims_by_emp(emp_cd: str):
    code = _str(emp_cd)[:5]
    if not code:
        return []
    conn = connections["default"]
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT CLMCA_ID, CLM_CA_TYPE, CA_NO, EMP_CD, APPCN_NO, APPCN_DATE
            FROM fi_pn_mh_fpen_caclaim
            WHERE EMP_CD = %s
            ORDER BY CLMCA_ID
            """,
            [code],
        )
        return [
            {
                "clmca_id": _str(r[0]),
                "clm_ca_type": _str(r[1]),
                "ca_no": _str(r[2]),
                "emp_cd": _str(r[3]),
                "appcn_no": _str(r[4]),
                "appcn_date": _fmt_date(r[5]),
            }
            for r in cur.fetchall()
        ]


def prefill_from_emp(emp_cd: str, clm_ca_type: str | None = None) -> dict:
    """
    Prefill claim fields when Emp Code is entered (FI_PN_MH_FPENSION_CLAIM_E behaviour).
    Sources: emp_per, emp_adm, emp_fin, pensioner, pension_proposal.
    Ret CPI only when proposal has it; otherwise blank for user entry.
    """
    code = _str(emp_cd)[:5]
    if not code:
        return {"error": "Employee Code is required"}

    claim_type = (_str(clm_ca_type) or "CM").upper()[:2]
    conn = connections["default"]
    with conn.cursor() as cur:
        name = _lookup_emp_name(cur, code)
        if not name:
            cur.execute(
                "SELECT 1 FROM fi_xx_mh_emp_adm WHERE EMP_CD = %s LIMIT 1",
                [code],
            )
            if not cur.fetchone():
                return {"error": f"Employee {code} not found"}

        prefill = {
            "emp_cd": code,
            "disp_name": name,
            "clm_ca_type": claim_type,
            # Defaults for new claim entry (user can change)
            "fpen_start_mnth": datetime.now().month,
            "fprn_start_yr": datetime.now().year,
            "last_fpen_mth": datetime.now().month,
            "last_fpen_yr": datetime.now().year,
            "dod_emp_pensioner": "",
            "emp_dod": "",
            "emp_birth_dt": _lookup_emp_birth_dt(cur, code),
            "retirement_cpi": "",
            "class_cd": "",
        }
        fp_class = _lookup_familypensioner_app_class(cur, code)
        if fp_class:
            prefill["class_cd"] = fp_class
        sep_info = _lookup_separation_info(cur, code)
        prefill["separation_dt"] = sep_info["separation_dt"]
        prefill["exp_ret_dt"] = sep_info["exp_ret_dt"]
        prefill["separation_type"] = sep_info["separation_type"]
        prefill["emp_dod"] = _lookup_emp_dod(cur, code)

        # Separation / class for Double FP upto; pensioner death stays blank for user input.
        cur.execute(
            """
            SELECT SCALE_SL, EMP_CLASS
            FROM fi_xx_mh_emp_fin
            WHERE EMP_CD = %s
            LIMIT 1
            """,
            [code],
        )
        fin = cur.fetchone()
        if fin:
            if fin[0] is not None:
                prefill["scale_cd"] = _str(fin[0])
            if not prefill.get("class_cd") and fin[1] is not None:
                prefill["class_cd"] = _normalize_emp_class(fin[1])

        cur.execute(
            """
            SELECT ORIGINAL_PENSION_AMT, PAYABLE_PENSION, CA_NUMBER,
                   SINGLE_FPEN_AMT, DOUBLE_FPEN_AMT
            FROM fi_pn_mh_pensioner
            WHERE EMP_CD = %s
            LIMIT 1
            """,
            [code],
        )
        pen = cur.fetchone()
        if pen:
            service_amt = pen[0] if pen[0] is not None else pen[1]
            if service_amt is not None:
                prefill["service_pension_amt"] = _num(service_amt)
            if pen[2]:
                prefill["ca_no"] = _str(pen[2])

        cur.execute(
            """
            SELECT DOUBLE_FPEN_ELIGIBILITY, DOUBLE_FPEN_UPTO, CA_NUMBER,
                   PENSION_OPTION, INCENTIVE_HOLDER_FLG, BASE_CPI
            FROM fi_pn_mh_pension_proposal
            WHERE EMP_CD = %s
            ORDER BY
              CASE WHEN PENSION_TYPE IN ('F','FP','FAMILY') THEN 0 ELSE 1 END,
              PENSION_PROPOSAL_DT DESC
            LIMIT 1
            """,
            [code],
        )
        prop = cur.fetchone()
        if prop:
            prefill["double_fpen_eligibility"] = (
                1 if prop[0] in (1, "1", True) else 0
            )
            # DOUBLE_FPEN_UPTO is computed from DOD + emp DOB (form rule), not proposal alone
            if prop[2] and not prefill.get("ca_no"):
                prefill["ca_no"] = _str(prop[2])
            if prop[3]:
                prefill["pension_opt"] = _str(prop[3])
            if prop[4]:
                prefill["incentive_holder_flg"] = _str(prop[4])[:1]
            if prop[5] is not None:
                prefill["retirement_cpi"] = _num(prop[5])

        if claim_type == "CE":
            prefill["double_fpen_eligibility"] = 0
            prefill["double_fpen_upto"] = ""

        matches = find_claims_by_emp(code)
        return {
            "prefill": prefill,
            "matches": matches,
            "exists": bool(name or pen or prop or fin),
        }


def _parse_date(value):
    text = _str(value)
    if not text:
        return None
    text = text[:10]
    try:
        return datetime.strptime(text, "%Y-%m-%d")
    except ValueError:
        try:
            return datetime.strptime(text, "%d-%m-%Y")
        except ValueError:
            return None


def _parse_int(value):
    if value in (None, ""):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _parse_dec(value):
    if value in (None, ""):
        return None
    try:
        return Decimal(str(value))
    except Exception:
        return None


def allocate_claim_id(cur, clm_ca_type: str) -> str:
    """Oracle PRE-INSERT: CLM_CA_TYPE || '/' || next serial."""
    claim_type = (_str(clm_ca_type) or "CA").upper()[:2]
    cur.execute(
        """
        SELECT COALESCE(MAX(CAST(SUBSTRING(CLMCA_ID, 4) AS UNSIGNED)), 0) + 1
        FROM fi_pn_mh_fpen_caclaim
        WHERE SUBSTRING(CLMCA_ID, 1, 2) = %s
        """,
        [claim_type],
    )
    next_sl = int(cur.fetchone()[0] or 1)
    return f"{claim_type}/{next_sl}"


def _applicant_row_values(app, sl_no, clmca_id, user, now):
    """Column values shared by applicant INSERT / UPDATE."""
    active = (
        _parse_int(app.get("fpen_active"))
        if app.get("fpen_active") not in (None, "")
        else 1
    )
    vals = {
        "sl_no": sl_no,
        "name": _str(app.get("name"))[:100],
        "clmca_id": clmca_id,
        "dob": _parse_date(app.get("dob")),
        "fpen_active": active,
        "fpen_start_mnth": _parse_int(app.get("fpen_start_mnth")),
        "fprn_start_yr": _parse_int(app.get("fprn_start_yr")),
        "impl_mnth": _parse_int(app.get("impl_mnth")),
        "impl_yr": _parse_int(app.get("impl_yr")),
        "relation_cd": _parse_int(app.get("relation_cd")),
        "bank_cd": _str(app.get("bank_cd"))[:6] or None,
        "account_no": _str(app.get("account_no"))[:20] or None,
        "lic_bank_cd": _str(app.get("lic_bank_cd"))[:6] or None,
        "status_flg": _str(app.get("status_flg"))[:1] or None,
        "sex": _str(app.get("sex"))[:1] or None,
        "fpen_inactive_from_dt": _parse_date(app.get("fpen_inactive_from_dt")),
        "fpen_clos_reason": _str(app.get("fpen_clos_reason"))[:2] or None,
        "handicap_flg": _str(app.get("handicap_flg"))[:1] or "N",
        "pan_no": _str(app.get("pan_no"))[:10] or None,
        "relief_tag": _str(app.get("relief_tag"))[:1] or None,
        "user": (user or "SMPK")[:5],
        "now": now,
    }
    return vals


def _replace_applicants(cur, clmca_id, named, user, now):
    """
    Upsert claim applicants.

    Bulk DELETE+INSERT fails when First FP has rows in
    fi_pn_mh_familypensioner referencing (SL_NO, CLMCA_ID). Existing serial
    numbers are updated in place; new ones inserted; only unreferenced
    leftover rows are removed.
    """
    kept = []
    for i, app in enumerate(named, start=1):
        sl_no = _parse_int(app.get("sl_no")) or i
        kept.append(sl_no)
        v = _applicant_row_values(app, sl_no, clmca_id, user, now)

        cur.execute(
            """
            UPDATE fi_pn_md_fpen_appcn SET
                NAME = %s,
                DOB = %s,
                FPEN_ACTIVE = %s,
                FPEN_START_MNTH = %s,
                FPRN_START_YR = %s,
                IMPL_MNTH = %s,
                IMPL_YR = %s,
                RELATION_CD = %s,
                BANK_CD = %s,
                ACCOUNT_NO = %s,
                LIC_BANK_CD = %s,
                STATUS_FLG = %s,
                SEX = %s,
                FPEN_INACTIVE_FROM_DT = %s,
                FPEN_CLOS_REASON = %s,
                HANDICAP_FLG = %s,
                PAN_NO = %s,
                RELIEF_TAG = %s
            WHERE SL_NO = %s AND CLMCA_ID = %s
            """,
            [
                v["name"],
                v["dob"],
                v["fpen_active"],
                v["fpen_start_mnth"],
                v["fprn_start_yr"],
                v["impl_mnth"],
                v["impl_yr"],
                v["relation_cd"],
                v["bank_cd"],
                v["account_no"],
                v["lic_bank_cd"],
                v["status_flg"],
                v["sex"],
                v["fpen_inactive_from_dt"],
                v["fpen_clos_reason"],
                v["handicap_flg"],
                v["pan_no"],
                v["relief_tag"],
                sl_no,
                clmca_id,
            ],
        )
        if cur.rowcount == 0:
            cur.execute(
                """
                INSERT INTO fi_pn_md_fpen_appcn (
                    SL_NO, NAME, CLMCA_ID, DOB, FPEN_ACTIVE,
                    FPEN_START_MNTH, FPRN_START_YR, IMPL_MNTH, IMPL_YR,
                    DATE_CREATED, CREATED_BY,
                    RELATION_CD, BANK_CD, ACCOUNT_NO, LIC_BANK_CD,
                    STATUS_FLG, SEX, FPEN_INACTIVE_FROM_DT, FPEN_CLOS_REASON,
                    HANDICAP_FLG, PAN_NO, RELIEF_TAG
                ) VALUES (
                    %s, %s, %s, %s, %s,
                    %s, %s, %s, %s,
                    %s, %s,
                    %s, %s, %s, %s,
                    %s, %s, %s, %s,
                    %s, %s, %s
                )
                """,
                [
                    sl_no,
                    v["name"],
                    clmca_id,
                    v["dob"],
                    v["fpen_active"],
                    v["fpen_start_mnth"],
                    v["fprn_start_yr"],
                    v["impl_mnth"],
                    v["impl_yr"],
                    now,
                    v["user"],
                    v["relation_cd"],
                    v["bank_cd"],
                    v["account_no"],
                    v["lic_bank_cd"],
                    v["status_flg"],
                    v["sex"],
                    v["fpen_inactive_from_dt"],
                    v["fpen_clos_reason"],
                    v["handicap_flg"],
                    v["pan_no"],
                    v["relief_tag"],
                ],
            )

    # Drop applicants no longer on the form, unless First FP still references them.
    if kept:
        placeholders = ", ".join(["%s"] * len(kept))
        cur.execute(
            f"""
            DELETE a FROM fi_pn_md_fpen_appcn a
            WHERE a.CLMCA_ID = %s
              AND a.SL_NO NOT IN ({placeholders})
              AND NOT EXISTS (
                  SELECT 1 FROM fi_pn_mh_familypensioner f
                  WHERE f.CLMCA_ID = a.CLMCA_ID AND f.SL_NO = a.SL_NO
              )
            """,
            [clmca_id, *kept],
        )
    else:
        cur.execute(
            """
            DELETE a FROM fi_pn_md_fpen_appcn a
            WHERE a.CLMCA_ID = %s
              AND NOT EXISTS (
                  SELECT 1 FROM fi_pn_mh_familypensioner f
                  WHERE f.CLMCA_ID = a.CLMCA_ID AND f.SL_NO = a.SL_NO
              )
            """,
            [clmca_id],
        )


def save_claim(payload: dict, user_id: str = "SMPK") -> dict:
    """
    Insert or update FI_PN_MH_FPEN_CACLAIM + upsert FI_PN_MD_FPEN_APPCN rows.
    Returns saved claim (via get_claim_by_id).
    """
    from django.db import transaction

    data = payload or {}
    emp_cd = _str(data.get("emp_cd"))[:6]
    if not emp_cd:
        return {"error": "Employee Code is required"}

    clm_ca_type = (_str(data.get("clm_ca_type")) or "CA").upper()[:3]
    clmca_id = _str(data.get("clmca_id"))
    user = (_str(user_id) or "SMPK")[:5]
    now = datetime.now()

    applicants = data.get("applicants") or []
    named = [a for a in applicants if _str(a.get("name"))]

    created = False

    try:
        with transaction.atomic(using="default"):
            conn = connections["default"]
            with conn.cursor() as cur:
                if clmca_id:
                    cur.execute(
                        "SELECT 1 FROM fi_pn_mh_fpen_caclaim WHERE CLMCA_ID = %s LIMIT 1",
                        [clmca_id],
                    )
                    exists = cur.fetchone() is not None
                else:
                    exists = False
                    # Allocate under the same transaction to reduce duplicate-ID races
                    for _ in range(5):
                        clmca_id = allocate_claim_id(cur, clm_ca_type)
                        cur.execute(
                            "SELECT 1 FROM fi_pn_mh_fpen_caclaim WHERE CLMCA_ID = %s LIMIT 1",
                            [clmca_id],
                        )
                        if not cur.fetchone():
                            break
                    else:
                        return {"error": "Could not allocate a new Claim ID"}

                created = not exists

                dbl_eligible = (
                    1 if data.get("double_fpen_eligibility") in (1, "1", True) else 0
                )
                dod_parsed = _parse_date(data.get("dod_emp_pensioner"))
                # Eligible double upto — DIH uses death+10y when type DT & sep < exp ret
                if dbl_eligible:
                    emp_birth = _lookup_emp_birth_dt(cur, emp_cd)
                    adm_info = _lookup_separation_info(cur, emp_cd)
                    sep_iso = (
                        _str(data.get("separation_dt"))
                        or adm_info["separation_dt"]
                        or adm_info["exp_ret_dt"]
                    )
                    sep_type = (
                        data.get("separation_type")
                        if data.get("separation_type") not in (None, "")
                        else adm_info["separation_type"]
                    )
                    exp_ret = (
                        data.get("exp_ret_dt")
                        if data.get("exp_ret_dt") not in (None, "")
                        else adm_info["exp_ret_dt"]
                    )
                    class_cd = data.get("class_cd")
                    if class_cd in (None, ""):
                        class_cd = _lookup_familypensioner_app_class(cur, emp_cd)
                    if class_cd in (None, ""):
                        cur.execute(
                            """
                            SELECT EMP_CLASS FROM fi_xx_mh_emp_fin
                            WHERE EMP_CD = %s LIMIT 1
                            """,
                            [emp_cd],
                        )
                        c_row = cur.fetchone()
                        class_cd = c_row[0] if c_row else None
                    computed_upto = _compute_double_fpen_upto(
                        sep_iso,
                        emp_birth,
                        emp_class=class_cd,
                        dod_value=dod_parsed,
                        separation_type=sep_type,
                        exp_ret_value=exp_ret,
                    )
                    double_upto_val = (
                        datetime.combine(computed_upto, datetime.min.time())
                        if computed_upto
                        else _parse_date(data.get("double_fpen_upto"))
                    )
                else:
                    double_upto_val = None

                master_vals = {
                    "CLMCA_ID": clmca_id[:22],
                    "CLM_CA_TYPE": clm_ca_type,
                    "CA_NO": _str(data.get("ca_no"))[:22] or None,
                    "EMP_CD": emp_cd,
                    "APPCN_NO": _str(data.get("appcn_no"))[:22] or None,
                    "APPCN_DATE": _parse_date(data.get("appcn_date")),
                    "APPCN_STATUS": _parse_int(data.get("appcn_status")),
                    "DOUBLE_FPEN_ELIGIBILITY": dbl_eligible,
                    "DOUBLE_FPEN_UPTO": double_upto_val,
                    "APPLICANT_TYPE": _parse_int(data.get("applicant_type")),
                    "APPLICANT_NAME": _str(data.get("applicant_name"))[:60] or None,
                    "APPLICANT_ADDRESS": _str(data.get("applicant_address"))[:200]
                    or None,
                    "DOD_EMP_PENSIONER": dod_parsed,
                    "GURDIAN_RELATION_CD": _parse_int(data.get("gurdian_relation_cd")),
                    "DOB_GUARDIAN": _parse_date(data.get("dob_guardian")),
                    "SERVICE_PENSION_AMT": _parse_dec(data.get("service_pension_amt")),
                    "FPEN_START_MNTH": _parse_int(data.get("fpen_start_mnth")),
                    "FPRN_START_YR": _parse_int(data.get("fprn_start_yr")),
                    "RETIREMENT_CPI": _parse_dec(data.get("retirement_cpi")),
                    "PENSION_OPT": _str(data.get("pension_opt"))[:1] or None,
                    "LAST_FPEN_MTH": _parse_int(data.get("last_fpen_mth")),
                    "LAST_FPEN_YR": _parse_int(data.get("last_fpen_yr")),
                    "SCALE_CD": _str(data.get("scale_cd"))[:11] or None,
                    "LAST_BASIC_AT_RET": _parse_dec(data.get("last_basic_at_ret")),
                    "FPENSION_ROLL_NO": _str(data.get("fpension_roll_no"))[:22] or None,
                    "INCENTIVE_HOLDER_FLG": _str(data.get("incentive_holder_flg"))[:1]
                    or None,
                    "CONSOLID_CPI_SCL_STAMT": _parse_dec(
                        data.get("consolid_cpi_scl_stamt")
                    ),
                    "EQUIV_PAY_AT_BASE_CPI": _parse_dec(
                        data.get("equiv_pay_at_base_cpi")
                    ),
                    "CLASS": _parse_int(data.get("class_cd")),
                    "EMP_DOD": _parse_date(data.get("emp_dod")),
                    "REMARKS": _str(data.get("remarks"))[:200] or None,
                }

                if exists:
                    cur.execute(
                        """
                        UPDATE fi_pn_mh_fpen_caclaim SET
                            CLM_CA_TYPE=%(CLM_CA_TYPE)s,
                            CA_NO=%(CA_NO)s,
                            EMP_CD=%(EMP_CD)s,
                            APPCN_NO=%(APPCN_NO)s,
                            APPCN_DATE=%(APPCN_DATE)s,
                            APPCN_STATUS=%(APPCN_STATUS)s,
                            DOUBLE_FPEN_ELIGIBILITY=%(DOUBLE_FPEN_ELIGIBILITY)s,
                            DOUBLE_FPEN_UPTO=%(DOUBLE_FPEN_UPTO)s,
                            APPLICANT_TYPE=%(APPLICANT_TYPE)s,
                            APPLICANT_NAME=%(APPLICANT_NAME)s,
                            APPLICANT_ADDRESS=%(APPLICANT_ADDRESS)s,
                            DOD_EMP_PENSIONER=%(DOD_EMP_PENSIONER)s,
                            GURDIAN_RELATION_CD=%(GURDIAN_RELATION_CD)s,
                            DOB_GUARDIAN=%(DOB_GUARDIAN)s,
                            SERVICE_PENSION_AMT=%(SERVICE_PENSION_AMT)s,
                            FPEN_START_MNTH=%(FPEN_START_MNTH)s,
                            FPRN_START_YR=%(FPRN_START_YR)s,
                            RETIREMENT_CPI=%(RETIREMENT_CPI)s,
                            PENSION_OPT=%(PENSION_OPT)s,
                            LAST_FPEN_MTH=%(LAST_FPEN_MTH)s,
                            LAST_FPEN_YR=%(LAST_FPEN_YR)s,
                            SCALE_CD=%(SCALE_CD)s,
                            LAST_BASIC_AT_RET=%(LAST_BASIC_AT_RET)s,
                            FPENSION_ROLL_NO=%(FPENSION_ROLL_NO)s,
                            INCENTIVE_HOLDER_FLG=%(INCENTIVE_HOLDER_FLG)s,
                            CONSOLID_CPI_SCL_STAMT=%(CONSOLID_CPI_SCL_STAMT)s,
                            EQUIV_PAY_AT_BASE_CPI=%(EQUIV_PAY_AT_BASE_CPI)s,
                            CLASS=%(CLASS)s,
                            EMP_DOD=%(EMP_DOD)s,
                            REMARKS=%(REMARKS)s,
                            DATE_MODIFIED=%(DATE_MODIFIED)s,
                            MODIFIED_BY=%(MODIFIED_BY)s
                        WHERE CLMCA_ID=%(CLMCA_ID)s
                        """,
                        {
                            **master_vals,
                            "DATE_MODIFIED": now,
                            "MODIFIED_BY": user,
                        },
                    )
                else:
                    cur.execute(
                        """
                        INSERT INTO fi_pn_mh_fpen_caclaim (
                            CLMCA_ID, CLM_CA_TYPE, CA_NO, EMP_CD,
                            APPCN_NO, APPCN_DATE, APPCN_STATUS,
                            DOUBLE_FPEN_ELIGIBILITY, DOUBLE_FPEN_UPTO,
                            APPLICANT_TYPE, APPLICANT_NAME, APPLICANT_ADDRESS,
                            DOD_EMP_PENSIONER, GURDIAN_RELATION_CD, DOB_GUARDIAN,
                            SERVICE_PENSION_AMT,
                            DATE_CREATED, CREATED_BY,
                            FPEN_START_MNTH, FPRN_START_YR, RETIREMENT_CPI, PENSION_OPT,
                            LAST_FPEN_MTH, LAST_FPEN_YR, SCALE_CD, LAST_BASIC_AT_RET,
                            FPENSION_ROLL_NO, INCENTIVE_HOLDER_FLG,
                            CONSOLID_CPI_SCL_STAMT, EQUIV_PAY_AT_BASE_CPI,
                            CLASS, EMP_DOD, REMARKS
                        ) VALUES (
                            %(CLMCA_ID)s, %(CLM_CA_TYPE)s, %(CA_NO)s, %(EMP_CD)s,
                            %(APPCN_NO)s, %(APPCN_DATE)s, %(APPCN_STATUS)s,
                            %(DOUBLE_FPEN_ELIGIBILITY)s, %(DOUBLE_FPEN_UPTO)s,
                            %(APPLICANT_TYPE)s, %(APPLICANT_NAME)s, %(APPLICANT_ADDRESS)s,
                            %(DOD_EMP_PENSIONER)s, %(GURDIAN_RELATION_CD)s, %(DOB_GUARDIAN)s,
                            %(SERVICE_PENSION_AMT)s,
                            %(DATE_CREATED)s, %(CREATED_BY)s,
                            %(FPEN_START_MNTH)s, %(FPRN_START_YR)s, %(RETIREMENT_CPI)s, %(PENSION_OPT)s,
                            %(LAST_FPEN_MTH)s, %(LAST_FPEN_YR)s, %(SCALE_CD)s, %(LAST_BASIC_AT_RET)s,
                            %(FPENSION_ROLL_NO)s, %(INCENTIVE_HOLDER_FLG)s,
                            %(CONSOLID_CPI_SCL_STAMT)s, %(EQUIV_PAY_AT_BASE_CPI)s,
                            %(CLASS)s, %(EMP_DOD)s, %(REMARKS)s
                        )
                        """,
                        {
                            **master_vals,
                            "DATE_CREATED": now,
                            "CREATED_BY": user,
                        },
                    )

                # Upsert applicants — bulk DELETE fails once First FP has
                # fi_pn_mh_familypensioner rows referencing (SL_NO, CLMCA_ID).
                _replace_applicants(cur, clmca_id, named, user, now)
    except Exception as exc:
        return {"error": f"Save failed: {exc}"}

    claim = get_claim_by_id(clmca_id)
    if not claim:
        return {
            "error": (
                f"Claim {clmca_id} was written but could not be reloaded. "
                "Please Load by Claim ID."
            )
        }
    return {"exists": True, "claim": claim, "created": created}
