import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from employee.services.oracle_service import get_oracle_connection

EMP = "46585"
PPN = "PPN/09/2025/79"
conn = get_oracle_connection()
cur = conn.cursor()

for label, sql in [
    ("proposal_cols", """
        SELECT column_name FROM all_tab_columns
        WHERE owner='FINANCE' AND table_name='FI_PN_MH_PENSION_PROPOSAL'
        ORDER BY column_id
    """),
    ("proposal_row", """
        SELECT * FROM finance.fi_pn_mh_pension_proposal
        WHERE emp_cd = :emp AND ROWNUM = 1
    """),
    ("nominee_gr", """
        SELECT emp_cd, nominee_name, bank_cd, bank_ac_no, relation_cd
        FROM finance.fi_xx_md_nominee
        WHERE emp_cd = :emp AND nomin_type = 'GR'
    """),
    ("jv_amt", """
        SELECT SUM(amount) amt, dr_cr_flag FROM finance.fi_pn_td_jv
        WHERE voucher_no = 'PNJV/2025/8/00156'
        GROUP BY dr_cr_flag
    """),
]:
    print(f"\n=== {label} ===")
    try:
        cur.execute(sql, {"emp": EMP} if ":emp" in sql else {})
        cols = [d[0] for d in cur.description]
        for r in cur.fetchall():
            if label == "proposal_row":
                d = dict(zip(cols, r))
                for k in sorted(d.keys()):
                    if d[k] is not None and str(d[k]).strip():
                        if any(x in k for x in ["BANK", "ACCOUNT", "ACC", "ACNT", "SEPN", "RET", "CA_"]):
                            print(k, d[k])
            else:
                print(dict(zip(cols, r)))
    except Exception as e:
        print("ERR", e)

cur.close()
conn.close()
