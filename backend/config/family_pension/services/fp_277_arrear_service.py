"""
Family Pension 277-upgrade arrear calculation.

Oracle form: FI_PN_FAMILY_277_UPGRADE arrear trigger
(tables fi_pn_family_277_upgrade / _dtl; type-M first-month TD earn 209/208).

Ports the Forms PL/SQL logic literally (quarter months, DA sources,
fractional first month, CEIL relief, Feb arrear_upto = 28 only).
"""

from __future__ import annotations

import calendar
import math
from datetime import date, datetime, timedelta
from decimal import Decimal

from django.db import connection, connections, transaction


class Fp277ArrearError(Exception):
    pass


# Pre/post 2017 cut-off used by the form
_CPI_SWITCH = date(2017, 1, 1)
_DA_C1_END = date(2022, 1, 1)  # c1: wef_dt < 01-jan-2022


def _clip(value, max_len=None, default=""):
    if value is None:
        return default
    text = str(value).strip()
    if not text:
        return default
    if max_len is not None:
        return text[:max_len]
    return text


def _as_date(value):
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    text = str(value).strip()[:10]
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%d-%b-%Y"):
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


def _int_money(value) -> int:
    n = _num(value)
    return int(n) if n is not None else 0


def _ceil_rupee(value) -> int:
    """Oracle CEIL for non-negative rupee amounts."""
    return int(math.ceil(float(value or 0)))


def _add_months(d: date, months: int) -> date:
    months = int(months)
    y = d.year + (d.month - 1 + months) // 12
    m = (d.month - 1 + months) % 12 + 1
    last = calendar.monthrange(y, m)[1]
    return date(y, m, min(d.day, last))


def _last_day(d: date) -> date:
    return date(d.year, d.month, calendar.monthrange(d.year, d.month)[1])


def _quarter_mth_from_start(month: int) -> int:
    """Months remaining in quarter from death+1 month (form mth)."""
    if month in (1, 4, 7, 10):
        return 3
    if month in (2, 5, 8, 11):
        return 2
    return 1


def _quarter_mth_to_end(month: int) -> int:
    """Months in quarter up to arrear_upto month (form end_mth)."""
    if month in (1, 4, 7, 10):
        return 1
    if month in (2, 5, 8, 11):
        return 2
    return 3


def _validate_arrear_upto(d: date) -> None:
    """
    Form requires arrear_upto on last calendar day of month.
    February is hardcoded to day 28 (Oracle form; no leap-year branch).
    """
    if not d:
        raise Fp277ArrearError("Upto Date Must Be Given For Arrear........")
    mm, dd = d.month, d.day
    ok = False
    if mm in (1, 3, 5, 7, 8, 10, 12):
        ok = dd == 31
    elif mm in (4, 6, 9, 11):
        ok = dd == 30
    elif mm == 2:
        ok = dd == 28
    if not ok:
        raise Fp277ArrearError(
            "Upto Date Must Be The Last Date Of The Month...."
        )


def _fetchone(sql, params=None, alias=None):
    conn = connections[alias] if alias else connection
    with conn.cursor() as cur:
        cur.execute(sql, params or [])
        row = cur.fetchone()
        if not row:
            return None
        cols = [d[0].lower() for d in cur.description]
        return dict(zip(cols, row))


def _fetchall(sql, params=None, alias=None):
    conn = connections[alias] if alias else connection
    with conn.cursor() as cur:
        cur.execute(sql, params or [])
        cols = [d[0].lower() for d in cur.description]
        return [dict(zip(cols, r)) for r in cur.fetchall()]


def _exec_calc_da(sql, params):
    """Prefer default; fall back to finance calc_da / calc_da_2022."""
    try:
        rows = _fetchall(sql, params, alias=None)
        if rows:
            return rows
    except Exception:
        pass
    try:
        rows = _fetchall(sql, params, alias="finance")
        if rows:
            return rows
    except Exception:
        pass
    # 277-era rates after 2022 often live only on finance calc_da_2022
    try:
        sql_2022 = sql.replace("fi_pr_mh_calc_da", "fi_pr_mh_calc_da_2022")
        if sql_2022 != sql:
            rows = _fetchall(sql_2022, params, alias="finance")
            if rows:
                return rows
    except Exception:
        pass
    return []


_DA_INCEPT_277 = date(2017, 1, 1)
_DA_INCEPT_359 = date(2022, 1, 1)


def _emp_key(emp_cd):
    text = _clip(emp_cd, 5)
    if text.isdigit() and len(text) < 5:
        return text.zfill(5)
    return text


def _da_class_grp(emp_class) -> int:
    """
    Forms often hardcode grp=3; map EMP_CLASS so officers use grp 1.
    1/2 → emp_class_grp 1; 3/4/other → 3.
    """
    try:
        c = int(float(emp_class))
    except (TypeError, ValueError):
        return 3
    if c in (1, 2):
        return 1
    return 3


def load_upgrade(claim_id: str = None, emp_cd: str = None):
    cid = _clip(claim_id, 20) if claim_id else ""
    emp = _emp_key(emp_cd) if emp_cd else ""
    if cid:
        return _fetchone(
            """
            SELECT CLAIM_ID, CASE_NO, EMP_CD, EMP_CLASS,
                   PENSIONER_DEATH_DT, GENERATED_CPI, UPGRADED_CPI,
                   GENERATED_BASIC, UPGRADED_BASIC, ARREAR_UPTO,
                   ARREAR_PENSION, ARREAR_RELIEF, DATE_CREATED, CREATED_BY
            FROM fi_pn_family_277_upgrade
            WHERE CLAIM_ID = %s
            LIMIT 1
            """,
            [cid],
        )
    if emp:
        return _fetchone(
            """
            SELECT CLAIM_ID, CASE_NO, EMP_CD, EMP_CLASS,
                   PENSIONER_DEATH_DT, GENERATED_CPI, UPGRADED_CPI,
                   GENERATED_BASIC, UPGRADED_BASIC, ARREAR_UPTO,
                   ARREAR_PENSION, ARREAR_RELIEF, DATE_CREATED, CREATED_BY
            FROM fi_pn_family_277_upgrade
            WHERE EMP_CD = %s
            ORDER BY DATE_CREATED DESC
            LIMIT 1
            """,
            [emp],
        )
    return None


def load_upgrade_detail(claim_id: str):
    return _fetchall(
        """
        SELECT CLAIM_ID, PERIOD_FROM, PERIOD_TO, ARR_PEN, DA_PCT, ARR_RLF
        FROM fi_pn_family_277_upgrade_dtl
        WHERE CLAIM_ID = %s
        ORDER BY PERIOD_FROM, PERIOD_TO
        """,
        [_clip(claim_id, 20)],
    )


def _relief_tag(claim_id: str) -> str | None:
    row = _fetchone(
        """
        SELECT RELIEF_TAG
        FROM fi_pn_md_fpen_appcn
        WHERE CLMCA_ID = %s AND FPEN_ACTIVE = 1
        LIMIT 1
        """,
        [_clip(claim_id, 20)],
    )
    if not row:
        return None
    tag = _clip(row.get("relief_tag"), 1)
    return tag or "Y"


def _da_anchor_wef(death_plus_1: date, class_grp: int) -> date | None:
    """max(wef_dt) on Fi_Pr_mh_calc_da for class_grp with wef <= death+1."""
    rows = _exec_calc_da(
        """
        SELECT MAX(WEF_DT) AS wef_dt
        FROM fi_pr_mh_calc_da
        WHERE EMP_CLASS_GRP = %s
          AND WEF_DT <= %s
        """,
        [int(class_grp), death_plus_1],
    )
    if not rows or rows[0].get("wef_dt") is None:
        return None
    return _as_date(rows[0]["wef_dt"])


def _cursor_c1(death_plus_1: date, arrear_upto: date, class_grp: int):
    """
    Fi_Pr_mh_calc_da for emp_class_grp,
    wef between DA-in-force at death+1 and DA-in-force on arrear_upto,
    01-jan-2017 <= wef < 01-jan-2022.
    Uses 277-era series only (INCEPT_DT = 01-jan-2017).
    """
    sql = """
        SELECT WEF_DT AS wef_dt, DA_PCT AS da_pct
        FROM fi_pr_mh_calc_da
        WHERE EMP_CLASS_GRP = %s
          AND INCEPT_DT = %s
          AND WEF_DT >= COALESCE(
              (
                  SELECT MAX(WEF_DT)
                  FROM fi_pr_mh_calc_da
                  WHERE EMP_CLASS_GRP = %s
                    AND INCEPT_DT = %s
                    AND WEF_DT <= %s
              ),
              %s
          )
          AND WEF_DT <= (
              SELECT MAX(WEF_DT)
              FROM fi_pr_mh_calc_da
              WHERE EMP_CLASS_GRP = %s
                AND INCEPT_DT = %s
                AND WEF_DT <= %s
          )
          AND WEF_DT >= %s
          AND WEF_DT < %s
        ORDER BY WEF_DT
    """
    g = int(class_grp)
    inc = _DA_INCEPT_277
    params = [
        g, inc,
        g, inc, death_plus_1, _CPI_SWITCH,
        g, inc, arrear_upto,
        _CPI_SWITCH, _DA_C1_END,
    ]
    rows = _exec_calc_da(sql, params)
    out = []
    for r in rows:
        wef = _as_date(r.get("wef_dt"))
        pct = _num(r.get("da_pct"))
        if wef is not None and pct is not None:
            out.append({"wef_dt": wef, "da_pct": float(pct)})
    return out


def _cursor_c3(
    death_plus_1: date,
    arrear_upto: date,
    class_grp: int,
    upgraded_cpi: int = 277,
):
    """
    Post-2022 DA bands (wef >= 01-jan-2022).

    - upgraded_cpi >= 359 → 359-era rates (INCEPT_DT=2022) on fi_pr_mh_calc_da
      e.g. 0 / 0.41 / 2.33 ...
    - upgraded_cpi == 277 → continue 277-era rates from finance
      fi_pr_mh_calc_da_2022 (INCEPT_DT=2017), e.g. 29.58 / 30.13 ...
      (2025+ rows in that table may carry INCEPT_DT=2022 with high DA% —
       still the 277 continuation, not the 359 zero-series.)
    """
    g = int(class_grp)
    up = int(upgraded_cpi or 277)

    if up >= 359:
        sql = """
            SELECT WEF_DT AS wef_dt, DA_PCT AS da_pct
            FROM fi_pr_mh_calc_da
            WHERE EMP_CLASS_GRP = %s
              AND INCEPT_DT = %s
              AND WEF_DT >= COALESCE(
                  (
                      SELECT MAX(WEF_DT)
                      FROM fi_pr_mh_calc_da
                      WHERE EMP_CLASS_GRP = %s
                        AND INCEPT_DT = %s
                        AND WEF_DT <= %s
                  ),
                  %s
              )
              AND WEF_DT <= (
                  SELECT MAX(WEF_DT)
                  FROM fi_pr_mh_calc_da
                  WHERE EMP_CLASS_GRP = %s
                    AND INCEPT_DT = %s
                    AND WEF_DT <= %s
              )
              AND WEF_DT >= %s
            ORDER BY WEF_DT
        """
        inc = _DA_INCEPT_359
        params = [
            g, inc,
            g, inc, death_plus_1, _DA_C1_END,
            g, inc, arrear_upto,
            _DA_C1_END,
        ]
        rows = _exec_calc_da(sql, params)
    else:
        # Prefer finance calc_da_2022 — only place with post-2022 277-era %
        cont_from = date(2025, 1, 1)
        incept_ok = """
              (
                    INCEPT_DT = %s
                 OR (INCEPT_DT = %s AND WEF_DT >= %s AND DA_PCT >= 40)
              )
        """
        sql = f"""
            SELECT WEF_DT AS wef_dt, DA_PCT AS da_pct
            FROM fi_pr_mh_calc_da_2022
            WHERE EMP_CLASS_GRP = %s
              AND {incept_ok}
              AND WEF_DT >= COALESCE(
                  (
                      SELECT MAX(WEF_DT)
                      FROM fi_pr_mh_calc_da_2022
                      WHERE EMP_CLASS_GRP = %s
                        AND {incept_ok}
                        AND WEF_DT <= %s
                  ),
                  %s
              )
              AND WEF_DT <= (
                  SELECT MAX(WEF_DT)
                  FROM fi_pr_mh_calc_da_2022
                  WHERE EMP_CLASS_GRP = %s
                    AND {incept_ok}
                    AND WEF_DT <= %s
              )
              AND WEF_DT >= %s
            ORDER BY WEF_DT
        """
        params = [
            g,
            _DA_INCEPT_277, _DA_INCEPT_359, cont_from,
            g,
            _DA_INCEPT_277, _DA_INCEPT_359, cont_from, death_plus_1, _DA_C1_END,
            g,
            _DA_INCEPT_277, _DA_INCEPT_359, cont_from, arrear_upto,
            _DA_C1_END,
        ]
        try:
            rows = _fetchall(sql, params, alias="finance")
        except Exception:
            rows = []
        if not rows:
            # Last resort via _exec_calc_da → may rewrite to calc_da_2022
            sql_fb = """
                SELECT WEF_DT AS wef_dt, DA_PCT AS da_pct
                FROM fi_pr_mh_calc_da
                WHERE EMP_CLASS_GRP = %s
                  AND INCEPT_DT = %s
                  AND WEF_DT >= %s
                  AND WEF_DT <= %s
                ORDER BY WEF_DT
            """
            rows = _exec_calc_da(
                sql_fb, [g, _DA_INCEPT_277, _DA_C1_END, arrear_upto]
            )

    out = []
    for r in rows:
        wef = _as_date(r.get("wef_dt"))
        pct = _num(r.get("da_pct"))
        if wef is not None and pct is not None:
            out.append({"wef_dt": wef, "da_pct": float(pct)})
    return out


def _cursor_c2(death_plus_1: date, class_grp: int):
    """
    Pre-2017 DA from Fi_Pn_new_dapct (finance),
    wef >= anchor from calc_da at death+1, wef < 01-jan-2017.
    """
    anchor = _da_anchor_wef(death_plus_1, class_grp)
    if anchor is None:
        return []
    sql = """
        SELECT WEF_DT AS wef_dt, DA_PCT AS da_pct
        FROM fi_pn_new_dapct
        WHERE WEF_DT >= %s
          AND WEF_DT < %s
        ORDER BY WEF_DT
    """
    try:
        rows = _fetchall(sql, [anchor, _CPI_SWITCH], alias="finance")
    except Exception:
        rows = []
    out = []
    for r in rows:
        wef = _as_date(r.get("wef_dt"))
        pct = _num(r.get("da_pct"))
        if wef is not None and pct is not None:
            out.append({"wef_dt": wef, "da_pct": float(pct)})
    return out


def _party_names(claim_id: str, emp_cd: str) -> dict:
    """Employee (pensioner) + family pension applicant names for print sheet."""
    emp = _emp_key(emp_cd)
    cid = _clip(claim_id, 20)
    emp_name = None
    if emp:
        row = _fetchone(
            "SELECT NAME FROM fi_pn_mh_pensioner WHERE EMP_CD = %s LIMIT 1",
            [emp],
        )
        if row and row.get("name"):
            emp_name = str(row["name"]).strip()
        if not emp_name:
            try:
                row = _fetchone(
                    """
                    SELECT EMP_NAME AS name
                    FROM fi_xx_mh_emp_per
                    WHERE EMP_CD = %s
                    LIMIT 1
                    """,
                    [emp],
                )
                if row and row.get("name"):
                    emp_name = str(row["name"]).strip()
            except Exception:
                pass

    applicant_name = None
    if cid:
        row = _fetchone(
            """
            SELECT NAME
            FROM fi_pn_md_fpen_appcn
            WHERE CLMCA_ID = %s AND FPEN_ACTIVE = 1
            ORDER BY SL_NO
            LIMIT 1
            """,
            [cid],
        )
        if row and row.get("name"):
            applicant_name = str(row["name"]).strip()

    return {
        "emp_name": emp_name or "",
        "applicant_name": applicant_name or "",
    }


def _jsonable_row(row: dict | None) -> dict | None:
    if not row:
        return None
    out = {}
    for k, v in row.items():
        if isinstance(v, datetime):
            out[k] = v.date().isoformat()
        elif isinstance(v, date):
            out[k] = v.isoformat()
        elif isinstance(v, Decimal):
            out[k] = float(v)
        else:
            out[k] = v
    return out


def _relief_amt(basic: int, da_pct: float, tag: str | None) -> int:
    if tag == "N":
        return 0
    return _ceil_rupee((basic * da_pct) / 100.0)


def _frac_first_month(
    death_plus_1: date,
    monthly_pen: int,
    monthly_rlf: int,
    extra_full_months: int,
) -> tuple[int, int]:
    """
    When death+1 is not the 1st: ceil proration of first month + full months.
    extra_full_months is (n_mth - 1) or (end_mth - 1) as coded.
    """
    last = _last_day(death_plus_1)
    days = (last - death_plus_1).days + 1
    totdays = last.day
    frac_org = _ceil_rupee((monthly_pen * days) / totdays)
    frac_rlf = _ceil_rupee((monthly_rlf * days) / totdays)
    if extra_full_months > 0:
        frac_org += monthly_pen * extra_full_months
        frac_rlf += monthly_rlf * extra_full_months
    return frac_org, frac_rlf


def _serialize_dtl_row(row: dict) -> dict:
    pf = _as_date(row.get("period_from"))
    pt = _as_date(row.get("period_to"))
    return {
        "claim_id": row.get("claim_id"),
        "period_from": pf.isoformat() if pf else None,
        "period_to": pt.isoformat() if pt else None,
        "arr_pen": _int_money(row.get("arr_pen")),
        "da_pct": float(row["da_pct"]) if row.get("da_pct") is not None else None,
        "arr_rlf": _int_money(row.get("arr_rlf")),
    }


def upsert_upgrade_header(
    *,
    claim_id: str,
    emp_cd=None,
    case_no=None,
    emp_class=None,
    pensioner_death_dt=None,
    generated_cpi=None,
    upgraded_cpi=277,
    generated_basic=None,
    upgraded_basic=None,
    arrear_upto=None,
    user_id="SMPK",
) -> dict:
    """
    Insert or update fi_pn_family_277_upgrade header (upgrade step before arrear).
    """
    cid = _clip(claim_id, 20)
    if not cid:
        raise Fp277ArrearError("claim_id is required")

    death = _as_date(pensioner_death_dt)
    gen_basic = _int_money(generated_basic) if generated_basic is not None else None
    up_basic = _int_money(upgraded_basic) if upgraded_basic is not None else None
    gen_cpi = _num(generated_cpi)
    up_cpi = _num(upgraded_cpi) if upgraded_cpi is not None else 277
    au = _as_date(arrear_upto)

    existing = load_upgrade(cid)
    with connection.cursor() as cur:
        if existing:
            cur.execute(
                """
                UPDATE fi_pn_family_277_upgrade
                   SET CASE_NO = COALESCE(%s, CASE_NO),
                       EMP_CD = COALESCE(%s, EMP_CD),
                       EMP_CLASS = COALESCE(%s, EMP_CLASS),
                       PENSIONER_DEATH_DT = COALESCE(%s, PENSIONER_DEATH_DT),
                       GENERATED_CPI = COALESCE(%s, GENERATED_CPI),
                       UPGRADED_CPI = COALESCE(%s, UPGRADED_CPI),
                       GENERATED_BASIC = COALESCE(%s, GENERATED_BASIC),
                       UPGRADED_BASIC = COALESCE(%s, UPGRADED_BASIC),
                       ARREAR_UPTO = COALESCE(%s, ARREAR_UPTO)
                 WHERE CLAIM_ID = %s
                """,
                [
                    _clip(case_no, 20) or None,
                    _clip(emp_cd, 5) or None,
                    emp_class,
                    death,
                    gen_cpi,
                    up_cpi,
                    gen_basic,
                    up_basic,
                    au,
                    cid,
                ],
            )
        else:
            if death is None or up_basic is None:
                raise Fp277ArrearError(
                    "pensioner_death_dt and upgraded_basic are required for new upgrade row"
                )
            cur.execute(
                """
                INSERT INTO fi_pn_family_277_upgrade (
                    CLAIM_ID, CASE_NO, EMP_CD, EMP_CLASS,
                    PENSIONER_DEATH_DT, GENERATED_CPI, UPGRADED_CPI,
                    GENERATED_BASIC, UPGRADED_BASIC, ARREAR_UPTO,
                    ARREAR_PENSION, ARREAR_RELIEF,
                    DATE_CREATED, CREATED_BY
                ) VALUES (
                    %s, %s, %s, %s,
                    %s, %s, %s,
                    %s, %s, %s,
                    NULL, NULL,
                    NOW(), %s
                )
                """,
                [
                    cid,
                    _clip(case_no, 20) or None,
                    _clip(emp_cd, 5) or None,
                    emp_class,
                    death,
                    gen_cpi,
                    up_cpi if up_cpi is not None else 277,
                    gen_basic,
                    up_basic,
                    au,
                    _clip(user_id, 5) or "SMPK",
                ],
            )
    return load_upgrade(cid) or {}


def _cpi_basics_map(*, claim_id: str = None, emp_cd: str = None) -> dict[int, int]:
    """Load {cpi: basic} from fi_pn_cpi_consolidation."""
    from family_pension.services.cpi_consolidation_service import load_cpi_consolidation

    rows = load_cpi_consolidation(claim_id=claim_id, emp_cd=emp_cd)
    out: dict[int, int] = {}
    for r in rows:
        cpi = _num(r.get("cpi"))
        basic = _int_money(r.get("basic"))
        if cpi is not None and basic > 0:
            out[int(cpi)] = basic
    return out


def _resolve_arrear_era_basics(hdr: dict, cid: str, emp: str) -> dict:
    """
    Resolve monthly basics for each arrear CPI era from fi_pn_cpi_consolidation.

    Era mapping:
      - pre-2017 (cursor c2)     → 126 CPI basic
      - 2017–2021 (cursor c1)    → 277 CPI basic
      - from 2022 (cursor c3)    → 359 if upgraded_cpi=359, else 277
    """
    up_cpi = int(_num(hdr.get("upgraded_cpi")) or 0)
    gen = _int_money(hdr.get("generated_basic"))
    upg = _int_money(hdr.get("upgraded_basic"))

    basics = _cpi_basics_map(claim_id=cid, emp_cd=emp)
    if not basics or (up_cpi == 359 and 277 not in basics) or (
        up_cpi in (277, 359) and 126 not in basics and gen <= 0
    ):
        try:
            ensure_upgrade_from_claim(claim_id=cid, emp_cd=emp)
            basics = _cpi_basics_map(claim_id=cid, emp_cd=emp)
        except Exception:
            pass

    # Fallbacks from upgrade header when consolidation is incomplete
    if 126 not in basics and gen > 0:
        basics[126] = gen
    if up_cpi == 277 and 277 not in basics and upg > 0:
        basics[277] = upg
    if up_cpi == 359 and 359 not in basics and upg > 0:
        basics[359] = upg

    pen_126 = basics.get(126) or gen
    pen_277 = basics.get(277)
    pen_359 = basics.get(359)

    if up_cpi == 359:
        pen_pre = pen_126
        pen_mid = pen_277
        pen_post = pen_359 or upg
        if not pen_mid or pen_mid <= 0:
            raise Fp277ArrearError(
                "277 CPI basic missing in fi_pn_cpi_consolidation — "
                "regenerate First Family Pension / Methodology I basics first."
            )
        if not pen_post or pen_post <= 0:
            raise Fp277ArrearError(
                "359 CPI basic missing — upgrade / consolidation incomplete."
            )
    else:
        # 277-upgrade: mid and post both use 277 basic
        pen_pre = pen_126
        pen_mid = pen_277 or upg
        pen_post = pen_mid
        if not pen_mid or pen_mid <= 0:
            raise Fp277ArrearError(
                "277 CPI basic missing — upgrade / consolidation incomplete."
            )

    if not pen_pre or pen_pre <= 0:
        # Death on/after 2017 may not need 126; allow mid as pre fallback
        pen_pre = pen_mid

    return {
        "basics": basics,
        "pen_pre2017": int(pen_pre),
        "pen_2017_2021": int(pen_mid),
        "pen_from_2022": int(pen_post),
        "upgraded_cpi": up_cpi,
    }


def _run_da_cursor(
    *,
    bands: list[dict],
    monthly_basic: int,
    death_plus_1: date,
    au: date,
    mth: int,
    end_mth: int,
    tag: str | None,
    n: int,
    v_pen: int,
    tot_rlf: int,
    append_fn,
) -> tuple[int, int, int]:
    """
    Shared quarter-band loop for c1/c2/c3 using a fixed monthly basic.
    Returns updated (n, v_pen, tot_rlf).
    """
    pen = int(monthly_basic)
    for band in bands:
        da_pct = band["da_pct"]
        wef = band["wef_dt"]
        v_relief = _relief_amt(pen, da_pct, tag)
        n_mth = mth if n == 0 else 3
        v_wet_date = _add_months(wef, 3) - timedelta(days=1)

        if v_wet_date > au:
            if n == 0:
                if death_plus_1.day != 1:
                    extra = 0
                    if end_mth == 2:
                        extra = 1
                    elif end_mth == 3:
                        extra = 2
                    frac_org, frac_rlf = _frac_first_month(
                        death_plus_1, pen, v_relief, extra
                    )
                    append_fn(death_plus_1, au, frac_org, da_pct, frac_rlf)
                    v_pen += frac_org
                    tot_rlf += frac_rlf
                else:
                    append_fn(death_plus_1, au, pen * n_mth, da_pct, v_relief * n_mth)
                    v_pen += pen * n_mth
                    tot_rlf += v_relief * n_mth
                n = 1
            else:
                append_fn(wef, au, pen * end_mth, da_pct, v_relief * end_mth)
                v_pen += pen * end_mth
                tot_rlf += v_relief * end_mth
        else:
            if n == 0:
                if death_plus_1.day != 1:
                    extra = 0
                    if n_mth == 2:
                        extra = 1
                    elif n_mth == 3:
                        extra = 2
                    frac_org, frac_rlf = _frac_first_month(
                        death_plus_1, pen, v_relief, extra
                    )
                    append_fn(death_plus_1, v_wet_date, frac_org, da_pct, frac_rlf)
                    v_pen += frac_org
                    tot_rlf += frac_rlf
                else:
                    append_fn(
                        death_plus_1, v_wet_date, pen * n_mth, da_pct, v_relief * n_mth
                    )
                    v_pen += pen * n_mth
                    tot_rlf += v_relief * n_mth
                n = 1
            else:
                append_fn(wef, v_wet_date, pen * 3, da_pct, v_relief * 3)
                v_pen += pen * n_mth
                tot_rlf += v_relief * n_mth
    return n, v_pen, tot_rlf


def calculate_fp_277_arrear(
    *,
    claim_id: str = None,
    emp_cd: str = None,
    arrear_upto=None,
    user_id: str = "SMPK",
    dry_run: bool = False,
    update_monthly_bill: bool = True,
) -> dict:
    """
    Run Oracle arrear calculation for claim_id or emp_cd.

    Monthly basics by era are taken from fi_pn_cpi_consolidation:
      pre-2017 → CPI 126, 2017–2021 → CPI 277, from 2022 → CPI 359 (or 277).
    """
    hdr = load_upgrade(claim_id=claim_id, emp_cd=emp_cd)
    if not hdr:
        raise Fp277ArrearError(
            "Upgrade First Then Calculate Arrear........ (no upgrade row for this employee)"
        )

    cid = _clip(hdr.get("claim_id"), 20)
    emp = _emp_key(hdr.get("emp_cd") or emp_cd)

    death = _as_date(hdr.get("pensioner_death_dt"))
    if not death:
        raise Fp277ArrearError("PENSIONER_DEATH_DT is missing on upgrade row")

    au = _as_date(arrear_upto) if arrear_upto is not None else _as_date(
        hdr.get("arrear_upto")
    )
    _validate_arrear_upto(au)

    up_cpi = _num(hdr.get("upgraded_cpi"))
    if up_cpi is None or int(up_cpi) not in (277, 359):
        raise Fp277ArrearError("Upgrade First Then Calculate Arrear........")

    eras = _resolve_arrear_era_basics(hdr, cid, emp)
    old_pen = eras["pen_pre2017"]
    pen_mid = eras["pen_2017_2021"]
    pen_post = eras["pen_from_2022"]
    pen_rev = pen_post  # header "upgraded" rate for response / monthly bill

    class_grp = _da_class_grp(hdr.get("emp_class"))
    death_plus_1 = death + timedelta(days=1)
    mth = _quarter_mth_from_start(death_plus_1.month)
    end_mth = _quarter_mth_to_end(au.month)
    tag = _relief_tag(cid)
    names = _party_names(cid, emp)

    n = 0
    v_pen = 0
    tot_rlf = 0
    details: list[dict] = []

    def _append(
        period_from: date,
        period_to: date,
        arr_pen: int,
        da_pct: float,
        arr_rlf: int,
    ):
        details.append(
            {
                "claim_id": cid,
                "period_from": period_from,
                "period_to": period_to,
                "arr_pen": int(arr_pen),
                "da_pct": float(da_pct),
                "arr_rlf": int(arr_rlf),
            }
        )

    # --- Cursor c2: pre-2017 → 126 CPI basic ---
    if death_plus_1 < _CPI_SWITCH:
        n, v_pen, tot_rlf = _run_da_cursor(
            bands=_cursor_c2(death_plus_1, class_grp),
            monthly_basic=old_pen,
            death_plus_1=death_plus_1,
            au=au,
            mth=mth,
            end_mth=end_mth,
            tag=tag,
            n=n,
            v_pen=v_pen,
            tot_rlf=tot_rlf,
            append_fn=_append,
        )

    # --- Cursor c1: 2017–2021 → 277 CPI basic ---
    n, v_pen, tot_rlf = _run_da_cursor(
        bands=_cursor_c1(death_plus_1, au, class_grp),
        monthly_basic=pen_mid,
        death_plus_1=death_plus_1,
        au=au,
        mth=mth,
        end_mth=end_mth,
        tag=tag,
        n=n,
        v_pen=v_pen,
        tot_rlf=tot_rlf,
        append_fn=_append,
    )

    # --- Cursor c3: from 2022 → 359 (or 277 if not upgraded to 359) ---
    n, v_pen, tot_rlf = _run_da_cursor(
        bands=_cursor_c3(death_plus_1, au, class_grp, upgraded_cpi=int(up_cpi)),
        monthly_basic=pen_post,
        death_plus_1=death_plus_1,
        au=au,
        mth=mth,
        end_mth=end_mth,
        tag=tag,
        n=n,
        v_pen=v_pen,
        tot_rlf=tot_rlf,
        append_fn=_append,
    )

    result = {
        "ok": True,
        "message": "Arrear Calculation Completed......",
        "claim_id": cid,
        "emp_cd": emp,
        "case_no": hdr.get("case_no"),
        "emp_class": hdr.get("emp_class"),
        "da_class_grp": class_grp,
        "emp_name": names.get("emp_name") or "",
        "applicant_name": names.get("applicant_name") or "",
        "pensioner_death_dt": death.isoformat(),
        "death_plus_1": death_plus_1.isoformat(),
        "arrear_upto": au.isoformat(),
        "generated_basic": old_pen,
        "upgraded_basic": pen_rev,
        "upgraded_cpi": int(up_cpi),
        "cpi_basics": eras["basics"],
        "basic_pre2017": old_pen,
        "basic_2017_2021": pen_mid,
        "basic_from_2022": pen_post,
        "relief_tag": tag,
        "start_quarter_months": mth,
        "end_quarter_months": end_mth,
        "arrear_pension": int(v_pen),
        "arrear_relief": int(tot_rlf),
        "total_payable": int(v_pen) + int(tot_rlf),
        "detail_count": len(details),
        "details": [
            {
                "period_from": d["period_from"].isoformat(),
                "period_to": d["period_to"].isoformat(),
                "arr_pen": d["arr_pen"],
                "da_pct": d["da_pct"],
                "arr_rlf": d["arr_rlf"],
            }
            for d in details
        ],
        "dry_run": bool(dry_run),
        "monthly_bill_updated": False,
    }

    if dry_run:
        return result

    user = _clip(user_id, 5) or "SMPK"
    with transaction.atomic():
        with connection.cursor() as cur:
            cur.execute(
                "DELETE FROM fi_pn_family_277_upgrade_dtl WHERE CLAIM_ID = %s",
                [cid],
            )
            for d in details:
                cur.execute(
                    """
                    INSERT INTO fi_pn_family_277_upgrade_dtl (
                        CLAIM_ID, PERIOD_FROM, PERIOD_TO,
                        ARR_PEN, DA_PCT, ARR_RLF
                    ) VALUES (%s, %s, %s, %s, %s, %s)
                    """,
                    [
                        cid,
                        d["period_from"],
                        d["period_to"],
                        d["arr_pen"],
                        d["da_pct"],
                        d["arr_rlf"],
                    ],
                )
            cur.execute(
                """
                UPDATE fi_pn_family_277_upgrade
                   SET ARREAR_UPTO = %s,
                       ARREAR_PENSION = %s,
                       ARREAR_RELIEF = %s
                 WHERE CLAIM_ID = %s
                """,
                [au, int(v_pen), int(tot_rlf), cid],
            )

            if update_monthly_bill:
                cur.execute(
                    """
                    SELECT FAM_FMPEN_ID
                    FROM fi_pn_th_first_month_fpension
                    WHERE FPENSION_TYPE = 'M'
                      AND CLMCA_ID = %s
                    LIMIT 1
                    """,
                    [cid],
                )
                row = cur.fetchone()
                if row and row[0]:
                    pk = row[0]
                    cur.execute(
                        "DELETE FROM fi_pn_td_first_month_fpension WHERE FAM_FMPEN_ID = %s",
                        [pk],
                    )
                    cur.execute(
                        """
                        INSERT INTO fi_pn_td_first_month_fpension (
                            EARN_DEDN_TYPE, EARN_DEDN_CD, AMOUNT,
                            DATE_CREATED, CREATED_BY,
                            FAM_FMPEN_ID, ORIGINAL_AMT
                        ) VALUES (
                            'E', '209', %s, NOW(), %s, %s, %s
                        )
                        """,
                        [int(v_pen), user, pk, int(v_pen)],
                    )
                    cur.execute(
                        """
                        INSERT INTO fi_pn_td_first_month_fpension (
                            EARN_DEDN_TYPE, EARN_DEDN_CD, AMOUNT,
                            DATE_CREATED, CREATED_BY,
                            FAM_FMPEN_ID, ORIGINAL_AMT
                        ) VALUES (
                            'E', '208', %s, NOW(), %s, %s, %s
                        )
                        """,
                        [int(tot_rlf), user, pk, int(tot_rlf)],
                    )
                    result["monthly_bill_updated"] = True
                    result["fam_fmpen_id"] = pk

    result["upgrade"] = _jsonable_row(load_upgrade(claim_id=cid))
    return result


def ensure_upgrade_from_claim(
    *,
    claim_id: str = None,
    emp_cd: str = None,
    user_id: str = "SMPK",
) -> dict | None:
    """
    Auto-populate fi_pn_family_277_upgrade from the saved claim and
    Methodology-I calculation — called whenever the upgrade row is absent.

    Resolves:
      - CLAIM_ID, EMP_CD, CASE_NO from fi_pn_mh_fpen_caclaim
      - EMP_CLASS from fi_pn_mh_familypensioner.APP_CLASS (fallback: claim.CLASS)
      - PENSIONER_DEATH_DT from claim.DOD_EMP_PENSIONER
      - GENERATED_CPI = 126, GENERATED_BASIC = 30 % of 126-CPI notional (M-I chain)
      - UPGRADED_CPI  = 277, UPGRADED_BASIC  = FP_277_cpi from M-I
      - ARREAR_UPTO, ARREAR_PENSION, ARREAR_RELIEF left NULL (set later by calc)

    Returns the upgrade row dict if successful, None if claim not found.
    Raises Fp277ArrearError if required fields are missing or M-I fails.
    """
    from methodology1.services.cpi_chain_service import (
        compute_126_notional,
        CPI_277_REVISION,
        CPI_359_REVISION,
    )
    from methodology1.services.revision_resolver import (
        get_revision_column,
        get_calculation_start_revision,
    )
    from methodology1.services.family_pension_calculation_service import (
        calculate_family_pension,
    )

    # ── 1. Load claim ────────────────────────────────────────────────────────
    cid = _clip(claim_id, 20) if claim_id else ""
    emp = _emp_key(emp_cd) if emp_cd else ""

    if cid:
        claim = _fetchone(
            """
            SELECT CLMCA_ID, CA_NO, EMP_CD, CLASS,
                   DOD_EMP_PENSIONER, RETIREMENT_CPI,
                   LAST_BASIC_AT_RET, SCALE_CD
            FROM fi_pn_mh_fpen_caclaim
            WHERE CLMCA_ID = %s LIMIT 1
            """,
            [cid],
        )
    elif emp:
        claim = _fetchone(
            """
            SELECT CLMCA_ID, CA_NO, EMP_CD, CLASS,
                   DOD_EMP_PENSIONER, RETIREMENT_CPI,
                   LAST_BASIC_AT_RET, SCALE_CD
            FROM fi_pn_mh_fpen_caclaim
            WHERE EMP_CD = %s
            ORDER BY DATE_CREATED DESC LIMIT 1
            """,
            [emp],
        )
    else:
        return None

    if not claim:
        return None

    cid = _clip(claim.get("clmca_id"), 20)
    emp = _emp_key(claim.get("emp_cd") or emp_cd)
    case_no = claim.get("ca_no")
    dod = _as_date(claim.get("dod_emp_pensioner"))
    if not dod:
        raise Fp277ArrearError(
            "Pensioner death date (DOD_EMP_PENSIONER) is not set on the claim — "
            "update the claim before creating the upgrade record."
        )

    # ── 2. Resolve employee class ─────────────────────────────────────────────
    emp_class = None
    fp_row = _fetchone(
        "SELECT APP_CLASS FROM fi_pn_mh_familypensioner WHERE EMP_CD = %s LIMIT 1",
        [emp],
    )
    if fp_row and fp_row.get("app_class") is not None:
        emp_class = fp_row["app_class"]
    else:
        emp_class = claim.get("class")

    # ── 3. Resolve pay and separation date for M-I ────────────────────────────
    pensioner = _fetchone(
        """
        SELECT EMP_RET_DT, PENSION_EMOLUMENTS, ORIGINAL_PENSION_AMT
        FROM fi_pn_mh_pensioner
        WHERE EMP_CD = %s LIMIT 1
        """,
        [emp],
    ) or {}

    adm = _fetchone(
        """
        SELECT SEPARATION_DT
        FROM fi_xx_mh_emp_adm
        WHERE EMP_CD = %s LIMIT 1
        """,
        [emp],
    ) or {}

    sep_dt = (
        _as_date(adm.get("separation_dt"))
        or _as_date(pensioner.get("emp_ret_dt"))
    )
    last_pay = _num(claim.get("last_basic_at_ret")) or _num(
        pensioner.get("pension_emoluments")
    )
    scale = _clip(claim.get("scale_cd"), 20) or None

    if not sep_dt or not last_pay:
        raise Fp277ArrearError(
            "Cannot auto-create upgrade: separation date or last basic pay is missing "
            f"for employee {emp}."
        )

    # ── 4. Determine target upgrade CPI from claim's RETIREMENT_CPI ─────────
    retirement_cpi = _num(claim.get("retirement_cpi")) or 277
    # Upgrade target: 359 if pensioner retired on 359-CPI scale, else 277.
    target_cpi = 359 if retirement_cpi >= 359 else 277

    # ── 5. Methodology-I: compute notionals across the CPI chain ─────────────
    cat = str(int(float(emp_class))) if emp_class is not None else "3"
    m1 = calculate_family_pension(
        separation_date=sep_dt.isoformat(),
        category=cat,
        pay=last_pay,
        scale=scale,
    )
    if m1.get("error"):
        raise Fp277ArrearError(f"M-I calculation error: {m1['error']}")

    scale_revision = get_revision_column(sep_dt.isoformat())
    start_revision = get_calculation_start_revision(sep_dt.isoformat())

    # ── 6. UPGRADED_BASIC — notional at target CPI ───────────────────────────
    if target_cpi == 359:
        fp_target_notional = _num(m1.get("FP_359_cpi"))
        if fp_target_notional is None:
            raise Fp277ArrearError("M-I did not produce a 359-CPI notional for this employee.")
        upgraded_cpi_val = 359
    else:
        fp_target_notional = _num(m1.get("FP_277_cpi"))
        if fp_target_notional is None:
            raise Fp277ArrearError("M-I did not produce a 277-CPI notional for this employee.")
        upgraded_cpi_val = 277

    upgraded_basic = int(round(fp_target_notional))

    # ── 7. GENERATED_BASIC — always the 126-CPI notional (Oracle convention) ─
    # Oracle stores GENERATED_CPI=126 / GENERATED_BASIC=<126 notional> for both
    # 277-upgrade and 359-upgrade cases.  The 277 step is never stored as
    # "generated"; it is an intermediate revision only.
    generated_cpi = 126
    generated_basic = None

    if start_revision not in (CPI_277_REVISION, CPI_359_REVISION):
        notional_126 = compute_126_notional(
            last_pay,
            scale_revision,
            start_revision,
            None,
            sep_dt.isoformat(),
        )
        if notional_126 is not None:
            generated_basic = int(math.ceil(float(notional_126)))

    # Fallback when chain starts at 277/359 (no 126 step)
    if generated_basic is None:
        fp_277_notional = _num(m1.get("FP_277_cpi"))
        if fp_277_notional is not None and upgraded_cpi_val == 359:
            generated_cpi = 277
            generated_basic = int(round(fp_277_notional))
        else:
            generated_cpi = upgraded_cpi_val
            generated_basic = upgraded_basic

    # ── 8. Upsert the header row ──────────────────────────────────────────────
    hdr = upsert_upgrade_header(
        claim_id=cid,
        emp_cd=emp,
        case_no=case_no,
        emp_class=emp_class,
        pensioner_death_dt=dod,
        generated_cpi=generated_cpi,
        generated_basic=generated_basic,
        upgraded_cpi=upgraded_cpi_val,
        upgraded_basic=upgraded_basic,
        arrear_upto=None,
        user_id=user_id,
    )

    # Also persist full CPI ladder for arrear era lookups
    try:
        from family_pension.services.cpi_consolidation_service import (
            save_cpi_basics_from_methodology,
        )

        save_cpi_basics_from_methodology(
            claim_id=cid,
            emp_cd=emp,
            case_no=case_no,
            emp_class=emp_class if emp_class is not None else cat,
            separation_date=sep_dt,
            category=cat,
            pay=last_pay,
            scale=scale,
            m1_result=m1,
            user_id=user_id,
        )
    except Exception:
        pass

    return hdr


def get_upgrade_status(claim_id: str = None, emp_cd: str = None) -> dict:
    hdr = load_upgrade(claim_id=claim_id, emp_cd=emp_cd)
    auto_created = False

    # Re-sync header if auto-created with wrong generated CPI (277 instead of 126)
    if hdr and _num(hdr.get("upgraded_cpi")) == 359 and _num(hdr.get("generated_cpi")) == 277:
        try:
            hdr = ensure_upgrade_from_claim(claim_id=claim_id, emp_cd=emp_cd) or hdr
        except Exception:
            pass

    if not hdr:
        # Auto-create from claim + sanction data when possible
        try:
            hdr = ensure_upgrade_from_claim(
                claim_id=claim_id, emp_cd=emp_cd
            )
            if hdr:
                auto_created = True
        except Fp277ArrearError:
            hdr = None
        except Exception:
            hdr = None

    if not hdr:
        return {
            "found": False,
            "claim_id": _clip(claim_id, 20) if claim_id else None,
            "emp_cd": _emp_key(emp_cd) if emp_cd else None,
            "upgrade": None,
            "details": [],
            "message": "No 277 upgrade / arrear record for this employee",
        }
    cid = _clip(hdr.get("claim_id"), 20)
    emp = _emp_key(hdr.get("emp_cd") or emp_cd)
    dtl = load_upgrade_detail(cid)
    names = _party_names(cid, emp)
    pen = _int_money(hdr.get("arrear_pension"))
    rlf = _int_money(hdr.get("arrear_relief"))
    return {
        "found": True,
        "auto_created": auto_created,
        "claim_id": cid,
        "emp_cd": emp,
        "case_no": hdr.get("case_no"),
        "emp_class": hdr.get("emp_class"),
        "emp_name": names.get("emp_name") or "",
        "applicant_name": names.get("applicant_name") or "",
        "upgrade": _jsonable_row(hdr),
        "details": [_serialize_dtl_row(r) for r in dtl],
        "arrear_pension": pen,
        "arrear_relief": rlf,
        "total_payable": pen + rlf,
        "generated_basic": _int_money(hdr.get("generated_basic")),
        "upgraded_basic": _int_money(hdr.get("upgraded_basic")),
        "pensioner_death_dt": (
            _as_date(hdr.get("pensioner_death_dt")).isoformat()
            if _as_date(hdr.get("pensioner_death_dt"))
            else None
        ),
        "arrear_upto": (
            _as_date(hdr.get("arrear_upto")).isoformat()
            if _as_date(hdr.get("arrear_upto"))
            else None
        ),
    }
