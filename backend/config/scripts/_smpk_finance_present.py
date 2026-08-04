"""Tables already in smpk_pension from finance."""
import MySQLdb

SOURCE = dict(host="127.0.0.1", port=3307, user="root", passwd="root123", db="finance")
TARGET = dict(host="127.0.0.1", port=3306, user="root", passwd="root123", db="smpk_pension")

src = MySQLdb.connect(**SOURCE)
tgt = MySQLdb.connect(**TARGET)
sc = src.cursor()
tc = tgt.cursor()
sc.execute(
    "SELECT table_name FROM information_schema.tables "
    "WHERE table_schema='finance' AND table_name LIKE 'fi_%'"
)
finance_all = {r[0].lower() for r in sc.fetchall()}
tc.execute(
    "SELECT table_name FROM information_schema.tables "
    "WHERE table_schema='smpk_pension' AND table_name LIKE 'fi_%' ORDER BY table_name"
)
smpk = [r[0].lower() for r in tc.fetchall()]
print(f"Already in smpk_pension ({len(smpk)} fi_* tables):\n")
for t in smpk:
    print(t)
