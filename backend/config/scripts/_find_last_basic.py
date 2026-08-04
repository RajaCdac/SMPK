import MySQLdb

c = MySQLdb.connect(
    host="127.0.0.1", port=3306, user="root", passwd="root123", db="smpk_pension"
)
cur = c.cursor()
emp = "40436"

cur.execute("SHOW COLUMNS FROM fi_pn_mh_pension_proposal")
prop_cols = [r[0] for r in cur.fetchall()]
print(
    "proposal",
    [x for x in prop_cols if any(k in x.upper() for k in ("BASIC", "PAY", "LAST", "SCALE", "CPI", "EMOL"))],
)

cur.execute("SELECT * FROM fi_pn_mh_pension_proposal WHERE EMP_CD=%s LIMIT 1", (emp,))
row = cur.fetchone()
if row:
    d = dict(zip(prop_cols, row))
    for k, v in d.items():
        if any(x in k.upper() for x in ("BASIC", "PAY", "LAST", "SCALE", "CPI", "OPT", "INCENT", "CA")):
            print("PROP", k, v)

cur.execute("SHOW COLUMNS FROM fi_pn_mh_oldbill_param")
ob_cols = [r[0] for r in cur.fetchall()]
print("oldbill", [x for x in ob_cols if any(k in x.upper() for k in ("BASIC", "PAY", "LAST", "SCALE"))])
cur.execute("SELECT * FROM fi_pn_mh_oldbill_param WHERE EMP_CD=%s LIMIT 1", (emp,))
ob = cur.fetchone()
if ob:
    d = dict(zip(ob_cols, ob))
    for k, v in d.items():
        if any(x in k.upper() for x in ("BASIC", "PAY", "LAST", "SCALE", "CPI")):
            print("OB", k, v)

# claim already saved last_basic
cur.execute(
    "SELECT LAST_BASIC_AT_RET, SCALE_CD, EQUIV_PAY_AT_BASE_CPI, CONSOLID_CPI_SCL_STAMT FROM fi_pn_mh_fpen_caclaim WHERE EMP_CD=%s",
    (emp,),
)
print("saved claim basics", cur.fetchall())

# search tables with last_basic like columns
cur.execute(
    """
    SELECT TABLE_NAME, COLUMN_NAME FROM information_schema.COLUMNS
    WHERE TABLE_SCHEMA='smpk_pension'
      AND (COLUMN_NAME LIKE '%BASIC%' OR COLUMN_NAME LIKE '%LAST_PAY%' OR COLUMN_NAME LIKE '%LAST_BASIC%')
    ORDER BY TABLE_NAME, COLUMN_NAME
    """
)
for r in cur.fetchall():
    print("COL", r[0], r[1])
