"""
SEPARATE COMMUTATION BILL — PPC commutation bill print for VR / separate commutation (COM).

Runs after SEPCOM generation and PPC bill assignment (FI_PN_TH_SEPCOM.BILL_NO).
"""

import calendar

from django.utils import timezone

from master_data.models import FiPmMhBank, FiPmMhBankAbbr, FiPnMhEarndedn

from ..models import CommutationApplication, PensionProposal, PensionSummary
from ..oracle_mirror import FiPnMhPensioner, FiPnTdSepcom, FiPnThSepcom
from ..pension_calculation import reload_pension_case_from_db
from .commutation_bill_report_service import (
    CommutationBillReportError,
    _clean_report_name,
    _clip,
    _format_money,
    _format_run_date,
)
from .ppc_commutation_bill_service import _sum_sepcom_earn_dedn
from .sepcom_commutation_generation_service import (
    COM_PROC_TAG,
    _get_comm_app,
    refresh_sepcom_commutation_amounts,
)


def _format_amount_plain(value):
    return f"{float(value or 0):.2f}"


def _format_dd_mm_yyyy(value):
    if not value:
        return ""
    if hasattr(value, "strftime"):
        return value.strftime("%d/%m/%Y")
    return str(value)[:10]


def _month_name(month_no):
    try:
        month = int(month_no)
    except (TypeError, ValueError):
        return ""
    if 1 <= month <= 12:
        return calendar.month_name[month]
    return str(month)


def _bank_label_short(bank_cd, comm_app=None):
    if comm_app and str(comm_app.bank_desc or "").strip():
        return str(comm_app.bank_desc).strip().upper()

    bank_cd = _clip(bank_cd, 6)
    branch = FiPmMhBank.objects.filter(bank_cd=bank_cd).first() if bank_cd else None
    abbr = (
        FiPmMhBankAbbr.objects.filter(bank_type=bank_cd[:2]).first()
        if len(bank_cd) >= 2
        else None
    )
    bank_name = (abbr.bank_name if abbr else "").strip().upper()
    branch_desc = (branch.bank_desc if branch else "").strip().upper()
    city = (branch.city if branch else "").strip().upper()
    if bank_name and city:
        return f"{bank_name} {city}"
    if bank_name and branch_desc:
        tail = branch_desc.replace(",", " ").split()[-1]
        return f"{bank_name} {tail}"
    return bank_name or branch_desc or bank_cd


def _line_descriptions():
    return {
        row["earndedn_cd"]: row["earndedn_desc"]
        for row in FiPnMhEarndedn.objects.values("earndedn_cd", "earndedn_desc")
    }


def _resolve_header(emp_cd):
    emp_key = _clip(emp_cd, 5)
    header = (
        FiPnThSepcom.objects.filter(emp_cd=emp_key, com_proc_tag=COM_PROC_TAG)
        .order_by("-sepcom_yr", "-sepcom_month", "-date_created")
        .first()
    )
    if not header:
        raise CommutationBillReportError(
            "SEPCOM record not found. Run separate commutation generation first."
        )
    return header


def _build_page(header):
    refresh_sepcom_commutation_amounts(header)
    header.refresh_from_db()

    comm = _get_comm_app(header.emp_cd)
    impl = (comm.impl_fpen_combill if comm else "").strip().upper()
    if impl and impl != "COM":
        raise CommutationBillReportError(
            "Separate commutation bill applies only when implementation is COM."
        )

    bill_no = str(header.bill_no or (comm.bill_no if comm else "")).strip()
    if not bill_no:
        raise CommutationBillReportError(
            "PPC commutation bill not generated yet. Generate PPC bill first."
        )

    case = reload_pension_case_from_db(header.emp_cd)
    if not case:
        raise CommutationBillReportError("Pension case not found.")

    proposal = PensionProposal.objects.filter(emp_cd=header.emp_cd).first()
    pensioner = FiPnMhPensioner.objects.filter(emp_cd=header.emp_cd).first()
    if not pensioner and proposal and proposal.ca_number:
        pensioner = FiPnMhPensioner.objects.filter(
            ca_number=_clip(proposal.ca_number, 22)
        ).first()

    ca_no = _clip(
        header.ca_no
        or (proposal.ca_number if proposal else "")
        or (comm.ca_no if comm else "")
        or (pensioner.ca_number if pensioner else ""),
        22,
    )

    original_pension = None
    if pensioner and pensioner.original_pension_amt is not None:
        original_pension = float(pensioner.original_pension_amt)
    else:
        try:
            original_pension = float(case.summary.pension_amount)
        except PensionSummary.DoesNotExist:
            original_pension = None

    commutation_percent = None
    if comm and comm.commutation_per is not None:
        commutation_percent = float(comm.commutation_per)
    elif pensioner and pensioner.commutation_per is not None:
        commutation_percent = float(pensioner.commutation_per)
    elif case.commutation_percent is not None:
        commutation_percent = float(case.commutation_percent)

    commuted_portion = None
    if pensioner and pensioner.commuted_portion is not None:
        commuted_portion = float(pensioner.commuted_portion)
    elif original_pension is not None and commutation_percent:
        commuted_portion = round(original_pension * commutation_percent / 100.0, 2)

    desc_map = _line_descriptions()
    line_items = []
    total_original = 0.0
    total_amount = 0.0
    for td in FiPnTdSepcom.objects.filter(sepcom_id=header.sepcom_id).order_by(
        "earn_dedn_type", "earn_dedn_cd"
    ):
        original = float(td.original_amt if td.original_amt is not None else td.amount or 0)
        amount = float(td.amount or 0)
        total_original += original
        total_amount += amount
        description = (desc_map.get(td.earn_dedn_cd) or td.earn_dedn_cd or "").upper()
        if description == "COMMUTATION" or td.earn_dedn_cd == "203":
            description = "COMMUTATION"
        line_items.append(
            {
                "earn_dedn_type": td.earn_dedn_type,
                "earn_dedn_cd": td.earn_dedn_cd,
                "description": description,
                "original_amt": original,
                "amount": amount,
                "original_amt_display": _format_amount_plain(original),
                "amount_display": _format_amount_plain(amount),
            }
        )

    if not line_items:
        lump = float(header.original_com_amt or 0)
        earn, _ = _sum_sepcom_earn_dedn(header)
        amount = lump or float(earn)
        line_items.append(
            {
                "earn_dedn_type": "E",
                "earn_dedn_cd": "203",
                "description": "COMMUTATION",
                "original_amt": amount,
                "amount": amount,
                "original_amt_display": _format_amount_plain(amount),
                "amount_display": _format_amount_plain(amount),
            }
        )
        total_original = amount
        total_amount = amount

    emp_name = _clean_report_name(case.name)
    bank_cd = header.bank_cd or (comm.bank_cd if comm else "") or (
        proposal.bank_cd if proposal else ""
    )

    return {
        "emp_cd": header.emp_cd,
        "emp_name": emp_name,
        "employee_label": f"{header.emp_cd} {emp_name}".strip(),
        "sepcom_id": header.sepcom_id,
        "bill_no": bill_no,
        "ca_no": ca_no,
        "commutation_year": str(header.sepcom_yr or ""),
        "commutation_month": _month_name(header.sepcom_month),
        "original_pension_amt": original_pension,
        "original_pension_amt_display": (
            _format_amount_plain(original_pension)
            if original_pension is not None
            else ""
        ),
        "appcn_no": header.appcn_no or (str(comm.appcn_no) if comm else ""),
        "appcn_dt": _format_dd_mm_yyyy(header.appcn_dt or (comm.appcn_dt if comm else None)),
        "bank": _bank_label_short(bank_cd, comm),
        "commutation_percent": commutation_percent,
        "commutation_percent_display": (
            f"{int(commutation_percent)}%"
            if commutation_percent is not None and commutation_percent == int(commutation_percent)
            else (
                f"{commutation_percent:.2f}%".rstrip("0").rstrip(".")
                if commutation_percent is not None
                else ""
            )
        ),
        "commuted_portion": commuted_portion,
        "commuted_portion_display": (
            _format_money(commuted_portion) if commuted_portion is not None else ""
        ),
        "line_items": line_items,
        "total_original_amt": total_original,
        "total_amount": total_amount,
        "total_original_amt_display": _format_amount_plain(total_original),
        "total_amount_display": _format_amount_plain(total_amount),
        "report_kind": "separate_commutation_bill",
    }


def build_separate_commutation_bill_report(*, emp_codes=None, sepcom_ids=None):
    headers = []
    if sepcom_ids:
        headers = list(
            FiPnThSepcom.objects.filter(sepcom_id__in=[str(x) for x in sepcom_ids])
        )
    elif emp_codes:
        for emp in emp_codes:
            headers.append(_resolve_header(emp))
    else:
        raise CommutationBillReportError("emp_code or sepcom_id is required.")

    if not headers:
        raise CommutationBillReportError("SEPCOM record not found.")

    pages = [_build_page(h) for h in headers]
    total_pages = len(pages) or 1
    for index, page in enumerate(pages, start=1):
        page["page_no"] = index
        page["total_pages"] = total_pages

    return {
        "org_name": "SYAMA PRASAD MOOKERJEE PORT, KOLKATA",
        "report_title": "SEPARATE COMMUTATION BILL",
        "module_name": "FINANCE",
        "run_date": _format_run_date(),
        "pages": pages,
        "row_count": len(pages),
    }
