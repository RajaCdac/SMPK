"""
Class 1/2 Methodology-1 bunching from fi_pn_lic_master.

Used only when drawing the consolidation report. Stored M1 amounts are unchanged.
"""

from __future__ import annotations

_LIC_ALIAS: str | None = None


def _lic_db_alias() -> str | None:
    """Database that holds fi_pn_lic_master (finance mirror, else default)."""
    global _LIC_ALIAS
    if _LIC_ALIAS is not None:
        return _LIC_ALIAS or None

    from django.db import connections

    found = ""
    for alias in ("finance", "default"):
        if alias not in connections:
            continue
        try:
            with connections[alias].cursor() as cursor:
                cursor.execute(
                    """
                    SELECT COUNT(*)
                    FROM information_schema.tables
                    WHERE table_schema = DATABASE()
                      AND table_name = 'fi_pn_lic_master'
                    """
                )
                if cursor.fetchone()[0]:
                    found = alias
                    break
        except Exception:
            continue
    _LIC_ALIAS = found
    return found or None


def _money(value) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def fetch_class12_lic_basic_pension(emp_cd, category=None):
    """
    Class 1/2 Methodology-1 basic at 277 CPI from fi_pn_lic_master.BASIC_PENSION.

    Used when the officer wage header has no revised basic. None for other classes.
    """
    cat = str(category or "").strip()
    if cat not in ("1", "2"):
        return None
    emp = str(emp_cd or "").strip()[:5]
    if not emp:
        return None
    alias = _lic_db_alias()
    if not alias:
        return None

    from django.db import connections

    keys = list(dict.fromkeys([emp, emp.zfill(5)]))
    placeholders = ", ".join(["%s"] * len(keys))
    try:
        with connections[alias].cursor() as cursor:
            cursor.execute(
                f"""
                SELECT BASIC_PENSION
                FROM fi_pn_lic_master
                WHERE SALARY_ROLL_NO IN ({placeholders})
                  AND BASIC_PENSION IS NOT NULL
                ORDER BY DATE_MODIFIED DESC
                LIMIT 1
                """,
                keys,
            )
            row = cursor.fetchone()
    except Exception:
        return None
    if not row:
        return None
    return _money(row[0])


def fetch_class12_m1_bunching(emp_cd, category=None) -> dict | None:
    """
    Positive BUNCH_BASIC for a class 1/2 employee.

    Returns basic_pension, bunch_basic, and m1_bunched (their sum), or None.
    """
    cat = str(category or "").strip()
    if cat not in ("1", "2"):
        return None
    emp = str(emp_cd or "").strip()[:5]
    if not emp:
        return None
    alias = _lic_db_alias()
    if not alias:
        return None

    from django.db import connections

    keys = list(dict.fromkeys([emp, emp.zfill(5)]))
    placeholders = ", ".join(["%s"] * len(keys))
    try:
        with connections[alias].cursor() as cursor:
            cursor.execute(
                f"""
                SELECT BASIC_PENSION, BUNCH_BASIC
                FROM fi_pn_lic_master
                WHERE SALARY_ROLL_NO IN ({placeholders})
                  AND BUNCH_BASIC IS NOT NULL
                  AND BUNCH_BASIC <> 0
                ORDER BY DATE_MODIFIED DESC
                LIMIT 1
                """,
                keys,
            )
            row = cursor.fetchone()
    except Exception:
        return None
    if not row:
        return None
    basic = _money(row[0])
    extra = _money(row[1])
    if basic is None or extra is None or extra == 0:
        return None
    return {
        "basic_pension": basic,
        "bunch_basic": extra,
        "m1_bunched": basic + extra,
    }


def _employee_277_column(col) -> bool:
    if not isinstance(col, dict):
        return False
    kind = str(col.get("kind") or "").strip().lower()
    if kind not in ("", "employee"):
        return False
    if str(col.get("key") or "").startswith("359"):
        return False
    try:
        cpi = int(col.get("cpi") or 0)
    except (TypeError, ValueError):
        return False
    return cpi == 277


def apply_class12_bunch_to_comparison(comparison, bunch) -> bool:
    """
    Store employee M1@277 as basic + bunch.

    Employee M1@277 becomes LIC basic + bunch (the report figure), including
    when the wage-header basic is a different amount. A second pass does not
    add the bunch again. Family columns are left alone.
    Returns True when at least one column was updated.
    """
    if not isinstance(comparison, dict) or not isinstance(bunch, dict):
        return False
    basic = _money(bunch.get("basic_pension"))
    extra = _money(bunch.get("bunch_basic"))
    if basic is None or extra is None or extra == 0:
        return False
    total = round(basic + extra, 2)
    changed = False
    for col in comparison.get("columns") or []:
        if not _employee_277_column(col):
            continue
        m1 = _money(col.get("m1"))
        if m1 is not None and abs(m1 - total) < 0.51:
            continue
        new_m1 = total
        col["m1"] = new_m1
        m2_raw = col.get("m2_base") if col.get("m2_base") not in (None, "") else col.get("m2")
        m2 = _money(m2_raw)
        if m2 is not None:
            col["diff"] = round(m2 - new_m1, 2)
        pct = _money(col.get("oldage_percent"))
        if pct is not None and "oa_benefit_m1" in col:
            oa_m1 = round((new_m1 * pct) / 100.0, 2) if pct else 0.0
            oa_m2 = _money(col.get("oa_benefit_m2")) or 0.0
            col["oa_benefit_m1"] = oa_m1
            col["oa_diff"] = round(oa_m2 - oa_m1, 2)
            payable = max(m2, new_m1) if m2 is not None else new_m1
            col["payable_basic"] = payable
            oa_benefit = max(oa_m2, oa_m1)
            col["oa_benefit"] = oa_benefit
            col["revised_total_basic"] = round(payable + oa_benefit, 2)
        changed = True
    if changed:
        comparison["bunch_basic"] = extra
    return changed
