"""
Consolidation print columns with old-age splits (similar to DOD mid-CPI columns).

Print formula (no DA) — benefit part only:
  OA_M2 = M2 × %          (0 when % = 0)
  OA_M1 = M1 × %          (0 when % = 0)
  OA Diff = OA_M2 − OA_M1

Separate table — Pension with Old Age Benefit:
  Payable basic = max(M2, M1)
  Old age benefit = max(OA_M2, OA_M1)
  Revised basic = Payable + Old age benefit

Example — age-80 WEF Aug 2024:
  277: OA = 0
  359 upto Jul 2024: OA = 0
  359 from Aug 2024 @20%: OA = 20% of basic
"""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP
from typing import Any

from M2_oldage_arrear.services.oldage_service import (
    CPI_277_FROM,
    CPI_359_FROM,
    DISPLAY_HORIZON_END,
    OLDAGE_SLABS,
    percent_on_wef_date,
    wef_for_age,
    _as_date,
    _as_decimal,
    _money,
)

CPI_277_END = date(2021, 12, 31)


def _month_label(d: date | None) -> str:
    if not d:
        return ""
    months = (
        "Jan",
        "Feb",
        "Mar",
        "Apr",
        "May",
        "Jun",
        "Jul",
        "Aug",
        "Sep",
        "Oct",
        "Nov",
        "Dec",
    )
    return f"{months[d.month - 1]} {d.year}"


def _prev_month_end(d: date) -> date:
    first = date(d.year, d.month, 1)
    return first - timedelta(days=1)


def _float_or_none(value):
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _benefit_only(amount: Decimal | None, pct: Decimal) -> Decimal:
    """amount × pct/100 — benefit part only (0 when pct=0 or amount missing)."""
    if amount is None or pct <= 0:
        return Decimal("0.00")
    return (amount * pct / Decimal("100")).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )


def _segment_breaks(dob: date, window_start: date, window_end: date | None) -> list[date]:
    """Start dates of rate segments inside [window_start, window_end]."""
    end = window_end or DISPLAY_HORIZON_END
    breaks = {window_start}
    for lo, _hi, _pct in OLDAGE_SLABS:
        w = wef_for_age(dob, lo)
        if window_start < w <= end:
            breaks.add(w)
    return sorted(b for b in breaks if b <= end)


def _build_cpi_columns(
    *,
    dob: date,
    cpi: int,
    year_label: str,
    window_start: date,
    window_end: date | None,
    m2: Decimal | None,
    m1: Decimal | None,
    kind: str,
) -> list[dict[str, Any]]:
    if m2 is None and m1 is None:
        return []

    m2f = _float_or_none(m2)
    m1f = _float_or_none(m1)
    ends = window_end or DISPLAY_HORIZON_END
    starts = _segment_breaks(dob, window_start, ends)
    if not starts:
        return []

    cols = []
    for i, seg_start in enumerate(starts):
        if i + 1 < len(starts):
            seg_end = starts[i + 1] - timedelta(days=1)
            open_end = False
        else:
            seg_end = window_end
            open_end = window_end is None

        if seg_end is not None and seg_start > seg_end:
            continue

        pct = percent_on_wef_date(dob, seg_start)
        oa_m2 = _benefit_only(m2, pct)
        oa_m1 = _benefit_only(m1, pct)
        oa_m2_f = float(oa_m2)
        oa_m1_f = float(oa_m1)
        oa_diff = round(oa_m2_f - oa_m1_f, 2)

        base_diff = None
        if m2f is not None and m1f is not None:
            base_diff = round(m2f - m1f, 2)

        if m2f is not None and m1f is not None:
            payable = max(m2f, m1f)
        elif m2f is not None:
            payable = m2f
        elif m1f is not None:
            payable = m1f
        else:
            payable = None

        oa_benefit = max(oa_m2_f, oa_m1_f)
        revised = (
            round(payable + oa_benefit, 2) if payable is not None else oa_benefit
        )

        notes = []
        if i == 0 and len(starts) > 1:
            notes.append(f"upto {_month_label(_prev_month_end(starts[1]))}")
        elif i > 0:
            notes.append(f"from {_month_label(seg_start)}")
        if pct > 0:
            notes.append(f"Old age @{float(pct):g}%")

        period_note = " — ".join(notes)
        header_lines = [f"In {year_label} ({cpi} CPI)"]
        if period_note:
            header_lines.append(period_note)

        cols.append(
            {
                "key": f"{cpi}_oa_{seg_start.isoformat()}",
                "cpi": cpi,
                "kind": kind,
                "year_label": year_label,
                "period_note": period_note,
                "header_lines": header_lines,
                "header": " — ".join(header_lines),
                "period_from": seg_start.isoformat(),
                "period_to": None if open_end else (seg_end.isoformat() if seg_end else None),
                "oldage_percent": float(pct),
                "m2_base": m2f,
                "m2": m2f,
                "m1": m1f,
                "diff": base_diff,
                "oa_benefit_m2": oa_m2_f,
                "oa_benefit_m1": oa_m1_f,
                "oa_diff": oa_diff,
                "payable_basic": payable,
                "oa_benefit": oa_benefit,
                "revised_total_basic": revised,
                "oldage_addl": _money(oa_m2) if pct > 0 else 0.0,
            }
        )
    return cols


def build_oldage_pension_comparison(
    *,
    dob,
    m2_277,
    m1_277,
    m2_359,
    m1_359,
    is_employee_pension=True,
    as_on_date=None,
) -> dict[str, Any]:
    """
    Build pension_comparison with old-age mid-CPI columns for print.
    OA on print = % of full M2 / M1 (benefit only). No DA.
    """
    dob_d = _as_date(dob)
    as_on = _as_date(as_on_date) or date.today()
    kind = "employee" if is_employee_pension else "family"

    if not dob_d:
        return {
            "has_oldage_split": False,
            "has_oldage_calc_table": False,
            "columns": [],
            "section_title": (
                "EMPLOYEE PENSION" if is_employee_pension else "FAMILY PENSION"
            ),
        }

    b277 = _as_decimal(m2_277)
    a277 = _as_decimal(m1_277)
    b359 = _as_decimal(m2_359)
    a359 = _as_decimal(m1_359)

    columns: list[dict[str, Any]] = []
    columns.extend(
        _build_cpi_columns(
            dob=dob_d,
            cpi=277,
            year_label="2017",
            window_start=CPI_277_FROM,
            window_end=CPI_277_END,
            m2=b277,
            m1=a277,
            kind=kind,
        )
    )
    columns.extend(
        _build_cpi_columns(
            dob=dob_d,
            cpi=359,
            year_label="2022",
            window_start=CPI_359_FROM,
            window_end=None,
            m2=b359,
            m1=a359,
            kind=kind,
        )
    )

    has_split = len(columns) > 2 or any(
        (c.get("oldage_percent") or 0) > 0 for c in columns
    )

    wef80 = wef_for_age(dob_d, 80)
    return {
        "has_oldage_split": has_split,
        "has_death_split": False,
        "has_oldage_calc_table": has_split,
        "oldage_wef_80": wef80.isoformat(),
        "oldage_wef_80_display": _month_label(wef80),
        "date_of_birth": dob_d.isoformat(),
        "as_on_date": as_on.isoformat(),
        "section_title": (
            "EMPLOYEE PENSION" if is_employee_pension else "FAMILY PENSION"
        ),
        "is_employee_pension": is_employee_pension,
        "columns": columns,
        "m1_family_pension_277": _float_or_none(a277),
        "m1_family_pension_359": _float_or_none(a359),
        "display_m2_277": columns[0]["m2"] if columns else _float_or_none(b277),
        "display_m2_359": (
            next((c["m2"] for c in reversed(columns) if c["cpi"] == 359), None)
        ),
    }
