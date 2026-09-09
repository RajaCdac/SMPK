"""
Double Family Pension — port of FI_PN_MH_First_FPension.fmb
FPROC_CALCULATE_FPENSION2 double branch (with Methodology1 rates).

Rules:
  - Eligibility from claim DOUBLE_FPEN_ELIGIBILITY = 1
  - Double FP upto:
      * Die-in-harness (sep type DT and sep date < exp retirement):
          straight 10 years from separation date − 1 day
          (sep date is next day after date of death; no age cap)
      * Otherwise:
          MIN(separation/retirement + 7 years, DOB + age) − 1 day
          Age: Class I/II → 67 years; Class III/IV/other → 65 years
  - Single FP (Methodology1): take 30% of last pay, then apply CPI fitment
  - Double FP: same Methodology1 fitment chain on 50% of last pay
    (M1 chain’s first stage is 30% of the input pay; pass last×(5/3) so
    stage-1 = 50% of last pay, then fitment — e.g. 38000 → 26800 for 44733)
  - First-month payable can be full single, full double, or day-mix
"""

from __future__ import annotations

import calendar
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from decimal import Decimal, ROUND_DOWN, ROUND_HALF_UP
from typing import Any, Optional, Union


class DoubleFamilyPensionError(Exception):
    pass


# Single FP starts at this % of last basic; double uses 50% then same fitment.
_FP_PCT_SINGLE = 30.0
_FP_PCT_DOUBLE = 50.0


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


def _truthy_eligibility(value) -> bool:
    if value is None or value == "":
        return False
    if value is True:
        return True
    if isinstance(value, (int, float)):
        return int(value) == 1
    text = str(value).strip().upper()
    return text in {"1", "Y", "YES", "TRUE"}


def add_months(d: date, months: int) -> date:
    months = int(months)
    y = d.year + (d.month - 1 + months) // 12
    m = (d.month - 1 + months) % 12 + 1
    last = calendar.monthrange(y, m)[1]
    return date(y, m, min(d.day, last))


def last_day_of_month(y: int, m: int) -> date:
    return date(int(y), int(m), calendar.monthrange(int(y), int(m))[1])


def _money_round2(value) -> float:
    return float(
        Decimal(str(value or 0)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    )


def _floor_rupee(value) -> float:
    """Form: floor(act_pen_amt) for double path (no highest-side)."""
    return float(Decimal(str(value or 0)).to_integral_value(rounding=ROUND_DOWN))


def _rupee_half_up(value) -> float:
    return float(Decimal(str(value or 0)).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def _age_limit_months_for_class(emp_class: Any = None) -> int:
    """
    Class I / II → DOB + 67 years (804 months).
    Class III / IV / other → DOB + 65 years (780 months; Oracle form general).
    """
    if emp_class in (None, ""):
        return 780
    text = str(emp_class).strip().upper()
    try:
        c = int(float(text))
        return 804 if c in (1, 2) else 780
    except (TypeError, ValueError):
        pass
    if text in {"1", "2", "I", "II", "CLASS 1", "CLASS 2", "CLASS I", "CLASS II"}:
        return 804
    return 780


def is_die_in_harness(
    separation_type: Any = None,
    separation_dt: Optional[date] = None,
    exp_ret_dt: Optional[date] = None,
) -> bool:
    """
    Die-in-harness: separation type DT (death) and separation date before
    expected retirement date (death while still in service period).
    """
    st = str(separation_type or "").strip().upper()
    if st not in {"DT", "DE", "D", "DEATH"}:
        return False
    sep = _as_date(separation_dt)
    exp = _as_date(exp_ret_dt)
    if not sep or not exp:
        return False
    return sep < exp


def resolve_double_fpen_upto(
    *,
    separation_dt: Optional[date] = None,
    emp_dob: Optional[date] = None,
    emp_class: Any = None,
    claim_upto: Optional[date] = None,
    dod: Optional[date] = None,
    separation_type: Any = None,
    exp_ret_dt: Optional[date] = None,
) -> date:
    """
    Normal (retired / superannuation path):
      raw = MIN(separation/retirement + 84 months, DOB + age months)
      upto = raw − 1 day

    Die-in-harness (sep type DT and sep date < exp ret):
      straight 10 years from separation date − 1 day
      (sep is next day after date of death; no age cap)

    Class I/II age months = 804 (67y); else 780 (65y) for normal path only.
    Falls back to claim_upto if dates insufficient and claim has a date.
    """
    sep = _as_date(separation_dt)
    exp = _as_date(exp_ret_dt)
    dih = is_die_in_harness(separation_type, sep, exp)

    if dih:
        if not sep:
            if claim_upto:
                return claim_upto
            raise DoubleFamilyPensionError(
                "Cannot compute DOUBLE_FPEN_UPTO for die-in-harness "
                "(need separation date)"
            )
        # 10 years from sep (day after death); last inclusive day
        return add_months(sep, 120) - timedelta(days=1)

    base = sep or _as_date(dod)
    emp_dob = _as_date(emp_dob)
    age_months = _age_limit_months_for_class(emp_class)
    candidates = []
    if base:
        candidates.append(add_months(base, 84))  # 7 years after sep/ret
    if emp_dob:
        candidates.append(add_months(emp_dob, age_months))
    if candidates:
        raw = min(candidates)
        return raw - timedelta(days=1)
    if claim_upto:
        return claim_upto
    raise DoubleFamilyPensionError(
        "Cannot compute DOUBLE_FPEN_UPTO "
        "(need separation/retirement date and employee DOB)"
    )


# ---------------------------------------------------------------------------
# Mode + first-period payable
# ---------------------------------------------------------------------------

MODE_FULL_SINGLE = 1
MODE_FULL_DOUBLE = 2
MODE_PART_MIX = 3


@dataclass
class DoubleFpResult:
    eligible: bool
    double_fpen_upto: Optional[date]
    single_rate: float
    double_rate: float
    mode: int  # 1/2/3
    mode_label: str
    payable_fp_amt: float  # first-period amount for bill
    period_start: Optional[date]
    period_end: Optional[date]
    double_days: int
    single_days: int
    total_days: int
    details: dict


def _eligible_from_claim(claim_row_or_elig) -> bool:
    if isinstance(claim_row_or_elig, dict):
        return _truthy_eligibility(claim_row_or_elig.get("double_fpen_eligibility"))
    return _truthy_eligibility(claim_row_or_elig)


def _m1_payable_amount(m1_result: Optional[dict]) -> Optional[float]:
    """Pick 359 then 277 family pension from Methodology1 output."""
    if not m1_result or m1_result.get("error"):
        return None
    for key in ("FP_359_cpi", "FP_277_cpi"):
        amt = _num(m1_result.get(key))
        if amt is not None and amt > 0:
            return float(amt)
    return None


def m1_fitment_on_pct_of_last_pay(
    *,
    last_basic: float,
    pct: float,
    separation_date: Union[date, str, None],
    category: Any,
    scale: Optional[str] = None,
) -> Optional[float]:
    """
    Fitment on ``pct`` of last basic.

    Class 3/4: Methodology1 chain (stage-1 is 30% of input pay → scale input).
    Class 1/2: First-FP officer chain (full last pay stages then × pct/100).
    """
    basic = float(last_basic or 0)
    pct_f = float(pct or 0)
    if basic <= 0 or pct_f <= 0:
        return None
    if not separation_date or category in (None, ""):
        return None

    sep = (
        separation_date.isoformat()
        if isinstance(separation_date, date)
        else str(separation_date).strip()[:10]
    )
    cat = str(category).strip()
    try:
        if cat in {"1", "2", "I", "II", "O"}:
            from family_pension.services.class12_fp_service import (
                calculate_class12_family_pension_for_fp,
            )

            # Officer formula is on full basic → FP at 30%. Scale last_basic so
            # 30% of final basic equals (pct/100)*original last basic result:
            # family(pay) = f(pay)*0.3 linear in pay → pass pay*(pct/30).
            adj_pay = basic * (pct_f / _FP_PCT_SINGLE)
            m1 = calculate_class12_family_pension_for_fp(
                separation_date=sep,
                last_pay=adj_pay,
                scale=scale,
            )
            return _m1_payable_amount(m1)

        from methodology1.services.family_pension_calculation_service import (
            calculate_family_pension,
        )

        # Chain stage-1 = 30% of input_pay; want stage-1 = (pct/100)*basic
        input_pay = basic * (pct_f / _FP_PCT_SINGLE)
        m1 = calculate_family_pension(
            separation_date=sep,
            category=category,
            pay=input_pay,
            scale=scale,
        )
        return _m1_payable_amount(m1)
    except Exception:
        return None


def compute_double_monthly_rate(
    *,
    single_rate: float,
    last_basic: float,
    dod: Optional[date],
    retirement_dt: Optional[date],
    original_pension_amt: Optional[float] = None,
    separation_date: Union[date, str, None] = None,
    category: Any = None,
    scale: Optional[str] = None,
) -> dict:
    """
    Double monthly rate = Methodology1 fitment on 50% of last pay
    (single FP is the same pipeline on 30% of last pay).

    Prefer a fresh M1 run with pay scaled to 50%; if M1 inputs are missing,
    scale the known single M1 rate by 50/30 (valid when fitment is linear
    from a pure 30% first stage).
    """
    single = float(single_rate or 0)
    basic = float(last_basic or 0)
    half_basic = _money_round2(basic / 2.0)
    org = _num(original_pension_amt)
    die_after_ret = bool(dod and retirement_dt and dod > retirement_dt)

    method = "single_times_50_over_30"
    notes = []
    double_amt = None

    m1_double = m1_fitment_on_pct_of_last_pay(
        last_basic=basic,
        pct=_FP_PCT_DOUBLE,
        separation_date=separation_date,
        category=category,
        scale=scale,
    )
    if m1_double is not None and m1_double > 0:
        double_amt = float(m1_double)
        method = "m1_fitment_on_50pct_last_pay"
        notes.append(method)
    elif single > 0:
        # single = M1(on 30%); double ≈ M1(on 50%) when stages are proportional
        double_amt = single * (_FP_PCT_DOUBLE / _FP_PCT_SINGLE)
        notes.append(method)

    if double_amt is None or double_amt <= 0:
        # last-resort bare floor: 50% of last pay (no fitment)
        double_amt = half_basic if half_basic > 0 else 0.0
        method = "bare_50pct_last_pay"
        notes.append(method)

    double_amt = _money_round2(double_amt)

    return {
        "single_rate": _money_round2(single),
        "half_last_basic": half_basic,
        "original_pension_amt": org,
        "double_rate": double_amt,
        "method": method,
        "pct_of_last_pay": _FP_PCT_DOUBLE,
        "notes": notes,
        "cap_notes": notes,  # alias for any callers still reading cap_notes
        "die_after_retirement": die_after_ret,
    }


def classify_and_payable(
    *,
    eligible: bool,
    period_start: date,
    period_end: date,
    double_upto: Optional[date],
    single_rate: float,
    double_rate: float,
) -> dict:
    """
    Apportion first-period FP across single/double rates.

    period_start: typically DOD+1 (WEF)
    period_end: last day of generation bill month
    double_upto: inclusive end of double eligibility
    """
    single = float(single_rate or 0)
    double = float(double_rate or 0)

    if period_start > period_end:
        period_start, period_end = period_end, period_start

    total_days = (period_end - period_start).days + 1
    if total_days < 1:
        total_days = 1

    if not eligible or not double_upto or double <= 0:
        return {
            "mode": MODE_FULL_SINGLE,
            "mode_label": "full_single",
            "double_days": 0,
            "single_days": total_days,
            "total_days": total_days,
            "payable": _rupee_half_up(single),
            "payable_floor": False,
        }

    if double_upto < period_start:
        return {
            "mode": MODE_FULL_SINGLE,
            "mode_label": "full_single_after_double_upto",
            "double_days": 0,
            "single_days": total_days,
            "total_days": total_days,
            "payable": _rupee_half_up(single),
            "payable_floor": False,
        }

    if double_upto >= period_end:
        if period_start.day == 1 and period_end == last_day_of_month(
            period_end.year, period_end.month
        ):
            payable = _floor_rupee(double)
        else:
            month_days = calendar.monthrange(period_end.year, period_end.month)[1]
            payable = _floor_rupee(double * (total_days / float(month_days)))
        return {
            "mode": MODE_FULL_DOUBLE,
            "mode_label": "full_double",
            "double_days": total_days,
            "single_days": 0,
            "total_days": total_days,
            "payable": payable,
            "payable_floor": True,
        }

    double_end = min(double_upto, period_end)
    double_days = (double_end - period_start).days + 1
    if double_days < 0:
        double_days = 0
    single_days = total_days - double_days
    if single_days < 0:
        single_days = 0

    month_days = calendar.monthrange(period_end.year, period_end.month)[1]
    mix = (double * (double_days / float(month_days))) + (
        single * (single_days / float(month_days))
    )
    payable = _floor_rupee(mix)
    return {
        "mode": MODE_PART_MIX,
        "mode_label": "part_double_part_single",
        "double_days": double_days,
        "single_days": single_days,
        "total_days": total_days,
        "payable": payable,
        "payable_floor": True,
    }


def compute_double_family_pension(
    *,
    claim,
    emp_dob: Optional[date],
    single_fp_rate: float,
    last_basic: float,
    dod: date,
    retirement_dt: Optional[date],
    original_pension_amt: Optional[float],
    wef: date,
    bill_month: int,
    bill_year: int,
    separation_date: Union[date, str, None] = None,
    category: Any = None,
    scale: Optional[str] = None,
    separation_type: Any = None,
    exp_ret_dt: Optional[date] = None,
) -> DoubleFpResult:
    """
    Main entry used by First FP generation.

    single_fp_rate: Methodology1 payable family pension (monthly) on 30%+fitment.
    Double rate: same Methodology1 path on 50% of last pay.
    """
    eligible = _eligible_from_claim(claim)
    single = _money_round2(single_fp_rate)

    period_end = last_day_of_month(bill_year, bill_month)
    period_start = wef if wef else date(int(bill_year), int(bill_month), 1)
    month_start = date(int(bill_year), int(bill_month), 1)
    if period_start < month_start:
        period_start = month_start
    if period_start > period_end:
        period_end = last_day_of_month(period_start.year, period_start.month)

    if not eligible:
        pay = classify_and_payable(
            eligible=False,
            period_start=period_start,
            period_end=period_end,
            double_upto=None,
            single_rate=single,
            double_rate=0.0,
        )
        return DoubleFpResult(
            eligible=False,
            double_fpen_upto=_as_date(
                claim.get("double_fpen_upto") if isinstance(claim, dict) else None
            ),
            single_rate=single,
            double_rate=0.0,
            mode=pay["mode"],
            mode_label=pay["mode_label"],
            payable_fp_amt=float(pay["payable"]),
            period_start=period_start,
            period_end=period_end,
            double_days=pay["double_days"],
            single_days=pay["single_days"],
            total_days=pay["total_days"],
            details={"reason": "DOUBLE_FPEN_ELIGIBILITY not set"},
        )

    claim_upto = (
        _as_date(claim.get("double_fpen_upto")) if isinstance(claim, dict) else None
    )
    sep_for_upto = _as_date(separation_date) or _as_date(retirement_dt)
    emp_class = category
    if emp_class in (None, "") and isinstance(claim, dict):
        emp_class = claim.get("class_cd") or claim.get("emp_class")
    sep_type = separation_type
    exp_ret = _as_date(exp_ret_dt)
    if isinstance(claim, dict):
        if sep_type in (None, ""):
            sep_type = claim.get("separation_type")
        if not exp_ret:
            exp_ret = _as_date(claim.get("exp_ret_dt"))
        if not sep_for_upto:
            sep_for_upto = _as_date(claim.get("separation_dt"))
    age_months = _age_limit_months_for_class(emp_class)
    dih = is_die_in_harness(sep_type, sep_for_upto, exp_ret)
    # Always recompute (−1 day rule); DIH is straight sep+10y
    upto = resolve_double_fpen_upto(
        separation_dt=sep_for_upto,
        emp_dob=emp_dob,
        emp_class=emp_class,
        claim_upto=claim_upto,
        dod=dod,
        separation_type=sep_type,
        exp_ret_dt=exp_ret,
    )

    rate = compute_double_monthly_rate(
        single_rate=single,
        last_basic=last_basic,
        dod=dod,
        retirement_dt=retirement_dt,
        original_pension_amt=original_pension_amt,
        separation_date=separation_date or retirement_dt,
        category=category,
        scale=scale,
    )
    double = float(rate["double_rate"])

    pay = classify_and_payable(
        eligible=True,
        period_start=period_start,
        period_end=period_end,
        double_upto=upto,
        single_rate=single,
        double_rate=double,
    )

    age_label = "67" if age_months >= 804 else "65"
    if dih and sep_for_upto:
        service_limit = add_months(sep_for_upto, 120)
        raw_limits = [service_limit]
        service_note = "separation+10y (die-in-harness, no age cap)"
        claim_upto_note = "DOUBLE_FPEN_UPTO = separation+10y − 1 day (DIH)"
    else:
        service_limit = add_months(sep_for_upto, 84) if sep_for_upto else None
        raw_limits = [
            x
            for x in (
                service_limit,
                add_months(emp_dob, age_months) if emp_dob else None,
            )
            if x
        ]
        service_note = "separation/retirement+7y"
        claim_upto_note = (
            f"DOUBLE_FPEN_UPTO = MIN({service_note}, DOB+{age_label}y) − 1 day"
        )

    return DoubleFpResult(
        eligible=True,
        double_fpen_upto=upto,
        single_rate=single,
        double_rate=double,
        mode=pay["mode"],
        mode_label=pay["mode_label"],
        payable_fp_amt=float(pay["payable"]),
        period_start=period_start,
        period_end=period_end,
        double_days=pay["double_days"],
        single_days=pay["single_days"],
        total_days=pay["total_days"],
        details={
            **rate,
            "dod": dod.isoformat() if dod else None,
            "emp_dob": emp_dob.isoformat() if emp_dob else None,
            "emp_class": emp_class,
            "separation_dt": sep_for_upto.isoformat() if sep_for_upto else None,
            "separation_type": sep_type,
            "exp_ret_dt": exp_ret.isoformat() if exp_ret else None,
            "die_in_harness": dih,
            "retirement_dt": retirement_dt.isoformat() if retirement_dt else None,
            "die_after_retirement": bool(
                dod and retirement_dt and dod > retirement_dt
            ),
            "service_period_limit": (
                service_limit.isoformat() if service_limit else None
            ),
            f"age_{age_label}": (
                None
                if dih
                else (add_months(emp_dob, age_months).isoformat() if emp_dob else None)
            ),
            "raw_limit_date": min(raw_limits).isoformat() if raw_limits else None,
            "payable_floor": pay.get("payable_floor"),
            "claim_upto_note": claim_upto_note,
            "service_note": service_note,
        },
    )


def double_result_as_dict(r: DoubleFpResult) -> dict:
    return {
        "eligible": r.eligible,
        "double_fpen_upto": r.double_fpen_upto.isoformat()
        if r.double_fpen_upto
        else None,
        "single_rate": r.single_rate,
        "double_rate": r.double_rate,
        "mode": r.mode,
        "mode_label": r.mode_label,
        "payable_fp_amt": r.payable_fp_amt,
        "period_start": r.period_start.isoformat() if r.period_start else None,
        "period_end": r.period_end.isoformat() if r.period_end else None,
        "double_days": r.double_days,
        "single_days": r.single_days,
        "total_days": r.total_days,
        "details": r.details,
    }
