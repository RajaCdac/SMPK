"""
First Pension Advice letter (FI_PN_ADVICE).
"""

from django.utils import timezone

from employee.services.dept_wise_service import resolve_dept_wise_department
from employee.services.emp_data_service import (
    fetch_emp_data_posting,
    resolve_department_from_posting,
)

from ..oracle_mirror import (
    FiPnMhPensionProposal,
    FiPnMhPensioner,
    FiPnThFirstMonthPension,
)
from .proposal_sanction_report_service import (
    _clip,
    _employee_name,
    _format_roll_no,
)


class FirstPensionAdviceReportError(Exception):
    pass


ADVICE_REF_NO = "Fin/Adv/06/"
HANDOVER_TIME = "11-00 A.M."
CASH_WRITER_CONTACT = "Mr. Dilip Pal"
SIGNATORY_LEFT_CODE = "CVF"
SIGNATORY_TITLE = ("Financial Adviser &", "Chief Accounts Officer")


def _format_report_date(value=None):
    dt = value or timezone.localdate()
    if hasattr(dt, "date"):
        dt = dt.date()
    if hasattr(dt, "strftime"):
        return dt.strftime("%d/%m/%Y")
    return str(dt)[:10]


def _format_case_no(ca_number):
    return _clip(ca_number, 22)


def _resolve_through_office(emp_cd):
    dept = resolve_dept_wise_department(emp_cd)
    if dept:
        return dept
    posting = fetch_emp_data_posting(emp_cd)
    if posting:
        alloc = (posting.get("alloc_desc") or "").upper()
        if "MECHANICAL" in alloc:
            return "CHIEF MECHANICAL ENGG."
        if "ELECTRICAL" in alloc:
            return "CHIEF ELECTRICAL ENGG."
        if "CIVIL" in alloc:
            return "CHIEF ENGINEER (CIVIL)"
    dept = resolve_department_from_posting(emp_cd, fallback="")
    return dept.upper() if dept else ""


def _resolve_report_date(proposal, fmpen):
    if proposal and proposal.date_created:
        return _format_report_date(proposal.date_created)
    if fmpen and fmpen.date_of_execution:
        return _format_report_date(fmpen.date_of_execution)
    if fmpen and fmpen.date_created:
        return _format_report_date(fmpen.date_created)
    return _format_report_date()


def _resolve_handover_date(proposal):
    if proposal and proposal.separation_dt:
        return _format_report_date(proposal.separation_dt)
    return ""


def _build_body_paragraphs():
    cash_writer_date = "____________"
    cash_writer_time = "____________"
    cheque_date = "____________"

    return [
        (
            "This is to inform you that your pension card would be handed over to you "
            "by the Pension Section, Finance Department, at Head office, on "
            "___________________ at ____________________ i.e. on your superannuation/"
            "last working days."
        ),
        (
            "Two sets of report of first pension, gratuity and commutation, if any, "
            "are enclosed of which one copy would be retained by the Department "
            "concerned and the other would be handed over to you by the Department."
        ),
        (
            "You will also be required to collect the leave status for the last "
            "working month duly certified by the Department and would submit the same "
            "to the undersigned while collecting your pension card."
        ),
        (
            "You will be required to report to the Pension Section for appending your "
            "signature on the LICI formats as also collecting ECS Forms for "
            "remmitence of pension from the Section, in case you wish to opt. for the "
            "same and the same has not been forwarded along with your S of D papers."
        ),
        (
            "You are advised to report to the cash writer sec. under finance "
            f"deptartment at KOPT. Head office on {cash_writer_date} at "
            f"{cash_writer_time} and to meet {CASH_WRITER_CONTACT} there for "
            f"clearing necessary formalities required to recieve the cheque on "
            f"{cheque_date}."
        ),
    ]


def _build_copy_to_text():
    copy_report_date = "____________"
    copy_report_time = "____________"
    return (
        "for information with a request to hand over the original advice to collect "
        "the Pension Card to the employee concerned. He/she may be advised to "
        "bring alongwith him/her a joint photograph with his/her spouse, if any, "
        "in 4 copies, duly attested by a Competent Authority, in case the same "
        "has not been forwarded with the case file at Pension Section. The "
        "incumbent may be advised to report to the Pension Section, Finance "
        f"Department on {copy_report_date} at {copy_report_time} alongwith the "
        "statement of leave duly certified by the department for the last working "
        "month to enable him to get the payment of leave encashment on the said day "
        "itself. The payment of gratuity and commutation, if any, would also be "
        "attempted to be made on the said day itself to the employee concerned "
        "alongwith the handing over of the Pension Card."
    )


def _build_row(emp_cd):
    emp_key = _clip(emp_cd, 5)
    proposal = FiPnMhPensionProposal.objects.filter(emp_cd=emp_key).first()
    pensioner = FiPnMhPensioner.objects.filter(emp_cd=emp_key).first()
    fmpen = (
        FiPnThFirstMonthPension.objects.filter(emp_cd=emp_key)
        .order_by("-pension_yr", "-pension_month")
        .first()
    )

    if not proposal and not pensioner:
        raise FirstPensionAdviceReportError(
            "Employee pension record not found in pension proposal / pensioner tables."
        )

    ca_number = ""
    if proposal and proposal.ca_number:
        ca_number = proposal.ca_number
    elif pensioner and pensioner.ca_number:
        ca_number = pensioner.ca_number

    handover_date = _resolve_handover_date(proposal)
    through_office = _resolve_through_office(emp_key)
    body_paragraphs = _build_body_paragraphs()
    copy_to_text = _build_copy_to_text()

    return {
        "emp_cd": emp_key,
        "org_name": "SYAMA PRASAD MOOKERJEE PORT, KOLKATA",
        "advice_ref_no": ADVICE_REF_NO,
        "department_label": "Finance Department",
        "report_date": _resolve_report_date(proposal, fmpen),
        "recipient_name": _employee_name(emp_key, None, None, pensioner),
        "subject": "Issuance of Pension Card",
        "pension_case_no": _format_case_no(ca_number),
        "pension_roll_no": _format_roll_no(proposal, pensioner),
        "through_office": through_office,
        "copy_to_office": through_office,
        "copy_to_text": copy_to_text,
        "handover_date": handover_date,
        "handover_time": HANDOVER_TIME,
        "cash_writer_contact": CASH_WRITER_CONTACT,
        "signatory_left_code": SIGNATORY_LEFT_CODE,
        "signatory_title": list(SIGNATORY_TITLE),
        # Body only (no Copy-to). Kept as `paragraphs` for older UI clients.
        "paragraphs": body_paragraphs,
        "body_paragraphs": body_paragraphs,
        "page1_paragraph_count": len(body_paragraphs),
    }


def build_first_pension_advice_report(*, emp_codes=None):
    """Build FI_PN_ADVICE style letter payload."""
    codes = [_clip(c, 5) for c in (emp_codes or []) if _clip(c, 5)]
    if not codes:
        raise FirstPensionAdviceReportError("emp_code is required.")

    pages = []
    for emp_cd in codes:
        pages.append(_build_row(emp_cd))

    total_pages = len(pages) or 1
    for index, page in enumerate(pages, start=1):
        page["page_no"] = index
        page["total_pages"] = len(pages)

    return {
        "org_name": "SYAMA PRASAD MOOKERJEE PORT, KOLKATA",
        "report_title": "First Pension Advice",
        "pages": pages,
        "row_count": len(pages),
        "print_page_count": total_pages,
    }
