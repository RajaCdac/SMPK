"""
SEP_COMM_REP1.fmb — separate commutation report (step 4).

Runs after SEPCOM generation and PPC bill assignment; uses FI_PN_TH_SEPCOM
joined to commutation application / pension case.
"""

from django.utils import timezone

from master_data.models import FiPnMhEarndedn

from ..models import CommutationApplication, PensionProposal
from ..oracle_mirror import FiPnTdSepcom, FiPnThSepcom
from ..pension_calculation import reload_pension_case_from_db
from ..utils.amount_words import rupees_amount_in_words
from .commutation_bill_report_service import (
    CommutationBillReportError,
    _build_row,
    _clean_report_name,
    _format_case_no,
    _format_money_indian,
    _format_run_date,
)
from .ppc_commutation_bill_service import _sum_sepcom_earn_dedn
from .sepcom_commutation_generation_service import COM_PROC_TAG, _get_comm_app


def _line_descriptions():
    return {
        row["earndedn_cd"]: row["earndedn_desc"]
        for row in FiPnMhEarndedn.objects.values("earndedn_cd", "earndedn_desc")
    }


def _build_sepcom_page(header):
    comm = _get_comm_app(header.emp_cd)
    case = reload_pension_case_from_db(header.emp_cd)
    if not case:
        raise CommutationBillReportError("Pension case not found.")

    proposal = PensionProposal.objects.filter(emp_cd=header.emp_cd).first()
    earn, dedn = _sum_sepcom_earn_dedn(header)
    lump = float(header.original_com_amt or earn)
    desc_map = _line_descriptions()
    lines = []
    for td in FiPnTdSepcom.objects.filter(sepcom_id=header.sepcom_id).order_by(
        "earn_dedn_type", "earn_dedn_cd"
    ):
        lines.append(
            {
                "earn_dedn_type": td.earn_dedn_type,
                "earn_dedn_cd": td.earn_dedn_cd,
                "description": (desc_map.get(td.earn_dedn_cd) or td.earn_dedn_cd).upper(),
                "amount": float(td.amount or 0),
                "amount_display": _format_money_indian(td.amount),
            }
        )

    sanction = (
        (comm.sanction_parameter if comm else "")
        or "SEPARATE COMMUTATION"
    ).strip()

    return {
        "emp_cd": header.emp_cd,
        "sepcom_id": header.sepcom_id,
        "bill_no": header.bill_no or (comm.bill_no if comm else ""),
        "appcn_no": header.appcn_no or (str(comm.appcn_no) if comm else ""),
        "ref_no": comm.ref_no if comm else "",
        "fa_cao_report": _format_case_no(header.ca_no or (proposal.ca_number if proposal else "")),
        "pensioner_name": _clean_report_name(case.name),
        "designation": (case.designation or "").strip().upper(),
        "sepcom_month": header.sepcom_month,
        "sepcom_year": header.sepcom_yr,
        "gross_earn": float(earn),
        "gross_dedn": float(dedn),
        "gross_earn_display": _format_money_indian(earn),
        "gross_dedn_display": _format_money_indian(dedn),
        "net_amount_display": _format_money_indian(earn - dedn),
        "line_items": lines,
        "sanction_particulars": sanction.upper(),
        "commutation_amount_words": rupees_amount_in_words(lump),
        "report_kind": "sep_comm",
    }


def build_sep_comm_report(*, emp_codes=None, sepcom_ids=None):
    """SEP_COMM_REP payload for one or more SEPCOM rows."""
    headers = []
    if sepcom_ids:
        headers = list(
            FiPnThSepcom.objects.filter(sepcom_id__in=[str(x) for x in sepcom_ids])
        )
    elif emp_codes:
        for emp in emp_codes:
            h = (
                FiPnThSepcom.objects.filter(
                    emp_cd=str(emp).strip()[:5],
                    com_proc_tag=COM_PROC_TAG,
                )
                .order_by("-sepcom_yr", "-sepcom_month")
                .first()
            )
            if h:
                headers.append(h)

    if not headers:
        raise CommutationBillReportError(
            "SEPCOM record not found. Run commutation generation first."
        )

    pages = [_build_sepcom_page(h) for h in headers]

    # Enrich with sanction narrative from existing commutation report builder.
    for page in pages:
        try:
            legacy = _build_row(page["emp_cd"])
            page["sanction_narrative"] = legacy.get("sanction_narrative", "")
            page["amount_sought_commuted"] = legacy.get("amount_sought_commuted", "")
            page["commutation_reasons"] = legacy.get("commutation_reasons", "")
            page["medical_certificate"] = legacy.get("medical_certificate", "")
            page["previous_commutations"] = legacy.get("previous_commutations", "")
        except CommutationBillReportError:
            pass

    total_pages = len(pages) or 1
    for index, page in enumerate(pages, start=1):
        page["page_no"] = index
        page["total_pages"] = total_pages

    return {
        "org_name": "SYAMA PRASAD MOOKERJEE PORT, KOLKATA",
        "report_title": "SEPARATE COMMUTATION REPORT",
        "run_date": _format_run_date(),
        "pages": pages,
        "row_count": len(pages),
    }
