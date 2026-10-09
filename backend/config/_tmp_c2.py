import os, django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()
from employee.services.oracle_service import get_oracle_connection

conn = get_oracle_connection()
cur = conn.cursor()
cur.execute(
    """
    SELECT p.EMP_CD, p.NAME, p.APP_CLASS, e.BIRTH_DT, p.EMP_RET_DT
    FROM FINANCE.FI_PN_MH_PENSIONER p
    JOIN FINANCE.FI_XX_MH_EMP_PER e ON e.EMP_CD = p.EMP_CD
    WHERE p.APP_CLASS = 2
      AND e.BIRTH_DT >= DATE '1930-01-01'
      AND e.BIRTH_DT < DATE '1950-01-01'
    ORDER BY e.BIRTH_DT, p.EMP_CD
    """
)
rows = cur.fetchall()
print("Class 2 DOB 1930-49:", len(rows))
for emp, name, cls, dob, ret in rows:
    dob_s = dob.strftime("%Y-%m-%d") if dob else ""
    ret_s = ret.strftime("%Y-%m-%d") if ret else ""
    print(f"  {emp} c={cls} dob={dob_s} ret={ret_s} {(name or '')[:35]}")
cur.close()
conn.close()
