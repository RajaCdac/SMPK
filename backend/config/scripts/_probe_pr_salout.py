import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

try:
    from employee.services.oracle_service import get_oracle_connection

    conn = get_oracle_connection()
    cur = conn.cursor()

    for t in ["FI_PR_TH_SALOUT", "FI_PR_TD_SALOUT", "FI_PN_TH_SALOUT", "FI_PN_TD_SALOUT"]:
        cur.execute(
            "SELECT column_name, data_type FROM all_tab_columns "
            "WHERE owner='FINANCE' AND table_name=:t ORDER BY column_id",
            {"t": t},
        )
        cols = cur.fetchall()
        print(f"\n=== {t} ({len(cols)} cols) ===")
        for c in cols:
            print(f"  {c[0]}: {c[1]}")

    emp = "43186"
    print(f"\n=== FI_PR_TH_SALOUT sample {emp} (latest 5) ===")
    cur.execute(
        """
        SELECT * FROM (
            SELECT SAL_MTH, SAL_YR, FA_NO, SAL_BILL_NO, GROSS_EARN_AMT,
                   GROSS_DEDN_AMT, NET_EARN_AMT, SCALE_DESC, BASIC_RATE
            FROM FINANCE.FI_PR_TH_SALOUT
            WHERE EMP_CD = :emp
            ORDER BY SAL_YR DESC, SAL_MTH DESC
        ) WHERE ROWNUM <= 5
        """,
        {"emp": emp},
    )
    for row in cur.fetchall():
        print(row)

    print(f"\n=== FI_PN_TH_SALOUT sample {emp} (latest 5) ===")
    cur.execute(
        """
        SELECT * FROM (
            SELECT SAL_MTH, SAL_YR, FA_NO, SAL_BILL_NO, GROSS_EARN_AMT,
                   GROSS_DEDN_AMT, NET_EARN_AMT, SCALE_DESC, BASIC_RATE
            FROM FINANCE.FI_PN_TH_SALOUT
            WHERE EMP_CD = :emp
            ORDER BY SAL_YR DESC, SAL_MTH DESC
        ) WHERE ROWNUM <= 5
        """,
        {"emp": emp},
    )
    for row in cur.fetchall():
        print(row)

    print(f"\n=== FI_PR_TD_SALOUT basic 001 {emp} (latest 3) ===")
    cur.execute(
        """
        SELECT * FROM (
            SELECT SAL_MTH, SAL_YR, EARNDEDN_CD, ACT_EARNDEDN_AMT, ADJ_EARNDEDN_AMT
            FROM FINANCE.FI_PR_TD_SALOUT
            WHERE EMP_CD = :emp AND EARNDEDN_CD = '001'
            ORDER BY SAL_YR DESC, SAL_MTH DESC
        ) WHERE ROWNUM <= 3
        """,
        {"emp": emp},
    )
    for row in cur.fetchall():
        print(row)

    print(f"\n=== FI_PN_TD_SALOUT basic 001 {emp} (latest 3) ===")
    cur.execute(
        """
        SELECT * FROM (
            SELECT SAL_MTH, SAL_YR, EARNDEDN_CD, ACT_EARNDEDN_AMT, ADJ_EARNDEDN_AMT
            FROM FINANCE.FI_PN_TD_SALOUT
            WHERE EMP_CD = :emp AND EARNDEDN_CD = '001'
            ORDER BY SAL_YR DESC, SAL_MTH DESC
        ) WHERE ROWNUM <= 3
        """,
        {"emp": emp},
    )
    for row in cur.fetchall():
        print(row)

    # Row counts
    for t in ["FI_PR_TH_SALOUT", "FI_PN_TH_SALOUT"]:
        cur.execute(
            f"SELECT COUNT(*) FROM FINANCE.{t} WHERE EMP_CD = :emp", {"emp": emp}
        )
        print(f"{t} rows for {emp}:", cur.fetchone()[0])

    print("\n=== Audit: PR vs PN Dec/2023 43186 ===")
    cur.execute(
        """
        SELECT 'PR_TH', DATE_CREATED, CREATED_BY FROM FINANCE.FI_PR_TH_SALOUT
        WHERE EMP_CD='43186' AND SAL_MTH=12 AND SAL_YR=2023
        UNION ALL
        SELECT 'PN_TH', DATE_CREATED, CREATED_BY FROM FINANCE.FI_PN_TH_SALOUT
        WHERE EMP_CD='43186' AND SAL_MTH=12 AND SAL_YR=2023
        """
    )
    for row in cur.fetchall():
        print(row)

    for emp in ["42230", "43186"]:
        cur.execute(
            """
            SELECT BASIC_RATE FROM (
                SELECT BASIC_RATE FROM FINANCE.FI_PR_TH_SALOUT WHERE EMP_CD=:e
                ORDER BY SAL_YR DESC, SAL_MTH DESC
            ) WHERE ROWNUM=1
            """,
            {"e": emp},
        )
        pr_basic = cur.fetchone()[0]
        cur.execute(
            """
            SELECT BASIC_RATE FROM (
                SELECT BASIC_RATE FROM FINANCE.FI_PN_TH_SALOUT WHERE EMP_CD=:e
                ORDER BY SAL_YR DESC, SAL_MTH DESC
            ) WHERE ROWNUM=1
            """,
            {"e": emp},
        )
        pn_basic = cur.fetchone()[0]
        print(f"{emp}: PR last basic={pr_basic}, PN last basic={pn_basic}")

    cur.close()
    conn.close()
except Exception as e:
    print("Error:", e)
