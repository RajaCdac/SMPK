"""
Class 1/2 family pension for First FP generation only.

Does **not** alter Methodology1. Ports the officer last-pay revision
chain used for executive class FP (aligns with Oracle wage / First FP
amounts such as emp 22102 → 22575).

Real payscales in the claim/finance DB are like ``2007/RE/017``, not
``E-1`` / ``E-9``. Those codes are not required for post-1997 separations:
only last pay + separation date drive 2007 (126 CPI) and 2017 (277 CPI)
fitment. Pre-1997 starts optionally use E-grade when available for
scale-minimum steps.

Stages (on full basic, then FP = 30% of final 277 basic):
  2007: DA 78.2% + fitment 30% on (basic+DA), round up to ₹10
  2017: DA 119.8% + fitment 15% on (basic+DA), round up to ₹10
  family pension = round2(basic_2017 * 0.30)
"""

from __future__ import annotations

import math
import re
from datetime import date, datetime
from decimal import Decimal, ROUND_HALF_UP
from typing import Any, Optional, Union


class Class12FamilyPensionError(Exception):
    pass


REVISION_ORDER = ["1984", "1987", "1992", "1997", "2007", "2017"]


def _as_date(value) -> Optional[date]:
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    text = str(value).strip()[:10]
    try:
        return datetime.strptime(text, "%Y-%m-%d").date()
    except ValueError:
        return None


def _round2(amount) -> float:
    return round(float(amount), 2)


def _round_up_to_10(amount) -> int:
    """Excel ROUNDUP(value, -1) — next higher multiple of 10."""
    value = float(amount)
    if value <= 0:
        return 0
    return int(math.ceil(value / 10.0) * 10)


def _money(value) -> float:
    return float(
        Decimal(str(value or 0)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    )


def get_class12_start_revision(separation_date: Union[date, str, datetime]) -> str:
    """Separation date → starting revision stage (officer chain)."""
    if isinstance(separation_date, str):
        separation_date = datetime.strptime(separation_date[:10], "%Y-%m-%d")
    elif isinstance(separation_date, date) and not isinstance(
        separation_date, datetime
    ):
        separation_date = datetime(
            separation_date.year, separation_date.month, separation_date.day
        )

    if separation_date <= datetime(1986, 12, 31):
        return "1984"
    if separation_date <= datetime(1991, 12, 31):
        return "1987"
    if separation_date <= datetime(1996, 12, 31):
        return "1992"
    if separation_date <= datetime(2006, 12, 31):
        return "1997"
    if separation_date <= datetime(2016, 12, 31):
        return "2007"
    return "2017"


def _block_2007(basic_1997: float, rows: list) -> float:
    da = _round2(basic_1997 * 0.782)
    fitment = _round2((basic_1997 + da) * 0.30)
    basic_2007 = _round_up_to_10(basic_1997 + da + fitment)
    rows.append({"description": "DA @ 78.2% on Basic (126 CPI)", "value": da})
    rows.append(
        {"description": "Fitment @ 30% on Basic + DA", "value": fitment}
    )
    rows.append(
        {
            "description": "Basic Pay Over 126 CPI Points (01.01.2007)",
            "value": basic_2007,
        }
    )
    return float(basic_2007)


def _block_2017(basic_2007: float, rows: list) -> float:
    da = _round2(basic_2007 * 1.198)
    fitment = _round2((basic_2007 + da) * 0.15)
    basic_2017 = _round_up_to_10(basic_2007 + da + fitment)
    rows.append({"description": "DA @ 119.8% on Basic (277 CPI)", "value": da})
    rows.append(
        {"description": "Fitment @ 15% on Basic + DA", "value": fitment}
    )
    rows.append(
        {
            "description": "Basic Pay Over 277 CPI Points (01.01.2017)",
            "value": basic_2017,
        }
    )
    return float(basic_2017)


def _try_m2_class12(separation_date, last_pay, grade_or_band: Optional[str]):
    """Optional full chain with E-grade / pay-band via Methodology2 (no M1)."""
    if not grade_or_band:
        return None
    try:
        from methodology2.services.class1_2_service import (
            calculate_class12,
            validate_executive_grade,
        )

        grade = validate_executive_grade(grade_or_band, separation_date)
        if not grade:
            # Accept bare E-9 or pay-band string
            text = str(grade_or_band).strip()
            if re.match(r"^E-?\d", text, re.I):
                grade = text
            else:
                return None
        result = calculate_class12(separation_date, grade, last_pay)
        if result.get("error"):
            return None
        return result
    except Exception:
        return None


def calculate_class12_family_pension_for_fp(
    *,
    separation_date: Union[date, str, datetime],
    last_pay: float,
    scale: Optional[str] = None,
) -> dict[str, Any]:
    """
    Compute class 1/2 family pension for First FP generation.

    Returns::
        {
          "FP_277_cpi": float,   # payable family pension (at 277 / post-2017)
          "FP_359_cpi": None,    # officer path has no separate 359 FP band
          "basic_pay_2017": float,
          "start_revision": str,
          "path": str,
          "rows": list,
        }
    """
    try:
        pay = float(last_pay)
    except (TypeError, ValueError) as exc:
        raise Class12FamilyPensionError("last_pay must be a positive number") from exc
    if pay <= 0:
        raise Class12FamilyPensionError("last_pay must be a positive number")

    sep = separation_date
    if isinstance(sep, date) and not isinstance(sep, datetime):
        sep_str = sep.isoformat()
    else:
        sep_str = str(sep).strip()[:10]

    # Prefer full M2 chain if caller somehow has E-grade or pay-band text.
    full = _try_m2_class12(sep_str, pay, scale)
    if full and full.get("family_pension"):
        return {
            "FP_277_cpi": float(full["family_pension"]),
            "FP_359_cpi": None,
            "basic_pay_2017": float(full.get("basic_pay_2017") or 0),
            "start_revision": full.get("start_revision"),
            "path": "methodology2_class12",
            "grade": full.get("grade"),
            "rows": full.get("rows") or [],
        }

    start = get_class12_start_revision(sep_str)
    start_idx = REVISION_ORDER.index(start)
    rows: list = [
        {
            "description": (
                f"Basic Pay in the existing scale ({start} revised pay scale)"
            ),
            "value": pay,
        }
    ]

    # Early stages (pre-1997) need executive scale minima. Without E-grade /
    # pay-band we cannot port those; tell the user clearly.
    if start_idx <= REVISION_ORDER.index("1992"):
        raise Class12FamilyPensionError(
            "Class 1/2 FP for separation before 01/01/1997 needs an executive "
            "grade or pay-band (E-1… or min-max band). Scale codes like "
            f"2007/RE/017 alone are not enough for start stage {start}."
        )

    basic = pay
    # Port Methodology2 officer last-pay stages (no E-grade / RE code needed).
    # start "1997" → apply 2007 then 2017; "2007" → 2017 only; "2017" → 30% only.
    if start_idx <= REVISION_ORDER.index("1997"):
        basic = _block_2007(basic, rows)
    if start_idx <= REVISION_ORDER.index("2007") and start != "2017":
        basic = _block_2017(basic, rows)
    if start == "2017":
        rows.append(
            {
                "description": "Already on 2017 scale — no further officer fitment",
                "value": basic,
            }
        )

    basic_2017 = float(basic)
    family_pension = _round2(basic_2017 * 0.30)

    return {
        "FP_277_cpi": family_pension,
        "FP_359_cpi": None,
        "basic_pay_2017": basic_2017,
        "start_revision": start,
        "path": "first_fp_officer_last_pay_chain",
        "rows": rows,
        "scale_note": (
            f"Scale '{scale}' ignored for fitment (officer RE codes not needed "
            "for post-1997 last-pay chain)"
            if scale
            else None
        ),
    }


def load_familypensioner_app_class(emp_cd: Any) -> Any:
    """
    APP_CLASS from fi_pn_mh_familypensioner — primary class for family pension.

    Used when ESR (fi_xx_mh_emp_fin.EMP_CLASS) is blank; not the claim form CLASS.
    """
    emp = str(emp_cd or "").strip()
    if emp.isdigit() and len(emp) < 5:
        emp = emp.zfill(5)
    if not emp:
        return None
    sql = """
        SELECT APP_CLASS
        FROM fi_pn_mh_familypensioner
        WHERE EMP_CD = %s
          AND APP_CLASS IS NOT NULL
          AND CAST(APP_CLASS AS CHAR) <> ''
        ORDER BY DATE_CREATED DESC
        LIMIT 1
    """
    try:
        from django.db import connections

        with connections["finance"].cursor() as cur:
            cur.execute(sql, [emp])
            row = cur.fetchone()
            if row and row[0] not in (None, ""):
                return row[0]
    except Exception:
        pass
    try:
        from django.db import connection as default_conn

        with default_conn.cursor() as cur:
            cur.execute(sql, [emp])
            row = cur.fetchone()
            if row and row[0] not in (None, ""):
                return row[0]
    except Exception:
        pass
    return None


def resolve_category_for_fp(
    claim: dict,
    fin: dict,
    pensioner: dict,
    familypensioner_app_class: Any = None,
) -> str:
    """
    Resolve emp class for First FP / sanction report amounts.

    Order (business rule):
      1. fi_pn_mh_familypensioner.APP_CLASS (via load_familypensioner_app_class)
      2. ESR fi_xx_mh_emp_fin.EMP_CLASS
      3. Claim CLASS / pensioner APP_CLASS (if present)
      4. Default 3
    """
    for raw in (
        familypensioner_app_class,
        fin.get("emp_class") if fin else None,
        claim.get("class") if claim else None,
        pensioner.get("app_class") if pensioner else None,
    ):
        if raw in (None, ""):
            continue
        text = str(raw).strip().upper()
        mapping = {
            "I": "1",
            "II": "2",
            "III": "3",
            "IV": "4",
            "O": "1",
            "E": "3",
        }
        text = mapping.get(text, text)
        if text in {"1", "2", "3", "4"}:
            return text
        try:
            n = int(float(text))
            if n in (1, 2, 3, 4):
                return str(n)
        except (TypeError, ValueError):
            pass
    return "3"
