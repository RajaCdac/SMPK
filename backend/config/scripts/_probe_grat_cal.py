import os, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from employee.services.oracle_service import get_oracle_connection

EMP = "43917"
conn = get_oracle_connection()
cur = conn.cursor()

cur.execute(
    """
    SELECT column_name FROM all_tab_columns
    WHERE owner='FINANCE' AND table_name='FI_PN_MH_PENSIONER'
      AND (column_name LIKE '%BOY%' OR column_name LIKE '%SERVICE%' OR column_name LIKE '%TQS%' OR column_name LIKE '%TCC%')
    ORDER BY column_id
    """
)
cols = [r[0] for r in cur.fetchall()]
print("cols", cols)

cur.execute(f"SELECT {', '.join(cols[:20])} FROM FINANCE.FI_PN_MH_PENSIONER WHERE EMP_CD=:e", {"e": EMP})
row = cur.fetchone()
print(dict(zip(cols[:20], row)))

# GRAT_CAL source snippet
cur.execute(
    """
    SELECT line, text FROM all_source
    WHERE owner='FINANCE' AND name='GRAT_CAL' AND type='FUNCTION'
    ORDER BY line
    """
)
lines = cur.fetchall()
print("\nGRAT_CAL", len(lines), "lines")
for line, text in lines:
    print(f"{line}: {text.rstrip()}")

cur.close()
conn.close()
