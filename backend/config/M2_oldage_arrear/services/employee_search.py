"""
Find EMP_CD from a case no or roll no.

Pension masters always carry EMP_CD. Wage headers often do not; such a row
is linked through its roll no (masters) or another row with the same case no.
"""

from django.db import connection

WAGE_TABLES = (
    "fi_pn_wage_2017_hdr_offi2",
    "fi_pn_wage_2017_hdr_third",
    "fi_pn_wage_2022_hdr_third",
)

# CASE_NO is numeric in wage headers and text in masters; compare without
# leading zeros.
_CASE_EXPR = "TRIM(LEADING '0' FROM TRIM(CAST({col} AS CHAR)))"
_ROLL_EXPR = "UPPER(TRIM({col}))"


def _norm_case(value) -> str:
    return str(value or "").strip().lstrip("0")


def _norm_roll(value) -> str:
    return str(value or "").strip().upper()


def _has_emp(value) -> bool:
    return bool(str(value or "").strip())


def _emp_by_roll_in_masters(cursor, roll: str) -> list:
    found = []
    for table, col in (
        ("fi_pn_mh_familypensioner", "FPENSION_ROLL_NO"),
        ("fi_pn_mh_pensioner", "PENSION_ROLL_NO"),
        ("fi_pn_mh_pension_proposal", "PENSION_ROLL_NO"),
    ):
        cursor.execute(
            f"SELECT DISTINCT EMP_CD FROM {table} "
            f"WHERE {_ROLL_EXPR.format(col=col)} = %s",
            [roll],
        )
        found.extend(str(r[0]).strip() for r in cursor.fetchall() if _has_emp(r[0]))
    return found


def _emp_by_case_in_masters(cursor, case_no: str) -> list:
    found = []
    for table in ("fi_pn_mh_pension_proposal", "fi_pn_mh_familypensioner"):
        cursor.execute(
            f"SELECT DISTINCT EMP_CD FROM {table} "
            f"WHERE {_CASE_EXPR.format(col='CA_NUMBER')} = %s",
            [case_no],
        )
        found.extend(str(r[0]).strip() for r in cursor.fetchall() if _has_emp(r[0]))
    return found


def _wage_rows(cursor, column: str, value: str) -> list:
    expr = (_CASE_EXPR if column == "CASE_NO" else _ROLL_EXPR).format(col=column)
    rows = []
    for table in WAGE_TABLES:
        cursor.execute(
            f"""
            SELECT EMP_CD, CASE_NO, ROLL_NO, EMP_NAME, PEN_NAME, PENSIONER_TYPE
            FROM {table}
            WHERE {expr} = %s
            """,
            [value],
        )
        for r in cursor.fetchall():
            rows.append(
                {
                    "table": table,
                    "emp_cd": str(r[0] or "").strip(),
                    "case_no": str(r[1] or "").strip(),
                    "roll_no": str(r[2] or "").strip(),
                    "emp_name": str(r[3] or "").strip(),
                    "pen_name": str(r[4] or "").strip(),
                    "pensioner_type": str(r[5] or "").strip().upper(),
                }
            )
    return rows


def _emp_for_unlinked_wage_row(cursor, row: dict) -> list:
    """EMP_CD for a wage row that has none: by its roll, then by its case."""
    found = []
    roll = _norm_roll(row.get("roll_no"))
    if roll:
        found.extend(_emp_by_roll_in_masters(cursor, roll))
    case_no = _norm_case(row.get("case_no"))
    if not found and case_no:
        cursor.execute(
            f"""
            SELECT DISTINCT EMP_CD FROM {row['table']}
            WHERE {_CASE_EXPR.format(col='CASE_NO')} = %s
              AND EMP_CD IS NOT NULL AND TRIM(EMP_CD) <> ''
            """,
            [case_no],
        )
        found.extend(str(r[0]).strip() for r in cursor.fetchall())
        if not found:
            found.extend(_emp_by_case_in_masters(cursor, case_no))
    return found


def _describe(cursor, emp: str) -> dict:
    out = {"emp_cd": emp, "name": "", "case_no": "", "roll_no": ""}
    cursor.execute(
        "SELECT NAME, PENSION_ROLL_NO FROM fi_pn_mh_pensioner WHERE EMP_CD = %s LIMIT 1",
        [emp],
    )
    r = cursor.fetchone()
    if r:
        out["name"] = str(r[0] or "").strip()
        out["roll_no"] = str(r[1] or "").strip()
    cursor.execute(
        "SELECT CA_NUMBER, PENSION_ROLL_NO FROM fi_pn_mh_pension_proposal "
        "WHERE EMP_CD = %s LIMIT 1",
        [emp],
    )
    r = cursor.fetchone()
    if r:
        out["case_no"] = str(r[0] or "").strip()
        out["roll_no"] = out["roll_no"] or str(r[1] or "").strip()
    if not out["name"]:
        cursor.execute(
            "SELECT TITLE, FIRST_NAME, MIDDLE_NAME, LAST_NAME FROM fi_xx_mh_emp_per "
            "WHERE EMP_CD = %s LIMIT 1",
            [emp],
        )
        r = cursor.fetchone()
        if r:
            out["name"] = " ".join(str(p).strip() for p in r if p and str(p).strip())
    return out


def search_employee(by: str, value: str) -> dict:
    """
    by: "emp" | "case" | "roll"

    Returns {"matches": [{emp_cd, name, case_no, roll_no}],
             "unlinked": [wage rows found with no EMP_CD anywhere]}.
    """
    by = str(by or "emp").strip().lower()
    text = str(value or "").strip()
    result = {"matches": [], "unlinked": []}
    if not text:
        return result
    if by == "emp":
        result["matches"] = [{"emp_cd": text, "name": "", "case_no": "", "roll_no": ""}]
        return result

    emps = []
    with connection.cursor() as cursor:
        if by == "case":
            key = _norm_case(text)
            emps.extend(_emp_by_case_in_masters(cursor, key))
            wage = _wage_rows(cursor, "CASE_NO", key)
        else:
            key = _norm_roll(text)
            emps.extend(_emp_by_roll_in_masters(cursor, key))
            wage = _wage_rows(cursor, "ROLL_NO", key)

        for row in wage:
            if row["emp_cd"]:
                emps.append(row["emp_cd"])
                continue
            linked = _emp_for_unlinked_wage_row(cursor, row)
            if linked:
                emps.extend(linked)
            else:
                result["unlinked"].append(row)

        seen = []
        for emp in emps:
            if emp and emp not in seen:
                seen.append(emp)
        result["matches"] = [_describe(cursor, emp) for emp in seen]
    if result["matches"]:
        result["unlinked"] = []
    return result
