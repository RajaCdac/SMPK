"""
Family pensioner list from local MySQL smpk_pension.fi_pn_mh_familypensioner.

Supports DataTables server-side processing (draw / start / length / search / order).
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from django.db import connections

# Column index → SQL expression (must match frontend column order).
ORDER_COLUMNS = [
    "EMP_CD",
    "FPENSION_ROLL_NO",
    "CLMCA_ID",
    "CA_NUMBER",
    "ORIGINAL_SINGLE_FPENSION_AMT",
    "ORIGINAL_DOUBLE_FPENSION_AMT",
    "BASE_CPI",
    "APP_CLASS",
    "EMP_RET_DT",
    "WEF_DT",
    "DOUBLE_FPENSION_UPTO",
]


def _fmt_date(value):
    if value is None:
        return ""
    if isinstance(value, datetime):
        return value.strftime("%d-%m-%Y")
    if isinstance(value, date):
        return value.strftime("%d-%m-%Y")
    text = str(value).strip()
    return text[:10] if text else ""


def _num(value):
    if value is None:
        return None
    if isinstance(value, Decimal):
        return float(value)
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _row_dict(row):
    (
        emp_cd,
        roll_no,
        clmca_id,
        ca_number,
        sl_no,
        single_amt,
        double_amt,
        family_amt,
        base_cpi,
        emp_ret_dt,
        wef_dt,
        app_class,
        double_upto,
    ) = row
    return {
        "emp_cd": str(emp_cd or "").strip(),
        "roll_no": str(roll_no or "").strip(),
        "claim_id": str(clmca_id or "").strip(),
        "ca_number": str(ca_number or "").strip(),
        "sl_no": sl_no,
        "original_single_pension_amt": _num(single_amt),
        "original_double_pension_amt": _num(double_amt),
        "original_family_pension_amt": _num(family_amt),
        "base_cpi": _num(base_cpi),
        "emp_ret_dt": _fmt_date(emp_ret_dt),
        "wef_dt": _fmt_date(wef_dt),
        "app_class": app_class,
        "double_pension_upto": _fmt_date(double_upto),
    }


_SELECT = """
    EMP_CD,
    FPENSION_ROLL_NO,
    CLMCA_ID,
    CA_NUMBER,
    SL_NO,
    ORIGINAL_SINGLE_FPENSION_AMT,
    ORIGINAL_DOUBLE_FPENSION_AMT,
    ORIGINAL_FAMILY_PENSION_AMT,
    BASE_CPI,
    EMP_RET_DT,
    WEF_DT,
    APP_CLASS,
    DOUBLE_FPENSION_UPTO
"""


def _parse_int(value, default):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def datatable_family_pensioners(params) -> dict:
    """
    DataTables server-side response for the Family Pension dashboard.

    Expected query params (classic DataTables):
      draw, start, length, search[value], order[0][column], order[0][dir]
    """
    draw = _parse_int(params.get("draw"), 1)
    start = max(0, _parse_int(params.get("start"), 0))
    length = _parse_int(params.get("length"), 25)
    if length < 0 or length > 500:
        length = 25

    search = (
        params.get("search[value]")
        or params.get("search.value")
        or ""
    )
    search = str(search).strip()

    order_col = _parse_int(
        params.get("order[0][column]") or params.get("order.0.column"),
        0,
    )
    order_dir = str(
        params.get("order[0][dir]") or params.get("order.0.dir") or "asc"
    ).lower()
    if order_dir not in ("asc", "desc"):
        order_dir = "asc"
    if order_col < 0 or order_col >= len(ORDER_COLUMNS):
        order_col = 0
    order_sql = f"{ORDER_COLUMNS[order_col]} {order_dir.upper()}, SL_NO ASC"

    where_sql = ""
    where_params: list = []
    if search:
        like = f"%{search}%"
        where_sql = """
            WHERE EMP_CD LIKE %s
               OR FPENSION_ROLL_NO LIKE %s
               OR CLMCA_ID LIKE %s
               OR CA_NUMBER LIKE %s
        """
        where_params = [like, like, like, like]

    conn = connections["default"]
    with conn.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM fi_pn_mh_familypensioner")
        records_total = int(cur.fetchone()[0] or 0)

        if where_sql:
            cur.execute(
                f"SELECT COUNT(*) FROM fi_pn_mh_familypensioner {where_sql}",
                where_params,
            )
            records_filtered = int(cur.fetchone()[0] or 0)
        else:
            records_filtered = records_total

        cur.execute(
            f"""
            SELECT {_SELECT}
            FROM fi_pn_mh_familypensioner
            {where_sql}
            ORDER BY {order_sql}
            LIMIT %s OFFSET %s
            """,
            [*where_params, length, start],
        )
        data = [_row_dict(row) for row in cur.fetchall()]

    return {
        "draw": draw,
        "recordsTotal": records_total,
        "recordsFiltered": records_filtered,
        "data": data,
    }


def list_family_pensioners():
    """Full list (legacy). Prefer datatable_family_pensioners for the UI."""
    sql = f"""
        SELECT {_SELECT}
        FROM fi_pn_mh_familypensioner
        ORDER BY EMP_CD, SL_NO
    """
    conn = connections["default"]
    with conn.cursor() as cur:
        cur.execute(sql)
        return [_row_dict(row) for row in cur.fetchall()]
