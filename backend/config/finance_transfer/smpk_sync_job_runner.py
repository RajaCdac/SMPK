"""Background finance → smpk_pension sync job (one at a time)."""

from __future__ import annotations

import threading
from copy import deepcopy
from datetime import datetime
from pathlib import Path

from . import job_runner as oracle_job
from .smpk_sync_engine import (
    public_mysql_config,
    resolve_source_config,
    resolve_target_config,
    run_sync,
)

_LOCK = threading.Lock()
_LOG_DIR = Path(__file__).resolve().parent.parent / "scripts" / "dump_logs"
_STATUS_FILE = _LOG_DIR / "admin_smpk_sync_job.json"
_MAX_LOG_LINES = 400

_STATE = {
    "status": "idle",
    "job_id": None,
    "source": {},
    "target": {},
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

_ACTIVE_SOURCE_FULL: dict | None = None
_ACTIVE_TARGET_FULL: dict | None = None


def _now():
    return datetime.now().isoformat(timespec="seconds")


def _public_status() -> dict:
    data = deepcopy(_STATE)
    if isinstance(data.get("source"), dict):
        data["source"].pop("password", None)
    if isinstance(data.get("target"), dict):
        data["target"].pop("password", None)
    return data


def _persist():
    try:
        import json

        _LOG_DIR.mkdir(parents=True, exist_ok=True)
        _STATUS_FILE.write_text(
            json.dumps(_public_status(), indent=2, default=str),
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


def start_smpk_sync_job(
    tables: list[str] | None,
    *,
    mode: str = "insert_ignore",
    include_payroll: bool = False,
    batch_size: int = 2000,
    stop_on_error: bool = False,
    source_config=None,
    target_config=None,
) -> dict:
    global _ACTIVE_SOURCE_FULL, _ACTIVE_TARGET_FULL

    if oracle_job.get_status().get("status") == "running":
        raise RuntimeError(
            "An Oracle → MySQL transfer is already running. Wait for it to finish."
        )

    src_cfg = resolve_source_config(source_config)
    tgt_cfg = resolve_target_config(target_config)

    from .smpk_sync_engine import preview_sync_tables

    queue = preview_sync_tables(
        src_cfg,
        tgt_cfg,
        tables=tables,
        include_payroll=include_payroll,
    )
    if not queue:
        raise ValueError("No tables selected for sync.")

    with _LOCK:
        if _STATE["status"] == "running":
            raise RuntimeError(
                "A finance → smpk_pension sync is already running."
            )

        job_id = datetime.now().strftime("%Y%m%d-%H%M%S")
        _ACTIVE_SOURCE_FULL = dict(src_cfg)
        _ACTIVE_TARGET_FULL = dict(tgt_cfg)
        _STATE.update(
            {
                "status": "running",
                "job_id": job_id,
                "source": public_mysql_config(src_cfg),
                "target": public_mysql_config(tgt_cfg),
                "options": {
                    "mode": mode,
                    "include_payroll": bool(include_payroll),
                    "batch_size": int(batch_size),
                    "stop_on_error": bool(stop_on_error),
                },
                "queue": queue,
                "current_table": None,
                "current_index": 0,
                "total": len(queue),
                "completed": [],
                "failed": {},
                "results": {},
                "log": [],
                "started_at": _now(),
                "finished_at": None,
                "message": (
                    f"Started sync {job_id}: {len(queue)} table(s), mode={mode}"
                ),
            }
        )
        _persist()

    thread = threading.Thread(
        target=_run_job,
        name=f"smpk-sync-{job_id}",
        daemon=True,
    )
    thread.start()
    return get_status()


def _run_job():
    global _ACTIVE_SOURCE_FULL, _ACTIVE_TARGET_FULL

    opts = {}
    queue = []
    src_cfg = None
    tgt_cfg = None
    with _LOCK:
        opts = dict(_STATE["options"])
        queue = list(_STATE["queue"])
        src_cfg = dict(_ACTIVE_SOURCE_FULL) if _ACTIVE_SOURCE_FULL else None
        tgt_cfg = dict(_ACTIVE_TARGET_FULL) if _ACTIVE_TARGET_FULL else None

    def log_fn(msg: str):
        _append_log(msg)

    def on_table_done(table, index, total, result):
        with _LOCK:
            _STATE["current_table"] = table
            _STATE["current_index"] = index
            _STATE["message"] = f"Syncing {table} ({index}/{total})"
            _STATE["results"][table] = result
            status = str(result.get("status") or "")
            if status.startswith("error"):
                _STATE["failed"][table] = status
            else:
                _STATE["completed"].append(table)
                _STATE["failed"].pop(table, None)

    stop = False
    try:
        summary = run_sync(
            source_cfg=src_cfg,
            target_cfg=tgt_cfg,
            tables=queue,
            mode=opts.get("mode") or "insert_ignore",
            include_payroll=bool(opts.get("include_payroll")),
            batch_size=max(1, int(opts.get("batch_size") or 2000)),
            log_fn=log_fn,
            on_table_done=on_table_done,
        )
        with _LOCK:
            if summary.get("fail") and opts.get("stop_on_error"):
                _STATE["status"] = "error"
                _STATE["message"] = "Stopped with errors."
            elif summary.get("fail"):
                _STATE["status"] = "done"
                _STATE["message"] = (
                    f"Finished with errors: ok={summary['ok']}, fail={summary['fail']}."
                )
            else:
                _STATE["status"] = "done"
                _STATE["message"] = f"Finished successfully: {summary['ok']} table(s)."
    except Exception as exc:
        with _LOCK:
            _STATE["status"] = "error"
            _STATE["message"] = str(exc)
            _append_log(f"JOB FAIL: {exc}")
    finally:
        with _LOCK:
            _STATE["current_table"] = None
            _STATE["finished_at"] = _now()
            _ACTIVE_SOURCE_FULL = None
            _ACTIVE_TARGET_FULL = None
            _persist()
