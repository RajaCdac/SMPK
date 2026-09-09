"""
Recommendation & Sanction of Commutation report (FI_PN_MH_APPLICATION preview).
"""

from datetime import date

from django.utils import timezone

from employee.oracle_mirror import FiXxMhEmpPer
from employee.services.emp_data_service import resolve_employee_designation_name

from ..models import CommutationApplication, PensionProposal, PensionSummary
from ..oracle_mirror import FiPnMhApplication, FiPnMhPensioner
from ..pension_calculation import (
    get_commutation_application_for_employee,
    reload_pension_case_from_db,
)
from ..services.commutation_rate_service import (
    CommutationRateError,
    age_next_birthday,
    compute_commutation_for_employee,
    resolve_age_reference_date,
)
from ..services.proposal_sanction_report_service import _clean_report_name, _format_case_no
from ..utils.amount_words import rupees_amount_in_words


class CommutationBillReportError(Exception):
    pass


def _clip(value, max_len, default=""):
    if value is None:
        return default
    text = str(value).strip()
    if not text:
        return default
    return text[:max_len]


def _format_run_date(value=None):
    dt = value or timezone.localdate()
    if hasattr(dt, "strftime"):
        return dt.strftime("%d/%m/%Y")
    return str(dt)


def _format_money(value):
    n = float(value or 0)
    return f"{n:,.2f}"


def _format_money_indian(value):
    n = int(round(float(value or 0)))
    text = str(n)
    if len(text) <= 3:
        return f"{text}.00"
    last3 = text[-3:]
    rest = text[:-3]
    groups = []
    while rest:
        groups.append(rest[-2:])
        rest = rest[:-2]
    groups.reverse()
    return f"{','.join(groups + [last3])}.00"


def _employee_pronoun(emp_cd):
    per = FiXxMhEmpPer.objects.filter(emp_cd=_clip(emp_cd, 5)).first()
    if per:
        title = (per.title or "").strip().upper().rstrip(".")
        if title in ("MRS", "MS", "MISS", "SMT", "KUMARI"):
            return "her", "She"
    return "his", "He"


def _next_birthday_age(birth_date, ref_date):
    age = age_next_birthday(birth_date, ref_date)
    if age is None:
        return None, None
    ref = ref_date.date() if hasattr(ref_date, "date") else ref_date
    birth = birth_date.date() if hasattr(birth_date, "date") else birth_date
    try:
        next_bday = date(ref.year, birth.month, birth.day)
    except ValueError:
        next_bday = date(ref.year, birth.month, 28)
    if next_bday <= ref:
        try:
            next_bday = date(ref.year + 1, birth.month, birth.day)
        except ValueError:
            next_bday = date(ref.year + 1, birth.month, 28)
    return next_bday, age


def _display_nil(value, *, prefix=""):
    text = _clip(value, 500)
    if not text or text.upper() in ("NIL", "N/A", "NA", "NONE"):
        return f"{prefix}'NIL'" if prefix else "'NIL'"
    if prefix:
        return f"{prefix}{text}"
    return text


def _build_row(emp_cd):
    case = reload_pension_case_from_db(emp_cd)
    if not case:
        raise CommutationBillReportError(
            "Pension case not found. Complete no-pay entry first."
        )

    try:
        summary = case.summary
    except PensionSummary.DoesNotExist:
        raise CommutationBillReportError(
            "Pension amounts not calculated. Run amount calculation first."
        )

    comm_app = get_commutation_application_for_employee(emp_cd)
    if not comm_app:
        raise CommutationBillReportError(
            "Commutation application not found. Save commutation entry first."
        )

    oracle_app = (
        FiPnMhApplication.objects.filter(emp_cd=_clip(emp_cd, 5))
        .order_by("-appcn_dt")
        .first()
    )

    proposal = PensionProposal.objects.filter(emp_cd=str(emp_cd).strip()).first()
    if not proposal and str(emp_cd).strip().isdigit():
        proposal = PensionProposal.objects.filter(emp_cd=str(int(emp_cd))).first()

    pensioner = FiPnMhPensioner.objects.filter(emp_cd=_clip(emp_cd, 5)).first()

    ca_number = ""
    if proposal and proposal.ca_number:
        ca_number = proposal.ca_number
    elif comm_app.ca_no:
        ca_number = comm_app.ca_no
    elif oracle_app and oracle_app.ca_no:
        ca_number = oracle_app.ca_no

    pension_amount = float(summary.pension_amount or 0)
    commutation_percent = float(
        comm_app.commutation_per
        if comm_app.commutation_per is not None
        else case.commutation_percent or 0
    )
    if oracle_app and oracle_app.commutation_per is not None:
        commutation_percent = float(oracle_app.commutation_per)

    monthly_commuted = pension_amount * commutation_percent / 100.0
    if oracle_app and oracle_app.commutation_amt is not None:
        monthly_commuted = float(oracle_app.commutation_amt)

    lump_sum = float(summary.commutation_amount or 0)
    age_years = None
    rate_per_rupee = None
    if lump_sum <= 0 and commutation_percent > 0 and pension_amount > 0:
        try:
            comm_amounts = compute_commutation_for_employee(
                emp_cd,
                pension_amount=pension_amount,
                commutation_percent=commutation_percent,
                comm_app=comm_app,
                case=case,
                use_highest_side_round=False,
            )
            lump_sum = float(comm_amounts["lump_sum"])
            monthly_commuted = float(comm_amounts["monthly_commuted"])
            age_years = comm_amounts.get("age_yrs")
            rate_per_rupee = comm_amounts.get("rate_per_rupee")
        except CommutationRateError:
            lump_sum = 0.0

    impl_mode = (
        (comm_app.impl_fpen_combill or "").strip().upper()
        if comm_app.impl_fpen_combill
        else ""
    )
    if not impl_mode and oracle_app and oracle_app.impl_fpen_combill:
        impl_mode = oracle_app.impl_fpen_combill.strip().upper()

    default_sanction = (
        "SEPARATE COMMUTATION"
        if impl_mode == "COM"
        else "COMMUTATION ALONG WITH PENSION"
    )
    sanction_particulars = (
        (comm_app.sanction_parameter or "").strip()
        or (oracle_app.sanction_particulars if oracle_app else "")
        or default_sanction
    )
    commutation_reasons = (
        (comm_app.commutation_reasons or "").strip()
        or (oracle_app.commutation_reasons if oracle_app else "")
        or ""
    )

    mo_ref = (comm_app.mo_certificate_ref or "").strip()
    if oracle_app and oracle_app.mo_certificate_ref:
        mo_ref = oracle_app.mo_certificate_ref.strip()
    avg_life = (oracle_app.avg_expected_life if oracle_app else "") or ""
    if mo_ref:
        medical_certificate = _display_nil(mo_ref, prefix="No.- ")
    elif avg_life:
        medical_certificate = avg_life
    else:
        medical_certificate = "No.- 'NIL'"

    prev_comm = ""
    if oracle_app and oracle_app.prev_comm_particulars:
        prev_comm = oracle_app.prev_comm_particulars.strip()
    previous_commutations = _display_nil(prev_comm)

    separation_dt = None
    if proposal and proposal.separation_date:
        separation_dt = proposal.separation_date
    elif case.separation_date:
        separation_dt = case.separation_date
    else:
        separation_dt = case.retirement_date

    application_rcvd_dt = comm_app.application_rcvd_dt or comm_app.appcn_dt
    mo_certification_dt = comm_app.mo_certificate_dt
    if oracle_app:
        if not application_rcvd_dt:
            application_rcvd_dt = oracle_app.application_rcvd_dt or oracle_app.appcn_dt
        if not mo_certification_dt:
            mo_certification_dt = oracle_app.mo_certification_dt

    age_ref_date = resolve_age_reference_date(
        application_rcvd_dt=application_rcvd_dt,
        mo_certification_dt=mo_certification_dt,
        separation_dt=separation_dt,
    ) or (
        comm_app.commutation_dt
        or comm_app.appcn_dt
        or separation_dt
    )
    pronoun_lower, _pronoun_cap = _employee_pronoun(emp_cd)
    next_bday, age_from_ref = _next_birthday_age(case.birth_date, age_ref_date)
    if age_years is None:
        age_years = age_from_ref
    next_bday_text = (
        f"{next_bday.day}/{next_bday.month}/{next_bday.year}" if next_bday else ""
    )

    monthly_display = _format_money_indian(monthly_commuted)
    lump_display = _format_money_indian(lump_sum)

    sanction_narrative = (
        "Submitted to the Dy. Chairman for sanction. "
        f"The commuted value of Rs. {monthly_display} on the basis of the value "
        f"in the prescribed table at {age_years or ''} years {pronoun_lower} age on "
        f"next birth day on {next_bday_text} amount to Rs. {lump_display}"
    )

    return {
        "emp_cd": _clip(emp_cd, 5),
        "fa_cao_report": _format_case_no(ca_number),
        "pensioner_name": _clean_report_name(case.name),
        "designation": resolve_employee_designation_name(
            emp_cd, case=case, pensioner=pensioner
        ),
        "pension_amount": _format_money(pension_amount),
        "sanction_particulars": sanction_particulars.upper(),
        "amount_sought_commuted": _format_money(monthly_commuted),
        "commutation_reasons": commutation_reasons.upper(),
        "medical_certificate": medical_certificate,
        "previous_commutations": previous_commutations,
        "sanction_narrative": sanction_narrative,
        "commutation_amount_words": rupees_amount_in_words(lump_sum),
        "commutation_percent": commutation_percent,
    }


def build_commutation_bill_report(*, emp_codes=None):
    """Build commutation recommendation / sanction letter for employee(s)."""
    codes = [_clip(c, 5) for c in (emp_codes or []) if _clip(c, 5)]
    if not codes:
        raise CommutationBillReportError("emp_code is required.")

    pages = [_build_row(emp_cd) for emp_cd in codes]
    total_pages = len(pages) or 1
    for index, page in enumerate(pages, start=1):
        page["page_no"] = index
        page["total_pages"] = total_pages

    return {
        "org_name": "SYAMA PRASAD MOOKERJEE PORT, KOLKATA",
        "report_title": "RECOMMENDATION AND SANCTION OF COMMUTATION",
        "run_date": _format_run_date(),
        "pages": pages,
        "row_count": len(pages),
    }
