import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from employee.services.oracle_service import get_oracle_connection

conn = get_oracle_connection()
cur = conn.cursor()
cur.execute(
    """
    SELECT column_name FROM all_tab_columns
    WHERE owner = 'FINANCE' AND table_name = 'FI_PN_MH_EARNDEDN'
    ORDER BY column_id
    """
)
print("cols", [r[0] for r in cur.fetchall()])
cur.execute(
    """
    SELECT earndedn_cd, zonal_cd, alloc_cd
    FROM finance.fi_pn_mh_earndedn
    WHERE earndedn_cd IN ('200','201','203','205')
    """
)
for r in cur.fetchall():
    print("earn", r)
cur.close()
conn.close()
