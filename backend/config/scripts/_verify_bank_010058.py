import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from employee.services.oracle_service import get_oracle_connection

conn = get_oracle_connection()
cur = conn.cursor()
cur.execute(
    """
    SELECT bank_cd, bank_desc, rbi_cd, addr1, addr2, ps, city, bank_id
    FROM finance.fi_pm_mh_bank WHERE bank_cd = '010058'
    """
)
print("bank", dict(zip([d[0] for d in cur.description], cur.fetchone())))
cur.execute(
    "SELECT bank_cd, bank_ac_no FROM finance.fi_xx_mh_emp_fin WHERE emp_cd = '46585'"
)
print("emp_fin", dict(zip([d[0] for d in cur.description], cur.fetchone())))
cur.close()
conn.close()
