import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from django.db import connection

emp = "44500"
with connection.cursor() as cursor:
    cursor.execute(
        """
        SELECT TABLE_NAME, COLUMN_NAME
        FROM information_schema.COLUMNS
        WHERE TABLE_SCHEMA = DATABASE()
          AND TABLE_NAME IN (
            'fi_pn_mh_fpen_caclaim',
            'fi_pn_mh_familypensioner',
            'fi_pn_lic_master',
            'fi_pn_mh_pensioner'
          )
          AND (
            COLUMN_NAME LIKE '%PENSION%'
            OR COLUMN_NAME LIKE '%BASIC%'
            OR COLUMN_NAME LIKE '%AMT%'
          )
        ORDER BY TABLE_NAME, ORDINAL_POSITION
        """
    )
    print("COLS")
    for row in cursor.fetchall():
        print(row)

    cursor.execute(
        """
        SELECT ORIGINAL_PENSION_AMT, ORIGINAL_FAMILY_PENSION_AMT,
               ORIGINAL_SINGLE_FPENSION_AMT, ORIGINAL_DOUBLE_FPENSION_AMT,
               DOUBLE_FPENSION_UPTO
        FROM fi_pn_mh_familypensioner
        WHERE EMP_CD = %s
        """,
        [emp],
    )
    print("FAMILYPENSIONER", cursor.fetchall())
    cursor.execute(
        """
        SELECT SERVICE_PENSION_AMT, LAST_BASIC_AT_RET
        FROM fi_pn_mh_fpen_caclaim
        WHERE EMP_CD = %s
        """,
        [emp],
    )
    print("CLAIM", cursor.fetchall())
with connection.cursor() as cursor:
    cursor.execute(
        """
        SELECT COLUMN_NAME
        FROM information_schema.COLUMNS
        WHERE TABLE_SCHEMA = DATABASE()
          AND TABLE_NAME = 'fi_pn_wage_2017_hdr_offi2'
          AND (
            COLUMN_NAME LIKE '%PENSION%'
            OR COLUMN_NAME LIKE '%BASIC%'
            OR COLUMN_NAME LIKE '%SINGLE%'
            OR COLUMN_NAME LIKE '%DOUBLE%'
            OR COLUMN_NAME LIKE '%ENH%'
          )
        """
    )
    print("WAGE COLS", [r[0] for r in cursor.fetchall()])
    cursor.execute(
        """
        SELECT *
        FROM fi_pn_wage_2017_hdr_offi2
        WHERE EMP_CD = %s
        """,
        [emp],
    )
    cols = [c[0] for c in cursor.description]
    row = cursor.fetchone()
    print("FULL WAGE")
    if row:
        for name, val in zip(cols, row):
            if val not in (None, "", 0):
                print(f"  {name}={val}")

from django.db import connections

with connections["finance"].cursor() as cursor:
    cursor.execute(
        """
        SELECT SALARY_ROLL_NO, PENSION_ROLL_NO, BASIC_PENSION, ENHANCE_PENSION,
               SINGLE_PENSION, BUNCH_BASIC
        FROM fi_pn_lic_master
        WHERE SALARY_ROLL_NO IN (%s, %s)
           OR PENSION_ROLL_NO IN (%s, %s)
        """,
        [emp, emp.zfill(5), "LIC-114/F", "LIC-114"],
    )
    print("LIC EXACT", cursor.fetchall())
