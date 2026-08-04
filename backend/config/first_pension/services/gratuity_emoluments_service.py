"""
Gratuity emoluments for FFUNC_DCR_GRATUITY-style calculation.

Current retirees: last drawn basic + DA% from fi_pr_mh_calc_da (by class/quarter).
Older cases: actual basic + DA from payroll salout / fi_pr_mh_calc_da quarterly rate.
"""

from collections import defaultdict
from datetime import date, timedelta
from decimal import Decimal

from dateutil.relativedelta import relativedelta

from employee.services.oracle_service import (
    get_oracle_connection,
    oracle_reads_enabled,
    try_oracle_connection,
)

from ..oracle_mirror import FiPnMhPensioner, FiPnTdSalout, FiPnThSalout
from .da_rate_service import (
    flat_class_da_percent,
    lookup_ada_da_percent,
)
from .salout_transfer_service import (
    SaloutTransferError,
    _clip_emp,
    _resolve_pension_start,
)


# Separation before this year → payroll DA / calc_da quarterly lookup on increment month.
HISTORICAL_GRATUITY_CUTOFF_YEAR = 2026


def _da_reference_date(pension_start, separation_dt=None):
    if separation_dt:
        return (
            separation_dt.date()
            if hasattr(separation_dt, "date") and callable(separation_dt.date)
            else separation_dt
        )
    if pension_start:
        return (
            pension_start.date()
            if hasattr(pension_start, "date") and callable(pension_start.date)
            else pension_start
        )
    return None


def _flat_da_on_basic(basic, emp_class, reference_dt=None):
    if basic <= 0:
        return 0.0
    da_pct = flat_class_da_percent(emp_class, reference_dt)
    return float(
        (Decimal(str(basic)) * da_pct / Decimal("100")).quantize(Decimal("0.01"))
    )


def _apply_current_retiree_flat_da(
    basic, da, cca, pension_start, emp_class, *, separation_dt=None
):
    """
    Current retirees: use fi_pr_mh_calc_da rate on basic (ignore payroll DA line).
    """
    if _is_historical_case(pension_start, separation_dt) or basic <= 0:
        return da, cca
    ref = _da_reference_date(pension_start, separation_dt)
    return _flat_da_on_basic(basic, emp_class, ref), cca


def _finalize_emoluments_detail(
    detail, emp_class, pension_start, *, separation_dt=None
):
    """Recompute emoluments with flat class DA for current retirees."""
    if not detail:
        return None
    basic = float(detail.get("basic") or 0)
    cca = float(detail.get("cca") or 0)
    da = float(detail.get("da") or 0)
    da, cca = _apply_current_retiree_flat_da(
        basic, da, cca, pension_start, emp_class, separation_dt=separation_dt
    )
    total = basic + da + cca
    if total <= 0:
        return None
    out = dict(detail)
    out["basic"] = basic
    out["da"] = da
    out["cca"] = cca
    out["emoluments"] = total
    if not _is_historical_case(pension_start, separation_dt):
        ref = _da_reference_date(pension_start, separation_dt)
        out["da_percent"] = float(flat_class_da_percent(emp_class, ref))
    return out


def _net_line_amount(line):
    return float(line.act_earndedn_amt or 0) + float(line.adj_earndedn_amt or 0)


def _monthly_totals_from_pn_td(emp_cd):
    """Per-month basic / DA / CCA from fi_pn_td_salout."""
    rows = FiPnTdSalout.objects.filter(emp_cd=_clip_emp(emp_cd)).order_by(
        "sal_yr", "sal_mth", "earndedn_cd"
    )
    buckets = defaultdict(lambda: {"basic": 0.0, "da": 0.0, "cca": 0.0})
    for row in rows:
        key = (int(row.sal_yr), int(row.sal_mth))
        net = _net_line_amount(row)
        code = str(row.earndedn_cd or "").strip()
        if code == "001":
            buckets[key]["basic"] = net
        elif code == "007":
            buckets[key]["da"] = net
        elif code == "111":
            buckets[key]["cca"] = net
    months = []
    for key in sorted(buckets.keys()):
        item = buckets[key]
        total = item["basic"] + item["da"] + item["cca"]
        months.append(
            {
                "sal_yr": key[0],
                "sal_mth": key[1],
                "basic": item["basic"],
                "da": item["da"],
                "cca": item["cca"],
                "total": total,
            }
        )
    return months


def _monthly_totals_from_pr_td_oracle(emp_cd, window_start):
    """Historical payroll DA from FI_PR_TD_SALOUT (full earn lines)."""
    emp_key = _clip_emp(emp_cd)
    conn = get_oracle_connection()
    cur = conn.cursor()
    try:
        cur.execute(
            """
            SELECT SAL_MTH, SAL_YR, EARNDEDN_CD,
                   NVL(ACT_EARNDEDN_AMT, 0) + NVL(ADJ_EARNDEDN_AMT, 0)
            FROM FINANCE.FI_PR_TD_SALOUT
            WHERE EMP_CD = :emp
              AND TO_DATE(
                    '01/' || LPAD(SAL_MTH, 2, '0') || '/' || LPAD(SAL_YR, 4, '0'),
                    'DD/MM/RRRR'
                  ) >= :window_start
              AND EARNDEDN_CD IN ('001', '007', '111')
            ORDER BY SAL_YR, SAL_MTH, EARNDEDN_CD
            """,
            {"emp": emp_key, "window_start": window_start},
        )
        buckets = defaultdict(lambda: {"basic": 0.0, "da": 0.0, "cca": 0.0})
        for sal_mth, sal_yr, code, net in cur.fetchall():
            key = (int(sal_yr), int(sal_mth))
            code = str(code or "").strip()
            val = float(net or 0)
            if code == "001":
                buckets[key]["basic"] = val
            elif code == "007":
                buckets[key]["da"] = val
            elif code == "111":
                buckets[key]["cca"] = val
    finally:
        cur.close()
        conn.close()

    months = []
    for key in sorted(buckets.keys()):
        item = buckets[key]
        total = item["basic"] + item["da"] + item["cca"]
        months.append(
            {
                "sal_yr": key[0],
                "sal_mth": key[1],
                "basic": item["basic"],
                "da": item["da"],
                "cca": item["cca"],
                "total": total,
            }
        )
    return months


def _pension_start_date(emp_cd, separation_dt=None):
    if separation_dt:
        if hasattr(separation_dt, "date"):
            separation_dt = separation_dt.date()
        return separation_dt
    try:
        start_mth, start_yr = _resolve_pension_start(emp_cd)
        return date(int(start_yr), int(start_mth), 1)
    except SaloutTransferError:
        return None


def _wg_end_for_month(emp_cd, sal_yr, sal_mth):
    emp_key = _clip_emp(emp_cd)
    header = (
        FiPnThSalout.objects.filter(
            emp_cd=emp_key,
            sal_yr=sal_yr,
            sal_mth=sal_mth,
        ).first()
    )
    if header and header.wg_end_dt:
        return header.wg_end_dt

    conn = try_oracle_connection()
    if conn is None:
        return None
    cur = conn.cursor()
    try:
        cur.execute(
            """
            SELECT WG_END_DT FROM FINANCE.FI_PR_TH_SALOUT
            WHERE EMP_CD = :emp AND SAL_YR = :yr AND SAL_MTH = :mth
            """,
            {"emp": emp_key, "yr": sal_yr, "mth": sal_mth},
        )
        row = cur.fetchone()
        if row and row[0]:
            val = row[0]
            return val.date() if hasattr(val, "date") else val
    except Exception:
        return None
    finally:
        cur.close()
        conn.close()
    return None


def _mirror_pensioner_gratuity_emoluments(emp_cd):
    """Gratuity emoluments from MySQL FI_PN_MH_PENSIONER mirror (Oracle-processed)."""
    pen = FiPnMhPensioner.objects.filter(emp_cd=_clip_emp(emp_cd)).first()
    if not pen or pen.gratuity_emoluments is None:
        return None
    emoluments = float(pen.gratuity_emoluments)
    if emoluments <= 0:
        return None
    return {
        "emoluments": emoluments,
        "gratuity": float(pen.gratuity or 0),
    }


def _enrich_current_retiree_da(
    basic, da, cca, pension_start, emp_class, *, separation_dt=None
):
    """
    Current retirees: replace payroll DA with fi_pr_mh_calc_da rate on basic.
    """
    if not pension_start or basic <= 0:
        return da, cca
    if hasattr(pension_start, "date") and callable(pension_start.date):
        pension_start = pension_start.date()
    if int(pension_start.year) < HISTORICAL_GRATUITY_CUTOFF_YEAR:
        return da, cca
    ref = _da_reference_date(pension_start, separation_dt)
    return _flat_da_on_basic(basic, emp_class, ref), cca


def _compute_increment_month_da(basic, wg_end_dt, *, emp_class="III"):
    """DA for month ending day before pension start."""
    if not wg_end_dt or basic <= 0:
        return 0.0
    da_pct = lookup_ada_da_percent(wg_end_dt, emp_class)
    return float(
        (Decimal(str(basic)) * da_pct / Decimal("100")).quantize(Decimal("0.01"))
    )


def _last_pre_pension_month_emoluments(emp_cd, pension_start, months, *, emp_class="III"):
    """
    Emoluments for the salary month immediately before pension start.
    Uses actual payroll DA; for increment month applies ADA rate when PN salout
    only has basic (Oracle transfer behaviour).
    """
    if not months or not pension_start:
        return None

    pension_start = (
        pension_start.date()
        if hasattr(pension_start, "date") and callable(pension_start.date)
        else pension_start
    )
    pre_pension_end = pension_start - timedelta(days=1)

    target = None
    for month in reversed(months):
        wg_end = _wg_end_for_month(emp_cd, month["sal_yr"], month["sal_mth"])
        if wg_end == pre_pension_end:
            target = month
            break

    if target is None:
        target = months[-1]

    basic = float(target.get("basic") or 0)
    da = float(target.get("da") or 0)
    cca = float(target.get("cca") or 0)

    wg_end = _wg_end_for_month(emp_cd, target["sal_yr"], target["sal_mth"])
    payroll_da = float(target.get("da") or 0)
    if _is_historical_case(pension_start):
        if wg_end == pre_pension_end and basic > 0:
            ada_da = _compute_increment_month_da(basic, wg_end, emp_class=emp_class)
            da = payroll_da if payroll_da > 0 else ada_da
        elif da <= 0 and payroll_da > 0:
            da = payroll_da
    else:
        da = _flat_da_on_basic(basic, emp_class, pension_start)

    total = basic + da + cca
    if total <= 0:
        return None

    return {
        "emoluments": total,
        "basic": basic,
        "da": da,
        "cca": cca,
        "sal_mth": target["sal_mth"],
        "sal_yr": target["sal_yr"],
        "method": "last_pre_pension_payroll",
    }


def _oracle_pensioner_gratuity_emoluments(emp_cd):
    """Live Oracle GRATUITY_EMOLUMENTS when employee is already processed."""
    emp_key = _clip_emp(emp_cd)
    conn = get_oracle_connection()
    cur = conn.cursor()
    try:
        cur.execute(
            """
            SELECT GRATUITY_EMOLUMENTS, GRATUITY
            FROM FINANCE.FI_PN_MH_PENSIONER
            WHERE EMP_CD = :emp
            """,
            {"emp": emp_key},
        )
        row = cur.fetchone()
        if not row or row[0] is None:
            return None
        return {
            "emoluments": float(row[0]),
            "gratuity": float(row[1] or 0),
        }
    finally:
        cur.close()
        conn.close()


def _oracle_pn_td_last_month_emoluments(emp_cd, pension_start, *, emp_class="III"):
    """Last pre-pension month from live FI_PN_TD_SALOUT (read-only)."""
    if not pension_start:
        return None
    if hasattr(pension_start, "date"):
        pension_start = pension_start.date()
    pre_end = pension_start - timedelta(days=1)
    emp_key = _clip_emp(emp_cd)

    conn = get_oracle_connection()
    cur = conn.cursor()
    try:
        cur.execute(
            """
            SELECT SAL_YR, SAL_MTH, WG_END_DT
            FROM FINANCE.FI_PN_TH_SALOUT
            WHERE EMP_CD = :emp
            ORDER BY SAL_YR DESC, SAL_MTH DESC
            """,
            {"emp": emp_key},
        )
        target = None
        for sal_yr, sal_mth, wg_end in cur.fetchall():
            wg = wg_end.date() if wg_end and hasattr(wg_end, "date") else wg_end
            if wg == pre_end:
                target = (int(sal_yr), int(sal_mth))
                break
        if target is None:
            cur.execute(
                """
                SELECT SAL_YR, SAL_MTH FROM (
                    SELECT SAL_YR, SAL_MTH FROM FINANCE.FI_PN_TH_SALOUT
                    WHERE EMP_CD = :emp
                    ORDER BY SAL_YR DESC, SAL_MTH DESC
                ) WHERE ROWNUM = 1
                """,
                {"emp": emp_key},
            )
            row = cur.fetchone()
            if row:
                target = (int(row[0]), int(row[1]))

        if not target:
            return None

        sal_yr, sal_mth = target
        cur.execute(
            """
            SELECT EARNDEDN_CD,
                   NVL(ACT_EARNDEDN_AMT, 0) + NVL(ADJ_EARNDEDN_AMT, 0)
            FROM FINANCE.FI_PN_TD_SALOUT
            WHERE EMP_CD = :emp AND SAL_YR = :yr AND SAL_MTH = :mth
              AND EARNDEDN_CD IN ('001', '007', '111')
            """,
            {"emp": emp_key, "yr": sal_yr, "mth": sal_mth},
        )
        basic = da = cca = 0.0
        for code, net in cur.fetchall():
            code = str(code or "").strip()
            val = float(net or 0)
            if code == "001":
                basic = val
            elif code == "007":
                da = val
            elif code == "111":
                cca = val

        if not _is_historical_case(pension_start) and basic > 0:
            da = _flat_da_on_basic(basic, emp_class, pension_start)

        total = basic + da + cca
        if total <= 0:
            return None
        return {
            "emoluments": total,
            "basic": basic,
            "da": da,
            "cca": cca,
            "sal_mth": sal_mth,
            "sal_yr": sal_yr,
            "method": "oracle_pn_td_salout",
        }
    finally:
        cur.close()
        conn.close()


def _mysql_pn_td_last_month_emoluments(
    emp_cd, pension_start, *, emp_class="III", separation_dt=None
):
    """Last pre-pension month from local fi_pn_td_salout."""
    if not pension_start:
        return None
    if hasattr(pension_start, "date"):
        pension_start = pension_start.date()
    pre_end = pension_start - timedelta(days=1)
    emp_key = _clip_emp(emp_cd)

    headers = list(
        FiPnThSalout.objects.filter(emp_cd=emp_key)
        .exclude(sal_yr__gt=pension_start.year)
        .exclude(sal_yr=pension_start.year, sal_mth__gte=pension_start.month)
        .order_by("-sal_yr", "-sal_mth")
    )
    if not headers:
        return None

    target = None
    for header in headers:
        if header.wg_end_dt == pre_end:
            target = header
            break
    if target is None:
        target = headers[0]

    rows = FiPnTdSalout.objects.filter(
        emp_cd=emp_key,
        sal_yr=target.sal_yr,
        sal_mth=target.sal_mth,
        earndedn_cd__in=["001", "007", "111"],
    )
    basic = da = cca = 0.0
    for row in rows:
        net = _net_line_amount(row)
        code = str(row.earndedn_cd or "").strip()
        if code == "001":
            basic = net
        elif code == "007":
            da = net
        elif code == "111":
            cca = net

    if basic <= 0:
        basic = float(target.basic_rate or 0)

    if da <= 0 and basic > 0 and target.wg_end_dt == pre_end:
        if _is_historical_case(pension_start):
            da = _compute_increment_month_da(basic, target.wg_end_dt, emp_class=emp_class)
        else:
            da = _flat_da_on_basic(basic, emp_class, pension_start)

    da, cca = _enrich_current_retiree_da(
        basic, da, cca, pension_start, emp_class, separation_dt=separation_dt
    )

    total = basic + da + cca
    if total <= 0:
        return None
    return {
        "emoluments": total,
        "basic": basic,
        "da": da,
        "cca": cca,
        "sal_mth": target.sal_mth,
        "sal_yr": target.sal_yr,
        "method": "mysql_pn_td_salout",
    }


def _gratuity_emoluments_basic_plus_increment_da(
    emp_cd, pension_basic, pension_start, *, emp_class="III"
):
    """Pension basic + ADA on increment month (Oracle PN salout transfer pattern)."""
    if not pension_start or pension_basic <= 0:
        return None
    if hasattr(pension_start, "date"):
        pension_start = pension_start.date()
    pre_end = pension_start - timedelta(days=1)

    headers = list(
        FiPnThSalout.objects.filter(emp_cd=_clip_emp(emp_cd))
        .exclude(sal_yr__gt=pension_start.year)
        .exclude(sal_yr=pension_start.year, sal_mth__gte=pension_start.month)
        .order_by("-sal_yr", "-sal_mth")
    )
    target = None
    for header in headers:
        wg = header.wg_end_dt
        if wg == pre_end:
            target = header
            break
    if target is None and headers:
        target = headers[0]

    basic = float(pension_basic)
    if _is_historical_case(pension_start):
        da = 0.0
        if target and target.wg_end_dt == pre_end:
            da = _compute_increment_month_da(
                basic, target.wg_end_dt, emp_class=emp_class
            )
    else:
        da = _flat_da_on_basic(basic, emp_class, pension_start)

    total = basic + da
    if total <= basic:
        return None
    return {
        "emoluments": total,
        "basic": basic,
        "da": da,
        "cca": 0.0,
        "method": "basic_plus_increment_ada",
    }


def _is_historical_case(pension_start, separation_dt=None):
    ref = separation_dt or pension_start
    if not ref:
        return False
    if hasattr(ref, "date"):
        ref = ref.date()
    return int(ref.year) < HISTORICAL_GRATUITY_CUTOFF_YEAR


def _is_basic_only_emoluments(emoluments, pension_basic):
    """Reject mirror rows that store last basic without DA."""
    basic = float(pension_basic or 0)
    em = float(emoluments or 0)
    if basic <= 0 or em <= 0:
        return False
    return em <= basic * 1.02


def resolve_gratuity_emoluments(
    emp_cd,
    emp_class,
    pension_basic,
    *,
    separation_dt=None,
):
    """
    Returns (emoluments, source_label, detail_dict).

    Current retirees: last drawn basic from salout + fixed class DA% (not payroll DA).
    Historical retirees: actual payroll DA / ADA chart from salout mirrors.
    """
    pension_basic = float(pension_basic or 0)
    pension_start = _pension_start_date(emp_cd, separation_dt)
    historical = _is_historical_case(pension_start, separation_dt)

    if oracle_reads_enabled():
        try:
            pn_td = _oracle_pn_td_last_month_emoluments(
                emp_cd, pension_start, emp_class=emp_class
            )
            pn_td = _finalize_emoluments_detail(
                pn_td, emp_class, pension_start, separation_dt=separation_dt
            )
            if pn_td and pn_td["emoluments"] > 0:
                return (
                    float(pn_td["emoluments"]),
                    "oracle_pn_td_salout",
                    pn_td,
                )
        except Exception:
            pass

        if historical:
            try:
                oracle_pen = _oracle_pensioner_gratuity_emoluments(emp_cd)
                if oracle_pen and oracle_pen["emoluments"] > 0:
                    if not _is_basic_only_emoluments(
                        oracle_pen["emoluments"], pension_basic
                    ):
                        return (
                            oracle_pen["emoluments"],
                            "oracle_pensioner",
                            oracle_pen,
                        )
            except Exception:
                pass

    if historical:
        mirror_pen = _mirror_pensioner_gratuity_emoluments(emp_cd)
        if mirror_pen and not _is_basic_only_emoluments(
            mirror_pen["emoluments"], pension_basic
        ):
            return (
                mirror_pen["emoluments"],
                "mysql_pensioner",
                mirror_pen,
            )

    local_pn = _mysql_pn_td_last_month_emoluments(
        emp_cd, pension_start, emp_class=emp_class, separation_dt=separation_dt
    )
    local_pn = _finalize_emoluments_detail(
        local_pn, emp_class, pension_start, separation_dt=separation_dt
    )
    if local_pn and local_pn["emoluments"] > 0:
        return (
            float(local_pn["emoluments"]),
            "pn_td_salout",
            local_pn,
        )

    increment = _gratuity_emoluments_basic_plus_increment_da(
        emp_cd, pension_basic, pension_start, emp_class=emp_class
    )
    increment = _finalize_emoluments_detail(
        increment, emp_class, pension_start, separation_dt=separation_dt
    )
    if increment and increment["emoluments"] > pension_basic:
        return (
            float(increment["emoluments"]),
            "basic_plus_increment_ada",
            increment,
        )

    da_pct = float(flat_class_da_percent(emp_class, _da_reference_date(pension_start, separation_dt)))
    emoluments = pension_basic * (1 + da_pct / 100)
    return (
        emoluments,
        "current_da_percent",
        {"da_percent": da_pct, "basic": pension_basic},
    )


DEATH_SEPARATION_TYPES = frozenset({"DT", "DEATH", "D"})


def is_death_separation(separation_type):
    """Death / demise separation codes (Oracle dashboard uses DT)."""
    return str(separation_type or "").strip().upper() in DEATH_SEPARATION_TYPES


def uses_retirement_gratuity_comparison(gratuity_option, *, separation_type=None):
    """
    Oracle FPROC_FIRST_PENSION_PROCESS compares Opt-I vs Opt-II only when
    proposal GRATUITY_OPTION is 0 or 1. Death (2) uses FFUNC_DCR_GRATUITY directly.
    """
    if is_death_separation(separation_type):
        return False
    return normalize_gratuity_option(gratuity_option) in (0, 1)


def gratuity_qualifying_years(tccs_years, tccs_months, tccs_days=0):
    """
    TCCS qualifying years for Opt-I (FFUNC_DCR_GRATUITY option 0):
    months > 6 → years + 1; months < 6 → years;
    month = 6 and days > 0 → years + 1.
    """
    years = int(tccs_years or 0)
    months = int(tccs_months or 0)
    days = int(tccs_days or 0)
    if months > 6 or (months == 6 and days > 0):
        years += 1
    return years


def round_tqs_years_oracle(tqs_years, tqs_months, tqs_days=0):
    """
    Oracle FFunc_TQS_Round_2 fractional TQS rounding (pension, death gratuity, etc.):
    0–2 months → whole years; 3–8 months → +0.5; 9–11 months → +1.
    """
    years = int(tqs_years or 0)
    months = int(tqs_months or 0)
    if months < 3:
        return float(years)
    if months < 9:
        return years + 0.5
    return float(years + 1)


def round_tqs_years_for_gratuity_opt_ii(tqs_years, tqs_months, tqs_days=0):
    """
    Oracle live Opt-II (FFUNC_DCR_GRATUITY option 1) qualifying TQS multiplier:
    months < 6 → whole years only; months >= 6 → years + 1.
    """
    years = int(tqs_years or 0)
    months = int(tqs_months or 0)
    if months < 6:
        return float(years)
    return float(years + 1)


def _rounded_tqs_service_end(joining_date, rounded_tqs):
    """Calendar end date for rounded TQS (e.g. 32.5 → join + 32y 6m)."""
    if not joining_date:
        return None
    join = (
        joining_date.date()
        if hasattr(joining_date, "date") and callable(joining_date.date)
        else joining_date
    )
    years = int(rounded_tqs)
    extra_months = 6 if float(rounded_tqs) - years >= 0.25 else 0
    return join + relativedelta(years=years, months=extra_months)


def apply_vr_tqs_bonus(
    rounded_tqs,
    separation_type,
    *,
    joining_date=None,
    exp_retirement_date=None,
    round_fn=None,
):
    """
    VR: add 5 qualifying years (max 33). If enhanced service end exceeds
    expected retirement date, use TQS from joining to EXP_RET_DT instead.
    """
    if round_fn is None:
        round_fn = round_tqs_years_oracle

    if str(separation_type or "").strip().upper() != "VR":
        return float(rounded_tqs)

    tqs = float(rounded_tqs)
    if tqs > 33:
        tqs = 33.0
    elif tqs + 5 > 33:
        tqs = 33.0
    else:
        tqs = tqs + 5.0

    if joining_date and exp_retirement_date:
        exp_ret = (
            exp_retirement_date.date()
            if hasattr(exp_retirement_date, "date")
            and callable(exp_retirement_date.date)
            else exp_retirement_date
        )
        enhanced_end = _rounded_tqs_service_end(joining_date, tqs)
        if enhanced_end and enhanced_end > exp_ret:
            join = (
                joining_date.date()
                if hasattr(joining_date, "date") and callable(joining_date.date)
                else joining_date
            )
            capped = relativedelta(exp_ret, join)
            tqs = round_fn(capped.years, capped.months, capped.days)
            if tqs > 33:
                tqs = 33.0

    return tqs


def qualifying_tqs_for_gratuity_opt_ii(
    tqs_years,
    tqs_months,
    tqs_days=0,
    *,
    separation_type=None,
    joining_date=None,
    exp_retirement_date=None,
):
    """TQS for Opt-II: Oracle live round, VR weightage, cap at 33."""
    tqs = round_tqs_years_for_gratuity_opt_ii(tqs_years, tqs_months, tqs_days)
    tqs = apply_vr_tqs_bonus(
        tqs,
        separation_type,
        joining_date=joining_date,
        exp_retirement_date=exp_retirement_date,
        round_fn=round_tqs_years_for_gratuity_opt_ii,
    )
    if tqs > 33:
        tqs = 33.0
    return tqs


def qualifying_tqs_for_death_gratuity(tqs_years, tqs_months, tqs_days=0):
    """Death gratuity: FFunc_TQS_Round_2('N') then cap at 33 years."""
    tqs = round_tqs_years_oracle(tqs_years, tqs_months, tqs_days)
    if tqs > 33:
        tqs = 33.0
    return tqs


def _last_drawn_basic_only(emp_cd):
    """Last salout basic (map 101/103) — death gratuity pre-inception emoluments."""
    emp_cd = _clip_emp(emp_cd)
    rows = (
        FiPnTdSalout.objects.filter(emp_cd=emp_cd, earndedn_cd="001")
        .order_by("-sal_yr", "-sal_mth")
    )
    for row in rows:
        net = _net_line_amount(row)
        if net > 0:
            return float(net)

    if oracle_reads_enabled():
        try:
            conn = get_oracle_connection()
            cur = conn.cursor()
            cur.execute(
                """
                SELECT NVL(act_earndedn_amt, 0)
                  FROM FINANCE.FI_PN_TD_SALOUT A
                 WHERE A.EMP_CD = :emp
                   AND A.EARNDEDN_CD = (
                           SELECT EARNDEDN_CD
                             FROM FINANCE.FI_PR_MH_ERNDEDNMAP
                            WHERE MAP_CD IN (101, 103)
                              AND ROWNUM = 1
                       )
                   AND A.SAL_YR = (
                           SELECT MAX(SAL_YR)
                             FROM FINANCE.FI_PN_TD_SALOUT
                            WHERE EMP_CD = :emp
                       )
                   AND A.SAL_MTH = (
                           SELECT MAX(SAL_MTH)
                             FROM FINANCE.FI_PN_TD_SALOUT
                            WHERE EMP_CD = :emp
                              AND SAL_YR = (
                                      SELECT MAX(SAL_YR)
                                        FROM FINANCE.FI_PN_TD_SALOUT
                                       WHERE EMP_CD = :emp
                                  )
                       )
                """,
                {"emp": emp_cd},
            )
            row = cur.fetchone()
            cur.close()
            conn.close()
            if row and float(row[0] or 0) > 0:
                return float(row[0])
        except Exception:
            pass
    return 0.0


def normalize_gratuity_option(value):
    """
    Oracle FFUNC_DCR_GRATUITY codes: 0 = Opt-I, 1 = Opt-II, 2 = Death.
    Proposal form stores 0/1/2. Legacy UI used 3 for death gratuity only.
    """
    if value is None:
        return 0
    text = str(value).strip()
    if not text:
        return 0
    if text == "3":
        return 2
    try:
        n = int(text)
    except ValueError:
        return 0
    if n in (0, 1, 2):
        return n
    return 0


GRATUITY_OPTION_LABELS = {
    0: "Retirement Gratuity Opt-I (Gratuity Act 1972)",
    1: "Retirement Gratuity Opt-II (Living General Pensioners)",
    2: "Death Gratuity Opt-II",
}


def _gratuity_option_formula(
    *,
    emoluments,
    gratuity_option,
    separation_dt,
    tccs_years,
    tccs_months,
    tccs_days,
    tqs_years,
    tqs_months,
    tqs_days,
    emp_cd=None,
    emp_class=None,
    separation_type=None,
    joining_date=None,
    exp_retirement_date=None,
):
    """Formula amount and metadata for one gratuity option (no cap applied)."""
    from .gratuity_chart_service import lookup_death_multiple_factor

    option = normalize_gratuity_option(gratuity_option)
    emoluments = float(emoluments or 0)
    emoluments_used = emoluments
    service_years_used = None
    formula_amount = 0.0

    if option == 0:
        tccs = gratuity_qualifying_years(tccs_years, tccs_months, tccs_days)
        service_years_used = tccs
        formula_amount = (emoluments * 15 * tccs) / 26

    elif option == 1:
        from .gratuity_chart_service import lookup_maxadm_gratuity

        tqs = qualifying_tqs_for_gratuity_opt_ii(
            tqs_years,
            tqs_months,
            tqs_days,
            separation_type=separation_type,
            joining_date=joining_date,
            exp_retirement_date=exp_retirement_date,
        )
        service_years_used = tqs
        limits = lookup_maxadm_gratuity(separation_dt, gratuity_type=1)
        max_emolument = (limits or {}).get("max_emolument") or 0
        emoluments_used = emoluments
        if max_emolument > 0 and emoluments_used > max_emolument:
            emoluments_used = max_emolument
        formula_amount = (emoluments_used * tqs) / 2

    else:
        from .gratuity_chart_service import lookup_death_gratuity_chart

        chart = lookup_death_gratuity_chart(separation_dt, gratuity_type=2)
        inception = (chart or {}).get("inception_dt")
        sep = separation_dt
        if hasattr(sep, "date"):
            sep = sep.date()
        if inception and sep and sep >= inception:
            emoluments_used = emoluments
        elif emp_cd:
            emoluments_used = _last_drawn_basic_only(emp_cd) or emoluments
        else:
            emoluments_used = emoluments

        tqs = qualifying_tqs_for_death_gratuity(tqs_years, tqs_months, tqs_days)
        service_years_used = tqs
        multi_factor = lookup_death_multiple_factor(tqs, gratuity_type=2)
        if tqs > 20:
            multi_factor = float(tqs)
        elif multi_factor is None:
            multi_factor = float(tqs)
        formula_amount = emoluments_used * float(multi_factor)

    return {
        "formula_amount": float(formula_amount),
        "gratuity_option": option,
        "gratuity_option_label": GRATUITY_OPTION_LABELS.get(option, ""),
        "gratuity_qualifying_years": service_years_used,
        "gratuity_emoluments_used": float(emoluments_used),
    }


def _apply_gratuity_option_cap(formula_amount, gratuity_option, separation_dt):
    """Apply cap rules for the given option to a formula amount."""
    from ..pension_calculation import highest_side_round
    from .gratuity_chart_service import (
        DEFAULT_AFTER_INCEPTION_CAP,
        apply_chart_cap,
        lookup_death_gratuity_chart,
        lookup_maxadm_gratuity,
    )

    option = normalize_gratuity_option(gratuity_option)
    formula_amount = float(formula_amount or 0)
    payable = formula_amount

    if option == 0:
        chart = lookup_death_gratuity_chart(separation_dt, gratuity_type=0)
        payable = apply_chart_cap(payable, separation_dt, chart)
        if chart is None and payable > DEFAULT_AFTER_INCEPTION_CAP:
            payable = float(DEFAULT_AFTER_INCEPTION_CAP)

    elif option == 1:
        limits = lookup_maxadm_gratuity(separation_dt, gratuity_type=1)
        max_adm = (limits or {}).get("max_adm_gratuity") or DEFAULT_AFTER_INCEPTION_CAP
        if max_adm > 0 and payable > max_adm:
            payable = max_adm

    else:
        chart = lookup_death_gratuity_chart(separation_dt, gratuity_type=2)
        payable = apply_chart_cap(payable, separation_dt, chart)
        if chart is None and payable > DEFAULT_AFTER_INCEPTION_CAP:
            payable = float(DEFAULT_AFTER_INCEPTION_CAP)

    capped = payable < formula_amount
    return float(highest_side_round(payable)), capped


def calculate_ffunc_dcr_gratuity(
    *,
    emoluments,
    gratuity_option,
    separation_dt,
    tccs_years,
    tccs_months,
    tccs_days,
    tqs_years,
    tqs_months,
    tqs_days,
    emp_cd=None,
    emp_class=None,
    separation_type=None,
    joining_date=None,
    exp_retirement_date=None,
):
    """
    Port of Oracle FFUNC_DCR_GRATUITY — single option with formula + cap.
    """
    from ..pension_calculation import highest_side_round

    breakdown = _gratuity_option_formula(
        emoluments=emoluments,
        gratuity_option=gratuity_option,
        separation_dt=separation_dt,
        tccs_years=tccs_years,
        tccs_months=tccs_months,
        tccs_days=tccs_days,
        tqs_years=tqs_years,
        tqs_months=tqs_months,
        tqs_days=tqs_days,
        emp_cd=emp_cd,
        emp_class=emp_class,
        separation_type=separation_type,
        joining_date=joining_date,
        exp_retirement_date=exp_retirement_date,
    )
    formula_amount = float(highest_side_round(breakdown["formula_amount"]))
    payable, capped = _apply_gratuity_option_cap(
        formula_amount,
        breakdown["gratuity_option"],
        separation_dt,
    )

    return {
        "gratuity_amount": payable,
        "formula_amount": formula_amount,
        "gratuity_capped": capped,
        "gratuity_option": breakdown["gratuity_option"],
        "gratuity_option_label": breakdown["gratuity_option_label"],
        "gratuity_qualifying_years": breakdown["gratuity_qualifying_years"],
        "gratuity_emoluments_used": breakdown["gratuity_emoluments_used"],
    }


def calculate_gratuity_payable(
    *,
    emoluments,
    separation_dt,
    tccs_years,
    tccs_months,
    tccs_days,
    tqs_years,
    tqs_months,
    tqs_days,
    emp_cd=None,
    emp_class=None,
    gratuity_option=None,
    separation_type=None,
    joining_date=None,
    exp_retirement_date=None,
):
    """
    Compute Opt-I, Opt-II, and Death gratuity (FFUNC_DCR_GRATUITY options 0/1/2).

    Living retirees with proposal option 0 or 1: payable = higher of Opt-I vs Opt-II
    (Oracle FPROC_FIRST_PENSION_PROCESS). Death / option 2: payable = Death gratuity.
    """
    from ..pension_calculation import highest_side_round

    common = dict(
        emoluments=emoluments,
        separation_dt=separation_dt,
        tccs_years=tccs_years,
        tccs_months=tccs_months,
        tccs_days=tccs_days,
        tqs_years=tqs_years,
        tqs_months=tqs_months,
        tqs_days=tqs_days,
        emp_cd=emp_cd,
        emp_class=emp_class,
        separation_type=separation_type,
        joining_date=joining_date,
        exp_retirement_date=exp_retirement_date,
    )

    opt_i = _gratuity_option_formula(**common, gratuity_option=0)
    opt_ii = _gratuity_option_formula(**common, gratuity_option=1)
    death = _gratuity_option_formula(**common, gratuity_option=2)

    opt_i_amount = float(highest_side_round(opt_i["formula_amount"]))
    opt_ii_amount = float(highest_side_round(opt_ii["formula_amount"]))
    death_amount = float(highest_side_round(death["formula_amount"]))

    proposal_option = normalize_gratuity_option(gratuity_option)
    use_comparison = uses_retirement_gratuity_comparison(
        proposal_option, separation_type=separation_type
    )

    if not use_comparison or proposal_option == 2:
        winning_option = 2
        payable, capped = _apply_gratuity_option_cap(
            death_amount, 2, separation_dt
        )
        payable_basis = "death"
    elif opt_i_amount >= opt_ii_amount:
        winning_option = 0
        payable, capped = _apply_gratuity_option_cap(
            opt_i_amount, 0, separation_dt
        )
        payable_basis = "opt_i" if opt_i_amount > opt_ii_amount else "equal"
    else:
        winning_option = 1
        payable, capped = _apply_gratuity_option_cap(
            opt_ii_amount, 1, separation_dt
        )
        payable_basis = "opt_ii"

    return {
        "gratuity_amount": payable,
        "opt_i_gratuity_amount": opt_i_amount,
        "opt_ii_gratuity_amount": opt_ii_amount,
        "death_gratuity_amount": death_amount,
        "dcr_gratuity_amount": opt_i_amount,
        "option_gratuity_amount": opt_ii_amount,
        "dcr_gratuity_formula_amount": opt_i_amount,
        "option_gratuity_formula_amount": opt_ii_amount,
        "death_gratuity_formula_amount": death_amount,
        "gratuity_payable_basis": payable_basis,
        "gratuity_winning_option": winning_option,
        "gratuity_capped": capped,
        "gratuity_option": proposal_option,
        "gratuity_option_label": GRATUITY_OPTION_LABELS.get(proposal_option, ""),
        "dcr_gratuity_option_label": GRATUITY_OPTION_LABELS[0],
        "opt_ii_gratuity_option_label": GRATUITY_OPTION_LABELS[1],
        "death_gratuity_option_label": GRATUITY_OPTION_LABELS[2],
        "gratuity_qualifying_years": opt_ii["gratuity_qualifying_years"],
        "dcr_gratuity_qualifying_years": opt_i["gratuity_qualifying_years"],
        "opt_ii_gratuity_qualifying_years": opt_ii["gratuity_qualifying_years"],
        "death_gratuity_qualifying_years": death["gratuity_qualifying_years"],
        "gratuity_emoluments_used": opt_ii["gratuity_emoluments_used"],
        "dcr_gratuity_emoluments_used": opt_i["gratuity_emoluments_used"],
        "opt_ii_gratuity_emoluments_used": opt_ii["gratuity_emoluments_used"],
        "death_gratuity_emoluments_used": death["gratuity_emoluments_used"],
        "is_death_gratuity_case": not use_comparison or proposal_option == 2,
    }


def calculate_dcr_gratuity_breakdown(
    emoluments,
    qualifying_years,
    *,
    separation_dt=None,
    gratuity_option=0,
    tqs_years=0,
    tqs_months=0,
    tqs_days=0,
    emp_cd=None,
    emp_class=None,
):
    """Backward-compatible wrapper — defaults to Opt-I (TCCS × 15/26)."""
    result = calculate_ffunc_dcr_gratuity(
        emoluments=emoluments,
        gratuity_option=gratuity_option,
        separation_dt=separation_dt,
        tccs_years=qualifying_years,
        tccs_months=0,
        tccs_days=0,
        tqs_years=tqs_years or qualifying_years,
        tqs_months=tqs_months,
        tqs_days=tqs_days,
        emp_cd=emp_cd,
        emp_class=emp_class,
    )
    result["dcr_gratuity_amount"] = result["formula_amount"]
    return result


def calculate_dcr_gratuity(
    emoluments,
    qualifying_years,
    *,
    separation_dt=None,
    gratuity_option=0,
    **kwargs,
):
    """Payable gratuity after FFUNC_DCR_GRATUITY rules."""
    return calculate_dcr_gratuity_breakdown(
        emoluments,
        qualifying_years,
        separation_dt=separation_dt,
        gratuity_option=gratuity_option,
        **kwargs,
    )["gratuity_amount"]
