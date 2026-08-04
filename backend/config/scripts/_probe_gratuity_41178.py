import os
import sys
from pathlib import Path
from collections import defaultdict

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from employee.services.oracle_service import get_oracle_connection
from dateutil.relativedelta import relativedelta
from datetime import date

emp = "41178"
conn = get_oracle_connection()
cur = conn.cursor()

cur.execute(
    """
    SELECT SAL_MTH, SAL_YR, EARNDEDN_CD,
           NVL(ACT_EARNDEDN_AMT,0)+NVL(ADJ_EARNDEDN_AMT,0)
    FROM FINANCE.FI_PR_TD_SALOUT
    WHERE EMP_CD = :e
      AND TO_DATE('01/'||LPAD(SAL_MTH,2,'0')||'/'||LPAD(SAL_YR,4,'0'),'DD/MM/RRRR')
          >= TO_DATE('01/10/2007','DD/MM/RRRR')
    ORDER BY SAL_YR, SAL_MTH, EARNDEDN_CD
    """,
    {"e": emp},
)

months = defaultdict(lambda: {"001": 0.0, "007": 0.0, "111": 0.0})
for m, y, cd, amt in cur.fetchall():
    if cd in months[(y, m)]:
        months[(y, m)][cd] = float(amt)

print("PR TD emoluments (10-month window):")
emol_list = []
for key in sorted(months.keys()):
    b = months[key]["001"]
    da = months[key]["007"]
    cca = months[key]["111"]
    total = b + da + cca
    emol_list.append(total)
    print(f"  {key[1]:02d}/{key[0]}: basic={b} da={da} cca={cca} total={total}")

if emol_list:
    print(f"  avg total: {sum(emol_list)/len(emol_list):.2f}")
    print(f"  max total: {max(emol_list):.2f}")
    print(f"  last total: {emol_list[-1]:.2f}")

# Oracle stored values
print("\nOracle pensioner:")
print("  GRATUITY_EMOLUMENTS: 15637.12")
print("  PENSION_EMOLUMENTS: 8378.0")
print("  TCCS: 34y 1m 14d")
print("  GRATUITY: 306729")

emo = 15637.12
years = 34
g = emo * 15 * years / 26
print(f"\nOracle formula check: {emo} * 15 * {years} / 26 = {g:.2f}")

join = date(1974, 6, 17)
for label, end in [("separation 2008-08-01", date(2008, 8, 1)), ("SMPK ret 2010-06-01", date(2010, 6, 1))]:
    d = relativedelta(end, join)
    qy = d.years + (1 if d.months >= 6 else 0)
    print(f"  {label}: TCCS {d.years}y {d.months}m → gratuity years={qy}")

cur.close()
conn.close()
