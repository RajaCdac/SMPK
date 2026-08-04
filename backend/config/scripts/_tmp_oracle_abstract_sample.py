import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from employee.services.oracle_service import get_oracle_connection

conn = get_oracle_connection()
cur = conn.cursor()

cur.execute(
    """
    SELECT * FROM (
        SELECT a.bill_cd, a.dbill_reg_no, a.abstract_no, a.bill_amt, a.net_amt,
               COUNT(b.party_cd) cnt
        FROM finance.fi_pn_th_billpass a
        JOIN finance.fi_pn_td_billpass b
          ON a.bill_cd = b.bill_cd AND a.bill_dt = b.bill_dt
        WHERE a.dbill_reg_no LIKE 'PPN%'
        GROUP BY a.bill_cd, a.dbill_reg_no, a.abstract_no, a.bill_amt, a.net_amt
        HAVING COUNT(b.party_cd) BETWEEN 2 AND 20
        ORDER BY a.bill_dt DESC
    ) WHERE ROWNUM <= 3
    """
)
samples = cur.fetchall()
print("samples", samples)

if samples:
    bill_cd, dbill, *_ = samples[0]
    cur.execute(
        """
        SELECT party_cd, payee_name, pbill_amt, deduct_amt, net_amt, bill_pass_amt
        FROM finance.fi_pn_td_billpass
        WHERE bill_cd = :cd
        ORDER BY party_cd
        """,
        {"cd": bill_cd},
    )
    for r in cur.fetchall():
        print(" td", r)

cur.close()
conn.close()
