"""
Death / DCR gratuity — port of FI_PN_MH_First_FPension.fmb FFUNC_DCR_GRATUITY.

Follows form logic (not chart factor alone for TQS 20–33):
  option 0: (E×15×TCCS)/26 + ceilings
  option 1: (E×min(TQS,33))/2 + max-adm tables
  option 2 (death / First FP): E × multi_factor + death ceilings,
    with multi_factor rebuilt from TQS Y/M/D when 20 ≤ TQS < 33.
"""

from __future__ import annotations

import calendar
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP
from typing import Optional

from django.db import connection


class DcrGratuityError(Exception):
    pass


def _clip(value, max_len=None, default=""):
    if value is None:
        return default
    text = str(value).strip()
    if not text:
        return default
    if max_len is not None:
        return text[:max_len]
    return text


def _emp_key(emp_cd):
    text = _clip(emp_cd, 5)
    if text.isdigit() and len(text) < 5:
        return text.zfill(5)
    return text


def _as_date(value):
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    text = str(value).strip()[:10]
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    return None


def _num(value):
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _round2(value) -> float:
    return float(
        Decimal(str(value or 0)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    )


def _fetchone(sql, params=None):
    with connection.cursor() as cur:
        cur.execute(sql, params or [])
        row = cur.fetchone()
        if not row:
            return None
        cols = [d[0].lower() for d in cur.description]
        return dict(zip(cols, row))


def _fetchall(sql, params=None):
    with connection.cursor() as cur:
        cur.execute(sql, params or [])
        cols = [d[0].lower() for d in cur.description]
        return [dict(zip(cols, r)) for r in cur.fetchall()]


def _table_exists(name: str) -> bool:
    row = _fetchone("SHOW TABLES LIKE %s", [name])
    return bool(row)


# ---------------------------------------------------------------------------
# Oracle-ish date helpers
# ---------------------------------------------------------------------------


def months_between(end: date, start: date) -> float:
    """Approximate Oracle MONTHS_BETWEEN(end, start)."""
    if not end or not start:
        return 0.0
    return (
        (end.year - start.year) * 12
        + (end.month - start.month)
        + (end.day - start.day) / 31.0
    )


def add_months(d: date, months: int) -> date:
    months = int(months)
    y = d.year + (d.month - 1 + months) // 12
    m = (d.month - 1 + months) % 12 + 1
    last = calendar.monthrange(y, m)[1]
    return date(y, m, min(d.day, last))


def yr_month_day(start: date, end: date):
    """
    FPROC_YR_MONTH_DAY: completed years / months / leftover days
    between start and end (end is adjusted TQS end date).
    """
    total_months = int(months_between(end, start) // 1)  # TRUNC
    yrs = total_months // 12
    mon = total_months % 12
    mid = add_months(start, total_months)
    days = (end - mid).days
    return int(yrs), int(mon), int(days)


# ---------------------------------------------------------------------------
# TQS (FFunc_TQS_Round_2 with VC_DCR='N' → TQS years)
# ---------------------------------------------------------------------------


@dataclass
class TqsResult:
    tqs: float  # rounded years
    tccs: float  # rounded years
    pos_years: float
    tqs_yr: int
    tqs_month: int
    tqs_days: int
    join_dt: Optional[date]
    separation_dt: Optional[date]


def _sum_attend(emp: str, attend_desc: str) -> float:
    """Sum leave days for attend type (NPL / D-NON). 0 if leave tables missing."""
    if not _table_exists("fi_la_th_lvappl") or not _table_exists("fi_la_mh_attendtype"):
        return 0.0
    row = _fetchone(
        """
        SELECT COALESCE(SUM(L.lv_days), 0) AS days
        FROM fi_la_th_lvappl L
        JOIN fi_la_mh_attendtype A ON A.attend_cd = L.attend_cd
        WHERE L.emp_cd = %s AND A.attend_desc = %s
        """,
        [emp, attend_desc],
    )
    return float((row or {}).get("days") or 0)


def _sum_nopay_by_year(emp: str) -> dict:
    if not _table_exists("fi_la_th_lvappl") or not _table_exists("fi_la_mh_attendtype"):
        return {}
    rows = _fetchall(
        """
        SELECT YEAR(L.wef_dt) AS yr, COALESCE(SUM(L.lv_days), 0) AS days
        FROM fi_la_th_lvappl L
        JOIN fi_la_mh_attendtype A ON A.attend_cd = L.attend_cd
        WHERE L.emp_cd = %s AND A.attend_desc = 'NPL'
        GROUP BY YEAR(L.wef_dt)
        """,
        [emp],
    )
    return {int(r["yr"]): float(r["days"] or 0) for r in rows if r.get("yr") is not None}


def _sum_suspension_days(emp: str) -> float:
    if not _table_exists("fi_es_th_susp"):
        return 0.0
    # Withdrawal table optional
    if _table_exists("fi_es_th_suspwithdl"):
        row = _fetchone(
            """
            SELECT COALESCE(SUM(
                DATEDIFF(COALESCE(W.w_t_dt, CURDATE()), S.wef_dt)
            ), 0) AS days
            FROM fi_es_th_susp S
            LEFT JOIN fi_es_th_suspwithdl W ON S.ord_no = W.ord_no AND S.emp_cd = W.emp_cd
            WHERE S.emp_cd = %s
            """,
            [emp],
        )
    else:
        row = _fetchone(
            """
            SELECT COALESCE(SUM(DATEDIFF(CURDATE(), S.wef_dt)), 0) AS days
            FROM fi_es_th_susp S
            WHERE S.emp_cd = %s
            """,
            [emp],
        )
    return float((row or {}).get("days") or 0)


def _round_tqs_months_to_years(tqs_months: float) -> float:
    """
    Oracle FFunc_TQS_Round_2 remainder-on-12 rules (TQS still in months).

    rem < 3:         floor years
    3 < rem < 9:     floor + 0.5
    9 < rem < 12:    floor + 1
    rem == 3 or 9:   not rewritten in form (fall-through); treat as floor / +0.5
                    → match half-year intent: rem<=3 floor, rem<9 half, else full year
    """
    rem = tqs_months % 12
    base = int(tqs_months // 12)
    if rem < 3 or abs(rem - 0) < 1e-9:
        # rem=0 falls under rem < 3 in PL/SQL
        return float(base)
    if rem > 3 and rem < 9:
        return float(base) + 0.5
    if rem > 9 and rem < 12:
        return float(base + 1)
    # rem exactly 3 or 9 (unhandled in Oracle): use multi-factor spirit
    if rem >= 9:
        return float(base + 1)
    if rem > 3:
        return float(base) + 0.5
    return float(base)


def compute_tqs(emp_cd) -> TqsResult:
    """Port of FFunc_TQS_Round_2(emp, 'N') plus GLOBAL TQS Y/M/D."""
    emp = _emp_key(emp_cd)
    adm = _fetchone(
        """
        SELECT JOIN_DT, SEPARATION_DT, SEPARATION_TYPE, EXP_RET_DT
        FROM fi_xx_mh_emp_adm
        WHERE EMP_CD = %s
        LIMIT 1
        """,
        [emp],
    ) or {}
    per = _fetchone(
        "SELECT BIRTH_DT FROM fi_xx_mh_emp_per WHERE EMP_CD = %s LIMIT 1",
        [emp],
    ) or {}

    join_dt = _as_date(adm.get("join_dt"))
    sep_dt = _as_date(adm.get("separation_dt")) or _as_date(adm.get("exp_ret_dt"))
    dob = _as_date(per.get("birth_dt"))

    if not join_dt or not sep_dt:
        raise DcrGratuityError(
            f"Join / separation date not available for {emp} (required for TQS)"
        )

    boy_days = 0.0
    if dob:
        boy18 = add_months(dob, 18 * 12)
        if join_dt < boy18:
            boy_days = float((boy18 - join_dt).days)

    dies_non = _sum_attend(emp, "D-NON")
    susp = _sum_suspension_days(emp)
    days_to_subtract = dies_non + boy_days + susp

    pos_months = round(months_between(sep_dt, join_dt), 2)
    pos_years = round(pos_months / 12.0, 2)

    # TCCS path: subtract dies-non/boy/susp from separation, then NPL rules
    adj_sep_tccs = sep_dt - timedelta(days=int(round(days_to_subtract)))
    tccs_months = round(months_between(adj_sep_tccs, join_dt), 2)

    nopay_years = _sum_nopay_by_year(emp)
    days_to_sub = 0.0
    for _yr, nopay in nopay_years.items():
        if nopay >= 240:
            tccs_months -= 12
        else:
            days_to_sub += nopay

    # TQS end date after all day subtractions
    total_day_sub = days_to_subtract + days_to_sub
    tqs_end = sep_dt - timedelta(days=int(round(total_day_sub)))
    tqs_months = round(months_between(tqs_end, join_dt), 2)

    tqs_yr, tqs_month, tqs_days = yr_month_day(join_dt, tqs_end)

    tccs_years = round(tccs_months / 12.0, 2)
    tqs_years = _round_tqs_months_to_years(tqs_months)

    return TqsResult(
        tqs=float(tqs_years),
        tccs=float(tccs_years),
        pos_years=float(pos_years),
        tqs_yr=tqs_yr,
        tqs_month=tqs_month,
        tqs_days=tqs_days,
        join_dt=join_dt,
        separation_dt=sep_dt,
    )


# ---------------------------------------------------------------------------
# Emoluments (FFunc_Avg_Basic for gratuity / last month Basic+ADA)
# ---------------------------------------------------------------------------


def _map_earn_cd(map_cd: int) -> Optional[str]:
    row = _fetchone(
        """
        SELECT EARNDEDN_CD FROM fi_pr_mh_erndednmap
        WHERE MAP_CD = %s LIMIT 1
        """,
        [map_cd],
    )
    if row and row.get("earndedn_cd") is not None:
        return str(row["earndedn_cd"]).strip()
    defaults = {101: "001", 103: "003", 105: "005", 107: "007", 111: "011"}
    return defaults.get(int(map_cd))


def _last_sal_ym(emp: str):
    row = _fetchone(
        """
        SELECT SAL_YR, SAL_MTH
        FROM fi_pn_td_salout
        WHERE EMP_CD = %s
        ORDER BY SAL_YR DESC, SAL_MTH DESC
        LIMIT 1
        """,
        [emp],
    )
    if not row:
        row = _fetchone(
            """
            SELECT SAL_YR, SAL_MTH
            FROM fi_pr_td_salout
            WHERE EMP_CD = %s
            ORDER BY SAL_YR DESC, SAL_MTH DESC
            LIMIT 1
            """,
            [emp],
        )
    if not row:
        return None, None
    return int(row["sal_yr"]), int(row["sal_mth"])


def _salout_rate(emp: str, earn_cd: str, yr: int, mth: int, use_act: bool = False) -> float:
    col = "ACT_EARNDEDN_AMT" if use_act else "RATE"
    for table in ("fi_pn_td_salout", "fi_pr_td_salout"):
        row = _fetchone(
            f"""
            SELECT COALESCE({col}, 0) AS amt
            FROM {table}
            WHERE EMP_CD = %s AND EARNDEDN_CD = %s
              AND SAL_YR = %s AND SAL_MTH = %s
            LIMIT 1
            """,
            [emp, earn_cd, yr, mth],
        )
        if row is not None:
            return float(row.get("amt") or 0)
    return 0.0


def _last_month_component(emp: str, map_cd: int, use_act: bool = False) -> float:
    """FFunc_Sum_alowance one-month branch for gratuity (incentive='N')."""
    earn_cd = _map_earn_cd(map_cd)
    if not earn_cd:
        return 0.0
    yr, mth = _last_sal_ym(emp)
    if yr is None:
        return 0.0
    amt = _salout_rate(emp, earn_cd, yr, mth, use_act=use_act)
    if int(map_cd) == 101:
        # stagnation pay (map 103)
        stag_cd = _map_earn_cd(103)
        if stag_cd:
            amt += _salout_rate(emp, stag_cd, yr, mth, use_act=use_act)
    return amt


def _da_pct_for_class(emp_class, as_of: date) -> Optional[float]:
    if as_of is None:
        return None
    # fi_pr_mh_calc_da: EMP_CLASS_GRP / EMP_CLASS vary by dump — try both
    for sql in (
        """
        SELECT DA_PCT FROM fi_pr_mh_calc_da
        WHERE EMP_CLASS = %s AND WEF_DT <= %s
        ORDER BY WEF_DT DESC LIMIT 1
        """,
        """
        SELECT DA_PCT FROM fi_pr_mh_calc_da
        WHERE EMP_CLASS_GRP = %s AND WEF_DT <= %s
        ORDER BY WEF_DT DESC LIMIT 1
        """,
    ):
        try:
            row = _fetchone(sql, [emp_class, as_of])
            if row and row.get("da_pct") is not None:
                return float(row["da_pct"])
        except Exception:
            continue
    return None


def compute_gratuity_emoluments(
    emp_cd,
    *,
    pension_option: str = "G",
    incentive_holder: str = "N",
    last_basic_fallback: Optional[float] = None,
    emp_class: Optional[str] = None,
    as_of: Optional[date] = None,
) -> dict:
    """
    FFunc_Avg_Basic(emp, G/P, 'G', incentive):
      incentive N → last-month Basic(+stag) + ADA
      incentive Y → that sum / 3
    """
    emp = _emp_key(emp_cd)
    basic = _last_month_component(emp, 101)
    ada = _last_month_component(emp, 107)

    if basic <= 0 and last_basic_fallback:
        basic = float(last_basic_fallback)
        if ada <= 0 and as_of is not None:
            pct = _da_pct_for_class(emp_class or "3", as_of)
            if pct is not None:
                # stored DA_PCT may be full percent (17.28) or already rate
                rate = pct / 100.0 if pct > 1 else pct
                ada = basic * rate

    raw = basic + ada
    if str(incentive_holder or "N").upper() == "Y":
        emol = raw / 3.0
    else:
        emol = raw

    return {
        "basic": _round2(basic),
        "ada": _round2(ada),
        "emoluments": _round2(emol),
        "pension_option": _clip(pension_option, 1) or "G",
        "incentive_holder": _clip(incentive_holder, 1) or "N",
    }


def compute_basic_only_from_salout(emp_cd) -> float:
    """Pre-inception death path: ACT basic (+ stag) only."""
    return _round2(_last_month_component(_emp_key(emp_cd), 101, use_act=True))


# ---------------------------------------------------------------------------
# Death multi-factor rebuild (20 ≤ TQS < 33)
# ---------------------------------------------------------------------------


def death_multi_factor_from_ymd(tqs_yr: int, tqs_month: int, tqs_days: int) -> float:
    """
    Oracle override when VN_TQS >= 20 and VN_TQS < 33:

      months > 9                   → years + 1
      months = 9 and days > 0      → years + 1
      3 < months < 9               → years + 0.5
      months = 3 and days > 0      → years + 0.5
      else                         → years
    """
    y = int(tqs_yr or 0)
    m = int(tqs_month or 0)
    d = int(tqs_days or 0)
    if m > 9:
        return float(y + 1)
    if m == 9 and d > 0:
        return float(y + 1)
    if m > 3 and m < 9:
        return float(y) + 0.5
    if m == 3 and d > 0:
        return float(y) + 0.5
    return float(y)


def _death_mh_limits(separation_dt: date) -> dict:
    row = _fetchone(
        """
        SELECT inception_dt, before_inception_max_lt, after_inception_max_lt, wef_dt
        FROM fi_pn_mh_death_gratchart
        WHERE gratuity_type = 2
          AND wef_dt = (
              SELECT MAX(wef_dt) FROM fi_pn_mh_death_gratchart
              WHERE %s > wef_dt AND gratuity_type = 2
          )
        LIMIT 1
        """,
        [separation_dt],
    )
    if not row:
        raise DcrGratuityError("Death gratuity data not available in master (MH chart)")
    return {
        "inception_dt": _as_date(row.get("inception_dt")),
        "before_max": float(row.get("before_inception_max_lt") or 0),
        "after_max": float(row.get("after_inception_max_lt") or 0),
        "wef_dt": _as_date(row.get("wef_dt")),
    }


def _chart_multi_factor(tqs: float, separation_dt: date) -> Optional[float]:
    """
    FI_PN_MD_DEATH_GRATCHART factor for TQS band, type 2.
    Prefer latest WEF on/before separation (form SQL omits WEF; we disambiguate).
    """
    row = _fetchone(
        """
        SELECT multiple_factor, wef_dt, tqs_start_yrs, tqs_end_yrs
        FROM fi_pn_md_death_gratchart
        WHERE gratuity_type = 2
          AND %s BETWEEN tqs_start_yrs AND tqs_end_yrs
          AND wef_dt = (
              SELECT MAX(wef_dt) FROM fi_pn_md_death_gratchart
              WHERE gratuity_type = 2
                AND wef_dt < %s
                AND %s BETWEEN tqs_start_yrs AND tqs_end_yrs
          )
        LIMIT 1
        """,
        [tqs, separation_dt, tqs],
    )
    if not row:
        # last resort any matching band
        row = _fetchone(
            """
            SELECT multiple_factor FROM fi_pn_md_death_gratchart
            WHERE gratuity_type = 2
              AND %s BETWEEN tqs_start_yrs AND tqs_end_yrs
            ORDER BY wef_dt DESC
            LIMIT 1
            """,
            [tqs],
        )
    if not row or row.get("multiple_factor") is None:
        return None
    return float(row["multiple_factor"])


def _maxadm_for(separation_dt: date) -> dict:
    row = _fetchone(
        """
        SELECT max_emolument, max_adm_gratuity
        FROM fi_pn_md_maxadm_gratuity
        WHERE %s BETWEEN ret_dt_from AND ret_dt_to
        LIMIT 1
        """,
        [separation_dt],
    ) or {}
    return {
        "max_emolument": _num(row.get("max_emolument")),
        "max_adm_gratuity": _num(row.get("max_adm_gratuity")),
    }


def _highest_side_round(value: float) -> float:
    """Nearest whole rupee half-up (FFUNC_HIGHEST_SIDE_ROUND style)."""
    return float(Decimal(str(value or 0)).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


# ---------------------------------------------------------------------------
# Main FFUNC_DCR_GRATUITY
# ---------------------------------------------------------------------------


def ffunc_dcr_gratuity(
    emp_cd,
    *,
    pension_option: str = "G",
    gratuity_option: int = 2,
    incentive_holder: str = "N",
    last_basic_fallback: Optional[float] = None,
    emp_class: Optional[str] = None,
    retirement_dt: Optional[date] = None,
) -> dict:
    """
    Returns dict with amount, emoluments, tqs, multi_factor, etc.

    gratuity_option:
      0 retirement option I (Gratuity Act style)
      1 retirement option II
      2 death gratuity (First Family Pension)
    """
    emp = _emp_key(emp_cd)
    tqs_info = compute_tqs(emp)
    sep = retirement_dt or tqs_info.separation_dt
    if not sep:
        raise DcrGratuityError(
            f"Separation date not available for {emp}, cannot compute DCR gratuity"
        )

    option = int(gratuity_option) if gratuity_option is not None else 0
    p_tccs = float(tqs_info.tccs or 0)
    p_tqs = float(tqs_info.tqs or 0)

    emo = compute_gratuity_emoluments(
        emp,
        pension_option=pension_option,
        incentive_holder=incentive_holder,
        last_basic_fallback=last_basic_fallback,
        emp_class=emp_class,
        as_of=sep,
    )
    emoluments = float(emo["emoluments"])

    result = {
        "emp_cd": emp,
        "gratuity_option": option,
        "separation_dt": sep.isoformat(),
        "emoluments": emoluments,
        "emoluments_detail": emo,
        "tqs": p_tqs,
        "tccs": p_tccs,
        "tqs_yr": tqs_info.tqs_yr,
        "tqs_month": tqs_info.tqs_month,
        "tqs_days": tqs_info.tqs_days,
        "period_of_service": tqs_info.pos_years,
        "multi_factor": None,
        "gross_gratuity": 0.0,
        "gratuity_amt": 0.0,
        "ceiling_applied": None,
    }

    if option == 0:
        # (E * 15 * TCCS) / 26
        dcr = (emoluments * 15.0 * p_tccs) / 26.0
        mh = _fetchone(
            """
            SELECT inception_dt, before_inception_max_lt, after_inception_max_lt
            FROM fi_pn_mh_death_gratchart
            WHERE gratuity_type = 0
              AND wef_dt = (
                  SELECT MAX(wef_dt) FROM fi_pn_mh_death_gratchart
                  WHERE %s > wef_dt AND gratuity_type = 0
              )
            LIMIT 1
            """,
            [sep],
        )
        if mh:
            inception = _as_date(mh.get("inception_dt"))
            before_max = float(mh.get("before_inception_max_lt") or 0)
            after_max = float(mh.get("after_inception_max_lt") or 0)
            if inception and sep >= inception:
                if dcr > after_max:
                    dcr = after_max
                    result["ceiling_applied"] = after_max
            elif dcr > before_max:
                dcr = before_max
                result["ceiling_applied"] = before_max
        dcr = _highest_side_round(dcr)
        result["gross_gratuity"] = dcr
        result["gratuity_amt"] = dcr
        return result

    if option == 1:
        tqs = min(p_tqs, 33.0)
        result["tqs"] = tqs
        limits = _maxadm_for(sep)
        e = emoluments
        if limits["max_emolument"] and e > limits["max_emolument"]:
            e = float(limits["max_emolument"])
            result["emoluments"] = e
        dcr = (e * tqs) / 2.0
        result["gross_gratuity"] = _round2(dcr)
        if limits["max_adm_gratuity"] and dcr > limits["max_adm_gratuity"]:
            dcr = float(limits["max_adm_gratuity"])
            result["ceiling_applied"] = dcr
        result["gratuity_amt"] = _round2(dcr)
        return result

    # ---- option 2: death gratuity ----
    mh = _death_mh_limits(sep)
    inception = mh["inception_dt"]
    after_max = mh["after_max"]
    before_max = mh["before_max"]

    if inception and sep >= inception:
        emo_death = compute_gratuity_emoluments(
            emp,
            pension_option=pension_option,
            incentive_holder=incentive_holder,
            last_basic_fallback=last_basic_fallback,
            emp_class=emp_class,
            as_of=sep,
        )
        emol_death = float(emo_death["emoluments"])
        result["emoluments_detail"] = emo_death
    else:
        emol_death = compute_basic_only_from_salout(emp)
        if emol_death <= 0 and last_basic_fallback:
            emol_death = float(last_basic_fallback)
        result["emoluments_detail"] = {
            "basic": emol_death,
            "ada": 0.0,
            "emoluments": emol_death,
            "note": "pre-inception: basic only",
        }

    result["emoluments"] = emol_death

    tqs = float(p_tqs)
    multi = _chart_multi_factor(tqs, sep)

    if tqs > 33:
        tqs = 33.0
        result["tqs"] = tqs

    # Half-emoluments per completed 6 months, max 33× (form override)
    if 20.0 <= tqs < 33.0:
        multi = death_multi_factor_from_ymd(
            tqs_info.tqs_yr, tqs_info.tqs_month, tqs_info.tqs_days
        )
    elif multi is None:
        raise DcrGratuityError(
            f"Multiplication factor for TQS {tqs} not defined for Death Gratuity"
        )

    result["multi_factor"] = float(multi)
    gross = emol_death * float(multi)
    result["gross_gratuity"] = _round2(gross)
    dcr = gross

    if inception and sep >= inception:
        if dcr > after_max:
            dcr = after_max
            result["ceiling_applied"] = after_max
    else:
        if dcr > before_max:
            dcr = before_max
            result["ceiling_applied"] = before_max

    result["gratuity_amt"] = _round2(dcr)
    result["inception_dt"] = inception.isoformat() if inception else None
    result["after_inception_max"] = after_max
    result["before_inception_max"] = before_max
    return result
