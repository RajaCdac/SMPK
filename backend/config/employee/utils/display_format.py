def normalize_department_name(dept_desc):
    text = str(dept_desc or "").strip()
    if not text:
        return ""
    text_upper = text.upper()
    if text_upper.startswith("ADMIN/SECY"):
        return "SECRETARY"
    return text


def format_dept_designation(dept_desc, desig_desc):
    """Display as DEPT(DESIG), e.g. ACCOUNTS(ACCOUNTS OFFICER)."""
    dept = normalize_department_name(dept_desc)
    desig = str(desig_desc or "").strip()
    if dept and desig:
        return f"{dept}({desig})"
    if dept:
        return dept
    return desig
