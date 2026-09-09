"""Finance (3307) → smpk_pension (3306) sync helpers for admin UI."""

from __future__ import annotations

import sys
from pathlib import Path

from django.conf import settings

_SCRIPTS = Path(__file__).resolve().parent.parent / "scripts"
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from .engine import mysql_table_status_map, public_mysql_config, test_mysql_connection

from sync_finance_to_smpk import (  # noqa: E402
    SALARY_TABLES,
    SKIP_BY_DEFAULT,
    SYNC_MODES,
    TABLE_PREFIXES,
    connect,
    list_tables,
    ordered_tables,
    resolve_source_config,
    resolve_target_config,
    run_sync,
    select_tables_for_sync,
)

__all__ = [
    "SALARY_TABLES",
    "SYNC_MODES",
    "default_source_config",
    "default_target_config",
    "list_smpk_sync_tables",
    "public_mysql_config",
    "resolve_source_config",
    "resolve_target_config",
    "run_sync",
    "test_mysql_connection",
]


def _db_to_cfg(db_alias: str) -> dict:
    db = settings.DATABASES[db_alias]
    return {
        "host": db.get("HOST") or "localhost",
        "port": int(db.get("PORT") or 3306),
        "user": db.get("USER") or "root",
        "password": db.get("PASSWORD") or "",
        "database": db.get("NAME") or "",
    }


def default_source_config() -> dict:
    return public_mysql_config(resolve_source_config(_db_to_cfg("finance")))


def default_target_config() -> dict:
    return public_mysql_config(resolve_target_config(_db_to_cfg("default")))


def _parse_prefixes(prefix: str) -> tuple[str, ...]:
    raw = [p.strip().lower() for p in str(prefix or "").replace(";", ",").split(",") if p.strip()]
    return tuple(raw) if raw else TABLE_PREFIXES


def list_smpk_sync_tables(
    source_cfg: dict | None = None,
    target_cfg: dict | None = None,
    *,
    prefix: str = "",
    include_payroll: bool = False,
) -> list[dict]:
    src_cfg = resolve_source_config(source_cfg)
    tgt_cfg = resolve_target_config(target_cfg)
    prefixes = _parse_prefixes(prefix)

    finance_map = mysql_table_status_map(src_cfg)
    smpk_map = mysql_table_status_map(tgt_cfg)

    src = connect(src_cfg)
    try:
        src_tables = list_tables(src, src_cfg["database"], prefixes)
    finally:
        src.close()

    items = []
    for name in ordered_tables(src_tables):
        if name in SKIP_BY_DEFAULT and not include_payroll:
            continue
        key = name.upper()
        smpk = smpk_map.get(key) or {}
        finance = finance_map.get(key) or {}
        items.append(
            {
                "name": name,
                "finance_row_count": finance.get("row_count"),
                "in_finance": True,
                "in_smpk": bool(smpk.get("exists")),
                "smpk_row_count": smpk.get("row_count"),
                "skipped_by_default": name in SKIP_BY_DEFAULT,
            }
        )
    return items


def preview_sync_tables(
    source_cfg: dict | None,
    target_cfg: dict | None,
    *,
    tables: list[str] | None,
    include_payroll: bool,
) -> list[str]:
    src_cfg = resolve_source_config(source_cfg)
    tgt_cfg = resolve_target_config(target_cfg)
    src = connect(src_cfg)
    tgt = connect(tgt_cfg)
    try:
        src_tables = list_tables(src, src_cfg["database"], TABLE_PREFIXES)
        tgt_tables = list_tables(tgt, tgt_cfg["database"], TABLE_PREFIXES)
        return select_tables_for_sync(
            src_tables,
            tgt_tables,
            tables=tables,
            include_payroll=include_payroll,
            create_missing=True,
            recreate=False,
        )
    finally:
        src.close()
        tgt.close()
