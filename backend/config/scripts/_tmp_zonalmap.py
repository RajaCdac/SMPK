import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from employee.services.oracle_service import get_oracle_connection

c = get_oracle_connection().cursor()
c.execute(
    """
    SELECT ZONAL_CD, CPT_ZONAL_DES
    FROM FINANCE.FI_MA_M_H_ZONALMAP
    WHERE ZONAL_CD IN (10, 11, 30)
    """
)
print("zonalmap", c.fetchall())

c.execute(
    """
    SELECT abstract_no, abstract_dt, bill_cd
    FROM FINANCE.FI_PN_TH_BILLPASS
    WHERE bill_cd = 'PFN/10/2024/212'
    """
)
print("abstract pfn", c.fetchall())

c.close()
