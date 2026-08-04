import MySQLdb

c = MySQLdb.connect(
    host="127.0.0.1", port=3306, user="root", passwd="root123", db="smpk_pension"
)
cur = c.cursor()
emp = "40436"

queries = [
    ("pensioner emol", "SELECT PENSION_EMOLUMENTS, GRATUITY_EMOLUMENTS, ORIGINAL_PENSION_AMT FROM fi_pn_mh_pensioner WHERE EMP_CD=%s"),
    ("salout basic", "SELECT BASIC_RATE, SAL_MONTH, SAL_YEAR FROM fi_pn_th_salout WHERE EMP_CD=%s ORDER BY SAL_YEAR DESC, SAL_MONTH DESC LIMIT 5"),
    ("pr salout", "SELECT BASIC_RATE, SAL_MONTH, SAL_YEAR FROM fi_pr_th_salout WHERE EMP_CD=%s ORDER BY SAL_YEAR DESC, SAL_MONTH DESC LIMIT 5"),
    ("pensioncase", "SELECT last_basic, emp_code FROM first_pension_pensioncase WHERE emp_code=%s LIMIT 3"),
    ("cached ret", "SELECT last_basic, emp_cd FROM first_pension_cached_retirement_emp WHERE emp_cd=%s LIMIT 3"),
    ("md proposal", "SELECT * FROM fi_pn_md_pension_proposal WHERE EMP_CD=%s LIMIT 1"),
    ("application", "SHOW COLUMNS FROM fi_pn_mh_application"),
]

for title, q in queries:
    print("===", title, "===")
    try:
        if "%s" in q:
            cur.execute(q, (emp,))
        else:
            cur.execute(q)
        rows = cur.fetchall()
        print(rows[:10] if rows else rows)
        if title == "md proposal" and rows:
            cur.execute("SHOW COLUMNS FROM fi_pn_md_pension_proposal")
            cols = [r[0] for r in cur.fetchall()]
            d = dict(zip(cols, rows[0]))
            for k, v in d.items():
                if v is not None and any(
                    x in k.upper() for x in ("BASIC", "PAY", "LAST", "SCALE", "AMT")
                ):
                    print(k, v)
        if title == "application":
            print([r[0] for r in rows if "BASIC" in r[0].upper() or "PAY" in r[0].upper()])
    except Exception as e:
        print("ERR", e)

# check md proposal columns
try:
    cur.execute("SHOW COLUMNS FROM fi_pn_md_pension_proposal")
    cols = [r[0] for r in cur.fetchall()]
    print("md prop cols", [x for x in cols if any(k in x.upper() for k in ("BASIC", "PAY", "LAST", "SCALE"))])
except Exception as e:
    print(e)
