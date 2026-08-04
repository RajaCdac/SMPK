import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from employee.services.oracle_service import get_oracle_connection

conn = get_oracle_connection()
cur = conn.cursor()

# allocation description helpers from manual JV form
voucher = "PNJV/2025/8/00156"
cur.execute(
    """
    SELECT d.sl_no, d.zonal_cd, d.aloc_cd1, d.aloc_cd2, d.aloc_cd3,
           d.dr_cr_flag, d.amount, d.remarks
    FROM finance.fi_pn_th_jv h
    JOIN finance.fi_pn_td_jv d
      ON h.voucher_no = d.voucher_no AND h.voucher_dt = d.voucher_dt
    WHERE h.voucher_no = :vn
    ORDER BY d.sl_no
    """,
    {"vn": voucher},
)
lines = cur.fetchall()
print("lines", len(lines))
for r in lines:
    print(r)

# zonal desc
if lines:
    z = lines[0][1]
    try:
        cur.execute(
            """
            SELECT ZONAL_DESC FROM FINANCE.FI_MA_MH_ZONALTYPE_VW
            WHERE ZONAL_CD = :z
            """,
            {"z": z},
        )
        print("zonal desc", cur.fetchone())
    except Exception as exc:
        print("zonal err", exc)

# capdebt alloc desc for aloc1=121
for a1, a2, a3 in [(r[2], r[3], r[4]) for r in lines]:
    try:
        cur.execute(
            """
            SELECT ALLOC_DESC FROM FINANCE.FI_MA_MD_CAPDEBT_SL
            WHERE ALLOC_CD = :a2 AND CAPDEBT_ALLOC_CD = :a1
            """,
            {"a2": a2, "a1": a1},
        )
        row = cur.fetchone()
        print(f"capdebt {a1}/{a2}/{a3}", row)
    except Exception as exc:
        print("capdebt err", exc)
        break

cur.close()
conn.close()
