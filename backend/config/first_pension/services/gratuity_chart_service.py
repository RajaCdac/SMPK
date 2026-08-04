"""Oracle FI_PN_* gratuity chart lookups for FFUNC_DCR_GRATUITY.

Prefer MySQL mirrors; live Oracle only when ORACLE_READ_ENABLED.
"""

from datetime import date, datetime

from employee.services.oracle_service import try_oracle_connection

# Current statutory gratuity ceiling when chart row is missing (post-2017).
DEFAULT_AFTER_INCEPTION_CAP = 2_000_000


def _as_date(value):
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    return None


def _lookup_death_gratuity_chart_mysql(separation_dt, gratuity_type):
    from django.db import connection

    gtype = str(gratuity_type)
    try:
        with connection.cursor() as cur:
            cur.execute(
                """
                SELECT INCEPTION_DT, BEFORE_INCEPTION_MAX_LT, AFTER_INCEPTION_MAX_LT
                FROM fi_pn_mh_death_gratchart
                WHERE GRATUITY_TYPE = %s
                  AND WEF_DT < %s
                ORDER BY WEF_DT DESC
                LIMIT 1
                """,
                [gtype, separation_dt],
            )
            row = cur.fetchone()
    except Exception:
        return None
    if not row:
        return None
    return {
        "inception_dt": _as_date(row[0]),
        "before_inception_max_lt": float(row[1] or 0),
        "after_inception_max_lt": float(row[2] or 0),
    }


def lookup_death_gratuity_chart(separation_dt, *, gratuity_type):
    """
    FI_PN_MH_DEATH_GRATCHART row for retirement/death date.
    gratuity_type: 0 = retirement opt-I, 2 = death gratuity.
    """
    separation_dt = _as_date(separation_dt)
    if not separation_dt:
        return None

    mirrored = _lookup_death_gratuity_chart_mysql(separation_dt, gratuity_type)
    if mirrored:
        return mirrored

    conn = try_oracle_connection()
    if conn:
        try:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT inception_dt,
                       before_inception_max_lt,
                       after_inception_max_lt
                  FROM FINANCE.FI_PN_MH_DEATH_GRATCHART
                 WHERE wef_dt = (
                           SELECT MAX(wef_dt)
                             FROM FINANCE.FI_PN_MH_DEATH_GRATCHART
                            WHERE :sep_dt > wef_dt
                              AND gratuity_type = :gtype
                       )
                   AND gratuity_type = :gtype
                """,
                {"sep_dt": separation_dt, "gtype": str(gratuity_type)},
            )
            row = cur.fetchone()
            cur.close()
            if row:
                return {
                    "inception_dt": _as_date(row[0]),
                    "before_inception_max_lt": float(row[1] or 0),
                    "after_inception_max_lt": float(row[2] or 0),
                }
        except Exception:
            pass
        finally:
            try:
                conn.close()
            except Exception:
                pass
    return None


def _lookup_maxadm_gratuity_mysql(separation_dt, gratuity_type):
    from django.db import connection

    try:
        with connection.cursor() as cur:
            cur.execute(
                """
                SELECT MAX_EMOLUMENT, MAX_ADM_GRATUITY, RET_DT_FROM, RET_DT_TO
                FROM fi_pn_md_maxadm_gratuity
                WHERE GRATUITY_TYPE = %s
                ORDER BY RET_DT_FROM DESC
                """,
                [int(gratuity_type)],
            )
            rows = cur.fetchall()
    except Exception:
        return None

    for max_emol, max_adm, ret_from, ret_to in rows:
        start = _as_date(ret_from)
        end = _as_date(ret_to) or separation_dt
        if not start:
            continue
        if start <= separation_dt <= end:
            return {
                "max_emolument": float(max_emol or 0),
                "max_adm_gratuity": float(max_adm or 0),
            }
    return None


def lookup_maxadm_gratuity(separation_dt, *, gratuity_type=1):
    """FI_PN_MD_MAXADM_GRATUITY — emolument and admissible gratuity caps (opt-II)."""
    separation_dt = _as_date(separation_dt)
    if not separation_dt:
        return None

    mirrored = _lookup_maxadm_gratuity_mysql(separation_dt, gratuity_type)
    if mirrored:
        return mirrored

    conn = try_oracle_connection()
    if not conn:
        return None
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT max_emolument, max_adm_gratuity
              FROM (
                    SELECT max_emolument, max_adm_gratuity
                      FROM FINANCE.FI_PN_MD_MAXADM_GRATUITY
                     WHERE :sep_dt BETWEEN ret_dt_from
                           AND NVL(ret_dt_to, :sep_dt)
                       AND gratuity_type = :gtype
                     ORDER BY ret_dt_from DESC
                   )
             WHERE ROWNUM = 1
            """,
            {"sep_dt": separation_dt, "gtype": gratuity_type},
        )
        row = cur.fetchone()
        cur.close()
        if row:
            return {
                "max_emolument": float(row[0] or 0),
                "max_adm_gratuity": float(row[1] or 0),
            }
    except Exception:
        pass
    finally:
        try:
            conn.close()
        except Exception:
            pass
    return None


def _lookup_death_multiple_factor_mysql(tqs_years, gratuity_type):
    from django.db import connection

    tqs = int(tqs_years or 0)
    try:
        with connection.cursor() as cur:
            cur.execute(
                """
                SELECT MULTIPLE_FACTOR
                FROM fi_pn_md_death_gratchart
                WHERE GRATUITY_TYPE = %s
                  AND TQS_START_YRS <= %s
                  AND TQS_END_YRS >= %s
                LIMIT 1
                """,
                [int(gratuity_type), tqs, tqs],
            )
            row = cur.fetchone()
    except Exception:
        return None
    if row and row[0] is not None:
        return float(row[0])
    return None


def lookup_death_multiple_factor(tqs_years, *, gratuity_type=2):
    """FI_PN_MD_DEATH_GRATCHART — multiplication factor for death gratuity."""
    mirrored = _lookup_death_multiple_factor_mysql(tqs_years, gratuity_type)
    if mirrored is not None:
        return mirrored

    tqs = int(tqs_years or 0)
    conn = try_oracle_connection()
    if conn:
        try:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT multiple_factor
                  FROM FINANCE.FI_PN_MD_DEATH_GRATCHART
                 WHERE :tqs BETWEEN tqs_start_yrs AND tqs_end_yrs
                   AND gratuity_type = :gtype
                """,
                {"tqs": tqs, "gtype": gratuity_type},
            )
            row = cur.fetchone()
            cur.close()
            if row and row[0] is not None:
                return float(row[0])
        except Exception:
            pass
        finally:
            try:
                conn.close()
            except Exception:
                pass
    return None


def apply_chart_cap(amount, separation_dt, chart):
    """Apply before/after inception ceiling from death gratuity chart."""
    amount = float(amount or 0)
    separation_dt = _as_date(separation_dt)
    if not chart or not separation_dt:
        return amount

    inception = chart.get("inception_dt")
    after_cap = chart.get("after_inception_max_lt") or 0
    before_cap = chart.get("before_inception_max_lt") or 0

    if inception and separation_dt >= inception:
        if after_cap > 0 and amount > after_cap:
            return after_cap
    elif before_cap > 0 and amount > before_cap:
        return before_cap
    return amount
