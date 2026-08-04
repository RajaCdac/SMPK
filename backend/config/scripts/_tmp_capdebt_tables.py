import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from employee.services.oracle_service import get_oracle_connection

conn = get_oracle_connection()
cur = conn.cursor()
cur.execute(
    """
    SELECT table_name FROM all_tables
    WHERE owner = 'FINANCE' AND UPPER(table_name) LIKE '%CAPDEBT%'
    ORDER BY 1
    """
)
print("tables", [r[0] for r in cur.fetchall()])
cur.execute(
    """
    SELECT ALLOC_CD, ALLOC_DESC FROM FINANCE.FI_MA_MD_CAPDEBT_SL
    WHERE CAPDEBT_ALLOC_CD = '121' AND ALLOC_CD IN ('575', '576')
    """
)
print("sl", cur.fetchall())
cur.close()
conn.close()
