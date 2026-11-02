import os
import subprocess
import time

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

import MySQLdb
from django.db import connection, transaction

from M2_oldage_arrear.models import M2OldageArrearConsolidation as OA
from methodology2.models import M2ConsolCase
from methodology2.services.consol_store_service import sync_consol_store_from_snapshot
from methodology2.services.consolidation_service import snapshot_to_dict

TABLE = "m2_oldage_arrear_consolidation"
USERS = ("User1", "User2", "User3")
OUT = r"D:\SMPK\SMPK Docker\mysql\init\01-finance.sql"
TMP = OUT + ".new"

env = {}
for line in open(r"D:\SMPK\SMPK Docker\.env.docker", encoding="utf-8", errors="ignore"):
    line = line.strip()
    if "=" in line and not line.startswith("#"):
        k, v = line.split("=", 1)
        env[k.strip()] = v.strip().strip('"').strip("'")
remote = MySQLdb.connect(host="192.168.4.152", port=3308, user=env.get("SMPK_DB_USER") or "root",
                         passwd=env.get("SMPK_DB_PASSWORD") or env.get("MYSQL_PASSWORD"), db="finance",
                         charset="utf8mb4", connect_timeout=8)
rc = remote.cursor()
rc.execute(f"SHOW COLUMNS FROM {TABLE}")
cols = [r[0] for r in rc.fetchall() if r[0] != "id"]
rc.execute(f"SELECT {', '.join(cols)} FROM {TABLE} WHERE consolidated_by IN %s", [USERS])
docker_rows = {str(r[cols.index("emp_cd")]).strip(): r for r in rc.fetchall()}
rc.execute("SELECT MAX(updated_at) FROM m2_oldage_arrear_consolidation")
latest_docker = rc.fetchone()[0]
remote.close()

i_upd = cols.index("updated_at")
with connection.cursor() as lc:
    lc.execute(f"SELECT emp_cd, updated_at FROM {TABLE}")
    local_saved = {str(e).strip(): u for e, u in lc.fetchall()}
    todo = [e for e in docker_rows if e not in local_saved
            or (docker_rows[e][i_upd] and local_saved[e] and docker_rows[e][i_upd] > local_saved[e])]
    if todo:
        sql = (f"INSERT INTO {TABLE} ({', '.join(cols)}) VALUES ({', '.join(['%s'] * len(cols))}) "
               f"ON DUPLICATE KEY UPDATE {', '.join(f'{c} = VALUES({c})' for c in cols if c != 'emp_cd')}")
        with transaction.atomic():
            for emp in todo:
                lc.execute(sql, list(docker_rows[emp]))
        for obj in OA.objects.filter(emp_cd__in=todo):
            snap = snapshot_to_dict(obj)
            snap["oldage_benefit"] = obj.oldage_benefit or {}
            snap["date_of_birth"] = obj.date_of_birth.isoformat() if obj.date_of_birth else None
            sync_consol_store_from_snapshot(snap, source_app=M2ConsolCase.SOURCE_OA,
                                            user=obj.consolidated_by or "", snapshot_pk=obj.pk)
print(f"last-minute Docker saves imported: {len(todo)} {todo} | latest Docker save (UTC): {latest_docker}")

s = connection.settings_dict
cmd = [
    r"C:\Program Files\MySQL\MySQL Server 8.0\bin\mysqldump.exe",
    "-h", str(s.get("HOST") or "127.0.0.1"), "-P", str(s.get("PORT") or "3306"),
    "-u", str(s.get("USER") or "root"),
    "--single-transaction", "--routines", "--triggers", "--set-gtid-purged=OFF",
    "--no-tablespaces", "--default-character-set=utf8mb4",
    "--databases", str(s.get("NAME")),
]
start = time.time()
with open(TMP, "wb") as fh:
    proc = subprocess.run(cmd, stdout=fh, stderr=subprocess.PIPE,
                          env=dict(os.environ, MYSQL_PWD=str(s.get("PASSWORD") or "")))
err = proc.stderr.decode(errors="ignore").strip()
if proc.returncode != 0:
    os.remove(TMP)
    raise SystemExit(f"mysqldump failed ({proc.returncode}): {err[:400]}")
with open(TMP, "rb") as fh:
    fh.seek(max(0, os.path.getsize(TMP) - 200))
    tail = fh.read().decode(errors="ignore")
if "Dump completed" not in tail:
    raise SystemExit("dump looks incomplete; kept as " + TMP)
os.replace(TMP, OUT)
print(f"backup written: {OUT} | {os.path.getsize(OUT) / 1024 / 1024:,.0f} MB | {time.time() - start:.0f}s | warnings: {err[:200] or 'none'}")
