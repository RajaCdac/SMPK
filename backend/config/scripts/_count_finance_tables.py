"""Count FINANCE objects in Oracle."""
import os
import sys

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
django.setup()

from employee.services.oracle_service import get_oracle_connection

conn = get_oracle_connection()
cur = conn.cursor()

queries = [
    ("FINANCE tables", "SELECT COUNT(*) FROM ALL_TABLES WHERE OWNER = 'FINANCE'"),
    ("FINANCE views", "SELECT COUNT(*) FROM ALL_VIEWS WHERE OWNER = 'FINANCE'"),
    (
        "FI_PN tables",
        "SELECT COUNT(*) FROM ALL_TABLES WHERE OWNER = 'FINANCE' AND TABLE_NAME LIKE 'FI_PN%'",
    ),
    (
        "FI_XX tables",
        "SELECT COUNT(*) FROM ALL_TABLES WHERE OWNER = 'FINANCE' AND TABLE_NAME LIKE 'FI_XX%'",
    ),
    (
        "FI_LA tables",
        "SELECT COUNT(*) FROM ALL_TABLES WHERE OWNER = 'FINANCE' AND TABLE_NAME LIKE 'FI_LA%'",
    ),
    (
        "FI_PR tables",
        "SELECT COUNT(*) FROM ALL_TABLES WHERE OWNER = 'FINANCE' AND TABLE_NAME LIKE 'FI_PR%'",
    ),
    (
        "first-pension related (PN/XX/LA/PR)",
        """
        SELECT COUNT(*) FROM ALL_TABLES
        WHERE OWNER = 'FINANCE'
          AND (
            TABLE_NAME LIKE 'FI_PN%'
            OR TABLE_NAME LIKE 'FI_XX%'
            OR TABLE_NAME LIKE 'FI_LA%'
            OR TABLE_NAME LIKE 'FI_PR%'
          )
        """,
    ),
]

for label, sql in queries:
    cur.execute(sql)
    print(f"{label}: {cur.fetchone()[0]}")

cur.close()
conn.close()
