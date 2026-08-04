"""FI_XX_MH_EMP_DATA posting fields used for dept / designation display."""

from employee.services.oracle_service import get_oracle_connection, oracle_reads_enabled
from employee.utils.display_format import format_dept_designation, normalize_department_name


def _clip_emp(emp_code):
    return str(emp_code or "").strip()[:5]


def _fetch_emp_data_posting_mysql(emp_key):
    from employee.oracle_mirror import FiXxMhEmpData

    row = FiXxMhEmpData.objects.filter(emp_cd=emp_key).first()
    if not row:
        return None
    return {
        "alloc_desc": str(row.alloc_desc or "").strip(),
        "desig": str(row.desig or "").strip(),
        "dept_desc": str(row.dept_desc or "").strip(),
        "source": "mysql_emp_data",
    }


def _fetch_emp_data_posting_oracle(emp_key):
    conn = None
    try:
        conn = get_oracle_connection()
    except Exception:
        return None

    cur = conn.cursor()
    try:
        cur.execute(
            """
            SELECT ALLOC_DESC, DESIG, DEPT_DESC
            FROM FINANCE.FI_XX_MH_EMP_DATA
            WHERE EMP_CD = :emp_cd
            """,
            {"emp_cd": emp_key},
        )
        row = cur.fetchone()
        if not row:
            return None
        return {
            "alloc_desc": str(row[0]).strip() if row[0] else "",
            "desig": str(row[1]).strip() if row[1] else "",
            "dept_desc": str(row[2]).strip() if row[2] else "",
            "source": "oracle",
        }
    except Exception:
        return None
    finally:
        cur.close()
        conn.close()


def _is_dept_desig_label(text):
    """Stale cache used DEPT(DESIG) before ALLOC_DESC was stored."""
    label = str(text or "").strip()
    return "(" in label and label.endswith(")")


def _fetch_emp_data_posting_cache(emp_key):
    """
    Last Oracle employee search / dashboard row stored in MySQL.
    posting_alloc_desc is set when the employee was searched while Oracle was up.
    """
    from first_pension.models import CachedRetirementEmployee
    from first_pension.services.oracle_cache_service import load_employee_from_cache

    cached = load_employee_from_cache(emp_key)
    if cached:
        alloc_desc = str(cached.get("posting_alloc_desc") or "").strip()
        if not alloc_desc:
            designation = str(cached.get("designation") or "").strip()
            if designation and not _is_dept_desig_label(designation):
                alloc_desc = designation
        department = str(
            cached.get("posting_dept_desc") or cached.get("department") or ""
        ).strip()
        desig = str(cached.get("posting_desig_desc") or "").strip()
        designation = str(cached.get("designation") or "").strip()
        if alloc_desc or desig:
            return {
                "alloc_desc": alloc_desc,
                "desig": desig,
                "dept_desc": department,
                "source": "employee_cache",
            }
        if designation and _is_dept_desig_label(designation):
            return None
        if department:
            return {
                "alloc_desc": "",
                "desig": "",
                "dept_desc": department,
                "source": "employee_cache",
            }

    row = (
        CachedRetirementEmployee.objects.filter(emp_code=emp_key)
        .order_by("-retirement_year", "-retirement_month")
        .first()
    )
    if row:
        payload = row.row_payload if isinstance(row.row_payload, dict) else {}
        alloc_desc = str(payload.get("posting_alloc_desc") or "").strip()
        designation = str(
            payload.get("designation") or row.designation or ""
        ).strip()
        if not alloc_desc and designation and not _is_dept_desig_label(designation):
            alloc_desc = designation
        department = str(
            payload.get("posting_dept_desc") or payload.get("department") or ""
        ).strip()
        desig = str(payload.get("posting_desig_desc") or "").strip()
        if alloc_desc or desig:
            return {
                "alloc_desc": alloc_desc,
                "desig": desig,
                "dept_desc": department,
                "source": "dashboard_cache",
            }
        if designation and _is_dept_desig_label(designation):
            return None
        if department:
            return {
                "alloc_desc": "",
                "desig": "",
                "dept_desc": department,
                "source": "dashboard_cache",
            }
    return None


def _fetch_emp_data_posting_mirror(emp_key):
    """MySQL mirror only — designation master, no ALLOC_DESC."""
    from employee.oracle_mirror import FiXxMhEmpAdm
    from master_data.models import FiXxMhDesig

    adm = FiXxMhEmpAdm.objects.filter(emp_cd=emp_key).first()
    if not adm or adm.desig_cd is None:
        return None

    desig_desc = ""
    row = FiXxMhDesig.objects.filter(desig_cd=adm.desig_cd).first()
    if row and row.desig_desc:
        desig_desc = str(row.desig_desc).strip()

    if not desig_desc:
        return None

    return {
        "alloc_desc": "",
        "desig": desig_desc,
        "dept_desc": "",
        "source": "mysql_mirror",
    }


def fetch_emp_data_posting(emp_code):
    """
    Posting line for pension reports / employee display.

    Priority: live Oracle EMP_DATA → MySQL Oracle cache → designation mirror.
    """
    emp_key = _clip_emp(emp_code)
    if not emp_key:
        return None

    for loader in (
        _fetch_emp_data_posting_mysql,
        _fetch_emp_data_posting_oracle if oracle_reads_enabled() else lambda _k: None,
        _fetch_emp_data_posting_cache,
        _fetch_emp_data_posting_mirror,
    ):
        posting = loader(emp_key)
        if posting and (
            posting.get("alloc_desc")
            or posting.get("desig")
            or posting.get("dept_desc")
        ):
            return posting
    return None


def resolve_posting_designation_display(
    *,
    dept_desc=None,
    desig_desc=None,
    alloc_desc=None,
):
    """Prefer ALLOC_DESC; otherwise DEPT(DESIG) from master descriptions."""
    alloc = str(alloc_desc or "").strip()
    if alloc:
        return alloc.upper()
    formatted = format_dept_designation(dept_desc, desig_desc)
    return formatted.upper() if formatted else ""


def _nature_of_service_from_posting(posting):
    if not posting:
        return ""
    if posting.get("alloc_desc"):
        return str(posting["alloc_desc"]).strip().upper()
    return resolve_posting_designation_display(
        dept_desc=posting.get("dept_desc"),
        desig_desc=posting.get("desig"),
    )


def resolve_nature_of_service(emp_code, *, fallback=""):
    """Nature of service for pension sanction / employee display."""
    text = _nature_of_service_from_posting(fetch_emp_data_posting(emp_code))
    if text:
        return text
    fallback_text = str(fallback or "").strip()
    return fallback_text.upper() if fallback_text else ""


def resolve_department_from_posting(emp_code, *, fallback=""):
    posting = fetch_emp_data_posting(emp_code)
    if posting and posting.get("dept_desc"):
        return normalize_department_name(posting["dept_desc"])
    return normalize_department_name(fallback)
