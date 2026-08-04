import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from employee.services.oracle_service import get_oracle_connection

conn = get_oracle_connection()
cur = conn.cursor()
cur.execute(
    """
    SELECT bill_cd, bill_dt, dbill_reg_no, abstract_no, abstract_dt,
           bill_amt, sanc_amt, deduct_amt, net_amt, bill_desc, payee_name, mth
    FROM finance.fi_pn_th_billpass
    WHERE dbill_reg_no LIKE 'PPN%' AND ROWNUM <= 2
    """
)
cols = [d[0] for d in cur.description]
for r in cur.fetchall():
    print(dict(zip(cols, r)))

cur.execute(
    """
    SELECT column_name FROM all_tab_columns
    WHERE owner='FINANCE' AND table_name='FI_PN_TH_BILLPASS'
    ORDER BY column_id
    """
)
print("cols", [r[0] for r in cur.fetchall()])

cur.execute(
    """
    SELECT column_name FROM all_tab_columns
    WHERE owner='FINANCE' AND table_name='FI_PN_TD_BILLPASS'
    ORDER BY column_id
    """
)
print("td cols", [r[0] for r in cur.fetchall()])

cur.close()
conn.close()
