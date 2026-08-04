import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from employee.services.oracle_service import get_oracle_connection

conn = get_oracle_connection()
cur = conn.cursor()
for t in ["FI_XX_MH_EMP_DATA", "FI_XX_MH_DEPT", "FI_PR_TH_SALOUT", "FI_PR_TD_SALOUT"]:
    cur.execute(
        """
        SELECT column_name, data_type, data_length
        FROM all_tab_columns
        WHERE owner = 'FINANCE' AND table_name = :t
        ORDER BY column_id
        """,
        {"t": t},
    )
    print(f"\n=== {t} ===")
    for row in cur.fetchall():
        print(row)
cur.close()
conn.close()
