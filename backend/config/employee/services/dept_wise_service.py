"""FI_XX_DEPT_WISE_EMP_DTL — actual department via FA / budget centre (Oracle view mirror)."""

from __future__ import annotations

from employee.utils.display_format import normalize_department_name


def _clip_emp(emp_code) -> str:
    return str(emp_code or "").strip()[:5]


def _normalize_dept_label(text: str) -> str:
    label = str(text or "").strip().upper()
    if not label:
        return ""
    if label.startswith("ADMIN/SECY"):
        return "SECRETARY"
    return normalize_department_name(label) or label


def fetch_dept_wise_row(emp_code):
    """One row from fi_xx_dept_wise_emp_dtl (MySQL view)."""
    emp_key = _clip_emp(emp_code)
    if not emp_key:
        return None
    try:
        from employee.oracle_mirror import FiXxDeptWiseEmpDtl

        return FiXxDeptWiseEmpDtl.objects.filter(emp_cd=emp_key).first()
    except Exception:
        return None


def resolve_dept_wise_department(emp_code, *, fallback: str = "") -> str:
    """
    Department for pension letters (Through / Copy-to / sanction department line).
    Uses Oracle view FI_XX_DEPT_WISE_EMP_DTL mirrored on MySQL (DEPT_DESC only).
    Does not change employee designation — use desig master for that.
    """
    row = fetch_dept_wise_row(emp_code)
    if row and row.dept_desc:
        return _normalize_dept_label(row.dept_desc)
    return _normalize_dept_label(fallback)


def resolve_dept_wise_alloc_desc(emp_code) -> str:
    """Posting allocation from dept-wise view — not the employee designation."""
    row = fetch_dept_wise_row(emp_code)
    if row and row.alloc_desc:
        return str(row.alloc_desc).strip().upper()
    return ""
