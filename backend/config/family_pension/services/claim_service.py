"""
Family Pension Claim form — FI_PN_MH_FPENSION_CLAIM_E.fmb

Master: smpk_pension.fi_pn_mh_fpen_caclaim
Detail: smpk_pension.fi_pn_md_fpen_appcn
"""

from __future__ import annotations

from datetime import date, datetime
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


def empty_claim_form():
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
        "applicant_type": "",
        "applicant_name": "",
        "applicant_address": "",
        "dod_emp_pensioner": "",
        "gurdian_relation_cd": "",
        "disp_relation": "",
        "dob_guardian": "",
        "service_pension_amt": "",
        "fpen_start_mnth": "",
        "fprn_start_yr": "",
        "retirement_cpi": "",
        "pension_opt": "",
        "last_fpen_mth": "",
        "last_fpen_yr": "",
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
        "status_flg": "S",
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


def _fetch_applicants(cur, clmca_id):
    cur.execute(
        """
        SELECT
            a.SL_NO, a.NAME, a.DOB, a.SEX, a.RELATION_CD, r.RELATION_DESC,
            a.FPEN_ACTIVE, a.FPEN_START_MNTH, a.FPRN_START_YR,
            a.IMPL_MNTH, a.IMPL_YR, a.BANK_CD, a.ACCOUNT_NO, a.LIC_BANK_CD,
            a.STATUS_FLG, a.FPEN_INACTIVE_FROM_DT, a.FPEN_CLOS_REASON,
            a.HANDICAP_FLG, a.PAN_NO
        FROM fi_pn_md_fpen_appcn a
        LEFT JOIN fi_pm_mh_relation r ON r.RELATION_CD = a.RELATION_CD
        WHERE a.CLMCA_ID = %s
        ORDER BY a.SL_NO
        """,
        [clmca_id],
    )
    out = []
    for row in cur.fetchall():
        out.append(
            {
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
                "status_flg": _str(row[14]) or "S",
                "fpen_inactive_from_dt": _fmt_date(row[15]),
                "fpen_clos_reason": _str(row[16]),
                "handicap_flg": _str(row[17]) or "N",
                "pan_no": _str(row[18]),
            }
        )
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
            "class_cd": row[28] if row[28] is not None else "",
            "emp_dod": _fmt_date(row[29]),
            "remarks": _str(row[30]),
            "applicants": _fetch_applicants(cur, claim_id),
        }
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
        }

        cur.execute(
            """
            SELECT SEPARATION_DT
            FROM fi_xx_mh_emp_adm
            WHERE EMP_CD = %s
            LIMIT 1
            """,
            [code],
        )
        adm = cur.fetchone()
        if adm and adm[0]:
            prefill["dod_emp_pensioner"] = _fmt_date(adm[0])
            prefill["emp_dod"] = _fmt_date(adm[0])

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
            if fin[1] is not None:
                prefill["class_cd"] = fin[1]

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
                   PENSION_OPTION, INCENTIVE_HOLDER_FLG, BASE_CPI,
                   START_MONTH, START_YR, SEPARATION_DT
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
            if prop[1]:
                prefill["double_fpen_upto"] = _fmt_date(prop[1])
            if prop[2] and not prefill.get("ca_no"):
                prefill["ca_no"] = _str(prop[2])
            if prop[3]:
                prefill["pension_opt"] = _str(prop[3])
            if prop[4]:
                prefill["incentive_holder_flg"] = _str(prop[4])[:1]
            if prop[5] is not None:
                prefill["retirement_cpi"] = _num(prop[5])
            if prop[6] is not None:
                prefill["fpen_start_mnth"] = prop[6]
            if prop[7] is not None:
                prefill["fprn_start_yr"] = prop[7]
            if prop[8] and not prefill.get("dod_emp_pensioner"):
                prefill["dod_emp_pensioner"] = _fmt_date(prop[8])

        matches = find_claims_by_emp(code)
        return {
            "prefill": prefill,
            "matches": matches,
            "exists": bool(name or pen or prop or adm),
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


def save_claim(payload: dict, user_id: str = "SMPK") -> dict:
    """
    Insert or update FI_PN_MH_FPEN_CACLAIM + replace FI_PN_MD_FPEN_APPCN rows.
    Returns saved claim (via get_claim_by_id).
    """
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
            clmca_id = allocate_claim_id(cur, clm_ca_type)

        master_vals = {
            "CLMCA_ID": clmca_id[:22],
            "CLM_CA_TYPE": clm_ca_type,
            "CA_NO": _str(data.get("ca_no"))[:22] or None,
            "EMP_CD": emp_cd,
            "APPCN_NO": _str(data.get("appcn_no"))[:22] or None,
            "APPCN_DATE": _parse_date(data.get("appcn_date")),
            "APPCN_STATUS": _parse_int(data.get("appcn_status")),
            "DOUBLE_FPEN_ELIGIBILITY": 1
            if data.get("double_fpen_eligibility") in (1, "1", True)
            else 0,
            "DOUBLE_FPEN_UPTO": _parse_date(data.get("double_fpen_upto")),
            "APPLICANT_TYPE": _parse_int(data.get("applicant_type")),
            "APPLICANT_NAME": _str(data.get("applicant_name"))[:60] or None,
            "APPLICANT_ADDRESS": _str(data.get("applicant_address"))[:200] or None,
            "DOD_EMP_PENSIONER": _parse_date(data.get("dod_emp_pensioner")),
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
            "INCENTIVE_HOLDER_FLG": _str(data.get("incentive_holder_flg"))[:1] or None,
            "CONSOLID_CPI_SCL_STAMT": _parse_dec(data.get("consolid_cpi_scl_stamt")),
            "EQUIV_PAY_AT_BASE_CPI": _parse_dec(data.get("equiv_pay_at_base_cpi")),
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

        cur.execute(
            "DELETE FROM fi_pn_md_fpen_appcn WHERE CLMCA_ID = %s",
            [clmca_id],
        )
        for i, app in enumerate(named, start=1):
            sl_no = _parse_int(app.get("sl_no")) or i
            cur.execute(
                """
                INSERT INTO fi_pn_md_fpen_appcn (
                    SL_NO, NAME, CLMCA_ID, DOB, FPEN_ACTIVE,
                    FPEN_START_MNTH, FPRN_START_YR, IMPL_MNTH, IMPL_YR,
                    DATE_CREATED, CREATED_BY,
                    RELATION_CD, BANK_CD, ACCOUNT_NO, LIC_BANK_CD,
                    STATUS_FLG, SEX, FPEN_INACTIVE_FROM_DT, FPEN_CLOS_REASON,
                    HANDICAP_FLG, PAN_NO
                ) VALUES (
                    %s, %s, %s, %s, %s,
                    %s, %s, %s, %s,
                    %s, %s,
                    %s, %s, %s, %s,
                    %s, %s, %s, %s,
                    %s, %s
                )
                """,
                [
                    sl_no,
                    _str(app.get("name"))[:100],
                    clmca_id,
                    _parse_date(app.get("dob")),
                    _parse_int(app.get("fpen_active"))
                    if app.get("fpen_active") not in (None, "")
                    else 1,
                    _parse_int(app.get("fpen_start_mnth")),
                    _parse_int(app.get("fprn_start_yr")),
                    _parse_int(app.get("impl_mnth")),
                    _parse_int(app.get("impl_yr")),
                    now,
                    user,
                    _parse_int(app.get("relation_cd")),
                    _str(app.get("bank_cd"))[:6] or None,
                    _str(app.get("account_no"))[:20] or None,
                    _str(app.get("lic_bank_cd"))[:6] or None,
                    _str(app.get("status_flg"))[:1] or "S",
                    _str(app.get("sex"))[:1] or None,
                    _parse_date(app.get("fpen_inactive_from_dt")),
                    _str(app.get("fpen_clos_reason"))[:2] or None,
                    _str(app.get("handicap_flg"))[:1] or "N",
                    _str(app.get("pan_no"))[:10] or None,
                ],
            )

    claim = get_claim_by_id(clmca_id)
    return {"exists": True, "claim": claim, "created": not exists}
