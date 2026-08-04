"""Resolve Oracle scale codes (e.g. 2017/RE/007) to pay-band text via MySQL mirror or Oracle."""

from employee.services.oracle_service import try_oracle_connection


def _looks_like_pay_band(scale):
    if not scale:
        return False
    text = str(scale).strip()
    return "-" in text and "/" not in text


def fetch_scale_desc_from_mirror(scale_cd):
    if not scale_cd:
        return None
    try:
        from master_data.models import FiPmMhPayscale

        row = FiPmMhPayscale.objects.filter(scale_cd=str(scale_cd).strip()).first()
        if row and row.scale_desc:
            return str(row.scale_desc).strip()
    except Exception:
        pass
    return None


def fetch_scale_desc_from_oracle(scale_cd):
    if not scale_cd:
        return None
    conn = try_oracle_connection()
    if not conn:
        return None
    try:
        from methodology1.services.oracle_employee_service import (
            fetch_scale_desc_from_oracle as _oracle_fetch,
        )

        with conn.cursor() as cursor:
            return _oracle_fetch(cursor, scale_cd)
    except Exception:
        return None
    finally:
        conn.close()


def fetch_scale_desc(scale_cd):
    """MySQL mirror first, then live Oracle when reads are enabled."""
    if not scale_cd:
        return None
    key = str(scale_cd).strip()
    desc = fetch_scale_desc_from_mirror(key)
    if desc:
        return desc
    return fetch_scale_desc_from_oracle(key)


def batch_fetch_scale_desc_map(scale_cds):
    codes = sorted({str(code).strip() for code in scale_cds if code})
    if not codes:
        return {}

    result = {}
    try:
        from master_data.models import FiPmMhPayscale

        for row in FiPmMhPayscale.objects.filter(scale_cd__in=codes):
            key = str(row.scale_cd).strip()
            if key and row.scale_desc and key not in result:
                result[key] = str(row.scale_desc).strip()
    except Exception:
        pass

    missing = [code for code in codes if code not in result]
    if missing:
        conn = try_oracle_connection()
        if conn:
            try:
                from methodology1.services.oracle_employee_service import (
                    batch_fetch_scale_desc_map as _oracle_batch,
                )

                with conn.cursor() as cursor:
                    result.update(_oracle_batch(cursor, missing))
            except Exception:
                pass
            finally:
                conn.close()

    return result


def resolve_scale_from_employee_cache(emp_key):
    """Use a previously cached Oracle employee search row when mirror mapping fails."""
    from first_pension.models import CachedRetirementEmployee
    from first_pension.services.oracle_cache_service import load_employee_from_cache

    cached = load_employee_from_cache(emp_key)
    if cached:
        scale = cached.get("scale")
        if _looks_like_pay_band(scale):
            return str(scale).strip()

    row = (
        CachedRetirementEmployee.objects.filter(emp_code=str(emp_key).strip())
        .order_by("-retirement_year", "-retirement_month")
        .first()
    )
    if row and _looks_like_pay_band(row.scale):
        return str(row.scale).strip()
    if row and row.row_payload:
        scale = row.row_payload.get("scale")
        if _looks_like_pay_band(scale):
            return str(scale).strip()

    return None
