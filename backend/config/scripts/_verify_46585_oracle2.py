import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from employee.services.oracle_service import get_oracle_connection

EMP = "46585"
PPN = "PPN/09/2025/79"

conn = get_oracle_connection()
cur = conn.cursor()

def run(label, sql, params):
    print(f"\n=== {label} ===")
    cur.execute(sql, params)
    cols = [d[0] for d in cur.description]
    rows = cur.fetchall()
    if not rows:
        print("(no rows)")
    for r in rows:
        print(dict(zip(cols, r)))

run(
    "pension_bill",
    """
    SELECT bill_no, bill_month, bill_yr, bank_cd, total_amt_earned,
           total_amt_deducted, bill_abstract_no, abstract_date, voucher_no,
           cheque_no, cheque_dt, gen_lic_tag, date_created
    FROM finance.fi_pn_th_pension_bill
    WHERE bill_no = :bill
    """,
    {"bill": PPN},
)

run(
    "td_lines",
    """
    SELECT d.earn_dedn_type, d.earn_dedn_cd, d.amount
    FROM finance.fi_pn_th_first_month_pension h
    JOIN finance.fi_pn_td_first_month_pension d ON h.fmpen_id = d.fmpen_id
    WHERE h.emp_cd = :emp AND h.bill_no = :bill
    ORDER BY d.earn_dedn_type, d.earn_dedn_cd
    """,
    {"emp": EMP, "bill": PPN},
)

run(
    "td_sum",
    """
    SELECT SUM(CASE WHEN d.earn_dedn_type='E' THEN d.amount ELSE 0 END) earn,
           SUM(CASE WHEN d.earn_dedn_type='D' THEN d.amount ELSE 0 END) ded
    FROM finance.fi_pn_th_first_month_pension h
    JOIN finance.fi_pn_td_first_month_pension d ON h.fmpen_id = d.fmpen_id
    WHERE h.emp_cd = :emp AND h.bill_no = :bill
    """,
    {"emp": EMP, "bill": PPN},
)

run(
    "billpass_header",
    """
    SELECT bill_cd, bill_dt, dbill_reg_no, dbill_reg_dt, abstract_no,
           abstract_dt, bill_amt, deduct_amt, net_amt, mth, payee_name
    FROM finance.fi_pn_th_billpass
    WHERE dbill_reg_no = :bill
    """,
    {"bill": PPN},
)

run(
    "billpass_td",
    """
    SELECT b.party_cd, b.payee_name, b.pbill_amt, b.deduct_amt, b.net_amt, b.bill_pass_amt
    FROM finance.fi_pn_th_billpass a
    JOIN finance.fi_pn_td_billpass b
      ON a.bill_cd = b.bill_cd AND a.bill_dt = b.bill_dt
    WHERE a.dbill_reg_no = :bill
    """,
    {"bill": PPN},
)

run(
    "bank_130082",
    """
    SELECT bank_cd, bank_desc, addr1, addr2, ps, city, rbi_cd
    FROM finance.fi_pm_mh_bank WHERE bank_cd = '130082'
    """,
    {},
)

run(
    "bankabbr_13",
    """
    SELECT bank_type, bank_name FROM finance.fi_pm_mh_bankabbr WHERE bank_type = '13'
    """,
    {},
)

run(
    "account_search",
    """
    SELECT 'pensioner' src, emp_cd, account_no, bank_cd FROM finance.fi_pn_mh_pensioner
    WHERE emp_cd = :emp
    UNION ALL
    SELECT 'proposal' src, emp_cd, bank_ac_no, bank_cd FROM finance.fi_pn_mh_pension_proposal
    WHERE emp_cd = :emp AND ROWNUM = 1
    """,
    {"emp": EMP},
)

# search account from image
run(
    "acct_11110104877",
    """
    SELECT emp_cd, name, account_no, bank_cd FROM finance.fi_pn_mh_pensioner
    WHERE account_no LIKE '%11110104877%'
    """,
    {},
)

run(
    "ifsc_search",
    """
    SELECT bank_cd, bank_desc, rbi_cd FROM finance.fi_pm_mh_bank
    WHERE rbi_cd = 'SBIN0003334'
    """,
    {},
)

run(
    "jv",
    """
    SELECT voucher_no, voucher_dt, tot_amt, ref_no FROM finance.fi_pn_th_jv
    WHERE ref_no = :bill
    """,
    {"bill": PPN},
)

cur.close()
conn.close()
