import os
from pathlib import Path

import cx_Oracle
from django.conf import settings


def _init_oracle_client():
    """
    Thick mode: Windows dev path or ORACLE_CLIENT_LIB in Docker/Linux.

    Safe to call when the Instant Client is absent (e.g. MySQL-only Docker):
    the directory check + try/except let the app import and run without Oracle.
    """
    lib_dir = os.environ.get("ORACLE_CLIENT_LIB", "").strip()
    if not lib_dir:
        win_default = r"C:\oracle\instantclient_21\instantclient_23_0"
        if Path(win_default).is_dir():
            lib_dir = win_default
    if lib_dir and Path(lib_dir).is_dir():
        try:
            cx_Oracle.init_oracle_client(lib_dir=lib_dir)
        except Exception:
            # Client already initialised, or libs unusable — stay in MySQL-only mode.
            pass


_init_oracle_client()


def get_oracle_connection():
    conf = settings.ORACLE_DB

    dsn = cx_Oracle.makedsn(
        conf["HOST"],
        conf["PORT"],
        service_name=conf["SERVICE_NAME"],
    )

    conn = cx_Oracle.connect(
        conf["USER"],
        conf["PASSWORD"],
        dsn,
    )

    return conn


def oracle_reads_enabled():
    """When False, SMPK uses MySQL mirrors only (no live Oracle reads)."""
    return bool(getattr(settings, "ORACLE_READ_ENABLED", False))


def try_oracle_connection():
    """Open Oracle only when enabled; return None when offline or disabled."""
    if not oracle_reads_enabled():
        return None
    try:
        return get_oracle_connection()
    except Exception:
        return None
