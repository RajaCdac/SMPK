"""
Read-only first-pension archive from MySQL `smpk_pension` (imported finance tables).

Source: Oracle FINANCE schema dump, synced into local smpk_pension.
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from django.db import connections


def _clip_emp(emp_cd) -> str:
    return str(emp_cd or "").strip()[:5]


def _fmt_date(value):
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.strftime("%d-%m-%Y")
    if isinstance(value, date):
        return value.strftime("%d-%m-%Y")
    return str(value)


def _fmt_iso_date(value):
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date().isoformat()
    if isinstance(value, date):
        return value.isoformat()
    return str(value)[:10]


def _num(value):
    if value is None:
        return None
    if isinstance(value, Decimal):
        return float(value)
    try:
        return float(value)
    except (TypeError, ValueError):
        return value


def _fetchone(sql, params=None):
    conn = connections["default"]
    with conn.cursor() as cur:
        cur.execute(sql, params or [])
        row = cur.fetchone()
        if not row:
            return None
        cols = [c[0] for c in cur.description]
        return dict(zip(cols, row))


def _fetchall(sql, params=None):
    conn = connections["default"]
    with conn.cursor() as cur:
        cur.execute(sql, params or [])
        cols = [c[0] for c in cur.description]
        return [dict(zip(cols, row)) for row in cur.fetchall()]


def live_case_exists(emp_cd: str) -> bool:
    """Prefer live for processing — archive only notes when also in live."""
    try:
        from first_pension.models import PensionCase

        return PensionCase.objects.filter(emp_code=_clip_emp(emp_cd)).exists()
    except Exception:
        return False


def get_employee_header(emp_cd: str) -> dict | None:
    emp = _clip_emp(emp_cd)
    adm = _fetchone(
        """
        SELECT EMP_CD, JOIN_DT, EXP_RET_DT, SEPARATION_DT, SEPARATION_TYPE
        FROM FI_XX_MH_EMP_ADM
        WHERE EMP_CD = %s
        """,
        [emp],
    )
    if not adm:
        # Still allow archive lookup via pensioner / oldbill alone.
        pen = _fetchone(
            "SELECT EMP_CD, CA_NUMBER FROM FI_PN_MH_PENSIONER WHERE EMP_CD = %s LIMIT 1",
            [emp],
        )
        old = _fetchone(
            "SELECT EMP_CD FROM FI_PN_MH_OLDBILL_PARAM WHERE EMP_CD = %s",
            [emp],
        )
        if not pen and not old:
            return None
        adm = {
            "EMP_CD": emp,
            "JOIN_DT": None,
            "EXP_RET_DT": None,
            "SEPARATION_DT": None,
            "SEPARATION_TYPE": None,
        }

    per = _fetchone(
        """
        SELECT TITLE, FIRST_NAME, MIDDLE_NAME, LAST_NAME, BIRTH_DT
        FROM FI_XX_MH_EMP_PER
        WHERE EMP_CD = %s
        """,
        [emp],
    ) or {}
    fin = _fetchone(
        """
        SELECT SCALE_SL, EMP_CLASS
        FROM FI_XX_MH_EMP_FIN
        WHERE EMP_CD = %s
        """,
        [emp],
    ) or {}

    parts = [
        per.get("TITLE"),
        per.get("FIRST_NAME"),
        per.get("MIDDLE_NAME"),
        per.get("LAST_NAME"),
    ]
    name = " ".join(str(p).strip() for p in parts if p and str(p).strip())

    return {
        "emp_id": emp,
        "name": name or emp,
        "join_date": _fmt_date(adm.get("JOIN_DT")),
        "expected_retirement_date": _fmt_date(
            adm.get("SEPARATION_DT") or adm.get("EXP_RET_DT")
        ),
        "birth_date": _fmt_date(per.get("BIRTH_DT")),
        "class": fin.get("EMP_CLASS"),
        "scale": fin.get("SCALE_SL"),
        "basic_amount": None,
        "separation_type": adm.get("SEPARATION_TYPE"),
        "designation": None,
    }


def get_no_pay(emp_cd: str) -> dict | None:
    row = _fetchone(
        """
        SELECT EMP_CD, APPOINTMENT_DT, RETIREMENT_DT, BIRTH_DT,
               NPAY_PRIOR_10MTH, NPAY_MORETHAN_240_DYS, DNON_DAYS,
               SUSP_DAYS, BOY_SERV_DAYS, EDN_LV_DAYS
        FROM FI_PN_MH_OLDBILL_PARAM
        WHERE EMP_CD = %s
        """,
        [_clip_emp(emp_cd)],
    )
    if not row:
        return None
    return {
        "emp_code": row["EMP_CD"],
        "no_pay_days": int(row["NPAY_PRIOR_10MTH"] or 0),
        "no_pay_more_than_240_days": int(row["NPAY_MORETHAN_240_DYS"] or 0),
        "dies_non_days": int(row["DNON_DAYS"] or 0),
        "suspension_days": int(row["SUSP_DAYS"] or 0),
        "boys_serv_days": int(row["BOY_SERV_DAYS"] or 0),
        "edn_lv_days": int(row["EDN_LV_DAYS"] or 0) if row.get("EDN_LV_DAYS") is not None else None,
        "appointment_dt": _fmt_date(row.get("APPOINTMENT_DT")),
        "retirement_dt": _fmt_date(row.get("RETIREMENT_DT")),
    }


def get_commutations(emp_cd: str) -> list[dict]:
    rows = _fetchall(
        """
        SELECT APPCN_NO, APPCN_DT, EMP_CD, APPLICATION_TIME, COMM_START_MNTH,
               COMM_START_YR, APPLICATION_RCVD_DT, IMPL_FPEN_COMBILL,
               COMMUTATION_DATE, RESTORATION_DT, COMMUTATION_PER,
               MO_CERTIFICATION_DT, MO_CERTIFICATE_REF, COMMUTATION_REASONS,
               BANK_CD, REF_NO, IMPL_BILL_NO, SANCTION_PARTICULARS,
               COMMUTATION_AMT, PEN_AMT, CA_NO
        FROM FI_PN_MH_APPLICATION
        WHERE EMP_CD = %s
        ORDER BY APPCN_DT DESC, APPCN_NO DESC
        """,
        [_clip_emp(emp_cd)],
    )
    out = []
    for r in rows:
        out.append(
            {
                "appcn_no": r.get("APPCN_NO"),
                "emp_cd": r.get("EMP_CD"),
                "application_time": r.get("APPLICATION_TIME"),
                "comm_start_mnth": r.get("COMM_START_MNTH"),
                "comm_start_yr": r.get("COMM_START_YR"),
                "appcn_dt": _fmt_iso_date(r.get("APPCN_DT")),
                "application_rcvd_dt": _fmt_iso_date(r.get("APPLICATION_RCVD_DT")),
                "impl_fpen_combill": r.get("IMPL_FPEN_COMBILL"),
                "commutation_dt": _fmt_iso_date(r.get("COMMUTATION_DATE")),
                "restoration_dt": _fmt_iso_date(r.get("RESTORATION_DT")),
                "commutation_per": _num(r.get("COMMUTATION_PER")),
                "mo_certificate_dt": _fmt_iso_date(r.get("MO_CERTIFICATION_DT")),
                "mo_certificate_ref": r.get("MO_CERTIFICATE_REF"),
                "commutation_reasons": r.get("COMMUTATION_REASONS"),
                "bank_cd": r.get("BANK_CD"),
                "ref_no": r.get("REF_NO"),
                "bill_no": r.get("IMPL_BILL_NO"),
                "sanction_parameter": r.get("SANCTION_PARTICULARS"),
                "commutation_amt": _num(r.get("COMMUTATION_AMT")),
                "pen_amt": _num(r.get("PEN_AMT")),
                "ca_no": r.get("CA_NO"),
            }
        )
    return out


def get_amount(emp_cd: str) -> dict | None:
    row = _fetchone(
        """
        SELECT *
        FROM FI_PN_MH_PENSIONER
        WHERE EMP_CD = %s
        LIMIT 1
        """,
        [_clip_emp(emp_cd)],
    )
    if not row:
        return None

    def ymd(y, m, d):
        if y is None and m is None and d is None:
            return None
        return f"{int(y or 0)}Y {int(m or 0)}M {int(d or 0)}D"

    return {
        "calculated": True,
        "inputs_ready": True,
        "ca_number": row.get("CA_NUMBER"),
        "original_pension_amount": _num(row.get("ORIGINAL_PENSION_AMT")),
        "pension_amount": _num(row.get("ORIGINAL_PENSION_AMT")),
        "payable_pension": _num(row.get("PAYABLE_PENSION")),
        "commutation_percent": _num(row.get("COMMUTATION_PER")),
        "commuted_portion": _num(row.get("COMMUTED_PORTION")),
        "commutation_amount": _num(row.get("COMMUTED_PORTION")),
        "rate_commuted_portion": _num(row.get("RATE_COMMUTED_PORTION")),
        "gratuity_amount": _num(row.get("GRATUITY")),
        "gratuity_emoluments": _num(row.get("GRATUITY_EMOLUMENTS")),
        "pension_emoluments": _num(row.get("PENSION_EMOLUMENTS")),
        "pension_basic": _num(row.get("PENSION_EMOLUMENTS")),
        "emoluments_basic": _num(row.get("PENSION_EMOLUMENTS")),
        "last_basic": _num(row.get("PENSION_EMOLUMENTS")),
        "relief": _num(row.get("RELIEF")),
        "no_pay_days": _num(row.get("NO_PAY_PERIOD")),
        "dies_non_days": row.get("DIES_NON_PERIOD"),
        "tccs": ymd(row.get("TCCS_YR"), row.get("TCCS_MONTH"), row.get("TCCS_DAYS")),
        "tqs": ymd(row.get("TQS_YR"), row.get("TQS_MONTH"), row.get("TQS_DAYS")),
        "total_service": ymd(row.get("POS_YR"), row.get("POS_MONTH"), row.get("POS_DAYS")),
        "effective_stdt_pension": _fmt_date(row.get("EFFECTIVE_STDT_PENSION")),
        "date_commutation": _fmt_date(row.get("DATE_COMMUTATION")),
        "restoration_dt": _fmt_date(row.get("DT_OF_RESTORATION")),
        "single_fpen_amt": _num(row.get("SINGLE_FPEN_AMT")),
        "double_fpen_amt": _num(row.get("DOUBLE_FPEN_AMT")),
        "source": "archive_finance",
    }


def get_proposal(emp_cd: str) -> dict | None:
    row = _fetchone(
        """
        SELECT CA_NUMBER, EMP_CD, PENSION_PROPOSAL_DT, SEPARATION_DT, PENSION_TYPE
        FROM FI_PN_MH_PENSION_PROPOSAL
        WHERE EMP_CD = %s
        ORDER BY PENSION_PROPOSAL_DT DESC
        LIMIT 1
        """,
        [_clip_emp(emp_cd)],
    )
    if not row:
        return None
    return {
        "ca_number": row.get("CA_NUMBER"),
        "emp_cd": row.get("EMP_CD"),
        "pension_proposal_dt": _fmt_date(row.get("PENSION_PROPOSAL_DT")),
        "separation_dt": _fmt_date(row.get("SEPARATION_DT")),
        "pension_type": row.get("PENSION_TYPE"),
    }


def get_bills(emp_cd: str) -> list[dict]:
    rows = _fetchall(
        """
        SELECT DISTINCT
               b.BILL_NO, b.BILL_TYPE, b.BILL_MONTH, b.BILL_YR,
               b.VOUCHER_NO, b.TOTAL_AMT_EARNED, b.TOTAL_AMT_DEDUCTED,
               b.BANK_CD, b.POSTED, b.ABSTRACT_DATE
        FROM FI_PN_TH_PENSION_BILL b
        INNER JOIN FI_PN_TH_FIRST_MONTH_PENSION h
          ON h.BILL_NO = b.BILL_NO
        WHERE h.EMP_CD = %s
        ORDER BY b.BILL_YR DESC, b.BILL_MONTH DESC, b.BILL_NO DESC
        """,
        [_clip_emp(emp_cd)],
    )
    return [
        {
            "bill_no": r.get("BILL_NO"),
            "bill_type": r.get("BILL_TYPE"),
            "bill_month": r.get("BILL_MONTH"),
            "bill_year": r.get("BILL_YR"),
            "voucher_no": r.get("VOUCHER_NO"),
            "total_earned": _num(r.get("TOTAL_AMT_EARNED")),
            "total_deducted": _num(r.get("TOTAL_AMT_DEDUCTED")),
            "bank_cd": r.get("BANK_CD"),
            "posted": r.get("POSTED"),
            "abstract_date": _fmt_date(r.get("ABSTRACT_DATE")),
        }
        for r in rows
    ]


def get_bill_detail(bill_no: str) -> dict | None:
    bill = _fetchone(
        "SELECT * FROM FI_PN_TH_PENSION_BILL WHERE BILL_NO = %s",
        [str(bill_no).strip()],
    )
    if not bill:
        return None
    lines = _fetchall(
        """
        SELECT FMPEN_ID, EMP_CD, CA_NO, PENSION_TYPE, PENSION_MONTH, PENSION_YR,
               ORIGINAL_FPENSION_AMT, PAYABLE_PENSION, BILL_NO, BANK_CD
        FROM FI_PN_TH_FIRST_MONTH_PENSION
        WHERE BILL_NO = %s
        ORDER BY EMP_CD
        """,
        [str(bill_no).strip()],
    )
    voucher_no = bill.get("VOUCHER_NO")
    journals = []
    if voucher_no:
        journals = get_journal(voucher_no).get("headers") or []
    else:
        # JV may reference bill as REF_NO
        jv_rows = _fetchall(
            """
            SELECT VOUCHER_NO, VOUCHER_DT, REF_NO, TOT_AMT, TRAN_TYPE, NARRATION
            FROM FI_PN_TH_JV
            WHERE REF_NO = %s
            ORDER BY VOUCHER_DT DESC
            """,
            [str(bill_no).strip()],
        )
        journals = [
            {
                "voucher_no": r.get("VOUCHER_NO"),
                "voucher_dt": _fmt_date(r.get("VOUCHER_DT")),
                "ref_no": r.get("REF_NO"),
                "tot_amt": _num(r.get("TOT_AMT")),
                "tran_type": r.get("TRAN_TYPE"),
                "narration": r.get("NARRATION"),
            }
            for r in jv_rows
        ]

    return {
        "bill_no": bill.get("BILL_NO"),
        "bill_type": bill.get("BILL_TYPE"),
        "bill_month": bill.get("BILL_MONTH"),
        "bill_year": bill.get("BILL_YR"),
        "voucher_no": bill.get("VOUCHER_NO"),
        "total_earned": _num(bill.get("TOTAL_AMT_EARNED")),
        "total_deducted": _num(bill.get("TOTAL_AMT_DEDUCTED")),
        "bank_cd": bill.get("BANK_CD"),
        "posted": bill.get("POSTED"),
        "first_month_headers": [
            {
                "fmpen_id": ln.get("FMPEN_ID"),
                "emp_cd": ln.get("EMP_CD"),
                "ca_no": ln.get("CA_NO"),
                "pension_type": ln.get("PENSION_TYPE"),
                "pension_month": ln.get("PENSION_MONTH"),
                "pension_year": ln.get("PENSION_YR"),
                "original_fpension_amt": _num(ln.get("ORIGINAL_FPENSION_AMT")),
                "payable_pension": _num(ln.get("PAYABLE_PENSION")),
                "bank_cd": ln.get("BANK_CD"),
            }
            for ln in lines
        ],
        "journals": journals,
    }


def get_journal(voucher_no: str) -> dict:
    headers = _fetchall(
        """
        SELECT VOUCHER_NO, VOUCHER_DT, REF_NO, REF_DT, TOT_AMT, TRAN_TYPE,
               NARRATION, YR, MTH, FA_NO
        FROM FI_PN_TH_JV
        WHERE VOUCHER_NO = %s
        """,
        [str(voucher_no).strip()],
    )
    details = _fetchall(
        """
        SELECT VOUCHER_NO, SL_NO, ALOC_CD1, ALOC_CD2, ALOC_CD3,
               DR_CR_FLAG, AMOUNT, REMARKS, TYPE_CD
        FROM FI_PN_TD_JV
        WHERE VOUCHER_NO = %s
        ORDER BY SL_NO
        """,
        [str(voucher_no).strip()],
    )
    return {
        "voucher_no": str(voucher_no).strip(),
        "headers": [
            {
                "voucher_no": h.get("VOUCHER_NO"),
                "voucher_dt": _fmt_date(h.get("VOUCHER_DT")),
                "ref_no": h.get("REF_NO"),
                "ref_dt": _fmt_date(h.get("REF_DT")),
                "tot_amt": _num(h.get("TOT_AMT")),
                "tran_type": h.get("TRAN_TYPE"),
                "narration": h.get("NARRATION"),
                "year": h.get("YR"),
                "month": h.get("MTH"),
                "fa_no": h.get("FA_NO"),
            }
            for h in headers
        ],
        "details": [
            {
                "voucher_no": d.get("VOUCHER_NO"),
                "sl_no": d.get("SL_NO"),
                "aloc_cd1": d.get("ALOC_CD1"),
                "aloc_cd2": d.get("ALOC_CD2"),
                "aloc_cd3": d.get("ALOC_CD3"),
                "dr_cr_flag": d.get("DR_CR_FLAG"),
                "amount": _num(d.get("AMOUNT")),
                "remarks": d.get("REMARKS"),
                "type_cd": d.get("TYPE_CD"),
            }
            for d in details
        ],
    }


def build_archive_employee_payload(emp_cd: str) -> dict | None:
    header = get_employee_header(emp_cd)
    if not header:
        return None

    no_pay = get_no_pay(emp_cd)
    commutations = get_commutations(emp_cd)
    amount = get_amount(emp_cd)
    proposal = get_proposal(emp_cd)
    bills = get_bills(emp_cd)
    exists_in_live = live_case_exists(emp_cd)

    return {
        "mode": "archive",
        "read_only": True,
        "exists_in_live": exists_in_live,
        "prefer_live_message": (
            "This employee also exists in live First Pension. "
            "Prefer live for new processing; Archive is read-only history."
            if exists_in_live
            else None
        ),
        "employee": header,
        "no_pay_exists": bool(no_pay),
        "no_pay_data": no_pay,
        "commutation_list": commutations,
        "commutation_data": commutations[0] if commutations else None,
        "amount_data": amount,
        "proposal_data": proposal,
        "bills": bills,
        "has_archive_data": bool(
            no_pay or commutations or amount or proposal or bills
        ),
    }
