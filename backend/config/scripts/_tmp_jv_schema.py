import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from employee.services.oracle_service import get_oracle_connection

conn = get_oracle_connection()
cur = conn.cursor()

for t in [
    "FI_PN_TD_JV",
    "FI_PN_TH_BILLPASS",
    "FI_PN_MH_JRNLTYPE",
    "FI_PN_MD_JRNLTYPE",
]:
    cur.execute(
        """
        SELECT column_name, data_type, data_length
        FROM all_tab_columns
        WHERE owner = 'FINANCE' AND table_name = :t
        ORDER BY column_id
        """,
        {"t": t},
    )
    print("===", t)
    for r in cur.fetchall():
        print(r)

cur.execute(
    """
    SELECT bill_no, voucher_no, bill_month, bill_yr
    FROM finance.fi_pn_th_pension_bill
    WHERE substr(bill_no, 1, 3) = 'PPN'
      AND voucher_no IS NOT NULL
      AND ROWNUM <= 5
    """
)
print("sample bills", cur.fetchall())

cur.close()
conn.close()
