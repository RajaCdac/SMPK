"""
Background multi-table transfer job (one job at a time).

Progress is kept in-process and mirrored to scripts/dump_logs/admin_transfer_job.json
so restarts start clean (job stops) but last status can be inspected on disk.
"""

from __future__ import annotations

import threading
from copy import deepcopy
from datetime import datetime
from pathlib import Path

from .engine import (
    MYSQL_DEFAULTS,
    ORACLE_SCHEMA,
    apply_pending_foreign_keys,
    dump_table,
    public_mysql_config,
    resolve_mysql_config,
)

_LOCK = threading.Lock()
_LOG_DIR = Path(__file__).resolve().parent.parent / "scripts" / "dump_logs"
_STATUS_FILE = _LOG_DIR / "admin_transfer_job.json"
_MAX_LOG_LINES = 400

_STATE = {
    "status": "idle",  # idle | running | done | error
    "job_id": None,
    "oracle_schema": ORACLE_SCHEMA,
    "mysql": public_mysql_config(MYSQL_DEFAULTS),
    "options": {},
    "queue": [],
    "current_table": None,
    "current_index": 0,
    "total": 0,
    "completed": [],
    "failed": {},
    "results": {},
    "log": [],
    "started_at": None,
    "finished_at": None,
    "message": "",
}

# In-memory passwords for active job only (never written to status JSON).
_ACTIVE_MYSQL_FULL: dict | None = None


def _now():
    return datetime.now().isoformat(timespec="seconds")


def _public_status() -> dict:
    data = deepcopy(_STATE)
    # Ensure password never appears in responses / disk logs.
    if isinstance(data.get("mysql"), dict):
        data["mysql"].pop("password", None)
    if isinstance(data.get("options"), dict):
        mc = data["options"].get("mysql_config")
        if isinstance(mc, dict):
            data["options"]["mysql_config"] = public_mysql_config(mc)
    return data


def _persist():
    try:
        import json

        _LOG_DIR.mkdir(parents=True, exist_ok=True)
        safe = _public_status()
        _STATUS_FILE.write_text(
            json.dumps(safe, indent=2, default=str),
            encoding="utf-8",
        )
    except Exception:
        pass


def get_status() -> dict:
    with _LOCK:
        return _public_status()


def _append_log(line: str):
    stamp = datetime.now().strftime("%H:%M:%S")
    entry = f"[{stamp}] {line}"
    _STATE["log"].append(entry)
    if len(_STATE["log"]) > _MAX_LOG_LINES:
        _STATE["log"] = _STATE["log"][-_MAX_LOG_LINES:]
    _persist()


def start_transfer_job(
    tables: list[str],
    *,
    drop: bool = True,
    truncate: bool = False,
    batch_size: int = 2000,
    skip_foreign_keys: bool = True,
    constraints_only: bool = False,
    stop_on_error: bool = False,
    mysql_config=None,
) -> dict:
    global _ACTIVE_MYSQL_FULL

    from . import smpk_sync_job_runner

    if smpk_sync_job_runner.get_status().get("status") == "running":
        raise RuntimeError(
            "A finance → smpk_pension sync is already running. Wait for it to finish."
        )

    cfg = resolve_mysql_config(mysql_config)

    with _LOCK:
        if _STATE["status"] == "running":
            raise RuntimeError(
                "A transfer job is already running. Wait for it to finish "
                "or use status to monitor progress."
            )
        names = sorted({str(t).upper().strip() for t in tables if str(t).strip()})
        if not names:
            raise ValueError("Select at least one table.")
        if len(names) > 500:
            raise ValueError(
                "Max 500 tables per job from the UI. For full schema use the "
                "standalone script: python scripts/oracle_schema_to_mysql.py --all --drop"
            )

        job_id = datetime.now().strftime("%Y%m%d-%H%M%S")
        _ACTIVE_MYSQL_FULL = dict(cfg)
        _STATE.update(
            {
                "status": "running",
                "job_id": job_id,
                "mysql": public_mysql_config(cfg),
                "options": {
                    "drop": bool(drop),
                    "truncate": bool(truncate),
                    "batch_size": int(batch_size),
                    "skip_foreign_keys": bool(skip_foreign_keys),
                    "constraints_only": bool(constraints_only),
                    "stop_on_error": bool(stop_on_error),
                    "mysql_config": public_mysql_config(cfg),
                },
                "queue": names,
                "current_table": None,
                "current_index": 0,
                "total": len(names),
                "completed": [],
                "failed": {},
                "results": {},
                "log": [],
                "started_at": _now(),
                "finished_at": None,
                "message": (
                    f"Started job {job_id} with {len(names)} table(s) → "
                    f"{cfg['user']}@{cfg['host']}:{cfg['port']}/{cfg['database']}"
                ),
            }
        )
        _persist()

    thread = threading.Thread(
        target=_run_job,
        name=f"finance-transfer-{job_id}",
        daemon=True,
    )
    thread.start()
    return get_status()


def _run_job():
    global _ACTIVE_MYSQL_FULL

    opts = {}
    queue = []
    mysql_cfg = None
    with _LOCK:
        opts = dict(_STATE["options"])
        queue = list(_STATE["queue"])
        mysql_cfg = dict(_ACTIVE_MYSQL_FULL) if _ACTIVE_MYSQL_FULL else None

    def log_fn(msg: str):
        with _LOCK:
            if msg.strip().startswith("inserted ") and _STATE["log"]:
                last = _STATE["log"][-1]
                if "inserted " in last:
                    _STATE["log"][-1] = (
                        f"[{datetime.now().strftime('%H:%M:%S')}] {msg}"
                    )
                    _persist()
                    return
            _append_log(msg)

    stop = False
    for index, table in enumerate(queue, start=1):
        with _LOCK:
            if _STATE["status"] != "running":
                stop = True
            _STATE["current_table"] = table
            _STATE["current_index"] = index
            _STATE["message"] = f"Transferring {table} ({index}/{len(queue)})"
            _append_log(f"--- [{index}/{len(queue)}] {table} ---")
        if stop:
            break

        try:
            result = dump_table(
                table,
                drop=opts.get("drop", True),
                truncate=opts.get("truncate", False),
                batch_size=max(1, int(opts.get("batch_size") or 2000)),
                skip_foreign_keys=opts.get("skip_foreign_keys", True),
                constraints_only=opts.get("constraints_only", False),
                log_fn=log_fn,
                mysql_config=mysql_cfg,
            )
            with _LOCK:
                _STATE["completed"].append(table)
                _STATE["results"][table] = result
                _STATE["failed"].pop(table, None)
                _append_log(
                    f"OK {table}: rows={result.get('rows')}, "
                    f"fk_applied={result.get('fk_applied')}, "
                    f"fk_pending={result.get('fk_pending')}"
                )
        except Exception as exc:
            with _LOCK:
                _STATE["failed"][table] = str(exc)
                _append_log(f"FAIL {table}: {exc}")
                if opts.get("stop_on_error"):
                    _STATE["status"] = "error"
                    _STATE["message"] = f"Stopped on error at {table}: {exc}"
                    _STATE["finished_at"] = _now()
                    _STATE["current_table"] = None
                    _ACTIVE_MYSQL_FULL = None
                    _persist()
                    return

    with _LOCK:
        failed_n = len(_STATE["failed"])
        ok_n = len(_STATE["completed"])
        _STATE["current_table"] = None
        _STATE["finished_at"] = _now()
        if failed_n and ok_n == 0:
            _STATE["status"] = "error"
            _STATE["message"] = f"All tables failed ({failed_n})."
        elif failed_n:
            _STATE["status"] = "done"
            _STATE["message"] = f"Finished with errors: ok={ok_n}, failed={failed_n}."
        else:
            _STATE["status"] = "done"
            _STATE["message"] = f"Finished successfully: {ok_n} table(s)."
        if opts.get("skip_foreign_keys"):
            _append_log(
                "Note: FKs were deferred (skip_foreign_keys=true). "
                "Use Apply pending FKs after parent tables are loaded."
            )
        _ACTIVE_MYSQL_FULL = None
        _persist()


def run_apply_pending_fks(mysql_config=None) -> dict:
    with _LOCK:
        if _STATE["status"] == "running":
            raise RuntimeError("Cannot apply FKs while a transfer job is running.")
    cfg = resolve_mysql_config(mysql_config)
    try:
        apply_pending_foreign_keys(mysql_config=cfg)
        with _LOCK:
            _STATE["mysql"] = public_mysql_config(cfg)
            _append_log(
                f"Applied pending foreign keys on "
                f"{cfg['user']}@{cfg['host']}:{cfg['port']}/{cfg['database']}."
            )
            _STATE["message"] = "Pending FK apply finished."
        return {
            "ok": True,
            "message": "Pending foreign keys processed.",
            "mysql": public_mysql_config(cfg),
        }
    except Exception as exc:
        raise RuntimeError(str(exc)) from exc
