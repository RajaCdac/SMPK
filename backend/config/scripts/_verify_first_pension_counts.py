"""Compare Oracle vs MySQL row counts for key first-pension tables."""
import os
import sys

import django
import MySQLdb

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
django.setup()

from employee.services.oracle_service import get_oracle_connection

TABLES = [
    # Employee / service
    "FI_XX_MH_EMP_ADM",
    "FI_XX_MH_EMP_PER",
    "FI_XX_MH_EMP_FIN",
    "FI_XX_MD_FINSCALE",
    # No-pay
    "FI_PN_MH_OLDBILL_PARAM",
    "FI_PN_MD_OLDBILL_PARAM",
    # Commutation / application
    "FI_PN_MH_APPLICATION",
    # Proposal
    "FI_PN_MH_PENSION_PROPOSAL",
    "FI_PN_MD_PENSION_PROPOSAL",
    # Pensioner / amounts
    "FI_PN_MH_PENSIONER",
    # Salary / emoluments
    "FI_PN_TH_SALOUT",
    "FI_PN_TD_SALOUT",
    "FI_PR_TH_SALOUT",
    "FI_PR_TD_SALOUT",
    # Bills / first month
    "FI_PN_TH_PENSION_BILL",
    "FI_PN_TH_FIRST_MONTH_PENSION",
    "FI_PN_TD_FIRST_MONTH_PENSION",
    # Journal
    "FI_PN_TH_JV",
    "FI_PN_TD_JV",
    # Leave (no-pay detail)
    "FI_LA_TH_LVAPPL",
    "FI_LA_MH_ATTENDTYPE",
    "FI_LA_MH_LVREASON",
    # Masters used by pension calc
    "FI_PN_MD_COMMRATE_RUPEE",
    "FI_PN_MD_MAXADM_GRATUITY",
    "FI_PN_MD_DEATH_GRATCHART",
]


def mysql_count(cur, table: str):
    try:
        cur.execute(f"SELECT COUNT(*) FROM `{table}`")
        return cur.fetchone()[0]
    except Exception as exc:
        return f"ERR:{exc.args[0] if getattr(exc, 'args', None) else exc}"


def oracle_count(cur, table: str):
    try:
        cur.execute(f"SELECT COUNT(*) FROM FINANCE.{table}")
        return cur.fetchone()[0]
    except Exception as exc:
        return f"ERR:{exc}"


def main():
    ora = get_oracle_connection()
    ora_cur = ora.cursor()
    my = MySQLdb.connect(
        host="localhost",
        port=3307,
        user="root",
        passwd="root123",
        db="finance",
        charset="utf8mb4",
    )
    my_cur = my.cursor()

    print(
        f"{'TABLE':<36} {'ORACLE':>12} {'MYSQL':>12} {'DIFF':>12} {'STATUS'}"
    )
    print("-" * 90)

    ok = 0
    mismatch = 0
    missing = 0

    for table in TABLES:
        o = oracle_count(ora_cur, table)
        m = mysql_count(my_cur, table)

        if isinstance(o, str) or isinstance(m, str):
            status = "MISSING/ERR"
            missing += 1
            diff = "-"
        elif o == m:
            status = "OK"
            ok += 1
            diff = 0
        else:
            status = "MISMATCH"
            mismatch += 1
            diff = m - o if isinstance(m, int) and isinstance(o, int) else "-"

        print(f"{table:<36} {str(o):>12} {str(m):>12} {str(diff):>12} {status}")

    print("-" * 90)
    print(f"OK={ok}  MISMATCH={mismatch}  MISSING/ERR={missing}  TOTAL={len(TABLES)}")

    # Sample known employee 46353
    print("\n=== Sample emp 46353 ===")
    checks = [
        (
            "OLDBILL_PARAM",
            "SELECT NPAY_PRIOR_10MTH, NPAY_MORETHAN_240_DYS, DNON_DAYS "
            "FROM FINANCE.FI_PN_MH_OLDBILL_PARAM WHERE EMP_CD = :e",
            "SELECT NPAY_PRIOR_10MTH, NPAY_MORETHAN_240_DYS, DNON_DAYS "
            "FROM FI_PN_MH_OLDBILL_PARAM WHERE EMP_CD = %s",
        ),
        (
            "PENSIONER",
            "SELECT CA_NUMBER, EMP_CD, PENSION_TYPE FROM FINANCE.FI_PN_MH_PENSIONER "
            "WHERE EMP_CD = :e AND ROWNUM <= 3",
            "SELECT CA_NUMBER, EMP_CD, PENSION_TYPE FROM FI_PN_MH_PENSIONER "
            "WHERE EMP_CD = %s LIMIT 3",
        ),
        (
            "APPLICATION",
            "SELECT EMP_CD, APPCN_NO FROM FINANCE.FI_PN_MH_APPLICATION "
            "WHERE EMP_CD = :e AND ROWNUM <= 3",
            "SELECT EMP_CD, APPCN_NO FROM FI_PN_MH_APPLICATION "
            "WHERE EMP_CD = %s LIMIT 3",
        ),
        (
            "PROPOSAL",
            "SELECT CA_NUMBER, EMP_CD FROM FINANCE.FI_PN_MH_PENSION_PROPOSAL "
            "WHERE EMP_CD = :e AND ROWNUM <= 3",
            "SELECT CA_NUMBER, EMP_CD FROM FI_PN_MH_PENSION_PROPOSAL "
            "WHERE EMP_CD = %s LIMIT 3",
        ),
    ]

    emp = "46353"
    for label, osql, msql in checks:
        print(f"\n-- {label} --")
        try:
            ora_cur.execute(osql, {"e": emp})
            print("  Oracle:", ora_cur.fetchall())
        except Exception as exc:
            print("  Oracle ERR:", exc)
        try:
            my_cur.execute(msql, (emp,))
            print("  MySQL :", my_cur.fetchall())
        except Exception as exc:
            print("  MySQL ERR:", exc)

    ora_cur.close()
    ora.close()
    my_cur.close()
    my.close()


if __name__ == "__main__":
    main()
