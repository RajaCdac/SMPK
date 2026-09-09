"""Load the existing standalone Oracle→MySQL dump helpers from scripts/."""

from __future__ import annotations

import sys
from pathlib import Path

_SCRIPTS = Path(__file__).resolve().parent.parent / "scripts"
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from oracle_table_to_mysql import (  # noqa: E402
    MYSQL_DEFAULTS,
    ORACLE_SCHEMA,
    apply_pending_foreign_keys,
    dump_table,
    list_oracle_finance_tables,
    mysql_table_status_map,
    public_mysql_config,
    resolve_mysql_config,
    test_mysql_connection,
)

__all__ = [
    "MYSQL_DEFAULTS",
    "ORACLE_SCHEMA",
    "apply_pending_foreign_keys",
    "dump_table",
    "list_oracle_finance_tables",
    "mysql_table_status_map",
    "public_mysql_config",
    "resolve_mysql_config",
    "test_mysql_connection",
]
