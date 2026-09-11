"""DA % lookup for old-age enhancement (fi_pr_mh_calc_da)."""

from __future__ import annotations

import math
from datetime import date, datetime
from decimal import Decimal

from django.db import connection

CPI_277_INCEPT = date(2017, 1, 1)
CPI_359_INCEPT = date(2022, 1, 1)


def class_grp_from_category(category) -> int:
    text = str(category or "3").strip().upper()
    if text in ("1", "2", "I", "II"):
        return 1
    return 3


def _as_date(value) -> date | None:
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    text = str(value).strip()[:10]
    for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y"):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    return None


def incepts_for_cpi(cpi: str | None) -> list[date]:
    """Prefer 2022 incept for 359-era; fall back to 2017 (class I/II often only has 2017)."""
    if str(cpi or "") == "359":
        return [CPI_359_INCEPT, CPI_277_INCEPT]
    return [CPI_277_INCEPT, CPI_359_INCEPT]


def lookup_da_pct(class_grp: int, cpi: str | None, as_of: date) -> float:
    """DA% in force on as_of for class group + CPI era."""
    if not as_of:
        return 0.0
    with connection.cursor() as cursor:
        for incept in incepts_for_cpi(cpi):
            cursor.execute(
                """
                SELECT DA_PCT
                FROM fi_pr_mh_calc_da
                WHERE EMP_CLASS_GRP = %s
                  AND INCEPT_DT = %s
                  AND WEF_DT <= %s
                ORDER BY WEF_DT DESC
                LIMIT 1
                """,
                [int(class_grp), incept, as_of],
            )
            row = cursor.fetchone()
            if row and row[0] is not None:
                return float(row[0])
    return 0.0


def da_wef_dates(class_grp: int, start: date, end: date) -> list[date]:
    """All DA WEF dates in (start, end] for 2017/2022 incepts (split points)."""
    if start > end:
        return []
    found: set[date] = set()
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT DISTINCT WEF_DT
            FROM fi_pr_mh_calc_da
            WHERE EMP_CLASS_GRP = %s
              AND INCEPT_DT IN (%s, %s)
              AND WEF_DT > %s
              AND WEF_DT <= %s
            ORDER BY WEF_DT
            """,
            [int(class_grp), CPI_277_INCEPT, CPI_359_INCEPT, start, end],
        )
        for (wef,) in cursor.fetchall():
            d = _as_date(wef)
            if d:
                found.add(d)
    return sorted(found)


def da_on_amount(amount: Decimal | float | None, da_pct: float) -> Decimal:
    """CEIL(amount × da% / 100), same style as pension bill relief."""
    if amount is None or not da_pct or da_pct <= 0:
        return Decimal("0")
    raw = float(amount) * float(da_pct) / 100.0
    return Decimal(str(int(math.ceil(raw))))
