import os
import sys

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
django.setup()

from employee.services.oracle_service import get_oracle_connection

EMP = "46353"


def main():
    conn = get_oracle_connection()
    cur = conn.cursor()
    try:
        cur.execute(
            """
            SELECT SUM(LV_DAYS), SUM(WET_DT - WEF_DT + 1)
            FROM FINANCE.FI_LA_TH_LVAPPL
            WHERE EMP_CD = :e AND ATTEND_CD IN (4, 34)
            """,
            {"e": EMP},
        )
        print("NPL sum LV_DAYS vs date span:", cur.fetchone())

        for codes, label in [((4, 34), "NPL"), ((3, 35), "HPL"), ((2, 33), "FPL")]:
            cur.execute(
                f"""
                SELECT SUM(LV_DAYS), SUM(WET_DT - WEF_DT + 1), COUNT(*)
                FROM FINANCE.FI_LA_TH_LVAPPL
                WHERE EMP_CD = :e AND ATTEND_CD IN {codes}
                """,
                {"e": EMP},
            )
            print(label, cur.fetchone())

        cur.execute(
            """
            SELECT EMP_CD, SAL_YR, SAL_MTH, LV_CD, NO_DAYS
            FROM FINANCE.FI_PN_MD_OLDBILL_PARAM
            WHERE LV_CD = 4 AND ROWNUM <= 10
            ORDER BY EMP_CD
            """
        )
        print("sample MD oldbill LV_CD=4:")
        for row in cur.fetchall():
            print(row)

        cur.execute(
            """
            SELECT TABLE_NAME
            FROM ALL_TABLES
            WHERE OWNER = 'FINANCE'
              AND (
                TABLE_NAME LIKE '%NPAY%'
                OR TABLE_NAME LIKE '%NOPAY%'
                OR TABLE_NAME LIKE '%OLDBILL%'
              )
            ORDER BY TABLE_NAME
            """
        )
        print("tables:", [r[0] for r in cur.fetchall()])

        cur.execute(
            "SELECT * FROM FINANCE.FI_PN_MH_OLDBILL_PARAM WHERE EMP_CD = :e",
            {"e": EMP},
        )
        print("MH OLDBILL:", cur.fetchone())
    finally:
        cur.close()
        conn.close()


def list_la_tables():
    conn = get_oracle_connection()
    cur = conn.cursor()
    try:
        cur.execute(
            """
            SELECT TABLE_NAME
            FROM ALL_TABLES
            WHERE OWNER = 'FINANCE' AND TABLE_NAME LIKE 'FI_LA%'
            ORDER BY TABLE_NAME
            """
        )
        tables = [r[0] for r in cur.fetchall()]
        print("FI_LA tables:", len(tables))
        for t in tables:
            if any(x in t for x in ("ATTEND", "LV", "ABS")):
                print(" ", t)
    finally:
        cur.close()
        conn.close()


if __name__ == "__main__":
    main()
    print()
    list_la_tables()
