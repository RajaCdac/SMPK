"""
Summary of Journal report — port of FI_PN_TD_JV_RPT.fmb / FI_PN_TD_JV_RPT.rdf.

RDF Q_1 joins FI_PN_TD_JV + FI_MA_M_H_ZONALMAP (CPT_ZONAL_DES) + FI_PN_TH_JV.
Abstract from FI_PN_TH_BILLPASS. Same layout for PFN / bank LIC / bank non-LIC;
wording differs via voucher type label and narration on the JV header.
"""

from calendar import month_name
from decimal import Decimal

from django.utils import timezone

from ..oracle_mirror import FiPnTdJv, FiPnThJv, FiPnThPensionBill
from .manual_journal_service import compute_journal_totals
from .zonalmap_service import lookup_cpt_zonal

ORG_NAME = "SYAMA PRASAD MOOKERJEE PORT, KOLKATA"
REPORT_TITLE = "Summary of Journal"

TRAN_TYPE_LABELS = {
    "PNJV/C": "Commutation JV",
    "PNJV/E": "Exgratia JV",
    "PNJV/F": "Family Pension JV",
    "PNJV/P": "Pension JV",
    "PNJV/G": "G20 JV",
    "PNJV/M": "Monthly All JV",
    "PNJV/N": "Manual JV",
}


class JournalSummaryReportError(Exception):
    pass


def _clip(value, max_len, default=""):
    if value is None:
        return default
    text = str(value).strip()
    if not text:
        return default
    return text[:max_len]


def _fin_yr_param(yr, mth):
    yr = int(yr)
    mth = int(mth)
    return yr - 1 if mth < 4 else yr


def _format_month_upper(mth):
    try:
        return month_name[int(mth)].upper()
    except (TypeError, ValueError, IndexError):
        return str(mth or "").upper()


def _format_dd_mm_yy(value):
    if not value:
        return ""
    if hasattr(value, "strftime"):
        return value.strftime("%d/%m/%y")
    return str(value)[:10]


def _format_dd_mm_yyyy(value=None):
    dt = value or timezone.localdate()
    if hasattr(dt, "strftime"):
        return dt.strftime("%d/%m/%Y")
    return str(dt)[:10]


def _format_abstract_dt(value):
    if not value:
        return ""
    if hasattr(value, "strftime"):
        return value.strftime("%d-%b-%y").upper()
    return str(value)[:12].upper()


def _format_oracle_amount(value):
    return f"{float(Decimal(str(value or 0))):.2f}"


def _format_alloc_cd(value):
    text = _clip(value, 7, "000")
    if text in ("0", ""):
        return "000"
    return text


def _detect_report_kind(*, ref_no, tran_type):
    ref = (ref_no or "").upper()
    if ref.startswith("PFN/") or tran_type == "PNJV/F":
        return "pfn_bill"
    if "LICI" in ref:
        return "bank_lic"
    if "NLIC" in ref:
        return "bank_non_lic"
    if ref.startswith("PPN/") or tran_type == "PNJV/P":
        return "ppn_bill"
    return "other"


def _bank_name_from_ref(ref_no):
    token = (ref_no or "").strip().split()[0].upper()
    if not token:
        return ""
    try:
        from master_data.models import FiPmMhBankAbbr

        row = FiPmMhBankAbbr.objects.filter(bank_type__iexact=token[:3]).first()
        if row and row.bank_name:
            name = row.bank_name.upper()
            if "BANK" not in name:
                name = f"{name} BANK"
            return name
    except Exception:
        pass
    return f"{token} BANK"


def _build_bank_narration(*, ref_no, mth, yr):
    bank = _bank_name_from_ref(ref_no)
    return (
        f"BEING THE AMOUNT OF MONTHLY PENSION OF {bank} "
        f"FOR THE MONTH OF {_format_month_upper(mth)} {int(yr)}"
    )


def _resolve_narration(*, header, bill, report_kind, mth, yr):
    narration = _clip(header.narration, 500)
    if narration:
        return narration
    if report_kind in ("bank_lic", "bank_non_lic"):
        return _build_bank_narration(ref_no=header.ref_no, mth=mth, yr=yr)
    if bill and bill.remarks:
        return _clip(bill.remarks, 500)
    return ""


def _voucher_type_label(tran_type):
    return TRAN_TYPE_LABELS.get(_clip(tran_type, 10), tran_type or "")


def _resolve_header(*, yr, mth, ref_no):
    fin_yr = _fin_yr_param(yr, mth)
    ref_no = _clip(ref_no, 25)
    qs = FiPnThJv.objects.filter(yr=fin_yr, mth=int(mth))
    if ref_no and ref_no.upper() not in ("ALL", "%"):
        qs = qs.filter(ref_no=ref_no)
    header = qs.order_by("-voucher_dt", "-voucher_no").first()

    # Bill calendar month often differs from JV month (e.g. PPN/02/2026/*
    # vouchered as PNJV/.../1/... in January). Fall back by bill/ref.
    if not header and ref_no and ref_no.upper() not in ("ALL", "%"):
        bill = FiPnThPensionBill.objects.filter(bill_no=ref_no).first()
        if bill and (bill.voucher_no or "").strip():
            header = FiPnThJv.objects.filter(voucher_no=bill.voucher_no).first()
        if not header:
            header = (
                FiPnThJv.objects.filter(ref_no=ref_no)
                .order_by("-voucher_dt", "-voucher_no")
                .first()
            )

    if not header:
        raise JournalSummaryReportError(
            f"No journal voucher found for fin yr={fin_yr}, month={mth}, ref={ref_no or 'ALL'}."
        )
    return header, fin_yr


def list_bills_for_journal_report(*, yr, mth):
    fin_yr = _fin_yr_param(yr, mth)
    refs = set(
        FiPnThJv.objects.filter(yr=fin_yr, mth=int(mth))
        .exclude(ref_no="")
        .values_list("ref_no", flat=True)
    )
    # Include PPN bills for the selected calendar month even if JV month differs.
    for bill_no in FiPnThPensionBill.objects.filter(
        bill_month=int(mth),
        bill_yr=int(yr),
    ).exclude(voucher_no="").values_list("bill_no", flat=True):
        refs.add(bill_no)
    for bill_no in FiPnThJv.objects.filter(
        ref_no__startswith=f"PFN/{int(mth):02d}/{int(yr)}/"
    ).values_list("ref_no", flat=True):
        refs.add(bill_no)
    for bill_no in FiPnThJv.objects.filter(
        ref_no__startswith=f"PPN/{int(mth):02d}/{int(yr)}/"
    ).values_list("ref_no", flat=True):
        refs.add(bill_no)

    items = [{"ref_no": r, "bill_no": r} for r in sorted(refs)]
    items.insert(0, {"ref_no": "ALL", "bill_no": "ALL"})
    return {"yr": int(yr), "mth": int(mth), "fin_yr": fin_yr, "bills": items}


def _fetch_abstract_from_mysql(*, ref_no, yr, mth):
    try:
        from django.db import connection

        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT DISTINCT abstract_no, abstract_dt
                FROM fi_pn_th_billpass
                WHERE TRIM(DBILL_REG_NO) = TRIM(%s)
                  AND MTH = %s
                  AND YEAR(BILL_DT) = %s
                LIMIT 1
                """,
                [_clip(ref_no, 25), int(mth), int(yr)],
            )
            row = cursor.fetchone()
            if row:
                return _clip(row[0], 22), row[1]
    except Exception:
        pass
    return "", None


def _fetch_abstract_from_oracle(*, ref_no, yr, mth):
    try:
        from employee.services.oracle_service import (
            oracle_reads_enabled,
            try_oracle_connection,
        )

        if not oracle_reads_enabled():
            return "", None
        conn = try_oracle_connection()
        if not conn:
            return "", None
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT DISTINCT abstract_no, abstract_dt
                FROM FINANCE.FI_PN_TH_BILLPASS
                WHERE LTRIM(RTRIM(DBILL_REG_NO)) = LTRIM(RTRIM(:ref_no))
                  AND MTH = :mth
                  AND TO_NUMBER(TO_CHAR(BILL_DT, 'YYYY')) = :yr
                """,
                {"ref_no": _clip(ref_no, 25), "mth": int(mth), "yr": int(yr)},
            )
            row = cursor.fetchone()
            if row:
                return _clip(row[0], 22), row[1]
    except Exception:
        pass
    return "", None


def _resolve_abstract(*, bill, ref_no, yr, mth):
    abstract_no = ""
    abstract_dt = None
    if bill:
        abstract_no = _clip(bill.bill_abstract_no, 22)
        abstract_dt = bill.abstract_date
    if not abstract_no or not abstract_dt:
        mysql_no, mysql_dt = _fetch_abstract_from_mysql(ref_no=ref_no, yr=yr, mth=mth)
        abstract_no = abstract_no or mysql_no
        abstract_dt = abstract_dt or mysql_dt
    if not abstract_no or not abstract_dt:
        ora_no, ora_dt = _fetch_abstract_from_oracle(ref_no=ref_no, yr=yr, mth=mth)
        abstract_no = abstract_no or ora_no
        abstract_dt = abstract_dt or ora_dt
    return abstract_no, abstract_dt


def build_journal_summary_report(*, yr, mth, ref_no=""):
    header, fin_yr = _resolve_header(yr=yr, mth=mth, ref_no=ref_no)
    ref_no = header.ref_no or _clip(ref_no, 25)
    bill = FiPnThPensionBill.objects.filter(bill_no=ref_no).first()

    report_kind = _detect_report_kind(ref_no=ref_no, tran_type=header.tran_type)
    abstract_no, abstract_dt = _resolve_abstract(
        bill=bill, ref_no=ref_no, yr=yr, mth=mth
    )
    narration = _resolve_narration(
        header=header,
        bill=bill,
        report_kind=report_kind,
        mth=mth,
        yr=yr,
    )
    voucher_type = _voucher_type_label(header.tran_type)

    detail_qs = FiPnTdJv.objects.filter(voucher_no=header.voucher_no).order_by(
        "-dr_cr_flag", "zonal_cd", "aloc_cd1", "aloc_cd2", "aloc_cd3"
    )

    zonal_cache = {}
    rows = []
    for line in detail_qs:
        z = int(line.zonal_cd)
        if z not in zonal_cache:
            # Display CPT_ZONAL_CD + desc (e.g. 12 → "10 REVENUE ACCOUNT")
            zonal_cache[z] = lookup_cpt_zonal(z)
        cpt = zonal_cache[z]
        amt = Decimal(str(line.amount or 0))
        is_debit = line.dr_cr_flag == "D"
        rows.append(
            {
                "sl_no": line.sl_no,
                "zonal_cd": z,
                "cpt_zonal_cd": cpt["cpt_zonal_cd"],
                "cpt_zonal_des": cpt["cpt_zonal_des"],
                "zonal_label": cpt["zonal_label"],
                "aloc_cd1": _format_alloc_cd(line.aloc_cd1),
                "aloc_cd2": _format_alloc_cd(line.aloc_cd2),
                "aloc_cd3": _format_alloc_cd(line.aloc_cd3),
                "dr_amount": _format_oracle_amount(amt) if is_debit else "",
                "cr_amount": _format_oracle_amount(amt) if not is_debit else "",
                "dr_cr_flag": line.dr_cr_flag,
                "amount": float(amt),
            }
        )

    debit, credit = compute_journal_totals(detail_qs)
    voucher_dt = _format_dd_mm_yy(header.voucher_dt)

    return {
        "org_name": ORG_NAME,
        "report_title": REPORT_TITLE,
        "report_kind": report_kind,
        "period_text": f"For the Month of {_format_month_upper(mth)}, {int(yr)}.",
        "run_date": _format_dd_mm_yyyy(),
        "page_text": "Page: 1 of 1",
        "yr": int(yr),
        "mth": int(mth),
        "fin_yr": fin_yr,
        "header": {
            "bill_no": ref_no,
            "abstract_no": abstract_no,
            "abstract_dt": _format_abstract_dt(abstract_dt),
            "voucher_no": header.voucher_no,
            "voucher_dt": voucher_dt,
            "voucher_no_dt": f"{header.voucher_no}  {voucher_dt}".strip(),
            "tran_type": header.tran_type or "",
            "voucher_type": voucher_type,
            "narration": narration,
            "tot_amt_display": _format_oracle_amount(header.tot_amt or debit),
        },
        "rows": rows,
        "totals": {
            "debit_amt": float(debit),
            "credit_amt": float(credit),
            "debit_display": _format_oracle_amount(debit),
            "credit_display": _format_oracle_amount(credit),
            "balanced": debit == credit,
        },
        "footer": {
            "left_title": "SENIOR ACCOUNTS OFFICER",
            "left_subtitle": "PENSION SECTION",
            "right_title": "FOR F.A & C.A.O.",
        },
    }
