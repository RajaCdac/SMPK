"""
LIC Claim Form — Normal (Oracle FI_PN_LIC_NORMAL_PEN_DTLS).

Params from FI_PN_LIC_BILL_GEN_E print: P_EMP_CD, P_LIC_SL_NO, P_ROLL_NO,
P_CLAIM_ID, P_AADHAR_NO.
"""

from __future__ import annotations

import math
from datetime import date, datetime

from django.db import connection
from django.db.utils import DatabaseError, ProgrammingError

from .lic_claim_generation_service import (
    LicClaimGenerationError,
    _as_str,
    _emp_key,
    load_normal_claim,
)


CLASS_ROMAN = {"1": "I", "2": "II", "3": "III", "4": "IV"}


def _num(value) -> float:
    if value is None or value == "":
        return 0.0
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _ceil_rupee(value: float) -> float:
    return float(math.ceil(_num(value))) if value is not None else 0.0


def _fmt_date(value) -> str:
    if not value:
        return ""
    if isinstance(value, datetime):
        value = value.date()
    if isinstance(value, date):
        return value.strftime("%d/%m/%Y")
    text = str(value).strip()
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"):
        try:
            return datetime.strptime(text[:10], fmt).strftime("%d/%m/%Y")
        except ValueError:
            continue
    return text


def _as_date(value) -> date | None:
    if not value:
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


def _safe_one(cursor, sql, params=None):
    try:
        cursor.execute(sql, params or [])
        return cursor.fetchone()
    except (ProgrammingError, DatabaseError):
        try:
            connection.rollback()
        except Exception:
            pass
        return None


def _quarter_month(dor: date) -> str:
    """Oracle CF_daFormula: month bucket 01 / 04 / 07 / 10."""
    m = dor.month
    if m in (1, 2, 3):
        return "01"
    if m in (4, 5, 6):
        return "04"
    if m in (7, 8, 9):
        return "07"
    return "10"


def _class_grp(emp_class) -> int:
    try:
        c = int(float(emp_class))
    except (TypeError, ValueError):
        return 1
    return 1 if c in (1, 2) else 3


def _dearness_pension(original: float, base_cpi: float, dor: date | None) -> float:
    """
    CF_1Formula / CF_DP (LIC normal claim form):
    DP is 0 when BASE_CPI = 126 or DOR >= 01-Apr-2010;
    else CEIL(original / 2) for older cases.
    """
    cutoff = date(2010, 4, 1)
    if int(base_cpi or 0) == 126:
        return 0.0
    if dor and dor >= cutoff:
        return 0.0
    return _ceil_rupee(original / 2.0)


def _commutation_rate_for_age(cursor, age: int | None) -> float:
    """When RATE_COMMUTED_PORTION is blank, use most common rate for that age."""
    if age is None:
        return 0.0
    row = _safe_one(
        cursor,
        """
        SELECT p.RATE_COMMUTED_PORTION
        FROM fi_pn_mh_pensioner p
        INNER JOIN fi_xx_mh_emp_per e ON e.EMP_CD = p.EMP_CD
        LEFT JOIN fi_xx_mh_emp_adm a ON a.EMP_CD = p.EMP_CD
        WHERE p.RATE_COMMUTED_PORTION IS NOT NULL
          AND p.RATE_COMMUTED_PORTION > 0
          AND e.BIRTH_DT IS NOT NULL
          AND TIMESTAMPDIFF(
                YEAR,
                e.BIRTH_DT,
                COALESCE(p.EMP_RET_DT, a.SEPARATION_DT)
              ) = %s
        GROUP BY p.RATE_COMMUTED_PORTION
        ORDER BY COUNT(*) DESC, p.RATE_COMMUTED_PORTION
        LIMIT 1
        """,
        [int(age)],
    )
    return _num(row[0]) if row else 0.0


def _lookup_da_pct(cursor, *, cpi: int, class_grp: int, wef: date) -> float:
    """Mirror Oracle CF_daFormula rate lookup (best-effort for MySQL tables)."""
    q_mon = _quarter_month(wef)
    wef_q = date(wef.year, int(q_mon), 1)

    if cpi == 1708:
        row = _safe_one(
            cursor,
            """
            SELECT DISTINCT (DA_PCT - 50)
            FROM fi_pn_mh_ada_rate
            WHERE WEF_DT = %s AND EMP_TYPE = 'EGN' AND BASE_CPI_NO = 1708
            LIMIT 1
            """,
            [wef_q],
        )
        if row and row[0] is not None:
            return float(row[0])

    if cpi == 126:
        row = _safe_one(
            cursor,
            "SELECT DA_PCT FROM fi_pn_new_dapct WHERE WEF_DT = %s LIMIT 1",
            [wef_q],
        )
        if row and row[0] is not None:
            return float(row[0])

    if cpi == 198:
        row = _safe_one(
            cursor,
            """
            SELECT DA_PCT FROM fi_pr_mh_calc_da_2012wr
            WHERE EMP_CLASS_GRP = %s AND WEF_DT = %s
            LIMIT 1
            """,
            [class_grp, wef_q],
        )
        if row and row[0] is not None:
            return float(row[0])

    # 277 / 359 / fallback when era-specific tables are missing in MySQL
    row = _safe_one(
        cursor,
        """
        SELECT DA_PCT FROM fi_pr_mh_calc_da
        WHERE EMP_CLASS_GRP = %s AND WEF_DT = %s
        LIMIT 1
        """,
        [class_grp, wef_q],
    )
    if row and row[0] is not None:
        return float(row[0])

    row = _safe_one(
        cursor,
        """
        SELECT DA_PCT FROM fi_pr_mh_calc_da
        WHERE EMP_CLASS_GRP = %s AND WEF_DT <= %s
        ORDER BY WEF_DT DESC
        LIMIT 1
        """,
        [class_grp, wef_q],
    )
    if row and row[0] is not None:
        return float(row[0])
    return 0.0


def _da_amount(
    cursor,
    *,
    original: float,
    dp: float,
    cpi: int,
    emp_class,
    dor: date | None,
) -> tuple[float, float]:
    if not dor:
        return 0.0, 0.0
    class_grp = _class_grp(emp_class)
    pct = _lookup_da_pct(cursor, cpi=cpi, class_grp=class_grp, wef=dor)
    if pct <= 0:
        return 0.0, 0.0
    if cpi == 1708:
        amt = _ceil_rupee((original + dp) * pct / 100.0)
    else:
        amt = _ceil_rupee(original * pct / 100.0)
    return amt, pct


def _bank_branch(cursor, bank_cd: str) -> tuple[str, str]:
    if not bank_cd:
        return "", ""
    row = _safe_one(
        cursor,
        """
        SELECT CONCAT(
            IFNULL(NULLIF(TRIM(b.BANK_SHORT_NAME), ''), ''),
            CASE
              WHEN b.BANK_SHORT_NAME IS NULL OR TRIM(b.BANK_SHORT_NAME) = '' THEN ''
              ELSE ', '
            END,
            IFNULL(TRIM(a.BANK_DESC), ''),
            ' BRANCH'
        ),
        CONCAT_WS(
            ', ',
            NULLIF(TRIM(a.ADDR1), ''),
            NULLIF(TRIM(a.ADDR2), ''),
            NULLIF(TRIM(a.CITY), ''),
            NULLIF(TRIM(a.DIST), ''),
            NULLIF(TRIM(a.PS), ''),
            NULLIF(TRIM(a.STATE), ''),
            NULLIF(TRIM(CAST(a.PIN AS CHAR)), '')
        )
        FROM fi_pm_mh_bank a
        LEFT JOIN fi_pm_mh_bankabbr b
          ON b.BANK_TYPE = SUBSTR(a.BANK_CD, 1, 2)
        WHERE a.BANK_CD = %s
        LIMIT 1
        """,
        [bank_cd],
    )
    if not row:
        return "", ""
    return _as_str(row[0], 200), _as_str(row[1], 300)


def _age_last_birthday(dor: date | None, dob: date | None) -> int | None:
    if not dor or not dob:
        return None
    months = (dor.year - dob.year) * 12 + (dor.month - dob.month)
    if dor.day < dob.day:
        months -= 1
    return max(0, int(round(months / 12.0)))


def _fetch_pensioner_row(cursor, emp: str, cid: str):
    """
    Build print row from local finance schema only:
    first_pension_pensionproposal → fi_pn_mh_pensioner → emp_adm.
    (No remote Oracle connection.)
    """
    pen = _safe_one(
        cursor,
        """
        SELECT
          EMP_CD,
          ORIGINAL_PENSION_AMT,
          EFFECTIVE_STDT_PENSION,
          BASE_CPI,
          COMMUTED_PORTION,
          RATE_COMMUTED_PORTION,
          PAYABLE_PENSION,
          GRATUITY,
          COMMUTATION_PER,
          APP_CLASS,
          NAME,
          SEX,
          DOB,
          PAN_NO,
          ACCOUNT_NO,
          LIC_BANK_CD,
          BANK_CD,
          PENSION_ROLL_NO,
          CA_NUMBER,
          EMP_RET_DT
        FROM fi_pn_mh_pensioner
        WHERE EMP_CD = %s
          AND (%s = '' OR CA_NUMBER = %s)
        ORDER BY CA_NUMBER DESC
        LIMIT 1
        """,
        [emp, cid, cid],
    )
    if not pen:
        pen = _safe_one(
            cursor,
            """
            SELECT
              EMP_CD,
              ORIGINAL_PENSION_AMT,
              EFFECTIVE_STDT_PENSION,
              BASE_CPI,
              COMMUTED_PORTION,
              RATE_COMMUTED_PORTION,
              PAYABLE_PENSION,
              GRATUITY,
              COMMUTATION_PER,
              APP_CLASS,
              NAME,
              SEX,
              DOB,
              PAN_NO,
              ACCOUNT_NO,
              LIC_BANK_CD,
              BANK_CD,
              PENSION_ROLL_NO,
              CA_NUMBER,
              EMP_RET_DT
            FROM fi_pn_mh_pensioner
            WHERE EMP_CD = %s
            ORDER BY CA_NUMBER DESC
            LIMIT 1
            """,
            [emp],
        )
    if not pen:
        return None

    ca = _as_str(pen[18], 10) or cid

    sep_type = None
    sep_dt = None
    account_no = None
    lic_bank_cd = None
    bank_cd = None
    prop_roll = None
    ca_number = None

    # 1) App proposal table (primary for new cases in finance)
    dj = _safe_one(
        cursor,
        """
        SELECT separation_type, separation_date, account_no, lic_bank_cd,
               bank_cd, pension_roll_no, ca_number
        FROM first_pension_pensionproposal
        WHERE emp_cd = %s
          AND (%s = '' OR ca_number = %s)
        ORDER BY id DESC
        LIMIT 1
        """,
        [emp, ca, ca],
    )
    if not dj:
        dj = _safe_one(
            cursor,
            """
            SELECT separation_type, separation_date, account_no, lic_bank_cd,
                   bank_cd, pension_roll_no, ca_number
            FROM first_pension_pensionproposal
            WHERE emp_cd = %s
            ORDER BY id DESC
            LIMIT 1
            """,
            [emp],
        )
    if dj:
        sep_type = dj[0]
        sep_dt = dj[1]
        account_no = dj[2]
        lic_bank_cd = dj[3]
        bank_cd = dj[4]
        prop_roll = dj[5]
        ca_number = dj[6]

    # 2) Legacy finance proposal table — fill blanks only
    if not sep_dt or not account_no or not bank_cd or not prop_roll or not ca_number:
        prop = _safe_one(
            cursor,
            """
            SELECT SEPARATION_TYPE, SEPARATION_DT, ACCOUNT_NO, LIC_BANK_CD,
                   BANK_CD, PENSION_ROLL_NO, CA_NUMBER
            FROM fi_pn_mh_pension_proposal
            WHERE EMP_CD = %s
              AND (%s = '' OR CA_NUMBER = %s)
            ORDER BY CA_NUMBER DESC
            LIMIT 1
            """,
            [emp, ca, ca],
        )
        if not prop:
            prop = _safe_one(
                cursor,
                """
                SELECT SEPARATION_TYPE, SEPARATION_DT, ACCOUNT_NO, LIC_BANK_CD,
                       BANK_CD, PENSION_ROLL_NO, CA_NUMBER
                FROM fi_pn_mh_pension_proposal
                WHERE EMP_CD = %s
                ORDER BY CA_NUMBER DESC
                LIMIT 1
                """,
                [emp],
            )
        if prop:
            sep_type = sep_type or prop[0]
            sep_dt = sep_dt or prop[1]
            account_no = account_no or prop[2]
            lic_bank_cd = lic_bank_cd or prop[3]
            bank_cd = bank_cd or prop[4]
            prop_roll = prop_roll or prop[5]
            ca_number = ca_number or prop[6]

    # 3) Fill remaining blanks from pensioner / emp_adm
    if not sep_dt or not sep_type:
        adm = _safe_one(
            cursor,
            """
            SELECT SEPARATION_TYPE, SEPARATION_DT
            FROM fi_xx_mh_emp_adm
            WHERE EMP_CD = %s
            LIMIT 1
            """,
            [emp],
        )
        if adm:
            sep_type = sep_type or adm[0]
            sep_dt = sep_dt or adm[1]

    if not sep_dt:
        sep_dt = pen[19]  # EMP_RET_DT

    account_no = account_no or pen[14]
    lic_bank_cd = lic_bank_cd or pen[15]
    bank_cd = bank_cd or pen[16]
    prop_roll = prop_roll or pen[17]
    ca_number = ca_number or ca

    return (
        pen[0],
        pen[1],
        pen[2],
        pen[3],
        pen[4],
        pen[5],
        pen[6],
        pen[7],
        pen[8],
        pen[9],
        pen[10],
        pen[11],
        pen[12],
        pen[13],
        sep_type,
        sep_dt,
        account_no,
        lic_bank_cd,
        bank_cd,
        prop_roll,
        ca_number,
    )


def build_lic_normal_pen_dtls(emp_id, claim_id=None, aadhar_no=None) -> dict:
    """
    Build print payload for LIC Claim Form-Normal.
    Requires claim id (from saved / default LIC claim row).
    """
    emp = _emp_key(emp_id)
    if not emp:
        raise LicClaimGenerationError("Employee code is required")

    loaded = load_normal_claim(emp, claim_id=claim_id)
    claim = loaded.get("claim") or {}
    cid = _as_str(claim.get("claim_id") or claim_id, 10)
    if not cid:
        raise LicClaimGenerationError("Claim ID not found — save LIC claim first")

    with connection.cursor() as cursor:
        row = _fetch_pensioner_row(cursor, emp, cid)
        if not row:
            raise LicClaimGenerationError(
                f"No pensioner data for employee {emp}"
            )

        (
            _emp_cd,
            original,
            eff_stdt,
            base_cpi,
            commuted_portion,
            rate_commuted,
            payable,
            gratuity,
            commutation_per,
            app_class,
            pen_name,
            pen_sex,
            pen_dob,
            pen_pan,
            sep_type,
            sep_dt,
            account_no,
            lic_bank_cd,
            bank_cd,
            prop_roll,
            ca_number,
        ) = row

        per = _safe_one(
            cursor,
            """
            SELECT
              TRIM(CONCAT_WS(' ', TITLE, FIRST_NAME, MIDDLE_NAME, LAST_NAME)),
              SEX,
              BIRTH_DT
            FROM fi_xx_mh_emp_per
            WHERE EMP_CD = %s
            LIMIT 1
            """,
            [emp],
        )
        name = _as_str(per[0] if per else None) or _as_str(pen_name) or loaded.get(
            "emp_name", ""
        )
        sex_raw = _as_str(per[1] if per else None) or _as_str(pen_sex)
        gender = (
            "MALE"
            if sex_raw.upper().startswith("M")
            else ("FEMALE" if sex_raw else "")
        )
        dob = _as_date(per[2] if per else None) or _as_date(pen_dob)
        dor = _as_date(sep_dt)

        fin = _safe_one(
            cursor,
            "SELECT EMP_CLASS FROM fi_xx_mh_emp_fin WHERE EMP_CD = %s LIMIT 1",
            [emp],
        )
        emp_class = None
        if fin and fin[0] is not None:
            emp_class = fin[0]
        elif app_class is not None:
            emp_class = app_class
        class_code = str(int(float(emp_class))) if emp_class not in (None, "") else ""
        class_roman = CLASS_ROMAN.get(class_code, class_code)

        pan_row = _safe_one(
            cursor,
            "SELECT PAN_NO FROM fi_xx_mh_emp_adm WHERE EMP_CD = %s LIMIT 1",
            [emp],
        )
        pan_no = _as_str(pan_row[0] if pan_row else None) or _as_str(pen_pan)

        original_f = _num(original)
        payable_f = _num(payable)
        cpi = int(_num(base_cpi))
        age = _age_last_birthday(dor, dob)
        dp = _dearness_pension(original_f, cpi, dor)
        da_amt, da_pct = _da_amount(
            cursor,
            original=original_f,
            dp=dp,
            cpi=cpi,
            emp_class=emp_class or 1,
            dor=dor,
        )
        # Field 13 total = Basic(payable) + DP + Initial DA
        tot_pension = _ceil_rupee(da_amt + dp + payable_f)

        portion = _num(commuted_portion)
        rate = _num(rate_commuted)
        if rate <= 0 and portion > 0:
            rate = _commutation_rate_for_age(cursor, age)
        commutation_value = _ceil_rupee(rate * portion) if rate and portion else 0.0

        bank_name, bank_addr = _bank_branch(cursor, _as_str(bank_cd, 10))

        payable_from = None
        if dor:
            y, m = dor.year, dor.month + 1
            if m > 12:
                m = 1
                y += 1
            payable_from = date(y, m, 1)

        address = _as_str(claim.get("address"), 200)
        if not address:
            addr_row = _safe_one(
                cursor,
                """
                SELECT ADDRESS FROM fi_pn_lic_bill_gen
                WHERE EMP_CD = %s AND CLAIM_ID = %s
                LIMIT 1
                """,
                [emp, cid],
            )
            address = _as_str(addr_row[0] if addr_row else None, 200)

        return {
            "report_title": "LIC Claim Form-Normal",
            "org_scheme": "KOLKATA PORT TRUST EMPLOYEES' SUPERANNUATION SCHEME",
            "master_policy_no": "GS(CA)/211060",
            "subtitle": "DATA FOR RETIRED EMPLOYEES FOR WHOM FIRST ANNUITY",
            "installment_label": "INSTALLMENT WILL BE PAYABLE FROM",
            "dock_system": "EMPLOYEES OF KOLKATA DOCK SYSTEM",
            "office_code": "K.DOCK",
            "phone_placeholder": "PH. NO. :(................)",
            "emp_cd": emp,
            "emp_name": name,
            "lic_sl_no": claim.get("lic_sl_no"),
            "pen_roll_no": _as_str(claim.get("pen_roll_no") or prop_roll, 20),
            "claim_id": cid,
            "aadhar_no": _as_str(aadhar_no, 20),
            "gender": gender,
            "pan_no": pan_no,
            "emp_class": class_code,
            "emp_class_roman": class_roman,
            "birth_dt": _fmt_date(dob),
            "retirement_dt": _fmt_date(dor),
            "age_last_birthday": age,
            "separation_type": _as_str(sep_type, 10),
            # Form "Basic Pension" under item 13 = payable after commutation
            "basic_pension": payable_f,
            "original_pension": original_f,
            "dearness_pension": dp,
            "initial_da": da_amt,
            "da_pct": da_pct,
            "payable_pension": payable_f,
            "commuted_portion": portion,
            "commutation_per": _num(commutation_per),
            "commutation_rate": rate,
            "commutation_value": commutation_value,
            "initial_monthly_pension": tot_pension,
            "due_date_first_pension": _fmt_date(payable_from),
            "payable_from": (
                payable_from.strftime("%b/%Y").upper() if payable_from else ""
            ),
            "purchase_price": "",
            "income_tax_note": "Tax to be paid by the Annuitant Directly.",
            "address": address,
            "account_no": _as_str(account_no, 30),
            "bank_name_branch": bank_name,
            "bank_address": bank_addr,
            "base_cpi": cpi,
            "gratuity": _num(gratuity),
            "effective_stdt_pension": _fmt_date(eff_stdt),
            "lic_bank_cd": _as_str(lic_bank_cd, 10),
            "bank_cd": _as_str(bank_cd, 10),
            "ca_number": _as_str(ca_number, 10),
            "remarks": "",
        }
