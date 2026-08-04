import MySQLdb

c = MySQLdb.connect(
    host="127.0.0.1", port=3306, user="root", passwd="root123", db="smpk_pension"
)
cur = c.cursor()
emp = "40436"

for table in ("fi_pn_th_salout", "fi_pr_th_salout"):
    cur.execute(f"SHOW COLUMNS FROM {table}")
    cols = [r[0] for r in cur.fetchall()]
    print(table, [x for x in cols if any(k in x.upper() for k in ("BASIC", "EMP", "MONTH", "YEAR", "PERIOD", "PAY"))])
    # pick likely order cols
    month = next((x for x in cols if "MONTH" in x.upper() or x.upper() in ("MTH", "MM")), None)
    year = next((x for x in cols if "YEAR" in x.upper() or "YR" in x.upper()), None)
    basic = next((x for x in cols if "BASIC" in x.upper()), None)
    empcol = next((x for x in cols if x.upper() == "EMP_CD"), "EMP_CD")
    print(" use", empcol, basic, month, year)
    if basic:
        order = ""
        if year and month:
            order = f" ORDER BY {year} DESC, {month} DESC"
        cur.execute(
            f"SELECT {basic}"
            + (f", {month}" if month else "")
            + (f", {year}" if year else "")
            + f" FROM {table} WHERE {empcol}=%s{order} LIMIT 5",
            (emp,),
        )
        print(cur.fetchall())

cur.execute("SHOW COLUMNS FROM fi_pn_md_pension_proposal")
print("md", [r[0] for r in cur.fetchall()][:40])

cur.execute(
    "SELECT LAST_BASIC_AT_RET, SCALE_CD, RETIREMENT_CPI, EQUIV_PAY_AT_BASE_CPI, CONSOLID_CPI_SCL_STAMT FROM fi_pn_mh_fpen_caclaim WHERE EMP_CD=%s",
    (emp,),
)
print("claim", cur.fetchall())

# other claims with similar scale
cur.execute(
    "SELECT EMP_CD, LAST_BASIC_AT_RET, SCALE_CD FROM fi_pn_mh_fpen_caclaim WHERE SCALE_CD=%s LIMIT 5",
    ("2007/RE/003",),
)
print("same scale", cur.fetchall())
