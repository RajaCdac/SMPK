"""Cross-check emp 44377 JV line ~50227 zonal (12 vs 10) vs Oracle."""
import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from django.db import connection
from employee.services.oracle_service import get_oracle_connection


def dump(label, rows, cols=None):
    print(f"\n=== {label} ===")
    if cols:
        print("cols:", cols)
    for r in rows:
        print(r)
    print(f"count={len(rows)}")


def main():
    print("--- MySQL voucher PPN/07/2026/38 (44377) ---")
    with connection.cursor() as c:
        c.execute(
            """
            SELECT d.voucher_no, d.sl_no, d.dr_cr_flag, d.zonal_cd,
                   d.aloc_cd1, d.aloc_cd2, d.aloc_cd3, d.amount, h.ref_no
            FROM fi_pn_td_jv d
            JOIN fi_pn_th_jv h ON h.voucher_no = d.voucher_no
            WHERE h.ref_no = %s
            ORDER BY d.sl_no
            """,
            ["PPN/07/2026/38"],
        )
        dump("mysql jv lines", c.fetchall())

        c.execute(
            """
            SELECT earn_dedn_cd, earn_dedn_type, amount
            FROM fi_pn_td_first_month_pension
            WHERE fmpen_id = (
              SELECT fmpen_id FROM fi_pn_th_first_month_pension
              WHERE emp_cd = '44377' LIMIT 1
            )
            ORDER BY earn_dedn_cd
            """
        )
        dump("mysql first-month lines 44377", c.fetchall())

        c.execute(
            """
            SELECT earndedn_cd, earndedn_desc, zonal_cd, alloc_cd
            FROM fi_pn_mh_earndedn
            WHERE earndedn_cd = '645' OR alloc_cd = '596'
            """
        )
        dump("mysql earn master 645/596", c.fetchall())

    conn = get_oracle_connection()
    cur = conn.cursor()

    cur.execute(
        """
        SELECT EARNDEDN_CD, EARNDEDN_DESC, ZONAL_CD, ALLOC_CD
        FROM FINANCE.FI_PN_MH_EARNDEDN
        WHERE EARNDEDN_CD = '645'
        """
    )
    dump("oracle earn 645", cur.fetchall(), [d[0] for d in cur.description])

    cur.execute(
        """
        SELECT JRNAL_SRL_NO, ZONAL_CD, DR_CR_FLG, ALOC_CD1, ALOC_CD2, ALOC_CD3
        FROM FINANCE.FI_PN_MD_JRNLTYPE
        WHERE ALOC_CD1 = '596'
        ORDER BY JRNAL_SRL_NO, ZONAL_CD, DR_CR_FLG
        """
    )
    dump("oracle MD journal aloc 596", cur.fetchall(), [d[0] for d in cur.description])

    cur.execute(
        """
        SELECT JRNAL_SRL_NO, ZONAL_CD, DR_CR_FLG, ALOC_CD1, ALOC_CD2, ALOC_CD3
        FROM FINANCE.FI_PN_MD_JRNLTYPE
        WHERE ZONAL_CD = 10 AND ALOC_CD1 IN ('596', '186', '121', '103')
        ORDER BY ALOC_CD1
        """
    )
    dump("oracle MD zonal=10 for main GL", cur.fetchall())

    cur.execute(
        """
        SELECT d.ZONAL_CD, COUNT(*), MIN(d.AMOUNT), MAX(d.AMOUNT)
        FROM FINANCE.FI_PN_TD_JV d
        WHERE d.ALOC_CD1 = '596'
        GROUP BY d.ZONAL_CD
        ORDER BY d.ZONAL_CD
        """
    )
    dump("oracle hist ALOC 596 by zonal", cur.fetchall())

    cur.execute(
        """
        SELECT d.VOUCHER_NO, d.ZONAL_CD, d.ALOC_CD1, d.ALOC_CD2, d.ALOC_CD3,
               d.AMOUNT, h.REF_NO, h.VOUCHER_DT, h.TRAN_TYPE
        FROM FINANCE.FI_PN_TD_JV d
        JOIN FINANCE.FI_PN_TH_JV h ON h.VOUCHER_NO = d.VOUCHER_NO
        WHERE d.ALOC_CD1 = '596' AND d.ZONAL_CD = 10
        """
    )
    dump("oracle ALOC 596 with zonal 10", cur.fetchall())

    cur.execute(
        """
        SELECT d.VOUCHER_NO, d.SL_NO, d.DR_CR_FLAG, d.ZONAL_CD,
               d.ALOC_CD1, d.ALOC_CD2, d.ALOC_CD3, d.AMOUNT, h.REF_NO
        FROM FINANCE.FI_PN_TD_JV d
        JOIN FINANCE.FI_PN_TH_JV h ON h.VOUCHER_NO = d.VOUCHER_NO
        WHERE d.AMOUNT = 50227
        ORDER BY h.VOUCHER_DT DESC
        """
    )
    dump("oracle amount=50227 lines", cur.fetchall())

    cur.execute(
        """
        SELECT d.SL_NO, d.DR_CR_FLAG, d.ZONAL_CD,
               d.ALOC_CD1, d.ALOC_CD2, d.ALOC_CD3, d.AMOUNT
        FROM FINANCE.FI_PN_TD_JV d
        WHERE d.VOUCHER_NO = 'PNJV/2026/6/00092'
        ORDER BY d.SL_NO
        """
    )
    dump("oracle full PNJV/2026/6/00092 (same amt other bill)", cur.fetchall())

    cur.execute(
        """
        SELECT * FROM (
          SELECT d.VOUCHER_NO, d.ZONAL_CD, d.ALOC_CD1, d.ALOC_CD2, d.ALOC_CD3,
                 d.DR_CR_FLAG, d.AMOUNT, h.REF_NO, h.VOUCHER_DT
          FROM FINANCE.FI_PN_TD_JV d
          JOIN FINANCE.FI_PN_TH_JV h ON h.VOUCHER_NO = d.VOUCHER_NO
          WHERE d.ALOC_CD1 = '596' AND h.REF_NO LIKE 'PPN%'
          ORDER BY h.VOUCHER_DT DESC
        ) WHERE ROWNUM <= 12
        """
    )
    dump("oracle recent PPN ALOC 596", cur.fetchall())

    cur.execute(
        """
        SELECT ZONAL_CD, CPT_ZONAL_DES
        FROM FINANCE.FI_MA_M_H_ZONALMAP
        WHERE ZONAL_CD IN (10, 11, 12, 30)
        ORDER BY ZONAL_CD
        """
    )
    dump("oracle zonal CPT desc", cur.fetchall())

    cur.close()
    conn.close()


if __name__ == "__main__":
    main()
