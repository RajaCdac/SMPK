import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from employee.services.oracle_service import get_oracle_connection

bill = "PPN/07/2026/207"
conn = get_oracle_connection()
cur = conn.cursor()

cur.execute(
    """
    SELECT bill_cd, bill_dt, dbill_reg_no, dbill_reg_dt, fbill_reg_no, fbill_reg_dt,
           bill_desc, abstract_no, abstract_dt, bill_amt, sanc_amt, deduct_amt, net_amt, mth, payee_name
    FROM finance.fi_pn_th_billpass
    WHERE dbill_reg_no = :b
    """,
    {"b": bill},
)
cols = [d[0] for d in cur.description]
rows = cur.fetchall()
print("billpass header rows:", len(rows))
for r in rows:
    print(dict(zip(cols, r)))

if rows:
    bill_cd, bill_dt = rows[0][0], rows[0][1]
    cur.execute(
        """
        SELECT party_cd, payee_name, pbill_amt, deduct_amt, net_amt, bill_desc, bill_pass_amt
        FROM finance.fi_pn_td_billpass
        WHERE bill_cd = :cd AND bill_dt = :dt
        ORDER BY party_cd
        """,
        {"cd": bill_cd, "dt": bill_dt},
    )
    tcols = [d[0] for d in cur.description]
    td = cur.fetchall()
    print("td rows:", len(td))
    for r in td[:10]:
        print(dict(zip(tcols, r)))

cur.close()
conn.close()

# mysql bill
from first_pension.oracle_mirror import FiPnThPensionBill

b = FiPnThPensionBill.objects.filter(bill_no=bill).first()
if b:
    print(
        "mysql bill:",
        b.bill_no,
        b.bill_abstract_no,
        b.abstract_date,
        b.voucher_no,
        b.total_amt_earned,
        b.total_amt_deducted,
    )
