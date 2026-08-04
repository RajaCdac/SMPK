# Full MySQL import on first Docker start

Place **one** full dump of `smpk_pension` here before the **first** `docker compose up`:

- `01-smpk_pension.sql` — recommended name (runs first)
- or `01-smpk_pension.sql.gz`

MySQL runs these files **only when the data volume is empty** (first install).

## Steps

1. Export on your old PC (see `scripts/export-mysql.ps1` or SQLyog → Export database `smpk_pension`).
2. Copy the `.sql` file into this folder as `01-smpk_pension.sql`.
3. Fresh volume + start:

```powershell
cd D:\SMPK\SMPK
docker compose down -v
docker compose up -d --build
```

4. Open http://localhost and log in with your **existing** users from the dump.

To re-import a different dump later, use `scripts/restore-mysql-docker.ps1` (does not require wiping the volume).

**Do not commit** `.sql` files (they may contain passwords and real employee data).
