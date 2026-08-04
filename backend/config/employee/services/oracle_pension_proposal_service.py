from employee.services.oracle_commutation_service import _to_oracle_date
from employee.services.oracle_service import get_oracle_connection


def _clip(value, max_len, default=""):
    if value is None:
        return default
    text = str(value).strip()
    if not text:
        return default
    return text[:max_len]


def _checkbox_yn(value):
    """Checkbox -> Oracle VARCHAR2(1): checked Y, unchecked N (never bind raw bool)."""
    if value is True:
        return "Y"
    if value is False:
        return "N"
    if isinstance(value, str):
        text = value.strip().upper()
        if text in ("Y", "YES", "TRUE", "1", "ON"):
            return "Y"
        return "N"
    if value in (1,):
        return "Y"
    return "N"


def _yn(value):
    """General Y/N flag (strings, legacy 1/0, or booleans)."""
    return _checkbox_yn(value)


def _num(value, default=None):
    if value is None or value == "":
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _int_or_none(value):
    if value is None or value == "":
        return None
    return int(value)


def _held_grat_flg_code(value):
    """Map SMPK held_up_flag to Oracle HELD_GRAT_FLG (VARCHAR2(1))."""
    text = str(value or "").strip().upper()
    if not text:
        return " "
    if text == "GP":
        return "H"
    return text[0]


def _pension_type_code(value):
    """N, F, P, etc. — use first letter (form may send single-char codes)."""
    text = str(value or "").strip().upper()
    if not text:
        return " "
    return text[0]


def _earn_dedn_type_code(row):
    raw = str(row.get("type") or "").strip().upper()
    if raw in ("D", "DEDN", "DEDUCTION"):
        return "D"
    return "E"


def get_next_pension_proposal_no():
    conn = get_oracle_connection()
    cur = conn.cursor()
    try:
        cur.execute(
            """
            SELECT NVL(MAX(TO_NUMBER(PENSION_PROPOSAL_NO)), 0) + 1
            FROM FINANCE.FI_PN_MH_PENSION_PROPOSAL
            WHERE REGEXP_LIKE(PENSION_PROPOSAL_NO, '^[0-9]+$')
            """
        )
        row = cur.fetchone()
        if row and row[0]:
            return str(int(row[0]))
    except Exception:
        pass
    finally:
        cur.close()
        conn.close()
    return "1"


def _sync_fi_pn_md_pension_proposal_rows(cur, ca_number, earning_deductions, user_code):
    """
  Earning/deduction grid -> FINANCE.FI_PN_MD_PENSION_PROPOSAL (keyed by CA_NUMBER).
    """
    ca = _clip(ca_number, 22)
    if not ca:
        raise ValueError("CA Number is required to save earning/deduction rows in Oracle.")

    cur.execute(
        """
        DELETE FROM FINANCE.FI_PN_MD_PENSION_PROPOSAL
        WHERE CA_NUMBER = :CA_NUMBER
        """,
        {"CA_NUMBER": ca},
    )

    user = (user_code or "SYS")[:5]
    inserted = 0

    for row in earning_deductions or []:
        if not isinstance(row, dict):
            continue
        code = _clip(row.get("code"), 3)
        if not code:
            continue

        ed_type = _earn_dedn_type_code(row)
        amount = _num(row.get("amount"), 0) or 0
        priority = _int_or_none(row.get("deduction_priority")) or 0
        deducted_amt = amount if ed_type == "D" else 0

        cur.execute(
            """
            INSERT INTO FINANCE.FI_PN_MD_PENSION_PROPOSAL (
                EARNDEDN_CD,
                CA_NUMBER,
                EARN_DEDN_TYPE,
                AMOUNT,
                E_D_PRIORITY,
                DEDUCTED_AMT,
                DATE_CREATED,
                CREATED_BY
            ) VALUES (
                :EARNDEDN_CD,
                :CA_NUMBER,
                :EARN_DEDN_TYPE,
                :AMOUNT,
                :E_D_PRIORITY,
                :DEDUCTED_AMT,
                SYSDATE,
                :USER_CODE
            )
            """,
            {
                "EARNDEDN_CD": code,
                "CA_NUMBER": ca,
                "EARN_DEDN_TYPE": ed_type,
                "AMOUNT": amount,
                "E_D_PRIORITY": priority,
                "DEDUCTED_AMT": deducted_amt,
                "USER_CODE": user,
            },
        )
        inserted += 1

    return inserted


def _build_oracle_payload(proposal, *, user_code="SYS"):
    separation_dt = _to_oracle_date(proposal.separation_date)
    proposal_dt = _to_oracle_date(proposal.pension_proposal_date) or separation_dt
    if not separation_dt:
        raise ValueError("Separation date is required for Oracle pension proposal.")
    if not proposal_dt:
        raise ValueError("Pension proposal date is required for Oracle pension proposal.")

    pension_proposal_no = (proposal.pension_proposal_no or "").strip()
    if not pension_proposal_no:
        pension_proposal_no = get_next_pension_proposal_no()

    ca_number = (proposal.ca_number or "").strip() or str(proposal.emp_cd).strip()

    return {
        "EMP_CD": str(proposal.emp_cd).strip(),
        "CA_NUMBER": _clip(ca_number, 22, str(proposal.emp_cd).strip()),
        "PENSION_TYPE": _pension_type_code(proposal.pension_type),
        "PENSION_PROPOSAL_NO": _clip(pension_proposal_no, 30, "1"),
        "PENSION_PROPOSAL_DT": proposal_dt,
        "IMPL_MONTH": _int_or_none(proposal.implemented_month),
        "IMPL_YR": _int_or_none(proposal.implemented_year),
        "START_MONTH": _int_or_none(proposal.start_month),
        "START_YR": _int_or_none(proposal.start_year),
        "EMPLOYEE_STATUS": _clip(proposal.employee_status, 1, "E"),
        "VIGILANCE_CLEARANCE_TAG": _checkbox_yn(proposal.vigilance_cleared),
        "VIGILANCE_CLEARANCE_REF_NO": _clip(
            proposal.vigilance_clearance_ref_no, 22
        ),
        "VIGILANCE_CLEARANCE_REF_DT": _to_oracle_date(
            proposal.vigilance_clearance_ref_dt
        ),
        "PROV_PEN_PERCENTAGE": _num(proposal.provisional_pension_pct),
        "QUARTER_STATUS": _clip(proposal.quarter_status, 1),
        "PENSION_OPTION": _clip(proposal.pension_option, 1, " "),
        "PENSION_ROLL_NO": _clip(proposal.pension_roll_no, 22),
        "ID_CARD_SUBMITTED": _checkbox_yn(proposal.id_card_submitted),
        "PORT_CITY_RESIDENT": _clip(proposal.port_city_resident, 1),
        "SEPARATION_TYPE": _clip(proposal.separation_type, 3),
        "SEPARATION_DT": separation_dt,
        "COMP_ALLOWANCE_CHECK_TAG": (
            1
            if proposal.compassionate_allowance
            or _num(proposal.compassionate_allowance_amt)
            else 0
        ),
        "COMP_ALLOWANCE": _num(proposal.compassionate_allowance_amt),
        "GRATUITY_OPTION": _int_or_none(proposal.gratuity_option),
        "BANK_CD": _clip(proposal.bank_cd, 6),
        "DOUBLE_FPEN_ELIGIBILITY": 1 if proposal.eligible_double_family_pension else 0,
        "DOUBLE_FPEN_UPTO": _to_oracle_date(proposal.double_family_pension_upto_date),
        "BASE_CPI": _num(proposal.retirement_cpi),
        "EXTRA_GRAT_TCCS_FLG": _checkbox_yn(proposal.extra_tccs_enabled),
        "EXTRA_GRAT_TCCS_DAYS": _int_or_none(proposal.extra_tccs_days),
        "EXTRA_GRAT_TCCS_MON": _int_or_none(proposal.extra_tccs_months),
        "EXTRA_GRAT_TCCS_YR": _int_or_none(proposal.extra_tccs_years),
        "INCENTIVE_HOLDER_FLG": _clip(proposal.incentive_holder, 1),
        "HELD_GRAT_FLG": _held_grat_flg_code(proposal.held_up_flag),
        "HELD_GRAT_AMT": _num(proposal.held_gratuity_amt),
        "LETTER_NO": _clip(proposal.held_recovery_ref_no, 15),
        "ACEPTED_DT": _to_oracle_date(proposal.held_recovery_date),
        "HELD_COMMU_AMT": _num(proposal.held_recovery_amt),
        "LIC_BANK_CD": _clip(proposal.lic_bank_cd, 6),
        "REGN_NO": _clip(proposal.regn_no, 22),
        "REGN_DATE": _to_oracle_date(proposal.regn_date),
        "ACCOUNT_NO": _clip(proposal.account_no, 20),
        "OPT_GIVEN_BY": _clip(proposal.option_given_by, 1),
        "NOMIN_EFORM_GRAT_FLG": _clip(proposal.nominee_eform, 1),
        "VR_REF_NO": _clip(proposal.vr_ref_no, 30),
        "VR_REF_DT": _to_oracle_date(proposal.vr_ref_dt),
        "USER_CODE": (user_code or "SYS")[:5],
        "_generated_proposal_no": pension_proposal_no,
    }


def upsert_fi_pn_mh_pension_proposal(proposal, *, user_code="SYS"):
    """
    Insert/update FINANCE.FI_PN_MH_PENSION_PROPOSAL and sync earning/deduction rows
    to FINANCE.FI_PN_MD_PENSION_PROPOSAL (by CA_NUMBER).
    """
    payload = _build_oracle_payload(proposal, user_code=user_code)
    earning_rows = proposal.earning_deductions or []

    conn = get_oracle_connection()
    cur = conn.cursor()
    try:
        lookup_bind = {"EMP_CD": payload["EMP_CD"]}
        cur.execute(
            """
            SELECT COUNT(*)
            FROM FINANCE.FI_PN_MH_PENSION_PROPOSAL
            WHERE EMP_CD = :EMP_CD
            """,
            lookup_bind,
        )
        exists = cur.fetchone()[0] > 0

        write_payload = {k: v for k, v in payload.items() if not k.startswith("_")}

        if exists:
            cur.execute(
                """
                UPDATE FINANCE.FI_PN_MH_PENSION_PROPOSAL
                SET CA_NUMBER = :CA_NUMBER,
                    PENSION_TYPE = :PENSION_TYPE,
                    PENSION_PROPOSAL_NO = :PENSION_PROPOSAL_NO,
                    PENSION_PROPOSAL_DT = :PENSION_PROPOSAL_DT,
                    IMPL_MONTH = :IMPL_MONTH,
                    IMPL_YR = :IMPL_YR,
                    START_MONTH = :START_MONTH,
                    START_YR = :START_YR,
                    EMPLOYEE_STATUS = :EMPLOYEE_STATUS,
                    VIGILANCE_CLEARANCE_TAG = :VIGILANCE_CLEARANCE_TAG,
                    VIGILANCE_CLEARANCE_REF_NO = :VIGILANCE_CLEARANCE_REF_NO,
                    VIGILANCE_CLEARANCE_REF_DT = :VIGILANCE_CLEARANCE_REF_DT,
                    PROV_PEN_PERCENTAGE = :PROV_PEN_PERCENTAGE,
                    QUARTER_STATUS = :QUARTER_STATUS,
                    PENSION_OPTION = :PENSION_OPTION,
                    PENSION_ROLL_NO = :PENSION_ROLL_NO,
                    ID_CARD_SUBMITTED = :ID_CARD_SUBMITTED,
                    PORT_CITY_RESIDENT = :PORT_CITY_RESIDENT,
                    SEPARATION_TYPE = :SEPARATION_TYPE,
                    SEPARATION_DT = :SEPARATION_DT,
                    COMP_ALLOWANCE_CHECK_TAG = :COMP_ALLOWANCE_CHECK_TAG,
                    COMP_ALLOWANCE = :COMP_ALLOWANCE,
                    GRATUITY_OPTION = :GRATUITY_OPTION,
                    BANK_CD = :BANK_CD,
                    DOUBLE_FPEN_ELIGIBILITY = :DOUBLE_FPEN_ELIGIBILITY,
                    DOUBLE_FPEN_UPTO = :DOUBLE_FPEN_UPTO,
                    BASE_CPI = :BASE_CPI,
                    EXTRA_GRAT_TCCS_FLG = :EXTRA_GRAT_TCCS_FLG,
                    EXTRA_GRAT_TCCS_DAYS = :EXTRA_GRAT_TCCS_DAYS,
                    EXTRA_GRAT_TCCS_MON = :EXTRA_GRAT_TCCS_MON,
                    EXTRA_GRAT_TCCS_YR = :EXTRA_GRAT_TCCS_YR,
                    INCENTIVE_HOLDER_FLG = :INCENTIVE_HOLDER_FLG,
                    HELD_GRAT_FLG = :HELD_GRAT_FLG,
                    HELD_GRAT_AMT = :HELD_GRAT_AMT,
                    LETTER_NO = :LETTER_NO,
                    ACEPTED_DT = :ACEPTED_DT,
                    HELD_COMMU_AMT = :HELD_COMMU_AMT,
                    LIC_BANK_CD = :LIC_BANK_CD,
                    REGN_NO = :REGN_NO,
                    REGN_DATE = :REGN_DATE,
                    ACCOUNT_NO = :ACCOUNT_NO,
                    OPT_GIVEN_BY = :OPT_GIVEN_BY,
                    NOMIN_EFORM_GRAT_FLG = :NOMIN_EFORM_GRAT_FLG,
                    VR_REF_NO = :VR_REF_NO,
                    VR_REF_DT = :VR_REF_DT,
                    DATE_MODIFIED = SYSDATE,
                    MODIFIED_BY = :USER_CODE
                WHERE EMP_CD = :EMP_CD
                """,
                write_payload,
            )
        else:
            cur.execute(
                """
                INSERT INTO FINANCE.FI_PN_MH_PENSION_PROPOSAL (
                    EMP_CD, CA_NUMBER, PENSION_TYPE, PENSION_PROPOSAL_NO,
                    PENSION_PROPOSAL_DT, IMPL_MONTH, IMPL_YR, START_MONTH, START_YR,
                    EMPLOYEE_STATUS, VIGILANCE_CLEARANCE_TAG,
                    VIGILANCE_CLEARANCE_REF_NO, VIGILANCE_CLEARANCE_REF_DT,
                    PROV_PEN_PERCENTAGE, QUARTER_STATUS, PENSION_OPTION,
                    PENSION_ROLL_NO, ID_CARD_SUBMITTED, PORT_CITY_RESIDENT,
                    SEPARATION_TYPE, SEPARATION_DT,
                    COMP_ALLOWANCE_CHECK_TAG, COMP_ALLOWANCE, GRATUITY_OPTION,
                    BANK_CD, DOUBLE_FPEN_ELIGIBILITY, DOUBLE_FPEN_UPTO, BASE_CPI,
                    EXTRA_GRAT_TCCS_FLG, EXTRA_GRAT_TCCS_DAYS, EXTRA_GRAT_TCCS_MON,
                    EXTRA_GRAT_TCCS_YR, INCENTIVE_HOLDER_FLG, HELD_GRAT_FLG,
                    HELD_GRAT_AMT, LETTER_NO, ACEPTED_DT, HELD_COMMU_AMT,
                    LIC_BANK_CD, REGN_NO, REGN_DATE, ACCOUNT_NO,
                    OPT_GIVEN_BY, NOMIN_EFORM_GRAT_FLG, VR_REF_NO, VR_REF_DT,
                    DATE_CREATED, CREATED_BY
                ) VALUES (
                    :EMP_CD, :CA_NUMBER, :PENSION_TYPE, :PENSION_PROPOSAL_NO,
                    :PENSION_PROPOSAL_DT, :IMPL_MONTH, :IMPL_YR, :START_MONTH, :START_YR,
                    :EMPLOYEE_STATUS, :VIGILANCE_CLEARANCE_TAG,
                    :VIGILANCE_CLEARANCE_REF_NO, :VIGILANCE_CLEARANCE_REF_DT,
                    :PROV_PEN_PERCENTAGE, :QUARTER_STATUS, :PENSION_OPTION,
                    :PENSION_ROLL_NO, :ID_CARD_SUBMITTED, :PORT_CITY_RESIDENT,
                    :SEPARATION_TYPE, :SEPARATION_DT,
                    :COMP_ALLOWANCE_CHECK_TAG, :COMP_ALLOWANCE, :GRATUITY_OPTION,
                    :BANK_CD, :DOUBLE_FPEN_ELIGIBILITY, :DOUBLE_FPEN_UPTO, :BASE_CPI,
                    :EXTRA_GRAT_TCCS_FLG, :EXTRA_GRAT_TCCS_DAYS, :EXTRA_GRAT_TCCS_MON,
                    :EXTRA_GRAT_TCCS_YR, :INCENTIVE_HOLDER_FLG, :HELD_GRAT_FLG,
                    :HELD_GRAT_AMT, :LETTER_NO, :ACEPTED_DT, :HELD_COMMU_AMT,
                    :LIC_BANK_CD, :REGN_NO, :REGN_DATE, :ACCOUNT_NO,
                    :OPT_GIVEN_BY, :NOMIN_EFORM_GRAT_FLG, :VR_REF_NO, :VR_REF_DT,
                    SYSDATE, :USER_CODE
                )
                """,
                write_payload,
            )

        if cur.rowcount == 0:
            raise ValueError(
                f"No row written in FI_PN_MH_PENSION_PROPOSAL for {proposal.emp_cd}."
            )

        earn_count = _sync_fi_pn_md_pension_proposal_rows(
            cur,
            write_payload["CA_NUMBER"],
            earning_rows,
            user_code,
        )

        conn.commit()
        return {
            "exists": exists,
            "pension_proposal_no": payload["_generated_proposal_no"],
            "ca_number": write_payload["CA_NUMBER"],
            "earning_deduction_rows_synced": earn_count,
        }
    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()
        conn.close()
