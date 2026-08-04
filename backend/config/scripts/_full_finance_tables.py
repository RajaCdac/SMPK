"""Full finance fi_% tables vs smpk_pension."""
import MySQLdb

SOURCE = dict(host="127.0.0.1", port=3307, user="root", passwd="root123", db="finance")
TARGET = dict(host="127.0.0.1", port=3306, user="root", passwd="root123", db="smpk_pension")

src = MySQLdb.connect(**SOURCE)
tgt = MySQLdb.connect(**TARGET)
sc = src.cursor()
tc = tgt.cursor()
sc.execute(
    "SELECT table_name FROM information_schema.tables "
    "WHERE table_schema='finance' AND table_name LIKE 'fi_%' ORDER BY table_name"
)
finance_all = [r[0].lower() for r in sc.fetchall()]
tc.execute(
    "SELECT table_name FROM information_schema.tables "
    "WHERE table_schema='smpk_pension' AND table_name LIKE 'fi_%'"
)
smpk_all = {r[0].lower() for r in tc.fetchall()}

missing = [t for t in finance_all if t not in smpk_all]
present = [t for t in finance_all if t in smpk_all]

print(f"Finance fi_* tables: {len(finance_all)}")
print(f"Already in smpk_pension: {len(present)}")
print(f"Missing in smpk_pension: {len(missing)}")
print("\n--- MISSING (import these) ---")
for t in missing:
    print(t)
