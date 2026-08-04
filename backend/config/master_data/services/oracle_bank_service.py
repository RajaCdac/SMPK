from employee.services.oracle_service import get_oracle_connection
from master_data.services.bank_row_mapper import (
    oracle_bank_abbr_row_to_defaults,
    oracle_bank_row_to_defaults,
)
from master_data.services.bank_service import lookup_bank_desc


def fetch_oracle_bank_rows_for_sync():
    with get_oracle_connection().cursor() as cursor:
        cursor.execute("SELECT * FROM FINANCE.FI_PM_MH_BANK ORDER BY BANK_CD")
        column_names = [d[0] for d in cursor.description]
        rows = cursor.fetchall()

    result = []
    for row in rows:
        item = oracle_bank_row_to_defaults(column_names, row)
        if item:
            result.append(item)
    return result


def fetch_oracle_bank_abbr_rows_for_sync():
    with get_oracle_connection().cursor() as cursor:
        cursor.execute("SELECT * FROM FINANCE.FI_PM_MH_BANKABBR ORDER BY BANK_TYPE")
        column_names = [d[0] for d in cursor.description]
        rows = cursor.fetchall()

    result = []
    for row in rows:
        item = oracle_bank_abbr_row_to_defaults(column_names, row)
        if item:
            result.append(item)
    return result


def fetch_employee_bank_details(cursor, emp_id):
    bank = {
        "bank_cd": "",
        "bank_name": "",
        "account_no": "",
    }
    queries = [
        """
        SELECT e.EMP_CD, e.BANK_CD, b.BANK_DESC, e.BANK_AC_NO
        FROM FINANCE.FI_XX_MH_EMP_FIN e
        LEFT JOIN FINANCE.FI_PM_MH_BANK b ON e.BANK_CD = b.BANK_CD
        WHERE e.EMP_CD = :emp_id
        """,
        """
        SELECT e.EMP_CD, e.BANK_CD, b.BANK_DESC, e.BANK_AC_NO
        FROM FINANCE.FI_XX_MH_EMP_FIN e
        LEFT JOIN FINANCE.FI_PM_MH_BANK b ON e.BANK_CD = b.BANK_CD
        WHERE TRIM(e.EMP_CD) = TRIM(:emp_id)
        """,
    ]
    for query in queries:
        try:
            cursor.execute(query, {"emp_id": str(emp_id).strip()})
            row = cursor.fetchone()
            if row:
                bank_cd = str(row[1]).strip() if row[1] is not None else ""
                bank["bank_cd"] = bank_cd
                oracle_name = str(row[2]).strip() if row[2] is not None else ""
                bank["bank_name"] = oracle_name or lookup_bank_desc(bank_cd)
                bank["account_no"] = str(row[3]).strip() if row[3] is not None else ""
                break
        except Exception:
            continue
    return bank
