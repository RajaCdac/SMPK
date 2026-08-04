import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from employee.services.oracle_service import get_oracle_connection

conn = get_oracle_connection()
cur = conn.cursor()

for table in ["FI_PN_TH_JV", "FI_PN_TD_JV"]:
    cur.execute(
        """
        SELECT column_name, data_type, data_length
        FROM all_tab_columns
        WHERE owner='FINANCE' AND table_name = :t
        ORDER BY column_id
        """,
        {"t": table},
    )
    print(f"\n=== {table} ===")
    for r in cur.fetchall():
        print(r)

# sample manual jv rows
cur.execute(
    """
    SELECT voucher_no, yr, mth, voucher_dt, tran_type, ref_no, narration, tot_amt, voucher_for
    FROM (
        SELECT voucher_no, yr, mth, voucher_dt, tran_type, ref_no, narration, tot_amt, voucher_for
        FROM finance.fi_pn_th_jv
        WHERE tran_type NOT LIKE 'PNJV%'
        ORDER BY voucher_dt DESC
    ) WHERE ROWNUM <= 5
    """
)
print("\n=== non-PNJV sample headers ===")
cols = [d[0] for d in cur.description]
for r in cur.fetchall():
    print(dict(zip(cols, r)))

cur.execute(
    """
    SELECT DISTINCT tran_type FROM finance.fi_pn_th_jv
    WHERE ROWNUM <= 50
    ORDER BY 1
    """
)
print("\n=== tran_types ===", [r[0] for r in cur.fetchall()])

cur.close()
conn.close()
