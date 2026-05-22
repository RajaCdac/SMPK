import math
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta

from .models import CommutationApplication, PensionCase, PensionSummary


class PensionCalculationError(Exception):
    pass


def round_up_to_rupee(amount):
    """Fractional paisa rounds up to the next whole rupee (e.g. 1510318.08 → 1510319)."""
    return math.ceil(float(amount))


round_gratuity_up_to_rupee = round_up_to_rupee


def get_commutation_application_for_employee(emp_code):
    emp_key = str(emp_code).strip()
    app = CommutationApplication.objects.filter(emp_cd=emp_key).first()
    if not app and emp_key.isdigit():
        app = CommutationApplication.objects.filter(
            emp_cd=str(int(emp_key))
        ).first()
    if not app:
        app = CommutationApplication.objects.filter(
            emp_cd__iexact=emp_key
        ).first()
    return app


def get_commutation_percent_for_employee(emp_code, *, require_saved=False):
    """
    Commutation % from first_pension CommutationApplication (fresh DB read).
    When require_saved=True, missing application or null % raises.
    """
    comm = get_commutation_application_for_employee(emp_code)
    if not comm:
        if require_saved:
            raise PensionCalculationError(
                "Commutation application not found. Save commutation entry first."
            )
        return None
    comm = CommutationApplication.objects.get(pk=comm.pk)
    if comm.commutation_per is None:
        if require_saved:
            raise PensionCalculationError(
                "Commutation % is not set in commutation application."
            )
        return None
    return float(comm.commutation_per)


def reload_pension_case_from_db(emp_code):
    """Always read the latest pension case row before amount work."""
    case = PensionCase.objects.filter(
        emp_code=str(emp_code).strip()
    ).first()
    if not case:
        emp_key = str(emp_code).strip()
        if emp_key.isdigit():
            case = PensionCase.objects.filter(
                emp_code=str(int(emp_key))
            ).first()
        if not case:
            case = PensionCase.objects.filter(
                emp_code__iexact=emp_key
            ).first()
    if not case:
        return None
    return PensionCase.objects.get(pk=case.pk)


def fetch_calculation_inputs_from_db(emp_code):
    """
    Load inputs used for calculation directly from DB at call time.
    no_pay_days may legitimately be 0.
    """
    case = reload_pension_case_from_db(emp_code)
    if not case:
        return None

    commutation_percent = get_commutation_percent_for_employee(
        emp_code, require_saved=True
    )

    return {
        "case": case,
        "no_pay_days": int(case.no_pay_days),
        "dies_non_days": int(case.dies_non_days),
        "last_basic": float(case.last_basic),
        "commutation_percent": commutation_percent,
        "joining_date": case.joining_date,
        "retirement_date": case.retirement_date,
        "emp_class": case.emp_class,
    }


def calculate_pension_financials(
    *,
    joining_date,
    retirement_date,
    emp_class,
    last_basic,
    no_pay_days=0,
    dies_non_days=0,
    commutation_percent=40,
):
    """
    Same formulas as PensionProcessView.
    commutation_amount = pension_amount * 0.4 * 98.328 (per PensionProcessView).
    commutation_percent from DB is stored on the case for reference only.
    """
    join_date = joining_date
    ret_date = retirement_date
    if isinstance(join_date, datetime):
        join_date = join_date.date()
    if isinstance(ret_date, datetime):
        ret_date = ret_date.date()

    service_diff = relativedelta(ret_date, join_date)
    years = service_diff.years
    months = service_diff.months
    days = service_diff.days

    dies_non = int(dies_non_days or 0)
    tccs_date = ret_date - timedelta(days=dies_non)
    tccs_diff = relativedelta(tccs_date, join_date)
    tccs_years = tccs_diff.years
    tccs_months = tccs_diff.months
    tccs_days = tccs_diff.days

    nopay = int(no_pay_days or 0)
    tqs_date = tccs_date - timedelta(days=nopay)
    tqs_diff = relativedelta(tqs_date, join_date)
    tqs_years = tqs_diff.years
    tqs_months = tqs_diff.months
    tqs_days = tqs_diff.days

    basic = float(last_basic)
    pension_amount = basic * 0.5

    # Same as PensionProcessView: 40% of pension × commutation factor
    commutation_amount = round_up_to_rupee(
        pension_amount * 0.4 * 98.328
    )

    if emp_class in ["I", "II"]:
        da_percent = 54.32
    else:
        da_percent = 19.07
    da = basic * da_percent / 100

    qualifying_years = tccs_years
    if tccs_months >= 6 or (tccs_months == 6 and tccs_days > 0):
        qualifying_years += 1

    gratuity_amount = ((basic + da) * 15 * qualifying_years) / 26
    if gratuity_amount > 2000000:
        gratuity_amount = 2000000
    gratuity_amount = round_gratuity_up_to_rupee(gratuity_amount)

    return {
        "total_service_years": years,
        "total_service_months": months,
        "total_service_days": days,
        "tccs_years": tccs_years,
        "tccs_months": tccs_months,
        "tccs_days": tccs_days,
        "tqs_years": tqs_years,
        "tqs_months": tqs_months,
        "tqs_days": tqs_days,
        "pension_amount": round(pension_amount, 2),
        "commutation_amount": float(commutation_amount),
        "gratuity_amount": float(gratuity_amount),
        "commutation_percent": (
            float(commutation_percent)
            if commutation_percent is not None
            else 40.0
        ),
        "pension_start_date": ret_date,
    }


def serialize_amount_data(
    case,
    summary=None,
    calc=None,
    *,
    commutation_percent_from_app=None,
):
    """Inputs (no-pay, comm %) always reflect the pension case / commutation app."""
    data = {
        "case_id": case.id,
        "emp_code": case.emp_code,
        "last_basic": float(case.last_basic),
        "no_pay_days": int(case.no_pay_days),
        "dies_non_days": int(case.dies_non_days),
        "commutation_percent": (
            float(commutation_percent_from_app)
            if commutation_percent_from_app is not None
            else float(case.commutation_percent)
            if case.commutation_percent is not None
            else None
        ),
        "commutation_percent_from_app": commutation_percent_from_app,
        "pension_amount": None,
        "commutation_amount": None,
        "gratuity_amount": None,
        "calculated": False,
    }
    if summary:
        data.update({
            "pension_amount": float(summary.pension_amount),
            "commutation_amount": float(summary.commutation_amount),
            "gratuity_amount": float(summary.gratuity_amount),
            "total_service": (
                f"{summary.total_service_years}Y "
                f"{summary.total_service_months}M "
                f"{summary.total_service_days}D"
            ),
            "tccs": (
                f"{summary.tccs_years}Y "
                f"{summary.tccs_months}M "
                f"{summary.tccs_days}D"
            ),
            "tqs": (
                f"{summary.tqs_years}Y "
                f"{summary.tqs_months}M "
                f"{summary.tqs_days}D"
            ),
            "calculated": True,
        })
    if calc:
        data.update({
            "pension_amount": calc["pension_amount"],
            "commutation_amount": calc["commutation_amount"],
            "gratuity_amount": calc["gratuity_amount"],
            "commutation_percent": calc["commutation_percent"],
            "total_service": (
                f"{calc['total_service_years']}Y "
                f"{calc['total_service_months']}M "
                f"{calc['total_service_days']}D"
            ),
            "tccs": (
                f"{calc['tccs_years']}Y "
                f"{calc['tccs_months']}M "
                f"{calc['tccs_days']}D"
            ),
            "tqs": (
                f"{calc['tqs_years']}Y "
                f"{calc['tqs_months']}M "
                f"{calc['tqs_days']}D"
            ),
            "calculated": True,
        })
    return data


def run_pension_calculation_for_case(emp_code, user=None):
    """
    Calculate amounts using inputs read from DB at this moment
    (not values cached earlier in the session).
    """
    inputs = fetch_calculation_inputs_from_db(emp_code)
    if not inputs:
        raise PensionCalculationError(
            "Pension case not found. Complete no-pay entry before calculation."
        )

    case = inputs["case"]
    commutation_percent = inputs["commutation_percent"]

    calc = calculate_pension_financials(
        joining_date=inputs["joining_date"],
        retirement_date=inputs["retirement_date"],
        emp_class=inputs["emp_class"],
        last_basic=inputs["last_basic"],
        no_pay_days=inputs["no_pay_days"],
        dies_non_days=inputs["dies_non_days"],
        commutation_percent=commutation_percent,
    )

    case.commutation_percent = commutation_percent
    if user and user.is_authenticated:
        case.updated_by = user
    case.save()

    summary, _created = PensionSummary.objects.update_or_create(
        pension_case=case,
        defaults={
            "total_service_years": calc["total_service_years"],
            "total_service_months": calc["total_service_months"],
            "total_service_days": calc["total_service_days"],
            "tccs_years": calc["tccs_years"],
            "tccs_months": calc["tccs_months"],
            "tccs_days": calc["tccs_days"],
            "tqs_years": calc["tqs_years"],
            "tqs_months": calc["tqs_months"],
            "tqs_days": calc["tqs_days"],
            "pension_amount": calc["pension_amount"],
            "commutation_amount": calc["commutation_amount"],
            "gratuity_amount": calc["gratuity_amount"],
            "pension_start_date": calc["pension_start_date"],
        },
    )

    return case, summary, calc, commutation_percent


def build_amount_lookup_payload(emp_code):
    case = reload_pension_case_from_db(emp_code)
    if not case:
        return {
            "exists": False,
            "amount_data": None,
            "message": "No-pay / pension case not found. Save no-pay entry first.",
        }

    commutation_percent = get_commutation_percent_for_employee(
        emp_code, require_saved=False
    )
    has_commutation = bool(
        get_commutation_application_for_employee(emp_code)
    )
    summary = PensionSummary.objects.filter(pension_case_id=case.id).first()
    amount_data = serialize_amount_data(
        case,
        summary,
        commutation_percent_from_app=commutation_percent,
    )
    amount_data["has_commutation_application"] = has_commutation
    amount_data["inputs_ready"] = (
        has_commutation and commutation_percent is not None
    )

    return {
        "exists": True,
        "amount_data": amount_data,
    }
