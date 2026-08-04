import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from django.db import connection

emp = "41710"
with connection.cursor() as c:
    queries = {
        "pensioner": (
            "SELECT CA_NUMBER, EMP_CD, NAME, PENSION_ROLL_NO, LIC_BANK_CD, BANK_CD "
            "FROM fi_pn_mh_pensioner WHERE EMP_CD=%s",
            [emp],
        ),
        "proposal": (
            "SELECT CA_NUMBER, EMP_CD, NAME, PENSION_ROLL_NO, LIC_BANK_CD "
            "FROM fi_pn_mh_pension_proposal WHERE EMP_CD=%s",
            [emp],
        ),
        "fmpen": (
            "SELECT FMPEN_ID, EMP_CD, CA_NO, PENSION_MONTH, PENSION_YR "
            "FROM fi_pn_th_first_month_pension WHERE EMP_CD=%s",
            [emp],
        ),
        "per": (
            "SELECT EMP_CD, FIRST_NAME, MIDDLE_NAME, LAST_NAME "
            "FROM fi_xx_mh_emp_per WHERE EMP_CD=%s",
            [emp],
        ),
        "adm": (
            "SELECT EMP_CD, RET_DT, SEPARATION_DT, DESIG_CD "
            "FROM fi_xx_mh_emp_adm WHERE EMP_CD=%s",
            [emp],
        ),
    }
    for label, (sql, params) in queries.items():
        c.execute(sql, params)
        cols = [d[0] for d in c.description]
        rows = c.fetchall()
        print(f"--- {label} ({len(rows)})")
        if rows:
            print(dict(zip(cols, rows[0])))

    c.execute(
        """
        SELECT d.DESIG_DESC
        FROM fi_xx_mh_emp_adm a
        LEFT JOIN fi_xx_mh_desig d ON d.DESIG_CD = a.DESIG_CD
        WHERE a.EMP_CD = %s
        LIMIT 1
        """,
        [emp],
    )
    print("desig", c.fetchone())

    c.execute("SHOW TABLES LIKE %s", ["%advice%"])
    print("advice tables", c.fetchall())
