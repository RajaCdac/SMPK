import math
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta

from .models import (
    CommutationApplication,
    PensionCase,
    PensionProposal,
    PensionSummary,
)


class PensionCalculationError(Exception):
    pass


def round_up_to_rupee(amount):
    """Fractional paisa rounds up to the next whole rupee (e.g. 1510318.08 → 1510319)."""
    return math.ceil(float(amount))


round_gratuity_up_to_rupee = round_up_to_rupee


# --- Normal pension (faithful port of Oracle FFUNC_NORMAL_PENSION) ---------

# Pension constants. Rules verified empirically against
# FINANCE.FI_PN_MH_PENSIONER (21,725 'G' + 155 'P' processed pensioners):
#   * Government line  -> 50% of emoluments (flat). For pension start dates
#     from 2016 onward this matched 2,449 / 2,454 cases (99.8%); the few
#     outliers are penalty/compassionate/data-quirk cases. The pre-2006
#     TQS/33 proportionate reduction is NOT applied to current retirees.
#   * Port line        -> emoluments * min(TQS_years, 30) / 80.
NORMAL_PENSION_FRACTION = 0.5
PORT_LINE_DIVISOR = 80
PORT_LINE_TQS_CAP = 30
MIN_PENSION_FLOOR = 1850          # FFUNC_NORMAL_PENSION hard-coded minimum
MIN_QUALIFYING_YEARS = 10         # below this -> service gratuity, not pension


def _current_da_percent_for_class(emp_class):
    from .services.gratuity_emoluments_service import _current_da_percent

    return _current_da_percent(emp_class)


def highest_side_round(amount):
    """Port of FFUNC_HIGHEST_SIDE_ROUND: floor, +1 only if fraction > 0.009."""
    amount = float(amount)
    base = math.floor(amount)
    return base + 1 if (amount - base) > 0.009 else base


def calculate_normal_pension(
    *,
    emoluments,
    tqs_years,
    pension_option="G",
    scale_min_basic=None,
    min_pension=MIN_PENSION_FLOOR,
):
    """
    Compute normal pension, mirroring Oracle FFUNC_NORMAL_PENSION.

    emoluments      : pension emoluments (last basic / 10-month average basic).
    tqs_years       : Total Qualifying Service in whole years.
    pension_option  : 'G' Government line (×0.5) | 'P' Port line (×TQS/80).
    scale_min_basic : scale minimum; only used for the TQS>=33 floor.
    Returns a whole-rupee amount (highest-side rounded), or 0.0 when
    qualifying service is below the 10-year pension threshold.
    """
    emoluments = float(emoluments or 0)
    option = (pension_option or "G").strip().upper()

    if tqs_years < MIN_QUALIFYING_YEARS:
        return 0.0

    if option == "P":
        capped_tqs = min(tqs_years, PORT_LINE_TQS_CAP)
        pension = emoluments * capped_tqs / PORT_LINE_DIVISOR
    else:
        pension = emoluments * NORMAL_PENSION_FRACTION
        # Average must not fall below 50% of scale minimum once TQS >= 33.
        if scale_min_basic and tqs_years >= 33:
            floor_amt = float(scale_min_basic) * 0.5
            if pension < floor_amt:
                pension = floor_amt

    if pension < float(min_pension):
        pension = float(min_pension)

    return float(highest_side_round(pension))


def get_gratuity_option_for_employee(emp_code, default=0):
    """Gratuity option (0/1/2) from proposal — Oracle FFUNC_DCR_GRATUITY codes."""
    from .services.gratuity_emoluments_service import normalize_gratuity_option

    emp_key = str(emp_code).strip()[:5]
    proposal = PensionProposal.objects.filter(emp_cd=emp_key).first()
    if not proposal and emp_key.isdigit():
        proposal = PensionProposal.objects.filter(emp_cd=str(int(emp_key))).first()
    if proposal and (proposal.gratuity_option or "").strip():
        return normalize_gratuity_option(proposal.gratuity_option)
    try:
        from .oracle_mirror import FiPnMhPensionProposal

        mirror = FiPnMhPensionProposal.objects.filter(emp_cd=emp_key).first()
        if mirror and mirror.gratuity_option is not None:
            return normalize_gratuity_option(mirror.gratuity_option)
    except Exception:
        pass
    return default


def get_pension_option_for_employee(emp_code, default="G"):
    """Pension option ('G'/'P') from the saved PensionProposal, if any."""
    emp_key = str(emp_code).strip()
    proposal = PensionProposal.objects.filter(emp_cd=emp_key).first()
    if not proposal and emp_key.isdigit():
        proposal = PensionProposal.objects.filter(emp_cd=str(int(emp_key))).first()
    if proposal and proposal.pension_option:
        opt = proposal.pension_option.strip().upper()
        if opt:
            return opt[0]  # accept 'G'/'P' or 'GOVERNMENT'/'PORT'
    return default


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


def get_separation_type_for_employee(emp_code):
    """Separation type from pension case (process intake), proposal, or Oracle mirror."""
    case = reload_pension_case_from_db(emp_code)
    if case and (case.separation_type or "").strip():
        return case.separation_type.strip().upper()
    emp_key = str(emp_code).strip()
    proposal = PensionProposal.objects.filter(emp_cd=emp_key).first()
    if not proposal and emp_key.isdigit():
        proposal = PensionProposal.objects.filter(emp_cd=str(int(emp_key))).first()
    if proposal and (proposal.separation_type or "").strip():
        return proposal.separation_type.strip().upper()
    try:
        from .oracle_mirror import FiPnMhPensionProposal

        mirror = FiPnMhPensionProposal.objects.filter(emp_cd=emp_key[:5]).first()
        if mirror and (mirror.separation_type or "").strip():
            return mirror.separation_type.strip().upper()
    except Exception:
        pass
    return ""


def is_voluntary_retirement(emp_code):
    """VR: commutation is applied after separation, not at first pension."""
    return get_separation_type_for_employee(emp_code) == "VR"


def resolve_separation_date(emp_code, case=None):
    """
    Actual separation for service / gratuity — not EXP_RET_DT on PensionCase.
    Prefer case → proposal → Oracle mirror → retirement_date.
    """
    if case is None:
        case = reload_pension_case_from_db(emp_code)
    if case and case.separation_date:
        return case.separation_date

    emp_key = str(emp_code).strip()[:5]
    proposal = PensionProposal.objects.filter(emp_cd=emp_key).first()
    if not proposal and emp_key.isdigit():
        proposal = PensionProposal.objects.filter(emp_cd=str(int(emp_key))).first()
    if proposal and proposal.separation_date:
        return proposal.separation_date

    try:
        from .oracle_mirror import FiPnMhPensionProposal

        mirror = FiPnMhPensionProposal.objects.filter(emp_cd=emp_key).first()
        if mirror and mirror.separation_dt:
            return mirror.separation_dt
    except Exception:
        pass

    if case and case.retirement_date:
        return case.retirement_date
    return None


def _as_plain_date(value):
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date()
    return value


def _days_to_ymd_30(total_days: int) -> tuple[int, int, int]:
    """
    Convert a day-count to Y/M/D using Oracle-style 30-day months (360-day year).

    Used when deducting NPAY_PRIOR_10MTH from qualifying service (TQS).
    Example: 1353 days → 3y 9m 3d  (1353 = 3*360 + 9*30 + 3).
    """
    days = int(total_days or 0)
    if days <= 0:
        return 0, 0, 0
    years = days // 360
    rem = days % 360
    months = rem // 30
    day = rem % 30
    return years, months, day


def _subtract_service_ymd(
    years: int,
    months: int,
    days: int,
    sub_years: int,
    sub_months: int,
    sub_days: int,
) -> tuple[int, int, int]:
    """
    Subtract service period Y/M/D with 30-day month borrow (Oracle TQS path).
    """
    y = int(years or 0)
    m = int(months or 0)
    d = int(days or 0)
    d -= int(sub_days or 0)
    while d < 0:
        d += 30
        m -= 1
    m -= int(sub_months or 0)
    while m < 0:
        m += 12
        y -= 1
    y -= int(sub_years or 0)
    if y < 0:
        return 0, 0, 0
    return y, m, d


def resolve_service_tenure(
    *,
    joining_date,
    service_end,
    dies_non_days=0,
    suspension_days=0,
    boys_serv_days=0,
    no_pay_days=0,
    no_pay_more_than_240_days=0,
):
    """
    Oracle FFUNC_TQS_ROUND_2_Org service dates.

    Gross length (join → separation) via calendar Y/M/D (dateutil relativedelta).

    TCCS end = separation − (dies-non + suspension + boys service)
               [− 12 months × NPAY_MORETHAN_240_DYS when that field > 0]
               then calendar Y/M/D from join.

    TQS       = same base length as join→(separation − dies/susp/boys),
               then deduct no-pay as Y/M/D on a **30-day month / 360-day year**
               (not plain timedelta days). Emp 44377: NPAY 1353 → 3y 9m 3d
               subtracted from 37y 7m 27d → 33y 10m 24d (matches Oracle).
    """
    join_date = _as_plain_date(joining_date)
    end_date = _as_plain_date(service_end)
    if not join_date or not end_date:
        return {
            "total_service_years": 0,
            "total_service_months": 0,
            "total_service_days": 0,
            "tccs_years": 0,
            "tccs_months": 0,
            "tccs_days": 0,
            "tqs_years": 0,
            "tqs_months": 0,
            "tqs_days": 0,
        }

    base_subtract = (
        int(dies_non_days or 0)
        + int(suspension_days or 0)
        + int(boys_serv_days or 0)
    )
    base_end = end_date - timedelta(days=base_subtract)

    nopay = int(no_pay_days or 0)
    more_240 = int(no_pay_more_than_240_days or 0)
    if more_240 > 0:
        tccs_end = base_end - relativedelta(months=12 * more_240)
    else:
        tccs_end = base_end

    total_diff = relativedelta(end_date, join_date)
    tccs_diff = relativedelta(tccs_end, join_date)

    # TQS: calendar length join → base_end, then YMD no-pay (30-day months)
    base_diff = relativedelta(base_end, join_date)
    ny, nm, nd = _days_to_ymd_30(nopay)
    tqs_y, tqs_m, tqs_d = _subtract_service_ymd(
        base_diff.years,
        base_diff.months,
        base_diff.days,
        ny,
        nm,
        nd,
    )

    return {
        "total_service_years": total_diff.years,
        "total_service_months": total_diff.months,
        "total_service_days": total_diff.days,
        "tccs_years": tccs_diff.years,
        "tccs_months": tccs_diff.months,
        "tccs_days": tccs_diff.days,
        "tqs_years": tqs_y,
        "tqs_months": tqs_m,
        "tqs_days": tqs_d,
    }


def fetch_calculation_inputs_from_db(emp_code):
    """
    Load inputs used for calculation directly from DB at call time.
    no_pay_days may legitimately be 0.
    """
    case = reload_pension_case_from_db(emp_code)
    if not case:
        return None

    defer_commutation = is_voluntary_retirement(emp_code)
    if defer_commutation:
        commutation_percent = 0
    else:
        commutation_percent = get_commutation_percent_for_employee(
            emp_code, require_saved=True
        )

    emp_key = str(emp_code).strip()[:5]
    no_pay_days = int(case.no_pay_days)
    dies_non_days = int(case.dies_non_days)
    no_pay_more_than_240_days = int(case.no_pay_more_than_240_days)
    suspension_days = int(case.suspension_days)
    boys_serv_days = int(case.boys_serv_days)
    try:
        from .oracle_mirror import FiPnMhOldbillParam

        oldbill = FiPnMhOldbillParam.objects.filter(emp_cd=emp_key).first()
        if oldbill:
            if oldbill.npay_prior_10mth is not None:
                no_pay_days = int(oldbill.npay_prior_10mth)
            if oldbill.dnon_days is not None:
                dies_non_days = int(oldbill.dnon_days)
            if oldbill.npay_morethan_240_dys is not None:
                no_pay_more_than_240_days = int(oldbill.npay_morethan_240_dys)
            if oldbill.susp_days is not None:
                suspension_days = int(oldbill.susp_days)
            if oldbill.boy_serv_days is not None:
                boys_serv_days = int(oldbill.boy_serv_days)
    except Exception:
        pass

    from .services.salout_transfer_service import (
        ensure_salout_for_calculation,
        resolve_emoluments_basic,
    )

    try:
        ensure_salout_for_calculation(emp_code, force=False)
    except Exception:
        pass

    emoluments_basic, emoluments_source = resolve_emoluments_basic(
        emp_code,
        fallback_last_basic=float(case.last_basic),
    )

    separation_date = resolve_separation_date(emp_code, case)

    return {
        "case": case,
        "no_pay_days": no_pay_days,
        "dies_non_days": dies_non_days,
        "no_pay_more_than_240_days": no_pay_more_than_240_days,
        "suspension_days": suspension_days,
        "boys_serv_days": boys_serv_days,
        "last_basic": emoluments_basic,
        "emoluments_source": emoluments_source,
        "case_last_basic": float(case.last_basic),
        "commutation_percent": commutation_percent,
        "joining_date": case.joining_date,
        "retirement_date": case.retirement_date,
        "separation_date": separation_date,
        "emp_class": case.emp_class,
        "pension_option": get_pension_option_for_employee(emp_code),
        "gratuity_option": get_gratuity_option_for_employee(emp_code),
        "defer_commutation": defer_commutation,
    }


def calculate_pension_financials(
    *,
    joining_date,
    retirement_date,
    emp_class,
    last_basic,
    no_pay_days=0,
    dies_non_days=0,
    no_pay_more_than_240_days=0,
    suspension_days=0,
    boys_serv_days=0,
    commutation_percent=40,
    pension_option="G",
    defer_commutation=False,
    birth_date=None,
    application_rcvd_dt=None,
    mo_certification_dt=None,
    separation_dt=None,
    emp_code=None,
    gratuity_option=0,
):
    """
    Pension, gratuity and commutation financials.
    Commutation lump sum uses FI_PN_MD_COMMRATE_RUPEE by age (Oracle port).
    Gratuity follows Oracle FFUNC_DCR_GRATUITY (opt-I / opt-II / death).
    """
    join_date = joining_date
    ret_date = retirement_date
    if isinstance(join_date, datetime):
        join_date = join_date.date()
    if isinstance(ret_date, datetime):
        ret_date = ret_date.date()

    service_end = separation_dt or ret_date
    if isinstance(service_end, datetime):
        service_end = service_end.date()

    tenure = resolve_service_tenure(
        joining_date=join_date,
        service_end=service_end,
        dies_non_days=dies_non_days,
        suspension_days=suspension_days,
        boys_serv_days=boys_serv_days,
        no_pay_days=no_pay_days,
        no_pay_more_than_240_days=no_pay_more_than_240_days,
    )
    years = tenure["total_service_years"]
    months = tenure["total_service_months"]
    days = tenure["total_service_days"]
    tccs_years = tenure["tccs_years"]
    tccs_months = tenure["tccs_months"]
    tccs_days = tenure["tccs_days"]
    tqs_years = tenure["tqs_years"]
    tqs_months = tenure["tqs_months"]
    tqs_days = tenure["tqs_days"]

    basic = float(last_basic)
    pension_amount = calculate_normal_pension(
        emoluments=basic,
        tqs_years=tqs_years,
        pension_option=pension_option,
    )

    if defer_commutation:
        comm_pct = 0.0
        commutation_amount = 0
    else:
        comm_pct = float(commutation_percent if commutation_percent is not None else 40)
        from .services.commutation_rate_service import (
            CommutationRateError,
            compute_commutation_amounts,
        )

        try:
            comm_result = compute_commutation_amounts(
                pension_amount=pension_amount,
                commutation_percent=comm_pct,
                birth_date=birth_date,
                application_rcvd_dt=application_rcvd_dt,
                mo_certification_dt=mo_certification_dt,
                separation_dt=separation_dt or service_end,
                use_highest_side_round=True,
            )
            commutation_amount = comm_result["lump_sum"]
        except CommutationRateError as exc:
            raise PensionCalculationError(str(exc)) from exc

    from .services.gratuity_emoluments_service import (
        GRATUITY_OPTION_LABELS,
        calculate_gratuity_payable,
        resolve_gratuity_emoluments,
    )

    gratuity_emoluments = None
    gratuity_emoluments_source = None
    gratuity_detail = None
    if emp_code:
        (
            gratuity_emoluments,
            gratuity_emoluments_source,
            gratuity_detail,
        ) = resolve_gratuity_emoluments(
            emp_code,
            emp_class,
            basic,
            separation_dt=service_end,
        )
    else:
        da_percent = _current_da_percent_for_class(emp_class)
        gratuity_emoluments = basic * (1 + da_percent / 100)
        gratuity_emoluments_source = "current_da_percent"

    gratuity_breakdown = calculate_gratuity_payable(
        emoluments=gratuity_emoluments,
        gratuity_option=gratuity_option,
        separation_dt=service_end,
        tccs_years=tccs_years,
        tccs_months=tccs_months,
        tccs_days=tccs_days,
        tqs_years=tqs_years,
        tqs_months=tqs_months,
        tqs_days=tqs_days,
        emp_cd=emp_code,
        emp_class=emp_class,
        separation_type=get_separation_type_for_employee(emp_code)
        if emp_code
        else None,
        joining_date=join_date,
        exp_retirement_date=ret_date,
    )
    gratuity_amount = gratuity_breakdown["gratuity_amount"]
    dcr_gratuity_amount = gratuity_breakdown["dcr_gratuity_amount"]

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
        "pension_basic": basic,
        "pension_amount": round(pension_amount, 2),
        "commutation_amount": float(commutation_amount),
        "gratuity_amount": float(gratuity_amount),
        "dcr_gratuity_amount": float(dcr_gratuity_amount),
        "option_gratuity_amount": float(gratuity_breakdown["option_gratuity_amount"]),
        "opt_i_gratuity_amount": float(gratuity_breakdown["opt_i_gratuity_amount"]),
        "opt_ii_gratuity_amount": float(gratuity_breakdown["opt_ii_gratuity_amount"]),
        "death_gratuity_amount": float(
            gratuity_breakdown.get("death_gratuity_amount") or 0
        ),
        "gratuity_winning_option": gratuity_breakdown.get("gratuity_winning_option"),
        "dcr_gratuity_formula_amount": gratuity_breakdown.get(
            "dcr_gratuity_formula_amount"
        ),
        "option_gratuity_formula_amount": gratuity_breakdown.get(
            "option_gratuity_formula_amount"
        ),
        "gratuity_payable_basis": gratuity_breakdown.get("gratuity_payable_basis"),
        "gratuity_capped": bool(gratuity_breakdown["gratuity_capped"]),
        "gratuity_option": gratuity_breakdown.get("gratuity_option", gratuity_option),
        "gratuity_option_label": gratuity_breakdown.get(
            "gratuity_option_label",
            GRATUITY_OPTION_LABELS.get(gratuity_option, ""),
        ),
        "dcr_gratuity_option_label": gratuity_breakdown.get("dcr_gratuity_option_label"),
        "opt_ii_gratuity_option_label": gratuity_breakdown.get(
            "opt_ii_gratuity_option_label"
        ),
        "death_gratuity_option_label": gratuity_breakdown.get(
            "death_gratuity_option_label"
        ),
        "is_death_gratuity_case": gratuity_breakdown.get("is_death_gratuity_case"),
        "gratuity_emoluments": (
            float(gratuity_breakdown.get("gratuity_emoluments_used") or gratuity_emoluments)
            if gratuity_emoluments is not None
            else None
        ),
        "gratuity_emoluments_source": gratuity_emoluments_source,
        "gratuity_qualifying_years": gratuity_breakdown.get("gratuity_qualifying_years"),
        "gratuity_detail": gratuity_detail,
        "service_end_date": service_end,
        "commutation_percent": (
            0.0
            if defer_commutation
            else (
                float(commutation_percent)
                if commutation_percent is not None
                else 40.0
            )
        ),
        "defer_commutation": defer_commutation,
        "pension_start_date": ret_date,
    }


def _attach_dcr_gratuity_fields(data, case, *, calc=None, summary=None):
    """Expose DCRG vs proposal-option gratuity breakdown alongside payable amount."""
    if calc and calc.get("dcr_gratuity_amount") is not None:
        data["dcr_gratuity_amount"] = calc["dcr_gratuity_amount"]
        data["option_gratuity_amount"] = calc.get("option_gratuity_amount")
        data["opt_i_gratuity_amount"] = calc.get("opt_i_gratuity_amount")
        data["opt_ii_gratuity_amount"] = calc.get("opt_ii_gratuity_amount")
        data["death_gratuity_amount"] = calc.get("death_gratuity_amount")
        data["gratuity_winning_option"] = calc.get("gratuity_winning_option")
        data["dcr_gratuity_formula_amount"] = calc.get("dcr_gratuity_formula_amount")
        data["option_gratuity_formula_amount"] = calc.get(
            "option_gratuity_formula_amount"
        )
        data["gratuity_payable_basis"] = calc.get("gratuity_payable_basis")
        data["gratuity_capped"] = bool(calc.get("gratuity_capped"))
        data["gratuity_qualifying_years"] = calc.get("gratuity_qualifying_years")
        data["gratuity_option"] = calc.get("gratuity_option")
        data["gratuity_option_label"] = calc.get("gratuity_option_label")
        data["dcr_gratuity_option_label"] = calc.get("dcr_gratuity_option_label")
        data["opt_ii_gratuity_option_label"] = calc.get("opt_ii_gratuity_option_label")
        data["death_gratuity_option_label"] = calc.get("death_gratuity_option_label")
        data["is_death_gratuity_case"] = calc.get("is_death_gratuity_case")
        if calc.get("gratuity_emoluments") is not None:
            data["gratuity_emoluments"] = calc["gratuity_emoluments"]
        return data

    if not summary or not data.get("calculated"):
        return data

    from .services.gratuity_emoluments_service import (
        calculate_gratuity_payable,
        resolve_gratuity_emoluments,
    )

    separation_dt = resolve_separation_date(case.emp_code, case) or case.retirement_date
    emoluments, _, _detail = resolve_gratuity_emoluments(
        case.emp_code,
        case.emp_class,
        case.last_basic,
        separation_dt=separation_dt,
    )
    if emoluments is None:
        return data

    breakdown = calculate_gratuity_payable(
        emoluments=emoluments,
        gratuity_option=get_gratuity_option_for_employee(case.emp_code),
        separation_dt=separation_dt,
        tccs_years=summary.tccs_years,
        tccs_months=summary.tccs_months,
        tccs_days=summary.tccs_days,
        tqs_years=summary.tqs_years,
        tqs_months=summary.tqs_months,
        tqs_days=summary.tqs_days,
        emp_cd=case.emp_code,
        emp_class=case.emp_class,
        separation_type=get_separation_type_for_employee(case.emp_code),
        joining_date=case.joining_date,
        exp_retirement_date=case.retirement_date,
    )
    data["dcr_gratuity_amount"] = breakdown["dcr_gratuity_amount"]
    data["option_gratuity_amount"] = breakdown["option_gratuity_amount"]
    data["opt_i_gratuity_amount"] = breakdown["opt_i_gratuity_amount"]
    data["opt_ii_gratuity_amount"] = breakdown["opt_ii_gratuity_amount"]
    data["death_gratuity_amount"] = breakdown.get("death_gratuity_amount")
    data["gratuity_winning_option"] = breakdown.get("gratuity_winning_option")
    data["dcr_gratuity_formula_amount"] = breakdown.get("dcr_gratuity_formula_amount")
    data["option_gratuity_formula_amount"] = breakdown.get(
        "option_gratuity_formula_amount"
    )
    data["gratuity_payable_basis"] = breakdown.get("gratuity_payable_basis")
    data["gratuity_capped"] = breakdown["gratuity_capped"]
    data["gratuity_qualifying_years"] = breakdown["gratuity_qualifying_years"]
    data["gratuity_option"] = breakdown.get("gratuity_option")
    data["gratuity_option_label"] = breakdown.get("gratuity_option_label")
    data["dcr_gratuity_option_label"] = breakdown.get("dcr_gratuity_option_label")
    data["opt_ii_gratuity_option_label"] = breakdown.get("opt_ii_gratuity_option_label")
    data["death_gratuity_option_label"] = breakdown.get("death_gratuity_option_label")
    data["is_death_gratuity_case"] = breakdown.get("is_death_gratuity_case")
    data["gratuity_emoluments"] = float(
        breakdown.get("gratuity_emoluments_used") or emoluments
    )
    return data


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
        "emoluments_basic": None,
        "emoluments_source": None,
        "no_pay_days": int(case.no_pay_days),
        "dies_non_days": int(case.dies_non_days),
        "no_pay_more_than_240_days": int(case.no_pay_more_than_240_days),
        "suspension_days": int(case.suspension_days),
        "boys_serv_days": int(case.boys_serv_days),
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
            "pension_basic": calc.get("pension_basic"),
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
        if calc.get("pension_basic") is not None:
            data["last_basic"] = float(calc["pension_basic"])
            data["emoluments_basic"] = float(calc["pension_basic"])
    _attach_dcr_gratuity_fields(data, case, calc=calc, summary=summary)
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
    defer_commutation = inputs.get("defer_commutation", False)

    comm_app = None
    if not defer_commutation:
        comm_app = get_commutation_application_for_employee(emp_code)

    from .services.commutation_rate_service import resolve_commutation_context

    rate_ctx = resolve_commutation_context(
        emp_code,
        comm_app=comm_app,
        case=case,
    )

    calc = calculate_pension_financials(
        joining_date=inputs["joining_date"],
        retirement_date=inputs["retirement_date"],
        emp_class=inputs["emp_class"],
        last_basic=inputs["last_basic"],
        no_pay_days=inputs["no_pay_days"],
        dies_non_days=inputs["dies_non_days"],
        no_pay_more_than_240_days=inputs["no_pay_more_than_240_days"],
        suspension_days=inputs["suspension_days"],
        boys_serv_days=inputs["boys_serv_days"],
        commutation_percent=commutation_percent,
        pension_option=inputs.get("pension_option", "G"),
        defer_commutation=defer_commutation,
        birth_date=rate_ctx["birth_date"],
        application_rcvd_dt=rate_ctx["application_rcvd_dt"],
        mo_certification_dt=rate_ctx["mo_certification_dt"],
        separation_dt=inputs.get("separation_date") or rate_ctx["separation_dt"],
        emp_code=emp_code,
        gratuity_option=inputs.get("gratuity_option", 0),
    )

    case.commutation_percent = commutation_percent
    resolved_basic = float(inputs["last_basic"])
    if float(case.last_basic) != resolved_basic:
        case.last_basic = resolved_basic
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


def format_total_service(years, months, days):
    """Display total service as Y/M/D (pension amount screen)."""
    return f"{int(years)}Y {int(months)}M {int(days)}D"


def round_service_to_years(years, months, days):
    """Round up to whole years when any extra month or day remains (31Y 9M → 32)."""
    y = int(years)
    if int(months) > 0 or int(days) > 0:
        return y + 1
    return y


def format_service_tenure_years_only(years, months, days):
    """Proposal form: total service as rounded years only."""
    return f"{round_service_to_years(years, months, days)} Yrs"


def get_service_components_for_case(case):
    """Return (years, months, days) from PensionSummary or join-to-separation dates."""
    if not case:
        return None

    try:
        summary = case.summary
    except PensionSummary.DoesNotExist:
        summary = None

    if summary:
        return (
            summary.total_service_years,
            summary.total_service_months,
            summary.total_service_days,
        )

    end_date = resolve_separation_date(case.emp_code, case)
    if case.joining_date and end_date:
        join_date = case.joining_date
        if isinstance(join_date, datetime):
            join_date = join_date.date()
        if isinstance(end_date, datetime):
            end_date = end_date.date()
        diff = relativedelta(end_date, join_date)
        return (diff.years, diff.months, diff.days)

    return None


def get_total_service_for_case(case):
    """Total service from PensionSummary, or join date to separation/retirement."""
    components = get_service_components_for_case(case)
    if components:
        return format_total_service(*components)
    return ""


def get_service_tenure_for_employee(emp_code):
    case = reload_pension_case_from_db(emp_code)
    components = get_service_components_for_case(case)
    if components:
        return format_service_tenure_years_only(*components)
    return ""


def build_amount_lookup_payload(emp_code):
    from .services.legacy_prefill_service import load_amount_defaults

    case = reload_pension_case_from_db(emp_code)
    amount_defaults = load_amount_defaults(emp_code)

    if not case:
        return {
            "exists": False,
            "amount_data": None,
            "amount_defaults": amount_defaults,
            "message": "No-pay / pension case not found. Save no-pay entry first.",
        }

    defer_commutation = is_voluntary_retirement(emp_code)
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
        commutation_percent_from_app=(
            None if defer_commutation else commutation_percent
        ),
    )
    amount_data["has_commutation_application"] = has_commutation
    amount_data["is_voluntary_retirement"] = defer_commutation
    amount_data["defer_commutation"] = defer_commutation
    if defer_commutation:
        amount_data["commutation_percent"] = 0
        amount_data["inputs_ready"] = True
    else:
        amount_data["inputs_ready"] = (
            has_commutation and commutation_percent is not None
        )

    from .services.first_month_pension_service import get_first_month_status

    first_month = get_first_month_status(emp_code)
    if first_month:
        amount_data["first_month"] = first_month

    from .services.salout_transfer_service import get_salout_status, resolve_emoluments_basic

    emoluments_basic, emoluments_source = resolve_emoluments_basic(
        emp_code,
        fallback_last_basic=float(case.last_basic),
    )
    amount_data["emoluments_basic"] = emoluments_basic
    amount_data["emoluments_source"] = emoluments_source
    if emoluments_basic is not None:
        amount_data["pension_basic"] = emoluments_basic
        amount_data["last_basic"] = emoluments_basic
    amount_data["salout"] = get_salout_status(emp_code)

    return {
        "exists": True,
        "amount_data": amount_data,
        "amount_defaults": (
            None if amount_data.get("calculated") else amount_defaults
        ),
    }
