from datetime import date, datetime

from employee.services.employee_mirror_service import (
    fetch_emp_adm_separation_from_mirror,
)
from employee.services.oracle_service import (
    get_oracle_connection,
    oracle_reads_enabled,
)

ORACLE_REMARKS_COLUMN = "TERMIN_REMARK"


def _oracle_emp_bind_id(emp_code):
    """Use string bind for EMP_CD to avoid ORA-01722 type mismatches across tables."""
    return str(emp_code).strip()


def _parse_ui_separation_date(value):
    if not value:
        return None
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if hasattr(value, "date"):
        return value.date()
    text = str(value).strip()
    for fmt in ("%Y-%m-%d", "%d-%m-%Y"):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    return None


def _normalize_separation_type(value):
    """Oracle stores codes as VARCHAR2, e.g. RT, VR, DT."""
    return str(value).strip().upper()


def fetch_emp_adm_separation(emp_code):
    """Read separation from MySQL mirror, or Oracle when live reads are enabled."""
    if not oracle_reads_enabled():
        return fetch_emp_adm_separation_from_mirror(emp_code)
    try:
        return _fetch_emp_adm_separation_oracle(emp_code)
    except Exception:
        return fetch_emp_adm_separation_from_mirror(emp_code)


def _fetch_emp_adm_separation_oracle(emp_code):
    """Read SEPARATION_TYPE, SEPARATION_DT, TERMIN_REMARK from Oracle."""
    bind_id = _oracle_emp_bind_id(emp_code)
    conn = get_oracle_connection()
    cursor = conn.cursor()

    try:
        cursor.execute(
            f"""
            SELECT SEPARATION_TYPE, SEPARATION_DT, {ORACLE_REMARKS_COLUMN}
            FROM FINANCE.FI_XX_MH_EMP_ADM
            WHERE TO_CHAR(EMP_CD) = :emp_id
            """,
            {"emp_id": bind_id},
        )
        row = cursor.fetchone()
        if not row:
            return None

        sep_dt = row[1]
        separation_date = ""
        if sep_dt is not None:
            if hasattr(sep_dt, "strftime"):
                separation_date = sep_dt.strftime("%Y-%m-%d")
            else:
                separation_date = str(sep_dt)[:10]

        sep_type = row[0]
        return {
            "separation_type": str(sep_type).strip() if sep_type is not None else "",
            "separation_date": separation_date,
            "remarks": (row[2] or "") if row[2] is not None else "",
        }
    finally:
        cursor.close()
        conn.close()


def process_intake_is_complete_in_oracle(emp_code):
    """Prefer mirror when Oracle reads are disabled (avoid connection timeouts)."""
    if not oracle_reads_enabled():
        data = fetch_emp_adm_separation_from_mirror(emp_code)
    else:
        try:
            data = _fetch_emp_adm_separation_oracle(emp_code)
        except Exception:
            data = fetch_emp_adm_separation_from_mirror(emp_code)
    return bool(
        data
        and (data.get("separation_type") or "").strip()
        and data.get("separation_date")
    )


def update_emp_adm_separation(emp_code, separation_type, separation_date, remarks=""):
    """
    Update FINANCE.FI_XX_MH_EMP_ADM: SEPARATION_TYPE (RT, VR, …),
    SEPARATION_DT (DATE), TERMIN_REMARK.
    """
    bind_id = _oracle_emp_bind_id(emp_code)
    sep_type = _normalize_separation_type(separation_type)
    sep_date = _parse_ui_separation_date(separation_date)

    if not sep_type:
        raise ValueError("Separation type is required.")
    if not sep_date:
        raise ValueError("Invalid separation date.")

    conn = get_oracle_connection()
    cursor = conn.cursor()

    try:
        cursor.execute(
            """
            SELECT COUNT(*)
            FROM FINANCE.FI_XX_MH_EMP_ADM
            WHERE TO_CHAR(EMP_CD) = :emp_id
            """,
            {"emp_id": bind_id},
        )
        if cursor.fetchone()[0] == 0:
            raise ValueError(
                f"Employee {emp_code} not found in FINANCE.FI_XX_MH_EMP_ADM."
            )

        cursor.execute(
            f"""
            UPDATE FINANCE.FI_XX_MH_EMP_ADM
            SET SEPARATION_TYPE = :separation_type,
                SEPARATION_DT = :separation_dt,
                {ORACLE_REMARKS_COLUMN} = :remarks
            WHERE TO_CHAR(EMP_CD) = :emp_id
            """,
            {
                "separation_type": sep_type,
                "separation_dt": sep_date,
                "remarks": remarks or "",
                "emp_id": bind_id,
            },
        )

        if cursor.rowcount == 0:
            raise ValueError(
                f"No row updated in FI_XX_MH_EMP_ADM for employee {emp_code}."
            )

        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        cursor.close()
        conn.close()
