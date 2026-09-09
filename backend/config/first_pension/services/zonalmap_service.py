"""
FI_MA_M_H_ZONALMAP helpers.

JV detail stores internal ZONAL_CD (e.g. 12). Oracle RDF "Summary of Journal"
displays CPT_ZONAL_CD + CPT_ZONAL_DES (e.g. 10 REVENUE ACCOUNT).
"""

from functools import lru_cache

# From Oracle FINANCE.FI_MA_M_H_ZONALMAP (mirror when MySQL table is empty offline).
_FALLBACK_CPT = {
    10: (10, "REVENUE ACCOUNT"),
    11: (10, "REVENUE ACCOUNT"),
    12: (10, "REVENUE ACCOUNT"),
    20: (20, "CAPITAL ACCOUNT"),
    21: (20, "CAPITAL ACCOUNT"),
    22: (20, "CAPITAL ACCOUNT"),
    23: (20, "CAPITAL ACCOUNT"),
    24: (20, "CAPITAL ACCOUNT"),
    30: (30, "SUSPENSE ACCOUNT"),
    40: (40, "CASH & PAY"),
}


def _clip(value, max_len, default=""):
    if value is None:
        return default
    text = str(value).strip()
    if not text:
        return default
    return text[:max_len]


@lru_cache(maxsize=64)
def _fetch_map_row(zonal_cd: int):
    """(cpt_zonal_cd, cpt_zonal_des) or None."""
    z = int(zonal_cd)
    try:
        from django.db import connection

        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT CPT_ZONAL_CD, CPT_ZONAL_DES
                FROM fi_ma_m_h_zonalmap
                WHERE ZONAL_CD = %s
                LIMIT 1
                """,
                [z],
            )
            row = cursor.fetchone()
            if row and row[0] is not None:
                return int(row[0]), _clip(row[1], 60)
    except Exception:
        pass

    try:
        from employee.services.oracle_service import (
            oracle_reads_enabled,
            try_oracle_connection,
        )

        if oracle_reads_enabled():
            conn = try_oracle_connection()
            if conn:
                try:
                    with conn.cursor() as cursor:
                        cursor.execute(
                            """
                            SELECT CPT_ZONAL_CD, CPT_ZONAL_DES
                            FROM FINANCE.FI_MA_M_H_ZONALMAP
                            WHERE ZONAL_CD = :z
                            """,
                            {"z": z},
                        )
                        row = cursor.fetchone()
                        if row and row[0] is not None:
                            return int(row[0]), _clip(row[1], 60)
                finally:
                    try:
                        conn.close()
                    except Exception:
                        pass
    except Exception:
        pass

    return None


def lookup_cpt_zonal(zonal_cd):
    """
    Map stored JV zonal to display fields.

    Returns dict with zonal_cd, cpt_zonal_cd, cpt_zonal_des, zonal_label.
    """
    try:
        z = int(zonal_cd or 0)
    except (TypeError, ValueError):
        z = 0

    row = _fetch_map_row(z) if z else None
    if row is None:
        row = _FALLBACK_CPT.get(z)
    if row is None:
        return {
            "zonal_cd": z,
            "cpt_zonal_cd": z,
            "cpt_zonal_des": "",
            "zonal_label": str(z) if z else "",
        }

    cpt_cd, cpt_des = row
    label = f"{cpt_cd} {cpt_des}".strip() if cpt_des else str(cpt_cd)
    return {
        "zonal_cd": z,
        "cpt_zonal_cd": cpt_cd,
        "cpt_zonal_des": cpt_des,
        "zonal_label": label,
    }


def enrich_journal_line_zonal(line: dict) -> dict:
    """Add cpt_zonal_* + zonal_label for UI; keep stored zonal_cd."""
    if not isinstance(line, dict):
        return line
    info = lookup_cpt_zonal(line.get("zonal_cd"))
    line["cpt_zonal_cd"] = info["cpt_zonal_cd"]
    line["cpt_zonal_des"] = info["cpt_zonal_des"]
    line["zonal_label"] = info["zonal_label"]
    return line


def enrich_journal_lines(lines):
    return [enrich_journal_line_zonal(dict(line)) for line in (lines or [])]
