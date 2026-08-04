import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from employee.services.oracle_service import get_oracle_connection

EMP = "46585"
conn = get_oracle_connection()
cur = conn.cursor()

queries = [
    ("proposal", """
        SELECT emp_cd, ca_number, separation_dt, bank_cd, accnt_no, cpt_acc_no
        FROM finance.fi_pn_mh_pension_proposal WHERE emp_cd = :emp AND ROWNUM = 1
    """),
    ("td_excl_200", """
        SELECT d.earn_dedn_cd, d.amount FROM finance.fi_pn_td_first_month_pension d
        JOIN finance.fi_pn_th_first_month_pension h ON h.fmpen_id = d.fmpen_id
        WHERE h.emp_cd = :emp AND h.bill_no = 'PPN/09/2025/79' AND d.earn_dedn_type='E'
        ORDER BY d.earn_dedn_cd
    """),
    ("bankabbr_01", "SELECT bank_type, bank_name FROM finance.fi_pm_mh_bankabbr WHERE bank_type='01'"),
    ("bank_010058", "SELECT bank_cd, bank_desc, rbi_cd, addr1, addr2 FROM finance.fi_pm_mh_bank WHERE bank_cd='010058'"),
    ("lic_report_bank", """
        SELECT h.emp_cd, h.bank_cd, h.lic_bank_cd, p.account_no, p.name
        FROM finance.fi_pn_th_first_month_pension h
        JOIN finance.fi_pn_mh_pensioner p ON p.emp_cd = h.emp_cd
        WHERE h.emp_cd = :emp
    """),
]

for label, sql in queries:
    print(f"\n=== {label} ===")
    try:
        cur.execute(sql, {"emp": EMP} if ":emp" in sql else {})
        cols = [d[0] for d in cur.description]
        for r in cur.fetchall():
            print(dict(zip(cols, r)))
    except Exception as e:
        print("ERR", e)

cur.close()
conn.close()
