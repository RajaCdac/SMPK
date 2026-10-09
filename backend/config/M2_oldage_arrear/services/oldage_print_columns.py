"""
Consolidation print columns with old-age splits (similar to DOD mid-CPI columns).

Print formula (no DA) — benefit part only:
  OA_M2 = ceil_rupee(M2 x %)   (0 when % = 0)
  OA_M1 = ceil_rupee(M1 x %)   (0 when % = 0)
  OA Diff = OA_M2 - OA_M1

  ceil_rupee: any fraction -> next whole rupee (1011.01 / 1011.7 -> 1012).

Separate table — Pension with Old Age Benefit:
  Payable basic = max(M2, M1)
  Old age benefit = max(OA_M2, OA_M1)
  Revised basic = Payable + Old age benefit

Class 3/4 (has 359 bases):
  277 window 01.01.2017-31.12.2021, then 359 window from 01.01.2022 (open).

Class 1/2 (no 359 revision — only 277 bases):
  One continuous OA timeline from 01.01.2017 through the display horizon,
  always using 277 M2/M1 under heading "In 2017 (277 CPI)" (never "2022").
  Example — age-80 WEF Mar 2026:
    In 2017 (277 CPI) | upto Feb 2026
    In 2017 (277 CPI) | from Mar 2026 — Old age @20%

Example — age-80 WEF Aug 2024 (class 3/4):
  277: OA = 0
  359 upto Jul 2024: OA = 0
  359 from Aug 2024 @20%: OA = 20% of basic
"""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal, ROUND_CEILING
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


# One Excel group per age slab. Difference is M-II minus M-I for that %.
OA_EXCEL_SLAB_PCTS = (20, 30, 40, 50, 100)


def oldage_slab_excel_headers() -> list[str]:
    headers: list[str] = []
    for pct in OA_EXCEL_SLAB_PCTS:
        headers.extend(
            [
                f"Old Age {pct}% from",
                f"OA Benefit M-I @{pct}%",
                f"OA Benefit M-II @{pct}%",
                f"Difference @{pct}%",
            ]
        )
    return headers


def oldage_slab_excel_keys() -> list[str]:
    keys: list[str] = []
    for pct in OA_EXCEL_SLAB_PCTS:
        keys.extend(
            [
                f"oa_{pct}_from",
                f"oa_{pct}_m1",
                f"oa_{pct}_m2",
                f"oa_{pct}_diff",
            ]
        )
    return keys


def _slab_percent(value) -> int | None:
    if value is None or value == "":
        return None
    try:
        pct = int(round(float(value)))
    except (TypeError, ValueError):
        return None
    if pct in OA_EXCEL_SLAB_PCTS:
        return pct
    return None


def _slab_month_year(value) -> str:
    d = _as_date(value)
    if not d:
        return ""
    return _month_label(d).replace(" ", "-")


def oldage_slab_excel_values(columns) -> list:
    """
    From-month plus M-I, M-II and Difference for each old-age slab.

    From is the month that percentage first starts. Amounts are the latest
    column at that percentage, so a slab that continues into 359 CPI shows
    the 359 rupee benefit. Blank when that slab has not started.
    """
    grouped: dict[int, list[dict]] = {pct: [] for pct in OA_EXCEL_SLAB_PCTS}
    for col in columns or []:
        if not isinstance(col, dict):
            continue
        pct = _slab_percent(col.get("oldage_percent"))
        if pct is None or pct <= 0:
            continue
        grouped[pct].append(col)

    cells: list = []
    for pct in OA_EXCEL_SLAB_PCTS:
        cols = sorted(
            grouped[pct],
            key=lambda c: str(c.get("period_from") or ""),
        )
        if not cols:
            cells.extend(["", None, None, None])
            continue
        latest = cols[-1]
        m1 = _float_or_none(latest.get("oa_benefit_m1"))
        m2 = _float_or_none(latest.get("oa_benefit_m2"))
        diff = _float_or_none(latest.get("oa_diff"))
        if diff is None and m1 is not None and m2 is not None:
            diff = round(m2 - m1, 2)
        cells.extend(
            [
                _slab_month_year(cols[0].get("period_from")),
                m1,
                m2,
                diff,
            ]
        )
    return cells


def oldage_slab_excel_dict(columns) -> dict:
    return dict(zip(oldage_slab_excel_keys(), oldage_slab_excel_values(columns)))


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


def _ceil_rupee(value: Decimal) -> Decimal:
    """
    As per M1 OA rule: if any fraction after decimal, round up to next rupee.
    1011.01 / 1011.7 -> 1012; 1011.00 stays 1011.
    """
    return value.to_integral_value(rounding=ROUND_CEILING)


def _benefit_only(amount: Decimal | None, pct: Decimal) -> Decimal:
    """
    amount x pct/100 for Old Age Benefit Calculation Details (M1 / M2 rows).
    Ceil to next whole rupee when any paise/fraction exists.
    """
    if amount is None or pct <= 0:
        return Decimal("0")
    raw = amount * pct / Decimal("100")
    return _ceil_rupee(raw)


def _segment_breaks(dob: date, window_start: date, window_end: date | None) -> list[date]:
    """Start dates of rate segments inside [window_start, window_end]."""
    end = window_end or DISPLAY_HORIZON_END
    breaks = {window_start}
    for lo, _hi, _pct in OLDAGE_SLABS:
        w = wef_for_age(dob, lo)
        if window_start < w <= end:
            breaks.add(w)
    return sorted(b for b in breaks if b <= end)


def _header_for_segment(
    *,
    seg_start: date,
    year_label: str,
    cpi: int,
    continuous_277: bool,
) -> tuple[str, int, str]:
    """
    Return (year_label, cpi, header first line).

    Class 1/2 has no 359 revision — 277 CPI is always the 2017 revision.
    OA slab splits after Mar 2022 stay under "In 2017 (277 CPI)"; only the
    period note (upto / from / Old age @%) changes.
    """
    if continuous_277:
        return "2017", 277, "In 2017 (277 CPI)"
    return year_label, cpi, f"In {year_label} ({cpi} CPI)"


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
    continuous_277: bool = False,
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
        yl, cpi_tag, head = _header_for_segment(
            seg_start=seg_start,
            year_label=year_label,
            cpi=cpi,
            continuous_277=continuous_277,
        )
        header_lines = [head]
        if period_note:
            header_lines.append(period_note)

        cols.append(
            {
                "key": f"{cpi_tag}_oa_{seg_start.isoformat()}",
                "cpi": cpi_tag,
                "kind": kind,
                "year_label": yl,
                "period_note": period_note,
                "header_lines": header_lines,
                "header": " — ".join(header_lines),
                "period_from": seg_start.isoformat(),
                "period_to": (
                    None if open_end else (seg_end.isoformat() if seg_end else None)
                ),
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
                "bases_from_cpi": 277 if continuous_277 else cpi,
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

    When 359 bases are absent (class 1/2), build one continuous OA timeline
    on 277 amounts from 01.01.2017 through the horizon.
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

    has_277 = b277 is not None or a277 is not None
    has_359 = b359 is not None or a359 is not None
    # Class 1/2: no post-277 CPI revision — carry 277 bases across 2017→horizon.
    class12_continuous = has_277 and not has_359

    columns: list[dict[str, Any]] = []
    if class12_continuous:
        columns.extend(
            _build_cpi_columns(
                dob=dob_d,
                cpi=277,
                year_label="2017",
                window_start=CPI_277_FROM,
                window_end=None,
                m2=b277,
                m1=a277,
                kind=kind,
                continuous_277=True,
            )
        )
    else:
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
        "class12_continuous_277": class12_continuous,
        "oldage_wef_80": wef80.isoformat(),
        "oldage_wef_80_display": _month_label(wef80),
        "date_of_birth": dob_d.isoformat(),
        "as_on_date": as_on.isoformat(),
        "section_title": (
            "EMPLOYEE PENSION" if is_employee_pension else "FAMILY PENSION"
        ),
        "is_employee_pension": is_employee_pension,
        "columns": columns,
        # Family Methodology-1 only. Empty while the employee is alive.
        "m1_family_pension_277": (
            None if is_employee_pension else _float_or_none(a277)
        ),
        "m1_family_pension_359": (
            None if is_employee_pension else _float_or_none(a359)
        ),
        "display_m2_277": columns[0]["m2"] if columns else _float_or_none(b277),
        "display_m2_359": (
            None
            if class12_continuous
            else next(
                (c["m2"] for c in reversed(columns) if c.get("cpi") == 359),
                None,
            )
        ),
    }
