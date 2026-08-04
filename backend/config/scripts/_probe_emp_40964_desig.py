import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from employee.services.oracle_service import get_oracle_connection

EMP = "40964"
conn = get_oracle_connection()
cur = conn.cursor()


def show(title, sql, binds=None):
    print(f"\n=== {title} ===")
    try:
        cur.execute(sql, binds or {})
        cols = [d[0] for d in cur.description]
        print(" | ".join(cols))
        for row in cur.fetchall()[:20]:
            print(" | ".join(str(v) for v in row))
    except Exception as exc:
        print("ERR", exc)


show(
    "PENSIONER",
    "SELECT NAME, DESIG_CD FROM FINANCE.FI_PN_MH_PENSIONER WHERE EMP_CD = :e",
    {"e": EMP},
)
show(
    "PROPOSAL",
    "SELECT EMP_NAME FROM FINANCE.FI_PN_MH_PENSION_PROPOSAL WHERE EMP_CD = :e",
    {"e": EMP},
)
show(
    "DESIG 847",
    "SELECT DESIG_CD, DESIG_DESC FROM FINANCE.FI_XX_MH_DESIG WHERE DESIG_CD = 847",
)
show(
    "DESIG search SENIOR EXEC",
    """
    SELECT DESIG_CD, DESIG_DESC FROM FINANCE.FI_XX_MH_DESIG
    WHERE UPPER(DESIG_DESC) LIKE '%SENIOR EXECUTIVE ENGINEER%'
    """,
)
show(
    "DESIG search MECHANICAL DOCK",
    """
    SELECT DESIG_CD, DESIG_DESC FROM FINANCE.FI_XX_MH_DESIG
    WHERE UPPER(DESIG_DESC) LIKE '%MECHANICAL%DOCK%'
    """,
)
show(
    "EMP_DATA posting cols",
    """
    SELECT column_name FROM all_tab_columns
    WHERE owner = 'FINANCE' AND table_name = 'FI_XX_MH_EMP_DATA'
      AND (column_name LIKE '%DESIG%' OR column_name LIKE '%DEPT%'
           OR column_name LIKE '%POST%' OR column_name LIKE '%DIV%')
    ORDER BY column_id
    """,
)
show(
    "EMP_DATA",
    "SELECT * FROM FINANCE.FI_XX_MH_EMP_DATA WHERE EMP_CD = :e",
    {"e": EMP},
)
show(
    "EMP_POSTING if exists",
    """
    SELECT table_name FROM all_tables
    WHERE owner = 'FINANCE' AND table_name LIKE '%POST%'
    ORDER BY table_name
    """,
)

cur.close()
conn.close()
