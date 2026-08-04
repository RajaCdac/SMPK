"""Read-only Oracle bill check for given employee codes."""
import sys

from employee.services.oracle_service import get_oracle_connection

EMPS = sys.argv[1:] if len(sys.argv) > 1 else ["43544", "43424"]

SQL_PROP = """
SELECT EMP_CD, CA_NUMBER, BANK_CD, LIC_BANK_CD, PENSION_ROLL_NO, SEPARATION_DT
FROM FINANCE.FI_PN_MH_PENSION_PROPOSAL
WHERE EMP_CD = :emp
"""

SQL_TH = """
SELECT EMP_CD, FMPEN_ID, PENSION_MONTH, PENSION_YR, PENSION_TYPE,
       CA_NO, BILL_NO, BANK_CD, LIC_BANK_CD, PAYABLE_PENSION, ORIGINAL_FPENSION_AMT,
       DATE_CREATED, CREATED_BY
FROM FINANCE.FI_PN_TH_FIRST_MONTH_PENSION
WHERE EMP_CD = :emp
ORDER BY PENSION_YR DESC, PENSION_MONTH DESC
"""

SQL_BILL = """
SELECT BILL_NO, BILL_TYPE, BILL_MONTH, BILL_YR, BANK_CD,
       TOTAL_AMT_EARNED, TOTAL_AMT_DEDUCTED, GEN_LIC_TAG,
       BILL_ABSTRACT_NO, ABSTRACT_DATE, DATE_CREATED, CREATED_BY
FROM FINANCE.FI_PN_TH_PENSION_BILL
WHERE BILL_NO = :bill_no
"""

SQL_TD = """
SELECT EARN_DEDN_TYPE, EARN_DEDN_CD, AMOUNT
FROM FINANCE.FI_PN_TD_FIRST_MONTH_PENSION
WHERE FMPEN_ID = :fmpen_id
ORDER BY EARN_DEDN_TYPE, EARN_DEDN_CD
"""


def main():
    with get_oracle_connection().cursor() as cur:
        for emp in EMPS:
            print("=" * 70)
            print(f"EMPLOYEE {emp}")
            print("=" * 70)

            cur.execute(SQL_PROP, emp=emp)
            props = cur.fetchall()
            print(f"PROPOSAL rows: {len(props)}")
            for r in props:
                print(
                    f"  CA={r[1]} | bank_cd={r[2]} | lic_bank_cd={r[3]} "
                    f"| roll={r[4]} | sepn={r[5]}"
                )

            cur.execute(SQL_TH, emp=emp)
            rows = cur.fetchall()
            print(f"FIRST_MONTH headers: {len(rows)}")
            if not rows:
                print("  (no first-month pension in Oracle)")
                print()
                continue

            for r in rows:
                period = f"{int(r[2]):02d}/{int(r[3])}"
                print(f"  FMPEN={r[1]} | period={period} | type={r[4]}")
                print(f"  CA={r[5]} | BILL_NO={r[6] or '(empty)'}")
                print(f"  BANK_CD={r[7]} | LIC_BANK_CD={r[8]}")
                print(f"  Original={r[9]} | Payable={r[10]} | created={r[11]} {r[12]}")

                bill_no = r[6]
                if bill_no:
                    cur.execute(SQL_BILL, bill_no=bill_no)
                    bill = cur.fetchone()
                    if bill:
                        bperiod = f"{int(bill[2]):02d}/{int(bill[3])}"
                        print(f"  BILL HEADER: {bill[0]}")
                        print(
                            f"    bill period={bperiod} | bank={bill[4]} "
                            f"| earned={bill[5]} | deducted={bill[6]} | gen_lic={bill[7]}"
                        )
                        print(f"    abstract={bill[8]} | abstract_dt={bill[9]}")
                    else:
                        print(f"  BILL HEADER: NOT FOUND for {bill_no}")

                cur.execute(SQL_TD, fmpen_id=r[1])
                tds = cur.fetchall()
                print(f"  TD lines: {len(tds)}")
                for t in tds:
                    print(f"    {t[0]} {t[1]} = {t[2]}")
            print()


if __name__ == "__main__":
    main()

    with get_oracle_connection().cursor() as cur:
        print("=" * 70)
        print("EARN CODE DESCRIPTIONS (200,203,205,208)")
        cur.execute(
            """
            SELECT EARNDEDN_CD, EARNDEDN_DESC
            FROM FINANCE.FI_PN_MH_EARNDEDN
            WHERE EARNDEDN_CD IN ('200','203','205','208')
            ORDER BY EARNDEDN_CD
            """
        )
        for r in cur.fetchall():
            print(f"  {r[0]} = {r[1]}")

        print("=" * 70)
        print("ALL PENSIONERS ON PPN/09/2025/68 and /69")
        cur.execute(
            """
            SELECT EMP_CD, FMPEN_ID, BILL_NO, BANK_CD, LIC_BANK_CD
            FROM FINANCE.FI_PN_TH_FIRST_MONTH_PENSION
            WHERE BILL_NO IN ('PPN/09/2025/68', 'PPN/09/2025/69')
            ORDER BY BILL_NO, EMP_CD
            """
        )
        for r in cur.fetchall():
            print(f"  emp={r[0]} fmpen={r[1]} bill={r[2]} bank={r[3]} lic={r[4]}")
