import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from employee.services.oracle_service import get_oracle_connection

EMP = "46585"
conn = get_oracle_connection()
cur = conn.cursor()

cur.execute(
    """
    SELECT column_name FROM all_tab_columns
    WHERE owner = 'FINANCE' AND table_name = 'FI_XX_MH_EMP_FIN'
      AND (column_name LIKE '%BANK%' OR column_name LIKE '%AC%' OR column_name LIKE '%IFSC%'
           OR column_name LIKE '%RBI%' OR column_name LIKE '%BRANCH%')
    ORDER BY column_id
    """
)
print("=== bank-related columns ===")
for r in cur.fetchall():
    print(r[0])

cur.execute(
    """
    SELECT column_name FROM all_tab_columns
    WHERE owner = 'FINANCE' AND table_name = 'FI_XX_MH_EMP_FIN'
    ORDER BY column_id
    """
)
all_cols = [r[0] for r in cur.fetchall()]
print("\n=== all columns ===", len(all_cols))
print(", ".join(all_cols))

cur.execute(
    f"SELECT {', '.join(all_cols)} FROM finance.fi_xx_mh_emp_fin WHERE emp_cd = :emp",
    {"emp": EMP},
)
row = cur.fetchone()
if row:
    d = dict(zip(all_cols, row))
    for k, v in d.items():
        if v is not None and str(v).strip():
            print(f"{k}: {v}")

# compare pensioner
cur.execute(
    """
    SELECT emp_cd, bank_cd, account_no FROM finance.fi_pn_mh_pensioner WHERE emp_cd = :emp
    """,
    {"emp": EMP},
)
print("\n=== pensioner bank ===", dict(zip(["EMP_CD", "BANK_CD", "ACCOUNT_NO"], cur.fetchone() or [])))

# bank master for emp_fin bank_cd if present
if row:
    d = dict(zip(all_cols, row))
    bank_cd = d.get("BANK_CD") or d.get("BANK_CODE")
    if bank_cd:
        cur.execute(
            """
            SELECT b.bank_cd, b.bank_desc, b.rbi_cd, a.bank_name
            FROM finance.fi_pm_mh_bank b
            LEFT JOIN finance.fi_pm_mh_bankabbr a ON SUBSTR(b.bank_cd,1,2) = a.bank_type
            WHERE b.bank_cd = :cd
            """,
            {"cd": str(bank_cd).strip()},
        )
        r = cur.fetchone()
        if r:
            print("\n=== bank master for emp_fin bank_cd ===", dict(zip(["BANK_CD", "DESC", "RBI", "NAME"], r)))

cur.close()
conn.close()
