"""
Commutation age-rate lookup from FI_PN_MD_COMMRATE_RUPEE (MySQL mirror).

Ports Oracle FFUNC_AGE_NEXT_BIRTHDAY / Please_Find_BirthDay and rate selection
from FI_PN_FIRST_PENSION_PROCESS.fmb and FI_PN_COMUTATION_GENERATION.fmb.
"""

from datetime import date, datetime

from dateutil.relativedelta import relativedelta

from ..models import CommutationApplication, PensionProposal
from ..oracle_mirror import FiPnMdCommrateRupee, FiPnMhApplication, FiPnMhOldbillParam
from ..pension_calculation import (
    get_commutation_application_for_employee,
    highest_side_round,
    reload_pension_case_from_db,
    round_up_to_rupee,
)


class CommutationRateError(Exception):
    pass


def _as_date(value):
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    return None


def age_next_birthday(birth_date, ref_date):
    """
    Port of Oracle FFUNC_AGE_NEXT_BIRTHDAY / Please_Find_BirthDay.

    Same month as DOB: day on or after birthday → next-birthday age (year+1 − DOB year).
    Example: DOB 01-08-1966, ref 01-08-2026 → age 61 (not 60).
    """
    dob = _as_date(birth_date)
    ref = _as_date(ref_date)
    if not dob or not ref:
        return None

    day_curr = ref.day
    month_curr = ref.month
    year_curr = ref.year
    day_dob = dob.day
    month_dob = dob.month
    year_dob = dob.year

    if month_curr < month_dob:
        return year_curr - year_dob
    if month_curr == month_dob:
        if day_curr >= day_dob:
            return (year_curr + 1) - year_dob
        return year_curr - year_dob
    return (year_curr + 1) - year_dob


def _months_between_trunc(later, earlier):
    """Oracle Trunc(Months_Between(later, earlier), 0) for calendar dates."""
    later = _as_date(later)
    earlier = _as_date(earlier)
    if not later or not earlier:
        return 0
    diff = relativedelta(later, earlier)
    return diff.years * 12 + diff.months


def resolve_age_reference_date(
    *,
    application_rcvd_dt=None,
    mo_certification_dt=None,
    separation_dt=None,
):
    """
    If application received more than 12 months after separation, use MO
    certification date; otherwise use application received date.
    """
    rcvd = _as_date(application_rcvd_dt)
    sep = _as_date(separation_dt)
    mo = _as_date(mo_certification_dt)

    if rcvd and sep:
        gap_months = _months_between_trunc(rcvd, sep)
        if gap_months > 12 and mo:
            return mo
    if rcvd:
        return rcvd
    if mo:
        return mo
    return sep


def get_rate_per_rupee(age_yrs, ref_date=None):
    """Latest AMT_PER_RUPEE for age on or before ref_date (WEF_DT)."""
    if age_yrs is None:
        raise CommutationRateError("Age is required to look up commutation rate.")

    qs = FiPnMdCommrateRupee.objects.filter(age_yrs=int(age_yrs))
    ref = _as_date(ref_date)
    if ref:
        qs = qs.filter(wef_dt__lte=ref)
    row = qs.order_by("-wef_dt").first()
    if not row or row.amt_per_rupee is None:
        raise CommutationRateError(
            f"Commutation rate per rupee has not been declared for age {int(age_yrs)}."
        )
    return float(row.amt_per_rupee)


def _resolve_birth_date(case, emp_cd):
    if case and case.birth_date:
        return case.birth_date

    emp_key = str(emp_cd).strip()[:5]
    oldbill = FiPnMhOldbillParam.objects.filter(emp_cd=emp_key).first()
    if oldbill and oldbill.birth_dt:
        return oldbill.birth_dt

    try:
        from employee.oracle_mirror import FiXxMhEmpPer

        per = FiXxMhEmpPer.objects.filter(emp_cd=emp_key).first()
        if per and per.birth_dt:
            return per.birth_dt
    except Exception:
        pass

    return None


def resolve_commutation_context(emp_cd, *, comm_app=None, case=None, oracle_app=None):
    """Collect DOB and reference dates for commutation rate lookup."""
    emp_key = str(emp_cd).strip()
    case = case or reload_pension_case_from_db(emp_key)
    comm_app = comm_app or get_commutation_application_for_employee(emp_key)
    if not oracle_app:
        oracle_app = (
            FiPnMhApplication.objects.filter(emp_cd=emp_key[:5])
            .order_by("-appcn_dt")
            .first()
        )

    proposal = PensionProposal.objects.filter(emp_cd=emp_key).first()
    if not proposal and emp_key.isdigit():
        proposal = PensionProposal.objects.filter(emp_cd=str(int(emp_key))).first()

    birth_date = _resolve_birth_date(case, emp_key)
    separation_dt = None
    if proposal and proposal.separation_date:
        separation_dt = proposal.separation_date
    elif case and case.separation_date:
        separation_dt = case.separation_date
    elif case and case.retirement_date:
        separation_dt = case.retirement_date

    application_rcvd_dt = None
    mo_certification_dt = None
    # Oracle mirror (FI_PN_MH_APPLICATION) is authoritative after sync.
    if oracle_app:
        application_rcvd_dt = (
            oracle_app.application_rcvd_dt or oracle_app.appcn_dt
        )
        mo_certification_dt = oracle_app.mo_certification_dt
    if comm_app:
        if not application_rcvd_dt:
            application_rcvd_dt = (
                comm_app.application_rcvd_dt or comm_app.appcn_dt
            )
        if not mo_certification_dt:
            mo_certification_dt = comm_app.mo_certificate_dt

    age_ref_date = resolve_age_reference_date(
        application_rcvd_dt=application_rcvd_dt,
        mo_certification_dt=mo_certification_dt,
        separation_dt=separation_dt,
    )
    if not age_ref_date and separation_dt:
        age_ref_date = separation_dt

    age_yrs = age_next_birthday(birth_date, age_ref_date) if birth_date and age_ref_date else None

    return {
        "birth_date": birth_date,
        "application_rcvd_dt": application_rcvd_dt,
        "mo_certification_dt": mo_certification_dt,
        "separation_dt": separation_dt,
        "age_reference_date": age_ref_date,
        "age_yrs": age_yrs,
    }


def compute_commutation_amounts(
    *,
    pension_amount,
    commutation_percent,
    birth_date,
    application_rcvd_dt=None,
    mo_certification_dt=None,
    separation_dt=None,
    share_percent=100,
    comm_amount_override=None,
    use_highest_side_round=False,
):
    """
    Oracle commutation lump-sum:
      monthly portion = Trunc(pension * comm% / 100)  [or override]
      lump sum = portion * rate * share% / 100, rounded per context.
    """
    pension = float(pension_amount or 0)
    pct = float(commutation_percent or 0)
    if pension <= 0 or pct <= 0:
        return {
            "pension_amount": pension,
            "commutation_percent": pct,
            "monthly_commuted": 0.0,
            "lump_sum": 0.0,
            "age_yrs": None,
            "rate_per_rupee": None,
            "age_reference_date": None,
        }

    if comm_amount_override and float(comm_amount_override) > 0:
        monthly_commuted = int(float(comm_amount_override))
    else:
        monthly_commuted = int(pension * pct / 100.0)

    age_ref_date = resolve_age_reference_date(
        application_rcvd_dt=application_rcvd_dt,
        mo_certification_dt=mo_certification_dt,
        separation_dt=separation_dt,
    )
    if not age_ref_date:
        age_ref_date = separation_dt

    age_yrs = age_next_birthday(birth_date, age_ref_date)
    if age_yrs is None:
        raise CommutationRateError(
            "Date of birth and commutation reference date are required for rate lookup."
        )

    rate = get_rate_per_rupee(age_yrs, age_ref_date)
    base = monthly_commuted * rate * float(share_percent or 100) / 100.0
    if use_highest_side_round:
        lump_sum = float(highest_side_round(base))
    else:
        lump_sum = float(round_up_to_rupee(base))

    return {
        "pension_amount": pension,
        "commutation_percent": pct,
        "monthly_commuted": float(monthly_commuted),
        "lump_sum": lump_sum,
        "age_yrs": age_yrs,
        "rate_per_rupee": rate,
        "age_reference_date": age_ref_date,
    }


def compute_commutation_for_employee(
    emp_cd,
    *,
    pension_amount,
    commutation_percent,
    comm_app=None,
    case=None,
    share_percent=100,
    comm_amount_override=None,
    use_highest_side_round=False,
):
    ctx = resolve_commutation_context(emp_cd, comm_app=comm_app, case=case)
    if not ctx["birth_date"]:
        raise CommutationRateError(
            f"Date of birth not found for employee {emp_cd}. "
            "Complete pension case / employee master first."
        )
    return compute_commutation_amounts(
        pension_amount=pension_amount,
        commutation_percent=commutation_percent,
        birth_date=ctx["birth_date"],
        application_rcvd_dt=ctx["application_rcvd_dt"],
        mo_certification_dt=ctx["mo_certification_dt"],
        separation_dt=ctx["separation_dt"],
        share_percent=share_percent,
        comm_amount_override=comm_amount_override,
        use_highest_side_round=use_highest_side_round,
    )
