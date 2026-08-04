import MySQLdb

c = MySQLdb.connect(
    host="localhost", port=3306, user="root", passwd="root123", db="smpk_pension"
)
cur = c.cursor()
cur.execute("SHOW COLUMNS FROM fi_pn_td_salout")
print([r[0] for r in cur.fetchall()])
cur.close()
c.close()
