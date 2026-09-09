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


# Shared claim-source predicates (aliases: f = pensioner, c = claim)
# CM = From E-Form, CA = From Proposal (matches claim entry form)
_SQL_IS_EFORM = """
(
    UPPER(TRIM(COALESCE(c.CLM_CA_TYPE, ''))) IN ('CM', 'E')
    OR (
        TRIM(f.CLMCA_ID) LIKE 'CM/%'
        AND UPPER(TRIM(COALESCE(c.CLM_CA_TYPE, ''))) NOT IN ('CA', 'P')
    )
)
""".strip()

_SQL_IS_PROPOSAL = """
(
    UPPER(TRIM(COALESCE(c.CLM_CA_TYPE, ''))) IN ('CA', 'P')
    OR (
        TRIM(f.CLMCA_ID) LIKE 'CA/%'
        AND UPPER(TRIM(COALESCE(c.CLM_CA_TYPE, ''))) NOT IN ('CM', 'E')
    )
)
""".strip()


def _claim_source_search_mode(search: str) -> str | None:
    """Map table search text to CM/CA claim-source filters (not free-text)."""
    key = "".join(ch for ch in (search or "").lower() if ch.isalnum())
    if key in ("cm", "eform", "fromeform"):
        return "eform"
    if key in ("ca", "proposal", "fromproposal"):
        return "proposal"
    return None


def family_pensioner_summary() -> dict:
    """
    Lightweight analytics for FP dashboard stat cards.

    - Total records / From E-Form / From Proposal = **master rows**
      (same unit as DataTables "entries").
    - Employees / Class* = **distinct EMP_CD**.

    Claim source CM / CA from fi_pn_mh_fpen_caclaim.CLM_CA_TYPE
    (fallback: CLMCA_ID prefix CM/ or CA/).
    CM = From E-Form, CA = From Proposal.
    """
    sql = f"""
        SELECT
            COUNT(*) AS total_rows,
            COUNT(DISTINCT NULLIF(TRIM(f.EMP_CD), '')) AS unique_emps,
            SUM(CASE WHEN {_SQL_IS_EFORM} THEN 1 ELSE 0 END) AS from_eform,
            SUM(CASE WHEN {_SQL_IS_PROPOSAL} THEN 1 ELSE 0 END) AS from_proposal,
            COUNT(DISTINCT CASE
                WHEN ec.emp_class IN ('1', '2') THEN ec.emp_cd
            END) AS class_1_2,
            COUNT(DISTINCT CASE
                WHEN ec.emp_class IN ('3', '4') THEN ec.emp_cd
            END) AS class_3_4,
            COUNT(DISTINCT CASE
                WHEN ec.emp_class IS NULL
                  OR ec.emp_class NOT IN ('1', '2', '3', '4')
                THEN ec.emp_cd
            END) AS class_other
        FROM fi_pn_mh_familypensioner f
        LEFT JOIN fi_pn_mh_fpen_caclaim c
               ON c.CLMCA_ID = f.CLMCA_ID
        LEFT JOIN (
            SELECT
                NULLIF(TRIM(EMP_CD), '') AS emp_cd,
                CAST(
                    MAX(
                        CASE
                            WHEN APP_CLASS IS NULL OR TRIM(CAST(APP_CLASS AS CHAR)) = ''
                            THEN NULL
                            ELSE TRIM(CAST(APP_CLASS AS CHAR))
                        END
                    ) AS CHAR
                ) AS emp_class
            FROM fi_pn_mh_familypensioner
            WHERE NULLIF(TRIM(EMP_CD), '') IS NOT NULL
            GROUP BY NULLIF(TRIM(EMP_CD), '')
        ) ec ON ec.emp_cd = NULLIF(TRIM(f.EMP_CD), '')
    """

    conn = connections["default"]
    with conn.cursor() as cur:
        cur.execute(sql)
        row = cur.fetchone() or ()

    def _i(idx, default=0):
        try:
            v = row[idx]
            if v is None:
                return default
            return int(v)
        except (IndexError, TypeError, ValueError):
            return default

    return {
        "total_rows": _i(0),
        "unique_emps": _i(1),
        "from_eform": _i(2),
        "from_proposal": _i(3),
        "class_1_2": _i(4),
        "class_3_4": _i(5),
        "class_other": _i(6),
    }


def datatable_family_pensioners(params) -> dict:
    """
    DataTables server-side response for the Family Pension dashboard.

    Search:
      - "cm" / "eform" → claim type From E-Form (same as dashboard card)
      - "ca" / "proposal" → claim type From Proposal
      - otherwise free-text on emp / roll / claim id / ca number
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
    source_mode = _claim_source_search_mode(search)

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
    order_sql = (
        f"f.{ORDER_COLUMNS[order_col]} {order_dir.upper()}, f.SL_NO ASC"
    )

    from_join = """
        FROM fi_pn_mh_familypensioner f
        LEFT JOIN fi_pn_mh_fpen_caclaim c
               ON c.CLMCA_ID = f.CLMCA_ID
    """
    where_sql = ""
    where_params: list = []
    if source_mode == "eform":
        where_sql = f" WHERE {_SQL_IS_EFORM} "
    elif source_mode == "proposal":
        where_sql = f" WHERE {_SQL_IS_PROPOSAL} "
    elif search:
        like = f"%{search}%"
        where_sql = """
            WHERE f.EMP_CD LIKE %s
               OR f.FPENSION_ROLL_NO LIKE %s
               OR f.CLMCA_ID LIKE %s
               OR f.CA_NUMBER LIKE %s
        """
        where_params = [like, like, like, like]

    select_cols = ", ".join(f"f.{col.strip()}" for col in _SELECT.split(",") if col.strip())

    conn = connections["default"]
    with conn.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM fi_pn_mh_familypensioner")
        records_total = int(cur.fetchone()[0] or 0)

        if where_sql:
            cur.execute(
                f"SELECT COUNT(*) {from_join} {where_sql}",
                where_params,
            )
            records_filtered = int(cur.fetchone()[0] or 0)
        else:
            records_filtered = records_total

        cur.execute(
            f"""
            SELECT {select_cols}
            {from_join}
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
