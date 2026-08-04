import MySQLdb

tables = [
    "fi_pn_mh_application",
    "fi_pn_th_salout",
    "fi_pn_td_salout",
    "fi_pn_md_pension_proposal",
    "fi_pn_mh_pension_proposal",
    "fi_pn_td_jv",
    "fi_pn_td_first_month_pension",
    "fi_pn_mh_pmthsetup",
]
c = MySQLdb.connect(
    host="localhost", port=3306, user="root", passwd="root123", db="smpk_pension"
)
cur = c.cursor()
for t in tables:
    cur.execute(f"SHOW KEYS FROM `{t}` WHERE Key_name='PRIMARY'")
    pk = [(r[4], r[5]) for r in cur.fetchall()]  # Column_name, Seq
    cur.execute(f"SHOW COLUMNS FROM `{t}`")
    cols = [r[0] for r in cur.fetchall()[:12]]
    print(t, "PK=", pk, "cols=", cols)
cur.close()
c.close()
