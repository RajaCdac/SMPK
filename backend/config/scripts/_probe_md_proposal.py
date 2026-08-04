import MySQLdb

c = MySQLdb.connect(
    host="localhost", port=3307, user="root", passwd="root123", db="finance"
)
cur = c.cursor()
cur.execute("SHOW COLUMNS FROM FI_PN_MD_PENSION_PROPOSAL")
print("MD cols:", [r[0] for r in cur.fetchall()])
cur.execute(
    "SELECT * FROM FI_PN_MD_PENSION_PROPOSAL WHERE CA_NUMBER=%s LIMIT 30",
    ("38525",),
)
cols = [d[0] for d in cur.description]
rows = cur.fetchall()
print("rows", len(rows))
for r in rows:
    print(dict(zip(cols, r)))

c2 = MySQLdb.connect(
    host="localhost", port=3306, user="root", passwd="root123", db="smpk_pension"
)
cur2 = c2.cursor()
cur2.execute("SHOW TABLES LIKE %s", ("%pension_proposal%",))
print("smpk tables", cur2.fetchall())
cur2.execute("SHOW TABLES LIKE %s", ("%md_pension%",))
print("md tables", cur2.fetchall())
cur.close()
c.close()
cur2.close()
c2.close()
