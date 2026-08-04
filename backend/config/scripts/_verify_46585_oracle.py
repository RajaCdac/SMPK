import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from employee.services.oracle_service import get_oracle_connection

EMP = "46585"
PPN = "PPN/09/2025/79"

conn = get_oracle_connection()
cur = conn.cursor()

queries = [
    (
        "pensioner",
        """
        SELECT emp_cd, ca_number, name, bank_cd, account_no, emp_ret_dt,
               pension_roll_no, desig_cd, lic_bank_cd
        FROM finance.fi_pn_mh_pensioner
        WHERE emp_cd = :emp
        """,
    ),
    (
        "first_month_header",
        """
        SELECT fmpen_id, bill_no, pension_month, pension_yr, ca_no, bank_cd,
               lic_bank_cd, sys_man_tag, pension_type
        FROM finance.fi_pn_th_first_month_pension
        WHERE emp_cd = :emp
        ORDER BY pension_yr DESC, pension_month DESC
        """,
    ),
    (
        "pension_bill",
        """
        SELECT bill_no, bill_month, bill_yr, bank_cd, total_amt_earned,
               total_amt_deducted, bill_abstract_no, abstract_date, voucher_no,
               cheque_no, cheque_dt, gen_lic_tag, date_created
        FROM finance.fi_pn_th_pension_bill
        WHERE bill_no = :bill
        """,
    ),
    (
        "td_lines",
        """
        SELECT d.earn_dedn_type, d.earn_dedn_cd, d.amount
        FROM finance.fi_pn_th_first_month_pension h
        JOIN finance.fi_pn_td_first_month_pension d ON h.fmpen_id = d.fmpen_id
        WHERE h.emp_cd = :emp AND h.bill_no = :bill
        ORDER BY d.earn_dedn_type, d.earn_dedn_cd
        """,
    ),
    (
        "billpass_header",
        """
        SELECT bill_cd, bill_dt, dbill_reg_no, dbill_reg_dt, abstract_no,
               abstract_dt, bill_amt, deduct_amt, net_amt, mth, payee_name
        FROM finance.fi_pn_th_billpass
        WHERE dbill_reg_no = :bill
        """,
    ),
    (
        "billpass_td",
        """
        SELECT b.party_cd, b.payee_name, b.pbill_amt, b.deduct_amt, b.net_amt
        FROM finance.fi_pn_th_billpass a
        JOIN finance.fi_pn_td_billpass b
          ON a.bill_cd = b.bill_cd AND a.bill_dt = b.bill_dt
        WHERE a.dbill_reg_no = :bill
        """,
    ),
    (
        "bank",
        """
        SELECT b.bank_cd, b.bank_desc, b.addr1, b.addr2, b.ps, b.city, b.rbi_cd,
               a.bank_name
        FROM finance.fi_pn_mh_pensioner p
        LEFT JOIN finance.fi_pm_mh_bank b ON p.bank_cd = b.bank_cd
        LEFT JOIN finance.fi_pm_mh_bankabbr a ON SUBSTR(p.bank_cd,1,2) = a.bank_type
        WHERE p.emp_cd = :emp
        """,
    ),
    (
        "proposal",
        """
        SELECT emp_cd, ca_number, separation_dt, retirement_cpi, pension_proposal_no
        FROM finance.fi_pn_mh_pension_proposal
        WHERE emp_cd = :emp AND ROWNUM = 1
        """,
    ),
]

for label, sql in queries:
    print(f"\n=== {label} ===")
    params = {"emp": EMP}
    if ":bill" in sql:
        params["bill"] = PPN
    cur.execute(sql, params)
    cols = [d[0] for d in cur.description]
    rows = cur.fetchall()
    if not rows:
        print("(no rows)")
    for r in rows:
        print(dict(zip(cols, r)))

cur.close()
conn.close()
