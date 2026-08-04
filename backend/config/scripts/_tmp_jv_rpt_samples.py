import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from employee.services.oracle_service import get_oracle_connection

conn = get_oracle_connection()
cur = conn.cursor()

# PFN sample
cur.execute(
    """
    SELECT * FROM (
      SELECT h.ref_no, h.tran_type, h.narration, h.voucher_no, h.voucher_dt,
             h.yr, h.mth
      FROM finance.fi_pn_th_jv h
      WHERE h.ref_no LIKE 'PFN/%'
      ORDER BY h.voucher_dt DESC
    ) WHERE ROWNUM <= 2
    """
)
print("PFN headers:", cur.fetchall())

# bank LICI sample
cur.execute(
    """
    SELECT * FROM (
      SELECT h.ref_no, h.tran_type, h.narration, h.voucher_no
      FROM finance.fi_pn_th_jv h
      WHERE UPPER(h.ref_no) LIKE '%LICI%'
      ORDER BY h.voucher_dt DESC
    ) WHERE ROWNUM <= 2
    """
)
print("LICI:", cur.fetchall())

# NLIC sample
cur.execute(
    """
    SELECT * FROM (
      SELECT h.ref_no, h.tran_type, h.narration, h.voucher_no
      FROM finance.fi_pn_th_jv h
      WHERE UPPER(h.ref_no) LIKE '%NLIC%'
      ORDER BY h.voucher_dt DESC
    ) WHERE ROWNUM <= 2
    """
)
print("NLIC:", cur.fetchall())

# zonal desc format
cur.execute(
    """
    SELECT ZONAL_CD, ZONAL_DESC FROM FINANCE.FI_MA_MH_ZONALTYPE_VW
    WHERE ZONAL_CD IN (10, 30)
    """
)
print("zonal:", cur.fetchall())

cur.close()
conn.close()
