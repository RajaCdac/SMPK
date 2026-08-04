import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from employee.services.oracle_service import get_oracle_connection

conn = get_oracle_connection()
cur = conn.cursor()

queries = [
    """
    SELECT object_name, object_type
    FROM all_objects
    WHERE owner = 'FINANCE'
      AND (UPPER(object_name) LIKE '%JV%RPT%'
           OR UPPER(object_name) LIKE '%TD_JV%')
    ORDER BY object_name
    """,
    """
    SELECT report_name, report_desc
    FROM finance.fi_xx_xx_m_reports
    WHERE UPPER(report_name) LIKE '%JV%'
       OR UPPER(report_desc) LIKE '%JOURNAL%'
    """,
]

for q in queries:
    print("===", q.strip().split("\n")[1].strip(), "===")
    try:
        cur.execute(q)
        cols = [d[0] for d in cur.description]
        rows = cur.fetchall()
        print("cols", cols, "count", len(rows))
        for r in rows[:25]:
            print(r)
    except Exception as exc:
        print("ERR", exc)

# sample JV header+lines for report layout reference
cur.execute(
    """
    SELECT h.voucher_no, h.voucher_dt, h.tran_type, h.ref_no, h.narration, h.tot_amt,
           d.sl_no, d.zonal_cd, d.aloc_cd1, d.aloc_cd2, d.aloc_cd3,
           d.dr_cr_flag, d.amount, d.remarks
    FROM finance.fi_pn_th_jv h
    JOIN finance.fi_pn_td_jv d
      ON h.voucher_no = d.voucher_no AND h.voucher_dt = d.voucher_dt
    WHERE h.ref_no = 'PPN/09/2025/79'
    ORDER BY d.sl_no
    """
)
print("\n=== sample PPN/09/2025/79 ===")
for r in cur.fetchall():
    print(r)

cur.close()
conn.close()
