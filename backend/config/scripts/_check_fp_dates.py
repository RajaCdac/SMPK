import MySQLdb

conn = MySQLdb.connect(
    host="127.0.0.1", port=3306, user="root", passwd="root123", db="smpk_pension"
)
cur = conn.cursor()
cur.execute(
    "SHOW COLUMNS FROM fi_pn_mh_fpen_caclaim WHERE Field LIKE '%DATE%' OR Field LIKE '%MODIF%' OR Field LIKE '%CREAT%'"
)
for r in cur.fetchall():
    print(r)
