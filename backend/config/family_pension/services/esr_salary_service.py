"""
ESR Salary — Oracle FI_PR style (always MySQL smpk_pension / default DB):
  fi_pr_th_salout  — monthly salary header
  fi_pr_td_salout  — earning / deduction detail
  fi_pm_mh_earndedn / fi_pn_mh_earndedn — code descriptions
"""

from __future__ import annotations

from datetime import date, datetime
import time

from django.db import connections

from family_pension.services.esr_service import _fmt_value, _parse_int, _str

# Oracle dumps use utf8mb4_unicode_ci; MySQL 8 recreates may use utf8mb4_0900_ai_ci.
_SQL_COLLATE = "utf8mb4_unicode_ci"


def _collate(expr: str) -> str:
    return f"({expr}) COLLATE {_SQL_COLLATE}"


def _sql_eq(left: str, right: str) -> str:
    """String equality safe across mixed utf8mb4 collations."""
    return f"{_collate(left)} = {_collate(right)}"


_SAL_MONTH_NAMES = (
    "",
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

_SAL_NAME_JOIN = """
TRIM(CONCAT_WS(
    ' ',
    NULLIF(TRIM(p.TITLE), ''),
    NULLIF(TRIM(p.FIRST_NAME), ''),
    NULLIF(TRIM(p.MIDDLE_NAME), ''),
    NULLIF(TRIM(p.LAST_NAME), '')
))
""".strip()

_SAL_LIST_ORDER = [
    "EMP_CD",
    "NAME_EXPR",
    "LAST_SAL_YM",
    "BASIC_RATE",
    "GROSS_EARN_AMT",
    "NET_EARN_AMT",
    "SCALE_DESC",
]


def _fmt_money(value):
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _fmt_date(value) -> str:
    if value is None:
        return ""
    if isinstance(value, datetime):
        return value.date().strftime("%d/%m/%y")
    if isinstance(value, date):
        return value.strftime("%d/%m/%y")
    text = _str(value)
    return text


def _month_label(sal_mth, sal_yr) -> str:
    try:
        m = int(sal_mth)
        y = int(sal_yr)
    except (TypeError, ValueError):
        return ""
    name = _SAL_MONTH_NAMES[m] if 1 <= m <= 12 else str(m)
    return f"{name} {y}"


def _type_label(code) -> str:
    t = _str(code).upper()
    if t == "E":
        return "Earning"
    if t == "D":
        return "Deduction"
    if t == "G":
        return "Employer"
    return t or "—"


def _earndedn_desc_map(codes: list[str]) -> dict:
    """Resolve descriptions from payroll (fi_pm) then pension (fi_pn) masters."""
    out = {}
    if not codes:
        return out
    # Salary lines use payroll codes (001 Basic, 007 DA, …).
    # Pension masters only have 200+/600+ — both must be queried and merged.
    normalized = sorted({_str(c).strip() for c in codes if _str(c).strip()})
    # Also match zero-padded 3-char codes (001) when TD stores bare digits.
    lookup_keys = sorted(
        {
            *normalized,
            *[c.zfill(3) for c in normalized if c.isdigit() and len(c) < 3],
        }
    )
    if not lookup_keys:
        return out
    placeholders = ", ".join(["%s"] * len(lookup_keys))
    params = list(lookup_keys)

    def _load(table: str) -> list:
        try:
            with connections["default"].cursor() as cur:
                cur.execute(
                    f"""
                    SELECT EARNDEDN_CD, EARNDEDN_DESC
                    FROM {table}
                    WHERE TRIM(EARNDEDN_CD) IN ({placeholders})
                    """,
                    params,
                )
                return list(cur.fetchall() or [])
        except Exception:
            # Table missing / wrong schema — try without TRIM (some dumps).
            try:
                with connections["default"].cursor() as cur:
                    cur.execute(
                        f"""
                        SELECT EARNDEDN_CD, EARNDEDN_DESC
                        FROM {table}
                        WHERE EARNDEDN_CD IN ({placeholders})
                        """,
                        params,
                    )
                    return list(cur.fetchall() or [])
            except Exception:
                return []

    # Pension first, payroll overwrites — salary codes win when both exist.
    for row in _load("fi_pn_mh_earndedn") + _load("fi_pm_mh_earndedn"):
        if not row or len(row) < 2:
            continue
        key = _str(row[0]).strip()
        text = _str(row[1]).strip()
        if key and text:
            out[key] = text
            # Allow lookup by unpadded form too
            if key.isdigit():
                out[str(int(key))] = text
    return out


def _lines_for_months(emp_cd: str, months: list) -> dict:
    """Earning/deduction lines keyed by (yr, mth) from smpk_pension.fi_pr_td_salout."""
    if not months:
        return {}
    grouped: dict = {key: [] for key in months}
    clauses = []
    params: list = [emp_cd]
    for yr, mth in months:
        clauses.append("(d.SAL_YR = %s AND d.SAL_MTH = %s)")
        params.extend([yr, mth])
    # Prefer JOIN for descriptions (works even when separate master lookup fails).
    sql = f"""
        SELECT
            d.SAL_YR,
            d.SAL_MTH,
            d.EARNDEDN_CD,
            d.EARNDEDN_TYPE,
            d.NO_OF_UNITS,
            d.RATE,
            d.RATE_PCT_FLG,
            d.ACT_EARNDEDN_AMT,
            d.ADJ_EARNDEDN_AMT,
            d.ARR_EARN_AMT,
            COALESCE(
                NULLIF(TRIM(pm.EARNDEDN_DESC), ''),
                NULLIF(TRIM(pn.EARNDEDN_DESC), '')
            ) AS EARNDEDN_DESC
        FROM fi_pr_td_salout d
        LEFT JOIN fi_pm_mh_earndedn pm
          ON {_sql_eq("TRIM(pm.EARNDEDN_CD)", "TRIM(d.EARNDEDN_CD)")}
        LEFT JOIN fi_pn_mh_earndedn pn
          ON {_sql_eq("TRIM(pn.EARNDEDN_CD)", "TRIM(d.EARNDEDN_CD)")}
        WHERE {_collate("d.EMP_CD")} = %s
          AND ({' OR '.join(clauses)})
        ORDER BY d.SAL_YR DESC, d.SAL_MTH DESC, d.EARNDEDN_CD ASC
    """
    raw_rows = None
    try:
        with connections["default"].cursor() as cur:
            cur.execute(sql, params)
            raw_rows = cur.fetchall()
    except Exception:
        # Older DB without masters — fall back to lines only.
        sql_plain = f"""
            SELECT
                d.SAL_YR,
                d.SAL_MTH,
                d.EARNDEDN_CD,
                d.EARNDEDN_TYPE,
                d.NO_OF_UNITS,
                d.RATE,
                d.RATE_PCT_FLG,
                d.ACT_EARNDEDN_AMT,
                d.ADJ_EARNDEDN_AMT,
                d.ARR_EARN_AMT,
                NULL AS EARNDEDN_DESC
            FROM fi_pr_td_salout d
            WHERE {_collate("d.EMP_CD")} = %s
              AND ({' OR '.join(clauses)})
            ORDER BY d.SAL_YR DESC, d.SAL_MTH DESC, d.EARNDEDN_CD ASC
        """
        try:
            with connections["default"].cursor() as cur:
                cur.execute(sql_plain, params)
                raw_rows = cur.fetchall()
        except Exception:
            return grouped

    if not raw_rows:
        return grouped

    codes = sorted({_str(r[2]).strip() for r in raw_rows if r[2]})
    descs = _earndedn_desc_map(codes)

    for r in raw_rows:
        yr, mth = int(r[0]), int(r[1])
        key = (yr, mth)
        if key not in grouped:
            grouped[key] = []
        code = _str(r[2]).strip()
        rate_pct = int(r[6] or 0)
        joined_desc = _str(r[10]).strip() if len(r) > 10 else ""
        desc = joined_desc or descs.get(code) or descs.get(code.zfill(3)) or "—"
        grouped[key].append(
            {
                "code": code,
                "desc": desc,
                "type": _type_label(r[3]),
                "type_cd": _str(r[3]),
                "no_of_units": _fmt_money(r[4]),
                "rate": _fmt_money(r[5]),
                "rate_pct_flg": rate_pct,
                "actual": _fmt_money(r[7]),
                "adjusted": _fmt_money(r[8]),
                "arrear": _fmt_money(r[9]),
            }
        )
    return grouped


def get_emp_salary(emp_cd: str, months: int = 10) -> dict:
    """
    Last N salary months (header like Oracle FI_PR_TH_SALOUT)
    plus earning/deduction lines (FI_PR_TD_SALOUT) per month.
    """
    code = _str(emp_cd)[:5]
    if not code:
        return {"error": "Employee Code is required"}
    limit = max(1, min(24, int(months or 10)))

    conn = connections["default"]
    with conn.cursor() as cur:
        cur.execute(
            f"""
            SELECT
                {_SAL_NAME_JOIN} AS full_name,
                p.STATUS
            FROM fi_xx_mh_emp_per p
            WHERE {_collate("p.EMP_CD")} = %s
            LIMIT 1
            """,
            [code],
        )
        name_row = cur.fetchone()
        display_name = _str(name_row[0]) if name_row else ""
        status_raw = _str(name_row[1]) if name_row else ""

        cur.execute(
            f"""
            SELECT
                SAL_YR,
                SAL_MTH,
                FA_NO,
                SAL_BILL_NO,
                BASIC_RATE,
                SCALE_DESC,
                GROSS_EARN_AMT,
                NET_EARN_AMT,
                GROSS_DEDN_AMT,
                WG_ST_DT,
                WG_END_DT
            FROM fi_pr_th_salout
            WHERE {_collate("EMP_CD")} = %s
            ORDER BY SAL_YR DESC, SAL_MTH DESC
            LIMIT %s
            """,
            [code, limit],
        )
        rows = cur.fetchall()

    if not rows:
        return {
            "found": False,
            "emp_cd": code,
            "error": f"No salary records found for employee {code}",
        }

    month_keys = [(int(r[0]), int(r[1])) for r in rows]
    lines_map = _lines_for_months(code, month_keys)

    months_out = []
    for r in rows:
        sal_yr, sal_mth = int(r[0]), int(r[1])
        lines = lines_map.get((sal_yr, sal_mth)) or []
        # DA / ADA highlight from earn code 007
        da_amt = None
        for line in lines:
            if line.get("code") == "007":
                da_amt = line.get("actual")
                break
        months_out.append(
            {
                "sal_yr": sal_yr,
                "sal_mth": sal_mth,
                "month_label": _month_label(sal_mth, sal_yr),
                "fa_no": _str(r[2]).strip(),
                "sal_bill_no": _str(r[3]).strip(),
                "basic": _fmt_money(r[4]),
                "basic_rate": _fmt_money(r[4]),
                "scale_desc": _str(r[5]) or "—",
                "gross": _fmt_money(r[6]),
                "gross_earn_amt": _fmt_money(r[6]),
                "net": _fmt_money(r[7]),
                "net_earn_amt": _fmt_money(r[7]),
                "deduction": _fmt_money(r[8]),
                "gross_dedn_amt": _fmt_money(r[8]),
                "wg_st_dt": _fmt_date(r[9]) or "—",
                "wg_end_dt": _fmt_date(r[10]) or "—",
                "da": da_amt,
                "lines": lines,
            }
        )

    latest = months_out[0] if months_out else None
    return {
        "found": True,
        "emp_cd": code,
        "display_name": display_name or code,
        "status": _fmt_value("STATUS", status_raw) if status_raw else "",
        "months_count": len(months_out),
        "latest_month": latest["month_label"] if latest else "",
        "months": months_out,
    }


def summary_emp_salary() -> dict:
    """Analytics for ESR Salary dashboard cards."""
    sql = """
        SELECT
            COUNT(*) AS total_rows,
            COUNT(DISTINCT EMP_CD) AS total_emp,
            COUNT(DISTINCT SAL_YR * 100 + SAL_MTH) AS distinct_months,
            MAX(SAL_YR * 100 + SAL_MTH) AS latest_ym
        FROM fi_pr_th_salout
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

    latest_ym = _i(3)
    latest_label = ""
    if latest_ym:
        y, m = divmod(latest_ym, 100)
        latest_label = _month_label(m, y)

    latest_emp = 0
    if latest_ym:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT COUNT(DISTINCT EMP_CD)
                FROM fi_pr_th_salout
                WHERE SAL_YR * 100 + SAL_MTH = %s
                """,
                [latest_ym],
            )
            latest_emp = int((cur.fetchone() or (0,))[0] or 0)

    # Keep list endpoint total in sync (avoids another full COUNT DISTINCT).
    global _SAL_TOTAL_CACHE
    _SAL_TOTAL_CACHE = {"n": _i(1), "t": time.time()}

    return {
        "total_rows": _i(0),
        "total_emp": _i(1),
        "distinct_months": _i(2),
        "latest_month": latest_label,
        "latest_month_emp": latest_emp,
    }


_SAL_TOTAL_CACHE = {"n": None, "t": 0.0}
_SAL_TOTAL_TTL_SEC = 90.0


def _cached_emp_salary_total(conn) -> int:
    """COUNT(DISTINCT EMP_CD) is heavy on large salout — short TTL cache."""
    global _SAL_TOTAL_CACHE
    now = time.time()
    if (
        _SAL_TOTAL_CACHE["n"] is not None
        and (now - float(_SAL_TOTAL_CACHE["t"] or 0)) < _SAL_TOTAL_TTL_SEC
    ):
        return int(_SAL_TOTAL_CACHE["n"])
    with conn.cursor() as cur:
        cur.execute("SELECT COUNT(DISTINCT EMP_CD) FROM fi_pr_th_salout")
        n = int(cur.fetchone()[0] or 0)
    _SAL_TOTAL_CACHE = {"n": n, "t": now}
    return n


def _search_looks_like_emp_cd(text: str) -> bool:
    """Prefer index-friendly EMP_CD matching for short alphanumeric terms."""
    t = (text or "").strip()
    if not t or len(t) > 8:
        return False
    if " " in t:
        return False
    return t.replace("-", "").isalnum()


def datatable_emp_salary(params) -> dict:
    """
    DataTables list of employees with salary (latest month snapshot).

    Server-side paging/sort/search. Emp-code searches use EMP_CD prefix so the
    latest-month GROUP BY is not computed over the full salout table.
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
    if order_col < 0 or order_col >= len(_SAL_LIST_ORDER):
        order_col = 0
    order_key = _SAL_LIST_ORDER[order_col]

    if order_key == "NAME_EXPR":
        order_sql = f"({_SAL_NAME_JOIN}) {order_dir.upper()}, s.EMP_CD ASC"
    elif order_key == "LAST_SAL_YM":
        order_sql = (
            f"(s.SAL_YR * 100 + s.SAL_MTH) {order_dir.upper()}, s.EMP_CD ASC"
        )
    elif order_key == "EMP_CD":
        order_sql = f"s.EMP_CD {order_dir.upper()}"
    else:
        order_sql = f"s.{order_key} {order_dir.upper()}, s.EMP_CD ASC"

    if search and not _search_looks_like_emp_cd(search):
        like_any = f"%{search}%"
        latest_from = f"""
            FROM fi_pr_th_salout s
            INNER JOIN (
                SELECT s_all.EMP_CD, MAX(s_all.SAL_YR * 100 + s_all.SAL_MTH) AS ym
                FROM fi_pr_th_salout s_all
                INNER JOIN (
                    SELECT EMP_CD
                    FROM fi_xx_mh_emp_per
                    WHERE FIRST_NAME LIKE %s
                       OR LAST_NAME LIKE %s
                       OR MIDDLE_NAME LIKE %s
                       OR EMP_CD LIKE %s
                       OR TRIM(CONCAT_WS(
                            ' ',
                            NULLIF(TRIM(TITLE), ''),
                            NULLIF(TRIM(FIRST_NAME), ''),
                            NULLIF(TRIM(MIDDLE_NAME), ''),
                            NULLIF(TRIM(LAST_NAME), '')
                       )) LIKE %s
                ) match_e ON {_sql_eq("match_e.EMP_CD", "s_all.EMP_CD")}
                GROUP BY s_all.EMP_CD
            ) lm ON {_sql_eq("lm.EMP_CD", "s.EMP_CD")}
                AND (s.SAL_YR * 100 + s.SAL_MTH) = lm.ym
            LEFT JOIN fi_xx_mh_emp_per p ON {_sql_eq("p.EMP_CD", "s.EMP_CD")}
        """
        where_params = [like_any] * 5
        count_sql = f"""
            SELECT COUNT(DISTINCT match_e.EMP_CD)
            FROM fi_xx_mh_emp_per match_e
            INNER JOIN fi_pr_th_salout s_all ON {_sql_eq("s_all.EMP_CD", "match_e.EMP_CD")}
            WHERE match_e.FIRST_NAME LIKE %s
               OR match_e.LAST_NAME LIKE %s
               OR match_e.MIDDLE_NAME LIKE %s
               OR match_e.EMP_CD LIKE %s
               OR TRIM(CONCAT_WS(
                    ' ',
                    NULLIF(TRIM(match_e.TITLE), ''),
                    NULLIF(TRIM(match_e.FIRST_NAME), ''),
                    NULLIF(TRIM(match_e.MIDDLE_NAME), ''),
                    NULLIF(TRIM(match_e.LAST_NAME), '')
               )) LIKE %s
        """
        count_params = [like_any] * 5
    elif search:
        like_code = f"{search}%"
        latest_from = f"""
            FROM fi_pr_th_salout s
            INNER JOIN (
                SELECT EMP_CD, MAX(SAL_YR * 100 + SAL_MTH) AS ym
                FROM fi_pr_th_salout
                WHERE {_collate("EMP_CD")} LIKE %s
                GROUP BY EMP_CD
            ) lm ON {_sql_eq("lm.EMP_CD", "s.EMP_CD")}
                AND (s.SAL_YR * 100 + s.SAL_MTH) = lm.ym
            LEFT JOIN fi_xx_mh_emp_per p ON {_sql_eq("p.EMP_CD", "s.EMP_CD")}
        """
        where_params = [like_code]
        count_sql = f"""
            SELECT COUNT(DISTINCT EMP_CD)
            FROM fi_pr_th_salout
            WHERE {_collate("EMP_CD")} LIKE %s
        """
        count_params = [like_code]
    else:
        latest_from = f"""
            FROM fi_pr_th_salout s
            INNER JOIN (
                SELECT EMP_CD, MAX(SAL_YR * 100 + SAL_MTH) AS ym
                FROM fi_pr_th_salout
                GROUP BY EMP_CD
            ) lm ON {_sql_eq("lm.EMP_CD", "s.EMP_CD")}
                AND (s.SAL_YR * 100 + s.SAL_MTH) = lm.ym
            LEFT JOIN fi_xx_mh_emp_per p ON {_sql_eq("p.EMP_CD", "s.EMP_CD")}
        """
        where_params = []
        count_sql = None
        count_params = []

    conn = connections["default"]
    with conn.cursor() as cur:
        records_total = _cached_emp_salary_total(conn)

        if not search:
            records_filtered = records_total
        else:
            cur.execute(count_sql, count_params)
            records_filtered = int(cur.fetchone()[0] or 0)

        cur.execute(
            f"""
            SELECT
                s.EMP_CD,
                {_SAL_NAME_JOIN} AS full_name,
                s.SAL_YR,
                s.SAL_MTH,
                s.BASIC_RATE,
                s.GROSS_EARN_AMT,
                s.NET_EARN_AMT,
                s.SCALE_DESC
            {latest_from}
            ORDER BY {order_sql}
            LIMIT %s OFFSET %s
            """,
            [*where_params, length, start],
        )
        data = []
        for row in cur.fetchall():
            emp, full_name, sal_yr, sal_mth, basic, gross, net, scale = row
            data.append(
                {
                    "emp_cd": _str(emp),
                    "full_name": _str(full_name) or "—",
                    "last_month": _month_label(sal_mth, sal_yr) or "—",
                    "basic": _fmt_money(basic),
                    "gross": _fmt_money(gross),
                    "net": _fmt_money(net),
                    "scale_desc": _str(scale) or "—",
                }
            )

    return {
        "draw": draw,
        "recordsTotal": records_total,
        "recordsFiltered": records_filtered,
        "data": data,
    }


class SalarySaveError(Exception):
    """Validation / save failure for ESR salary next month."""


def _as_dec(value, field_label="Amount"):
    if value is None or value == "":
        return None
    try:
        from decimal import Decimal, InvalidOperation

        return Decimal(str(value).replace(",", "").strip())
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise SalarySaveError(f"Invalid {field_label}") from exc


def save_emp_salary_month(data: dict, *, user_code: str = "") -> dict:
    """
    Insert or update one payroll month (fi_pr_th_salout + 001/007 lines).

    Header is written to default DB (where list/detail header is read).
    Header and detail lines are written to smpk_pension (default DB) only.
    """
    from calendar import monthrange
    from decimal import Decimal
    from django.utils import timezone

    emp_cd = _str(data.get("emp_cd"))[:5]
    if not emp_cd:
        raise SalarySaveError("Employee Code is required")

    try:
        sal_yr = int(data.get("sal_yr"))
        sal_mth = int(data.get("sal_mth"))
    except (TypeError, ValueError) as exc:
        raise SalarySaveError("Salary year/month are required") from exc
    if sal_mth < 1 or sal_mth > 12:
        raise SalarySaveError("Invalid salary month")
    if sal_yr < 1990 or sal_yr > 2100:
        raise SalarySaveError("Invalid salary year")

    basic = _as_dec(data.get("basic_rate"), "basic rate")
    if basic is None:
        raise SalarySaveError("Basic rate is required")
    if basic < 0:
        raise SalarySaveError("Basic rate cannot be negative")

    scale = _str(data.get("scale_desc"))[:40]
    if scale in ("—", "-", "–"):
        scale = ""

    # Lines from client; always force 001 from basic; keep 007 if provided.
    raw_lines = data.get("lines") or []
    if not isinstance(raw_lines, list):
        raw_lines = []
    by_code = {}
    for line in raw_lines:
        if not isinstance(line, dict):
            continue
        code = _str(line.get("code") or line.get("earndedn_cd"))[:3]
        if code:
            by_code[code] = line

    line_001 = by_code.get("001") or {}
    line_007 = by_code.get("007") or {}

    def _line_amt(line, key, default=None):
        if not line:
            return default
        v = line.get(key)
        if v is None or v == "":
            return default
        return _as_dec(v, key)

    rate_001 = _line_amt(line_001, "rate", basic) or basic
    act_001 = _line_amt(line_001, "actual", basic) or basic
    # Keep header basic in sync with what we store on 001.
    rate_001 = basic
    act_001 = basic

    rate_007 = _line_amt(line_007, "rate", None)
    act_007 = _line_amt(line_007, "actual", None)
    pct_007 = line_007.get("rate_pct_flg")
    try:
        pct_007 = int(pct_007) if pct_007 not in (None, "") else 0
    except (TypeError, ValueError):
        pct_007 = 0
    if pct_007 and rate_007 is not None:
        act_007 = (basic * rate_007 / Decimal("100")).quantize(Decimal("0.01"))

    type_001 = _str(line_001.get("type_cd") or "E")[:1] or "E"
    type_007 = _str(line_007.get("type_cd") or "E")[:1] or "E"

    user = _str(user_code)[:5] or "SMPK"
    today = timezone.localdate()
    last_day = monthrange(sal_yr, sal_mth)[1]
    wg_st = date(sal_yr, sal_mth, 1)
    wg_end = date(sal_yr, sal_mth, last_day)

    fa_no = _str(data.get("fa_no")).strip()
    sal_bill_no = _str(data.get("sal_bill_no")).strip()
    if fa_no in ("—", "-", "–", "null", "None"):
        fa_no = ""
    if sal_bill_no in ("—", "-", "–", "null", "None"):
        sal_bill_no = ""
    # DB FA_NO is typically 5 chars; never invent codes (FK to fi_xx_mh_fixabs).
    fa_no = fa_no[:5]

    # Resolve FA that already exists for this employee and in fixabs master.
    # Inserts FA_NO exactly as stored on fi_xx_mh_fixabs (FK is strict).
    def _resolve_valid_fa(preferred: str) -> str:
        with connections["default"].cursor() as cur:
            if preferred:
                cur.execute(
                    f"""
                    SELECT f.FA_NO
                    FROM fi_xx_mh_fixabs f
                    WHERE {_sql_eq("TRIM(f.FA_NO)", "TRIM(%s)")}
                    LIMIT 1
                    """,
                    [preferred],
                )
                row = cur.fetchone()
                if row and _str(row[0]).strip():
                    return _str(row[0])
            # Prefer last salaried month's FA for this emp that still exists in master
            cur.execute(
                f"""
                SELECT f.FA_NO
                FROM fi_pr_th_salout s
                INNER JOIN fi_xx_mh_fixabs f
                  ON {_sql_eq("TRIM(f.FA_NO)", "TRIM(s.FA_NO)")}
                WHERE {_collate("s.EMP_CD")} = %s
                  AND s.FA_NO IS NOT NULL
                  AND TRIM(s.FA_NO) <> ''
                  AND NOT (s.SAL_YR = %s AND s.SAL_MTH = %s)
                ORDER BY s.SAL_YR DESC, s.SAL_MTH DESC
                LIMIT 1
                """,
                [emp_cd, sal_yr, sal_mth],
            )
            row = cur.fetchone()
            if row and _str(row[0]).strip():
                return _str(row[0])
            # Last resort: any FA used in salout that still exists in master
            cur.execute(
                f"""
                SELECT f.FA_NO
                FROM fi_xx_mh_fixabs f
                INNER JOIN fi_pr_th_salout s
                  ON {_sql_eq("TRIM(s.FA_NO)", "TRIM(f.FA_NO)")}
                LIMIT 1
                """
            )
            row = cur.fetchone()
            if row and _str(row[0]).strip():
                return _str(row[0])
        return ""

    fa_no = _resolve_valid_fa(fa_no)
    if not fa_no:
        raise SalarySaveError(
            "No valid FA / form (FA_NO) found for this employee. "
            "Cannot save: FA_NO must exist in fi_xx_mh_fixabs "
            "(use an employee who already has a paid salary month)."
        )

    # SAL_BILL_NO is NOT NULL — mirror Oracle style SAL/<fa>/<mm>/<yyyy>
    if not sal_bill_no:
        sal_bill_no = f"SAL/{fa_no:>5}/{sal_mth:02d}/{sal_yr}"[:20]

    # Gross = 001 + 007 (earnings only for this draft row)
    gross = (act_001 or Decimal("0")) + (act_007 or Decimal("0"))
    net = gross
    dedn = Decimal("0")

    th_sql = """
        INSERT INTO fi_pr_th_salout (
            EMP_CD, SAL_MTH, SAL_YR, FA_NO, SAL_BILL_NO,
            GROSS_EARN_AMT, GROSS_DEDN_AMT, NET_EARN_AMT,
            SCALE_DESC, BASIC_RATE, WG_ST_DT, WG_END_DT,
            DATE_CREATED, DATE_MODIFIED, MODIFIED_BY, CREATED_BY
        ) VALUES (
            %s, %s, %s, %s, %s,
            %s, %s, %s,
            %s, %s, %s, %s,
            %s, %s, %s, %s
        )
        ON DUPLICATE KEY UPDATE
            BASIC_RATE = VALUES(BASIC_RATE),
            SCALE_DESC = VALUES(SCALE_DESC),
            FA_NO = VALUES(FA_NO),
            SAL_BILL_NO = VALUES(SAL_BILL_NO),
            GROSS_EARN_AMT = VALUES(GROSS_EARN_AMT),
            GROSS_DEDN_AMT = VALUES(GROSS_DEDN_AMT),
            NET_EARN_AMT = VALUES(NET_EARN_AMT),
            WG_ST_DT = VALUES(WG_ST_DT),
            WG_END_DT = VALUES(WG_END_DT),
            DATE_MODIFIED = VALUES(DATE_MODIFIED),
            MODIFIED_BY = VALUES(MODIFIED_BY)
    """
    th_params = [
        emp_cd,
        sal_mth,
        sal_yr,
        fa_no,
        sal_bill_no,
        float(gross),
        float(dedn),
        float(net),
        scale or "",
        float(basic),
        wg_st,
        wg_end,
        today,
        today,
        user,
        user,
    ]

    def _upsert_td(conn_name: str):
        lines = [
            ("001", type_001, rate_001, 0, act_001),
            ("007", type_007, rate_007, pct_007, act_007),
        ]
        with connections[conn_name].cursor() as cur:
            for code, typ, rate, pct, act in lines:
                if code == "007" and rate is None and act is None:
                    # Skip empty 007 only if completely blank
                    continue
                cur.execute(
                    """
                    INSERT INTO fi_pr_td_salout (
                        EMP_CD, SAL_MTH, SAL_YR, EARNDEDN_CD, EARNDEDN_TYPE,
                        NO_OF_UNITS, RATE, RATE_PCT_FLG,
                        ACT_EARNDEDN_AMT, ADJ_EARNDEDN_AMT, ARR_EARN_AMT,
                        DATE_CREATED, DATE_MODIFIED, MODIFIED_BY, CREATED_BY
                    ) VALUES (
                        %s, %s, %s, %s, %s,
                        %s, %s, %s,
                        %s, %s, %s,
                        %s, %s, %s, %s
                    )
                    ON DUPLICATE KEY UPDATE
                        RATE = VALUES(RATE),
                        RATE_PCT_FLG = VALUES(RATE_PCT_FLG),
                        ACT_EARNDEDN_AMT = VALUES(ACT_EARNDEDN_AMT),
                        EARNDEDN_TYPE = VALUES(EARNDEDN_TYPE),
                        DATE_MODIFIED = VALUES(DATE_MODIFIED),
                        MODIFIED_BY = VALUES(MODIFIED_BY)
                    """,
                    [
                        emp_cd,
                        sal_mth,
                        sal_yr,
                        code,
                        typ,
                        None,
                        float(rate) if rate is not None else None,
                        int(pct or 0),
                        float(act) if act is not None else None,
                        None,
                        None,
                        today,
                        today,
                        user,
                        user,
                    ],
                )

    with connections["default"].cursor() as cur:
        cur.execute(th_sql, th_params)

    try:
        _upsert_td("default")
        td_errors = []
    except Exception as exc:
        raise SalarySaveError(
            f"Header saved but detail lines failed on smpk_pension: {exc}"
        ) from exc

    # Invalidate employee total cache (new month may create a new emp on list)
    global _SAL_TOTAL_CACHE
    _SAL_TOTAL_CACHE = {"n": None, "t": 0.0}

    bundle = get_emp_salary(emp_cd, months=10)
    return {
        "ok": True,
        "message": (
            f"Salary saved for {emp_cd} — "
            f"{_month_label(sal_mth, sal_yr)} (basic {float(basic):,.2f})"
        ),
        "emp_cd": emp_cd,
        "sal_yr": sal_yr,
        "sal_mth": sal_mth,
        "basic_rate": _fmt_money(basic),
        "td_warnings": td_errors,
        **(bundle if bundle.get("found") else {}),
    }

