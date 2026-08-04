import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from employee.services.oracle_service import get_oracle_connection

conn = get_oracle_connection()
cur = conn.cursor()
cur.execute(
    """
    SELECT table_name, column_name FROM all_tab_columns
    WHERE owner = 'FINANCE' AND UPPER(column_name) LIKE '%IFSC%'
    ORDER BY table_name
    """
)
for r in cur.fetchall():
    print(r)
cur.close()
conn.close()
