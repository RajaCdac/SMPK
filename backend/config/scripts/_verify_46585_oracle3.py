import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from employee.services.oracle_service import get_oracle_connection

EMP = "46585"
conn = get_oracle_connection()
cur = conn.cursor()

def run(label, sql, params=None):
    print(f"\n=== {label} ===")
    cur.execute(sql, params or {})
    cols = [d[0] for d in cur.description]
    rows = cur.fetchall()
    if not rows:
        print("(no rows)")
    for r in rows:
        print(dict(zip(cols, r)))

run(
    "acct_image",
    "SELECT emp_cd, name, account_no, bank_cd FROM finance.fi_pn_mh_pensioner WHERE account_no = '11110104877'",
)
run(
    "acct_like",
    "SELECT emp_cd, name, account_no, bank_cd FROM finance.fi_pn_mh_pensioner WHERE account_no LIKE '%04877%'",
)
run(
    "ifsc",
    "SELECT bank_cd, bank_desc, rbi_cd FROM finance.fi_pm_mh_bank WHERE rbi_cd = 'SBIN0003334'",
)
run(
    "sbi_kidder",
    "SELECT bank_cd, bank_desc, rbi_cd FROM finance.fi_pm_mh_bank WHERE UPPER(bank_desc) LIKE '%KIDDER%'",
)
run(
    "proposal_cols",
    """
    SELECT column_name FROM all_tab_columns
    WHERE owner='FINANCE' AND table_name='FI_PN_MH_PENSION_PROPOSAL'
      AND column_name LIKE '%BANK%' OR column_name LIKE '%ACCOUNT%' OR column_name LIKE '%AC_%'
    ORDER BY column_id
    """,
)
run(
    "proposal_46585",
    """
    SELECT emp_cd, ca_number, separation_dt, bank_cd, account_no
    FROM finance.fi_pn_mh_pension_proposal
    WHERE emp_cd = :emp AND ROWNUM = 1
    """,
    {"emp": EMP},
)

# Q2 style amounts - exclude earn 200?
run(
    "td_excl_200",
    """
    SELECT SUM(amount) FROM finance.fi_pn_td_first_month_pension d
    JOIN finance.fi_pn_th_first_month_pension h ON h.fmpen_id = d.fmpen_id
    WHERE h.emp_cd = :emp AND h.bill_no = 'PPN/09/2025/79'
      AND d.earn_dedn_type = 'E' AND d.earn_dedn_cd <> '200'
    """,
    {"emp": EMP},
)

run(
    "sepcom",
    """
    SELECT pb.bill_no, e.nominee_name, e.bank_ac_no, e.bank_cd
    FROM finance.fi_pn_th_pension_bill pb
    JOIN finance.fi_pn_th_sepcom mfb ON pb.bill_no = mfb.bill_no
    JOIN finance.fi_pn_td_sepcom mfd ON mfb.sepcom_id = mfd.sepcom_id
    JOIN finance.fi_pn_mh_earndedn e2 ON 1=1
    WHERE pb.bill_no = 'PPN/09/2025/79' AND ROWNUM <= 5
    """,
)

# emp fin / emp adm bank?
run(
    "emp_fin",
    """
    SELECT column_name FROM all_tab_columns
    WHERE owner='FINANCE' AND table_name='FI_XX_MH_EMP_FIN'
      AND (column_name LIKE '%BANK%' OR column_name LIKE '%AC%')
    ORDER BY column_id
    """,
)

run(
    "emp_per_bank",
    """
    SELECT column_name FROM all_tab_columns
    WHERE owner='FINANCE' AND table_name='FI_XX_MH_EMP_PER'
      AND (column_name LIKE '%BANK%' OR column_name LIKE '%AC%')
    ORDER BY column_id
    """,
)

cur.close()
conn.close()
