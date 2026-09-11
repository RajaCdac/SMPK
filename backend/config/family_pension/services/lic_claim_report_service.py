"""
LIC Claim Form — Family (Oracle FI_PN_LIC_FAMILY_PEN_DTLS).

Layout matched from live print sample (ordinary / extra / total pension).
"""

from __future__ import annotations

import math
from datetime import date, datetime, timedelta

from django.db import connection
from django.db.utils import DatabaseError, ProgrammingError

from .lic_claim_generation_service import (
    FamilyLicClaimError,
    _as_str,
    _emp_key,
    load_family_claim,
)


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


def _fmt_date_mon(value) -> str:
    """30-SEP-30 style used in extra-pension narrative."""
    if not value:
        return ""
    if isinstance(value, datetime):
        value = value.date()
    if isinstance(value, date):
        return value.strftime("%d-%b-%y").upper()
    return _fmt_date(value)


def _as_date(value):
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


def _age_on(as_of: date | None, dob: date | None) -> int | None:
    if not as_of or not dob:
        return None
    years = as_of.year - dob.year
    if (as_of.month, as_of.day) < (dob.month, dob.day):
        years -= 1
    return max(0, years)


def _da_block(basic: float, da_pct: float) -> dict:
    da_amt = _ceil_rupee(basic * da_pct / 100.0) if da_pct and basic else 0.0
    return {
        "basic_pension": basic,
        "dearness_pension": 0.0,
        "initial_dr": da_amt,
        "total": _ceil_rupee(basic + da_amt),
    }


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


def build_lic_family_pen_dtls(
    emp_id, claim_id=None, aadhar_no=None, da_pct=None
) -> dict:
    emp = _emp_key(emp_id)
    if not emp:
        raise FamilyLicClaimError("Employee code is required")

    loaded = load_family_claim(emp, claim_id=claim_id)
    claim = loaded.get("claim") or {}
    cid = _as_str(claim.get("claim_id") or claim_id, 10)
    if not cid:
        raise FamilyLicClaimError("Claim ID is required")
    if claim.get("lic_sl_no") is None or str(claim.get("lic_sl_no")).strip() == "":
        raise FamilyLicClaimError("LIC SL No is required — save LIC claim first")

    da = _num(da_pct if da_pct is not None else loaded.get("da_pct"))

    with connection.cursor() as cursor:
        row = _safe_one(
            cursor,
            """
            SELECT
              c.APPLICANT_NAME,
              c.APPLICANT_ADDRESS,
              c.DOD_EMP_PENSIONER,
              c.APPL_DOD,
              c.EMP_DOD,
              c.DOUBLE_FPEN_UPTO,
              c.FPEN_START_MNTH,
              c.FPRN_START_YR,
              c.FPENSION_ROLL_NO,
              f.ORIGINAL_SINGLE_FPENSION_AMT,
              f.ORIGINAL_DOUBLE_FPENSION_AMT,
              f.ORIGINAL_FAMILY_PENSION_AMT,
              f.DOUBLE_FPENSION_UPTO,
              f.SEX,
              f.DOB,
              f.WEF_DT,
              f.FPENSION_ROLL_NO
            FROM fi_pn_mh_fpen_caclaim c
            LEFT JOIN fi_pn_mh_familypensioner f
              ON f.EMP_CD = c.EMP_CD AND f.CLMCA_ID = c.CLMCA_ID
            WHERE c.EMP_CD = %s
              AND c.CLMCA_ID = %s
            LIMIT 1
            """,
            [emp, cid],
        )
        if not row:
            raise FamilyLicClaimError(
                f"No family pension claim {cid} for employee {emp}"
            )

        (
            applicant_name,
            applicant_address,
            dod1,
            dod2,
            dod3,
            claim_double_upto,
            start_mnth,
            start_yr,
            claim_roll,
            single_pen,
            double_pen,
            fam_pen,
            fp_double_upto,
            sex,
            dob,
            wef_dt,
            fp_roll,
        ) = row

        # Annuitant DOB/sex/bank preferentially from FP applicant master
        appcn = _safe_one(
            cursor,
            """
            SELECT NAME, DOB, SEX, BANK_CD, ACCOUNT_NO, PAN_NO,
                   CONCAT_WS(
                     ', ',
                     NULLIF(TRIM(PERM_ADDR1), ''),
                     NULLIF(TRIM(PERM_ADDR2), ''),
                     NULLIF(TRIM(PERM_PS), ''),
                     NULLIF(TRIM(PERM_CITY), ''),
                     NULLIF(TRIM(PERM_DIST), ''),
                     NULLIF(TRIM(PERM_STATE), ''),
                     NULLIF(TRIM(PERM_PIN), '')
                   )
            FROM fi_pn_md_fpen_appcn
            WHERE CLMCA_ID = %s
            ORDER BY SL_NO
            LIMIT 1
            """,
            [cid],
        )
        if appcn:
            if not applicant_name:
                applicant_name = appcn[0]
            if appcn[1]:
                dob = appcn[1]
            if appcn[2]:
                sex = appcn[2]
            bank_cd = _as_str(appcn[3], 10)
            account_no = _as_str(appcn[4], 30)
            pan_no = _as_str(appcn[5], 20)
            if appcn[6] and not applicant_address:
                applicant_address = appcn[6]
        else:
            bank_cd = ""
            account_no = ""
            pan_row = _safe_one(
                cursor,
                "SELECT PAN_NO FROM fi_xx_mh_emp_adm WHERE EMP_CD = %s LIMIT 1",
                [emp],
            )
            pan_no = _as_str(pan_row[0] if pan_row else None)

        bank_name, bank_addr = _bank_branch(cursor, bank_cd)

        ordinary_basic = _num(single_pen) or _num(fam_pen)
        total_basic = _num(double_pen) or ordinary_basic
        if total_basic < ordinary_basic:
            total_basic = ordinary_basic
        extra_basic = max(0.0, total_basic - ordinary_basic)

        ordinary = _da_block(ordinary_basic, da)
        total = _da_block(total_basic, da)
        # Extra DR = total DR − ordinary DR (matches Oracle sample totals)
        extra_dr = max(0.0, total["initial_dr"] - ordinary["initial_dr"])
        extra = {
            "basic_pension": extra_basic,
            "dearness_pension": 0.0,
            "initial_dr": extra_dr,
            "total": _ceil_rupee(extra_basic + extra_dr),
        }

        sex_raw = _as_str(sex)
        gender = (
            "FEMALE"
            if sex_raw.upper().startswith("F")
            else ("MALE" if sex_raw else "")
        )

        dod = _as_date(dod1) or _as_date(dod2) or _as_date(dod3)
        birth = _as_date(dob)
        double_upto = _as_date(fp_double_upto) or _as_date(claim_double_upto)

        # Vesting / first month: WEF, else day after DOD, else claim start m/y
        vesting = _as_date(wef_dt)
        if not vesting and dod:
            vesting = dod + timedelta(days=1)
        if not vesting and start_mnth and start_yr:
            try:
                vesting = date(int(start_yr), int(start_mnth), 1)
            except ValueError:
                vesting = None

        age = _age_on(vesting, birth)

        address = _as_str(claim.get("address"), 200) or _as_str(
            applicant_address, 200
        )
        roll = _as_str(claim.get("pen_roll_no") or fp_roll or claim_roll, 20)

        # Narrative for item 13
        extra_upto_text = ""
        if double_upto and vesting and total_basic and ordinary_basic:
            next_day = double_upto + timedelta(days=1)
            extra_upto_text = (
                f"@ {int(total_basic) if total_basic == int(total_basic) else total_basic} "
                f"P.M. w.e.f. {_fmt_date(vesting)} to {_fmt_date_mon(double_upto)} "
                f"and thereafter @ "
                f"{int(ordinary_basic) if ordinary_basic == int(ordinary_basic) else ordinary_basic} "
                f"P.M. w.e.f. {_fmt_date(next_day)} till Death or Re-Marriage "
                f"whichever is earlier."
            )
        elif double_upto:
            extra_upto_text = _fmt_date(double_upto)

        return {
            "report_title": "LIC Claim Form-Family",
            "org_scheme": "KOLKATA PORT TRUST EMPLOYEES' SUPERANNUATION SCHEME",
            "master_policy_no": "GS(CA)/211060",
            "subtitle": (
                "DATA FOR RETIRED EMPLOYEES FOR WHOM FIRST ANNUITY "
                "INSTALLMENT WILL BE PAYABLE FROM"
            ),
            "dock_system": "EMPLOYEES OF KOLKATA DOCK SYSTEM",
            "office_code": "K.DOCK",
            "emp_cd": emp,
            "emp_name": loaded.get("emp_name") or "",
            "applicant_name": _as_str(applicant_name)
            or loaded.get("applicant_name")
            or "",
            "lic_sl_no": claim.get("lic_sl_no"),
            "pen_roll_no": roll,
            "claim_id": cid,
            "aadhar_no": _as_str(aadhar_no, 20),
            "gender": gender,
            "pan_no": pan_no,
            "birth_dt": _fmt_date(birth),
            "date_of_death": _fmt_date(dod),
            "due_date_first_pension": _fmt_date(vesting),
            "due_date_vesting": _fmt_date(vesting),
            "age_on_vesting": age,
            "payable_from": (
                vesting.strftime("%b/%Y").upper() if vesting else ""
            ),
            "da_pct": da,
            "ordinary": ordinary,
            "extra": extra,
            "total_pension": total,
            "extra_pension_upto_text": extra_upto_text,
            "double_fpension_upto": _fmt_date(double_upto),
            "purchase_price": "",
            "income_tax_note": "To be paid by the Annuitant Directly",
            "address": address,
            "account_no": account_no,
            "bank_name_branch": bank_name,
            "bank_address": bank_addr,
            "deceased_lic_annuity_no": "",
            "post_dated_cheques_note": "",
            "remarks": "",
        }
