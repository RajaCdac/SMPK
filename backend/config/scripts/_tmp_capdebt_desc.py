import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from employee.services.oracle_service import get_oracle_connection

c = get_oracle_connection().cursor()
c.execute(
    """
    SELECT ALLOC_CD, ALLOC_DESC FROM FINANCE.FI_MA_MD_CAPDEBT
    WHERE ALLOC_CD IN ('103','121','436')
    """
)
print("cap", c.fetchall())
c.execute(
    """
    SELECT CAPDEBT_ALLOC_CD, ALLOC_CD, ALLOC_DESC
    FROM FINANCE.FI_MA_MD_CAPDEBT_SL
    WHERE CAPDEBT_ALLOC_CD = '121' AND ALLOC_CD IN ('575','576')
    """
)
print("sl", c.fetchall())
