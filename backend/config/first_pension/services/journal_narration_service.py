"""Default journal voucher narration (Oracle JV header text)."""

from ..models import PensionCase, PensionProposal
from ..oracle_mirror import (
    FiPnMhPensionProposal,
    FiPnMhPensioner,
    FiPnThFirstMonthPension,
)


def _clip_emp(emp_cd):
    return str(emp_cd or "").strip()[:5]


def _clip_bill(bill_no):
    return str(bill_no or "").strip()[:22]


def _format_separation_date(value):
    if not value:
        return ""
    if hasattr(value, "strftime"):
        return value.strftime("%d/%m/%Y")
    return str(value).strip()[:10]


def resolve_journal_narration_context(*, emp_cd=None, bill_no=None):
    """
    Resolve employee name, CA number, separation date, and emp code for JV narration.
    """
    emp_key = _clip_emp(emp_cd)
    ca_no = ""
    emp_name = ""

    if bill_no:
        headers = FiPnThFirstMonthPension.objects.filter(bill_no=_clip_bill(bill_no))
        header = (
            headers.filter(emp_cd=emp_key).first()
            if emp_key
            else headers.first()
        )
        if header:
            if not emp_key:
                emp_key = _clip_emp(header.emp_cd)
            ca_no = str(header.ca_no or "").strip()

    if not emp_key:
        return {
            "emp_cd": "",
            "emp_name": "",
            "ca_number": "",
            "separation_date": None,
        }

    case = PensionCase.objects.filter(emp_code=emp_key).first()
    if case and case.name:
        emp_name = str(case.name).strip()

    proposal = PensionProposal.objects.filter(emp_cd=emp_key).first()
    if proposal:
        if not emp_name and proposal.emp_name:
            emp_name = str(proposal.emp_name).strip()
        if not ca_no and proposal.ca_number:
            ca_no = str(proposal.ca_number).strip()

    pensioner = FiPnMhPensioner.objects.filter(emp_cd=emp_key).first()
    if pensioner:
        if not emp_name and pensioner.name:
            emp_name = str(pensioner.name).strip()
        if not ca_no and pensioner.ca_number:
            ca_no = str(pensioner.ca_number).strip()

    if not ca_no:
        mirror = FiPnMhPensionProposal.objects.filter(emp_cd=emp_key).first()
        if mirror and mirror.ca_number:
            ca_no = str(mirror.ca_number).strip()

    from ..pension_calculation import resolve_separation_date

    separation_date = resolve_separation_date(emp_key, case)

    return {
        "emp_cd": emp_key,
        "emp_name": emp_name or emp_key,
        "ca_number": ca_no,
        "separation_date": separation_date,
    }


def build_default_journal_narration(*, emp_cd=None, bill_no=None):
    """
    Oracle-style narration for first-pension journal vouchers:

    Amount passed in favour of {name}, case no {ca}, Retd. W.e.f {date}, emp code {emp}
    """
    ctx = resolve_journal_narration_context(emp_cd=emp_cd, bill_no=bill_no)
    emp_key = ctx.get("emp_cd") or ""
    if not emp_key:
        return ""

    name = ctx.get("emp_name") or emp_key
    ca_no = ctx.get("ca_number") or ""
    sep = _format_separation_date(ctx.get("separation_date"))

    segments = [f"Amount passed in favour of {name}", f"case no {ca_no}"]
    if sep:
        segments.append(f"Retd. W.e.f {sep}")
    segments.append(f"emp code {emp_key}")
    return ", ".join(segments)
