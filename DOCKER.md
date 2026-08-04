# SMPK — Docker deployment

## Same Windows machine as Oracle (your case)

Oracle runs on this PC (or is reached from this PC). Use **Docker Desktop on Windows**.

| How you run SMPK | `ORACLE_DB_HOST` in `.env` |
|------------------|------------------------------|
| **Docker Compose** (recommended) | `host.docker.internal` |
| **Without Docker** (venv + npm, like today) | `127.0.0.1` or `localhost` or your PC's LAN IP |

Inside a container, `127.0.0.1` is the **container**, not Windows — so do **not** use `localhost` in `.env` for Docker.

Check Oracle port from Windows:

```powershell
Test-NetConnection 127.0.0.1 -Port 1521
# or
Test-NetConnection host.docker.internal -Port 1521
```

If Oracle listens only on `192.168.4.62`, use that IP in `.env` instead of `host.docker.internal`.

### Quick start (same Windows PC)

```powershell
cd D:\SMPK\SMPK
copy .env.example .env
notepad .env
# ORACLE_DB_HOST=host.docker.internal
# ORACLE_DB_* = your real credentials
# MYSQL_PASSWORD = choose a password

docker compose up -d --build
# Full DB: see "Full database in Docker" below
```

Browser: **http://localhost**

MySQL in Docker is **separate** from any existing MySQL on this PC. Port `3306` is published — change `MYSQL_PUBLISH_PORT=3307` in `.env` if 3306 is already in use.

### Optional: skip Docker on this PC

If Oracle Instant Client is already installed (`C:\oracle\...`), you can keep your current workflow:

```powershell
# Backend
cd D:\SMPK\SMPK\backend\config
..\venv\Scripts\activate
# set env or use defaults in settings — MYSQL_HOST=127.0.0.1 if local MySQL
python manage.py runserver 0.0.0.0:8000

# Frontend (other terminal)
cd D:\SMPK\SMPK\frontend\frontend
npm run dev
```

Set in `.env` or system env: `ORACLE_DB_HOST=127.0.0.1`, `MYSQL_HOST=127.0.0.1` if using existing MySQL.

---

## Architecture

| Component | Where it runs |
|-----------|----------------|
| **Frontend** (nginx + React build) | Docker `frontend` → port **80** |
| **Backend** (Django + cx_Oracle) | Docker `backend` → port **8000** |
| **MySQL** (`smpk_pension`) | Docker `mysql` → port **3306** |
| **Oracle Finance** | **Same network** — existing server (e.g. `192.168.4.62:1521`) |

Oracle is **not** inside Docker. The backend container connects to your finance DB over the LAN.

## Prerequisites (new machine)

1. [Docker Desktop](https://www.docker.com/products/docker-desktop/) (Windows) or Docker Engine (Linux)
2. Network access from that PC to:
   - Oracle: `ORACLE_DB_HOST:1521` (firewall open)
3. Copy project folder or `git clone`

## Quick start

```powershell
cd D:\SMPK\SMPK
copy .env.example .env
# Edit .env — set MYSQL_PASSWORD, ORACLE_DB_* , DJANGO_SECRET_KEY
docker compose up -d --build
```

Open: **http://localhost**

### Full database in Docker (copy from old PC)

1. **Export** `smpk_pension` on the machine that has your data today:

```powershell
cd D:\SMPK\SMPK
.\scripts\export-mysql.ps1
# Or SQLyog: right-click database smpk_pension -> Export -> SQL file
```

2. **Import** — pick one:

**A — First Docker install (empty volume)** — copy dump, then wipe volume once:

```powershell
copy D:\backups\smpk_pension_full_20260101.sql D:\SMPK\SMPK\docker\mysql\init\01-smpk_pension.sql
docker compose down -v
docker compose up -d --build
```

MySQL loads `docker/mysql/init/*.sql` only on the **first** start (empty volume). Wait until `docker compose logs mysql` shows ready.

**B — MySQL already running in Docker** — import without deleting volume:

```powershell
.\scripts\restore-mysql-docker.ps1 -SqlFile D:\backups\smpk_pension_full.sql
```

**C — Replace everything** (re-copy dump + new volume):

```powershell
.\scripts\restore-mysql-docker.ps1 -SqlFile D:\backups\smpk_pension_full.sql -DropVolumeFirst
```

3. Log in with your **existing** users from the dump (no `createsuperuser` needed).

4. Backend still runs `migrate` on start — applies any new migrations on top of your restored data.

## `.env` — important values

```env
ORACLE_DB_HOST=192.168.4.62
ORACLE_DB_PORT=1521
ORACLE_DB_SERVICE_NAME=kopttestfin
ORACLE_DB_USER=system
ORACLE_DB_PASSWORD=your_password

MYSQL_HOST=mysql
MYSQL_PASSWORD=choose_a_strong_password
```

`MYSQL_HOST` must stay **`mysql`** (Docker service name) when using compose.

## Verify Oracle from the new PC

Before starting SMPK:

```powershell
Test-NetConnection 192.168.4.62 -Port 1521
```

If this fails, Docker cannot reach Oracle either — fix network/firewall first.

## MySQL container unhealthy

1. See the real error:

```powershell
docker compose logs mysql --tail 80
```

2. **First start with full `.sql`** — import can take **10–20+ minutes**. Wait; do not stop until logs show ready. Healthcheck allows up to ~15 minutes (`start_period`).

3. **Bad or huge SQL / wrong password** — reset and retry:

```powershell
docker compose down -v
# fix docker\mysql\init\01-smpk_pension.sql (UTF-8, from mysqldump/SQLyog)
docker compose up -d
docker compose logs -f mysql
```

4. **`.env` password** — use only letters and numbers in `MYSQL_PASSWORD` first (no `$` `!` `"`), same value after `down -v`.

5. **Port 3306 busy** — in `.env` set `MYSQL_PUBLISH_PORT=3307`.

## Useful commands

```powershell
docker compose logs -f backend
docker compose exec backend python manage.py migrate
docker compose exec backend python manage.py assign_user_role
docker compose down
docker compose down -v   # also deletes MySQL volume
```

## MySQL data on the new machine

| Goal | What to do |
|------|------------|
| **Full DB** (users, roles, cases, cache) | See **Full database in Docker** above |
| **Empty DB + demo login only** | `docker compose exec backend python manage.py seed_smpk_bootstrap` |

Dashboard retiree list still uses **Oracle** when online; restored MySQL holds saved forms, workflow dots, and cache.

## Offline / Oracle down

With `ORACLE_SYNC_REQUIRED=false` (default), forms save to MySQL. Dashboard uses cached Oracle data when available.

## Development without Docker

Keep using venv + `npm run dev`. Set `ORACLE_CLIENT_LIB` on Windows to your Instant Client path, or leave unset if the default path exists (see `oracle_service.py`).
