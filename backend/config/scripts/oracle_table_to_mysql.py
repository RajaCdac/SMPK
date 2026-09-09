#!/usr/bin/env python
"""
Dump one Oracle FINANCE table into local MySQL database `finance`.

Includes primary keys and foreign keys from Oracle metadata.

Usage:
    python oracle_table_to_mysql.py FI_LA_MH_ATTENDTYPE --drop
    python oracle_table_to_mysql.py FI_LA_TH_LVAPPL --drop
    python oracle_table_to_mysql.py FI_PN_MH_OLDBILL_PARAM --batch-size 2000

Load parent tables before child tables so foreign keys can be created.
If a parent is missing, FK SQL is saved to finance_pending_foreign_keys.sql.

Requirements (already in SMPK venv):
    cx_Oracle, mysqlclient

MySQL target defaults:
    host=localhost, port=3307, user=root, password=root123, database=finance
"""

from __future__ import annotations

import argparse
import os
import sys
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
CONFIG_DIR = SCRIPT_DIR.parent
if str(CONFIG_DIR) not in sys.path:
    sys.path.insert(0, str(CONFIG_DIR))

import cx_Oracle
import MySQLdb

try:
    from employee.services.oracle_service import get_oracle_connection
except Exception:
    get_oracle_connection = None


ORACLE_SCHEMA = "FINANCE"
PENDING_FK_FILE = SCRIPT_DIR / "finance_pending_foreign_keys.sql"

MYSQL_DEFAULTS = {
    "host": os.environ.get("MYSQL_HOST", "localhost"),
    "port": int(os.environ.get("MYSQL_PORT", "3307")),
    "user": os.environ.get("MYSQL_USER", "root"),
    "password": os.environ.get("MYSQL_PASSWORD", "root123"),
    "database": os.environ.get("MYSQL_DATABASE", "finance"),
}

ORACLE_DEFAULTS = {
    "host": os.environ.get("ORACLE_DB_HOST", "192.168.4.62"),
    "port": int(os.environ.get("ORACLE_DB_PORT", "1521")),
    "service_name": os.environ.get("ORACLE_DB_SERVICE_NAME", "koptfin"),
    "user": os.environ.get("ORACLE_DB_USER", "system"),
    "password": os.environ.get("ORACLE_DB_PASSWORD", "system"),
}


def resolve_mysql_config(overrides=None) -> dict:
    """Merge optional overrides with defaults (any MySQL host/port/db)."""
    cfg = {
        "host": str(MYSQL_DEFAULTS["host"]),
        "port": int(MYSQL_DEFAULTS["port"]),
        "user": str(MYSQL_DEFAULTS["user"]),
        "password": str(MYSQL_DEFAULTS["password"]),
        "database": str(MYSQL_DEFAULTS["database"]),
    }
    if overrides:
        for key in ("host", "port", "user", "password", "database"):
            if key not in overrides or overrides[key] is None:
                continue
            val = overrides[key]
            if key == "port":
                try:
                    cfg["port"] = int(val)
                except (TypeError, ValueError):
                    raise ValueError(f"Invalid MySQL port: {val!r}") from None
            elif key == "password":
                cfg["password"] = str(val)
            else:
                text = str(val).strip()
                if text != "":
                    cfg[key] = text
    if not cfg["host"]:
        cfg["host"] = "localhost"
    if not cfg["user"]:
        raise ValueError("MySQL user is required.")
    if not cfg["database"]:
        raise ValueError("MySQL database name is required.")
    if cfg["port"] <= 0 or cfg["port"] > 65535:
        raise ValueError(f"Invalid MySQL port: {cfg['port']}")
    return cfg


def public_mysql_config(cfg: dict | None = None) -> dict:
    """Safe for API responses (no password)."""
    resolved = resolve_mysql_config(cfg)
    return {
        "host": resolved["host"],
        "port": resolved["port"],
        "user": resolved["user"],
        "database": resolved["database"],
    }


@dataclass
class KeyConstraint:
    name: str
    columns: list[str] = field(default_factory=list)
    ref_table: str = ""
    ref_columns: list[str] = field(default_factory=list)
    delete_rule: str = "NO ACTION"


def connect_oracle():
    if get_oracle_connection is not None:
        try:
            return get_oracle_connection()
        except Exception:
            pass

    dsn = cx_Oracle.makedsn(
        ORACLE_DEFAULTS["host"],
        ORACLE_DEFAULTS["port"],
        service_name=ORACLE_DEFAULTS["service_name"],
    )
    return cx_Oracle.connect(
        ORACLE_DEFAULTS["user"],
        ORACLE_DEFAULTS["password"],
        dsn,
    )


def connect_mysql(*, create_db: bool = False, mysql_config=None):
    cfg = resolve_mysql_config(mysql_config)
    base_kwargs = {
        "host": cfg["host"],
        "port": cfg["port"],
        "user": cfg["user"],
        "passwd": cfg["password"],
        "charset": "utf8mb4",
    }
    if create_db:
        conn = MySQLdb.connect(**base_kwargs)
        cur = conn.cursor()
        db_name = cfg["database"]
        cur.execute(
            f"CREATE DATABASE IF NOT EXISTS `{db_name}` "
            "CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
        )
        conn.commit()
        cur.close()
        conn.close()

    return MySQLdb.connect(**base_kwargs, db=cfg["database"])


def test_mysql_connection(mysql_config=None) -> dict:
    """Connect, ensure DB exists, return version + public config."""
    cfg = resolve_mysql_config(mysql_config)
    conn = connect_mysql(create_db=True, mysql_config=cfg)
    cur = conn.cursor()
    try:
        cur.execute("SELECT VERSION(), DATABASE()")
        version, database = cur.fetchone()
        return {
            "ok": True,
            "mysql": public_mysql_config(cfg),
            "version": str(version or ""),
            "database": str(database or cfg["database"]),
            "message": (
                f"Connected to MySQL {version} as {cfg['user']}@"
                f"{cfg['host']}:{cfg['port']}/{cfg['database']}"
            ),
        }
    finally:
        cur.close()
        conn.close()


def oracle_columns(cur, table_name: str):
    cur.execute(
        """
        SELECT COLUMN_NAME,
               DATA_TYPE,
               DATA_LENGTH,
               DATA_PRECISION,
               DATA_SCALE,
               NULLABLE,
               DATA_DEFAULT
        FROM ALL_TAB_COLUMNS
        WHERE OWNER = :owner
          AND TABLE_NAME = :table_name
        ORDER BY COLUMN_ID
        """,
        {"owner": ORACLE_SCHEMA, "table_name": table_name.upper()},
    )
    rows = cur.fetchall()
    if not rows:
        raise ValueError(
            f"Table {ORACLE_SCHEMA}.{table_name.upper()} not found in Oracle."
        )
    return rows


def oracle_primary_key(cur, table_name: str) -> KeyConstraint | None:
    cur.execute(
        """
        SELECT c.constraint_name, cc.column_name, cc.position
        FROM ALL_CONSTRAINTS c
        JOIN ALL_CONS_COLUMNS cc
          ON c.owner = cc.owner
         AND c.constraint_name = cc.constraint_name
        WHERE c.owner = :owner
          AND c.table_name = :table_name
          AND c.constraint_type = 'P'
        ORDER BY cc.position
        """,
        {"owner": ORACLE_SCHEMA, "table_name": table_name.upper()},
    )
    rows = cur.fetchall()
    if not rows:
        return None

    return KeyConstraint(
        name=rows[0][0],
        columns=[row[1] for row in rows],
    )


def oracle_foreign_keys(cur, table_name: str) -> list[KeyConstraint]:
    cur.execute(
        """
        SELECT c.constraint_name,
               cc.column_name,
               cc.position,
               r.table_name AS ref_table,
               rcc.column_name AS ref_column,
               c.delete_rule
        FROM ALL_CONSTRAINTS c
        JOIN ALL_CONS_COLUMNS cc
          ON c.owner = cc.owner
         AND c.constraint_name = cc.constraint_name
        JOIN ALL_CONSTRAINTS r
          ON c.r_owner = r.owner
         AND c.r_constraint_name = r.constraint_name
        JOIN ALL_CONS_COLUMNS rcc
          ON r.owner = rcc.owner
         AND r.constraint_name = rcc.constraint_name
         AND cc.position = rcc.position
        WHERE c.owner = :owner
          AND c.table_name = :table_name
          AND c.constraint_type = 'R'
        ORDER BY c.constraint_name, cc.position
        """,
        {"owner": ORACLE_SCHEMA, "table_name": table_name.upper()},
    )

    grouped: dict[str, KeyConstraint] = {}
    for name, col, _pos, ref_table, ref_col, delete_rule in cur.fetchall():
        if name not in grouped:
            grouped[name] = KeyConstraint(
                name=name,
                ref_table=ref_table,
                delete_rule=delete_rule or "NO ACTION",
            )
        grouped[name].columns.append(col)
        grouped[name].ref_columns.append(ref_col)

    return list(grouped.values())


def mysql_type_for_oracle(data_type, data_length, precision, scale):
    dt = (data_type or "").upper()

    if dt in ("VARCHAR2", "NVARCHAR2", "CHAR", "NCHAR"):
        length = min(int(data_length or 255), 16383)
        return f"VARCHAR({max(length, 1)})"

    if dt == "NUMBER":
        if precision is None:
            return "DOUBLE"
        p = int(precision)
        s = int(scale or 0)
        if s == 0:
            # Signed MySQL INT max is 2_147_483_647 (~10 digits but only up to 2.1e9).
            # Oracle NUMBER(10) values like mobile 98xxxxxxxx overflow INT → ERROR 1264.
            if p <= 9:
                return "INT"
            if p <= 18:
                return "BIGINT"
            return f"DECIMAL({p},0)"
        return f"DECIMAL({p},{s})"

    if dt in ("FLOAT", "BINARY_FLOAT", "BINARY_DOUBLE"):
        return "DOUBLE"

    if dt == "DATE":
        return "DATETIME"

    if dt.startswith("TIMESTAMP"):
        return "DATETIME(6)"

    if dt in ("CLOB", "NCLOB", "LONG"):
        return "LONGTEXT"

    if dt in ("BLOB", "RAW", "LONG RAW"):
        return "LONGBLOB"

    if dt == "ROWID":
        return "VARCHAR(18)"

    return "TEXT"


def quote_ident(name: str) -> str:
    return f"`{name}`"


def mysql_delete_rule(delete_rule: str) -> str:
    rule = (delete_rule or "NO ACTION").upper().replace("_", " ")
    if rule == "CASCADE":
        return " ON DELETE CASCADE"
    if rule == "SET NULL":
        return " ON DELETE SET NULL"
    return ""


def build_create_table_sql(
    table_name: str,
    columns,
    primary_key: KeyConstraint | None,
):
    col_defs = []
    for name, data_type, data_length, precision, scale, nullable, _default in columns:
        mysql_type = mysql_type_for_oracle(
            data_type, data_length, precision, scale
        )
        null_sql = "NULL" if nullable == "Y" else "NOT NULL"
        col_defs.append(f"{quote_ident(name)} {mysql_type} {null_sql}")

    if primary_key and primary_key.columns:
        pk_cols = ", ".join(quote_ident(c) for c in primary_key.columns)
        col_defs.append(
            f"CONSTRAINT {quote_ident(primary_key.name)} PRIMARY KEY ({pk_cols})"
        )

    cols_sql = ",\n  ".join(col_defs)
    return (
        f"CREATE TABLE IF NOT EXISTS {quote_ident(table_name)} (\n"
        f"  {cols_sql}\n"
        f") ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci"
    )


def build_foreign_key_sql(table_name: str, fk: KeyConstraint) -> str:
    cols = ", ".join(quote_ident(c) for c in fk.columns)
    ref_cols = ", ".join(quote_ident(c) for c in fk.ref_columns)
    on_delete = mysql_delete_rule(fk.delete_rule)
    return (
        f"ALTER TABLE {quote_ident(table_name)} "
        f"ADD CONSTRAINT {quote_ident(fk.name)} "
        f"FOREIGN KEY ({cols}) "
        f"REFERENCES {quote_ident(fk.ref_table)} ({ref_cols})"
        f"{on_delete};"
    )


def mysql_table_exists(cur, table_name: str, *, database: str) -> bool:
    cur.execute(
        """
        SELECT COUNT(*)
        FROM information_schema.tables
        WHERE table_schema = %s
          AND table_name = %s
        """,
        (database, table_name),
    )
    return cur.fetchone()[0] > 0


def mysql_constraint_exists(
    cur, table_name: str, constraint_name: str, *, database: str
) -> bool:
    cur.execute(
        """
        SELECT COUNT(*)
        FROM information_schema.table_constraints
        WHERE table_schema = %s
          AND table_name = %s
          AND constraint_name = %s
        """,
        (database, table_name, constraint_name),
    )
    return cur.fetchone()[0] > 0


def drop_existing_foreign_keys(
    cur, table_name: str, foreign_keys: list[KeyConstraint], *, database: str
):
    for fk in foreign_keys:
        if mysql_constraint_exists(cur, table_name, fk.name, database=database):
            cur.execute(
                f"ALTER TABLE {quote_ident(table_name)} "
                f"DROP FOREIGN KEY {quote_ident(fk.name)}"
            )


def append_pending_fk(sql: str):
    with PENDING_FK_FILE.open("a", encoding="utf-8") as fh:
        fh.write(sql + "\n")


def apply_foreign_keys(
    cur,
    table_name: str,
    foreign_keys: list[KeyConstraint],
    *,
    skip_foreign_keys: bool,
    database: str,
) -> tuple[int, int]:
    if not foreign_keys:
        return 0, 0

    # During bulk schema dump, only queue FK SQL for a later pass.
    if skip_foreign_keys:
        pending = 0
        for fk in foreign_keys:
            append_pending_fk(build_foreign_key_sql(table_name, fk))
            pending += 1
        print(f"  FK queued for later: {pending}")
        return 0, pending

    applied = 0
    pending = 0

    for fk in foreign_keys:
        if not mysql_table_exists(cur, fk.ref_table, database=database):
            sql = build_foreign_key_sql(table_name, fk)
            append_pending_fk(sql)
            print(
                f"  FK deferred (parent missing): {fk.name} -> "
                f"{fk.ref_table}({', '.join(fk.ref_columns)})"
            )
            pending += 1
            continue

        if mysql_constraint_exists(cur, table_name, fk.name, database=database):
            print(f"  FK exists, skipping: {fk.name}")
            continue

        sql = build_foreign_key_sql(table_name, fk)
        try:
            cur.execute(sql)
            print(
                f"  FK applied: {fk.name} -> "
                f"{fk.ref_table}({', '.join(fk.ref_columns)})"
            )
            applied += 1
        except MySQLdb.Error as exc:
            append_pending_fk(sql)
            print(f"  FK deferred (error): {fk.name} — {exc}")
            pending += 1

    return applied, pending


def normalize_value(value):
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    if isinstance(value, date):
        return datetime(value.year, value.month, value.day)
    if isinstance(value, Decimal):
        return value
    if isinstance(value, (bytes, bytearray)):
        return bytes(value)
    if hasattr(value, "read"):
        data = value.read()
        if isinstance(data, bytes):
            return data
        return str(data) if data is not None else None
    return value


def fetch_oracle_rows(cur, table_name: str, column_names, batch_size: int):
    quoted_cols = ", ".join(column_names)
    sql = f"SELECT {quoted_cols} FROM {ORACLE_SCHEMA}.{table_name}"
    cur.execute(sql)

    while True:
        rows = cur.fetchmany(batch_size)
        if not rows:
            break
        yield [tuple(normalize_value(v) for v in row) for row in rows]


def insert_batch(
    mysql_cur,
    table_name: str,
    column_names,
    rows,
    *,
    mode: str = "insert",
):
    """
    mode:
      insert  — plain INSERT (fails on duplicate PK)
      append  — INSERT ... ON DUPLICATE KEY UPDATE (add new + refresh existing)
      ignore  — INSERT IGNORE (add new only; keep existing row as-is)
    """
    if not rows:
        return 0

    placeholders = ", ".join(["%s"] * len(column_names))
    col_list = ", ".join(quote_ident(c) for c in column_names)
    table_sql = quote_ident(table_name)

    if mode == "ignore":
        sql = (
            f"INSERT IGNORE INTO {table_sql} ({col_list}) "
            f"VALUES ({placeholders})"
        )
    elif mode == "append":
        # Upsert: new rows insert; existing PK rows get latest Oracle values.
        assignments = ", ".join(
            f"{quote_ident(c)}=VALUES({quote_ident(c)})" for c in column_names
        )
        sql = (
            f"INSERT INTO {table_sql} ({col_list}) VALUES ({placeholders}) "
            f"ON DUPLICATE KEY UPDATE {assignments}"
        )
    else:
        sql = f"INSERT INTO {table_sql} ({col_list}) VALUES ({placeholders})"

    mysql_cur.executemany(sql, rows)
    return len(rows)


def _log(msg: str, log_fn=None, *, end: str = "\n"):
    if log_fn:
        if end == "\n":
            log_fn(msg)
        return
    print(msg, end=end)


def list_oracle_finance_tables(prefixes: list[str] | None = None) -> list[dict]:
    """
    List Oracle FINANCE tables with approximate row counts (stats NUM_ROWS).
    Returns list of {name, num_rows}.
    """
    conn = connect_oracle()
    cur = conn.cursor()
    try:
        if prefixes:
            clauses = []
            binds = {"owner": ORACLE_SCHEMA}
            for i, prefix in enumerate(prefixes):
                key = f"p{i}"
                clauses.append(f"t.TABLE_NAME LIKE :{key}")
                binds[key] = f"{prefix.upper().strip()}%"
            where = " OR ".join(clauses)
            sql = f"""
                SELECT t.TABLE_NAME, NVL(t.NUM_ROWS, 0)
                FROM ALL_TABLES t
                WHERE t.OWNER = :owner
                  AND ({where})
                ORDER BY t.TABLE_NAME
            """
            cur.execute(sql, binds)
        else:
            cur.execute(
                """
                SELECT t.TABLE_NAME, NVL(t.NUM_ROWS, 0)
                FROM ALL_TABLES t
                WHERE t.OWNER = :owner
                ORDER BY t.TABLE_NAME
                """,
                {"owner": ORACLE_SCHEMA},
            )
        return [
            {"name": str(row[0]).upper(), "num_rows": int(row[1] or 0)}
            for row in cur.fetchall()
        ]
    finally:
        cur.close()
        conn.close()


def mysql_table_status_map(mysql_config=None) -> dict[str, dict]:
    """Return {TABLE_NAME_UPPER: {exists, row_count}} for the target MySQL DB."""
    cfg = resolve_mysql_config(mysql_config)
    conn = connect_mysql(create_db=True, mysql_config=cfg)
    cur = conn.cursor()
    try:
        cur.execute(
            """
            SELECT TABLE_NAME, TABLE_ROWS
            FROM information_schema.tables
            WHERE table_schema = %s
            """,
            (cfg["database"],),
        )
        out = {}
        for name, rows in cur.fetchall():
            key = str(name).upper()
            out[key] = {
                "exists": True,
                "row_count": int(rows or 0) if rows is not None else None,
            }
        return out
    finally:
        cur.close()
        conn.close()


def dump_table(
    table_name: str,
    *,
    drop: bool,
    batch_size: int,
    truncate: bool,
    skip_foreign_keys: bool,
    constraints_only: bool,
    append: bool = False,
    insert_ignore: bool = False,
    log_fn=None,
    mysql_config=None,
):
    """
    Copy one Oracle FINANCE table into a MySQL database (any host via mysql_config).
    Returns a result dict.

    Modes (mutually exclusive intent):
      drop           — DROP + CREATE + INSERT
      truncate       — keep structure, clear rows, INSERT
      append         — keep all existing rows; upsert Oracle rows by PK
      insert_ignore  — keep existing rows; insert only brand-new PKs
      (default insert after create) — plain INSERT
    """
    table_name = table_name.upper().strip()
    cfg = resolve_mysql_config(mysql_config)
    _log(f"Oracle source : {ORACLE_SCHEMA}.{table_name}", log_fn)
    _log(
        f"MySQL target  : {cfg['user']}@{cfg['host']}:{cfg['port']}/"
        f"{cfg['database']}.{table_name}",
        log_fn,
    )

    ora_conn = connect_oracle()
    ora_cur = ora_conn.cursor()
    mysql_conn = connect_mysql(create_db=True, mysql_config=cfg)
    mysql_cur = mysql_conn.cursor()

    total = 0
    applied = 0
    pending = 0
    try:
        columns = oracle_columns(ora_cur, table_name)
        column_names = [c[0] for c in columns]
        primary_key = oracle_primary_key(ora_cur, table_name)
        foreign_keys = oracle_foreign_keys(ora_cur, table_name)

        _log(f"Columns       : {len(column_names)}", log_fn)
        if primary_key:
            _log(
                f"Primary key   : {primary_key.name} "
                f"({', '.join(primary_key.columns)})",
                log_fn,
            )
        else:
            _log("Primary key   : none", log_fn)
        _log(f"Foreign keys  : {len(foreign_keys)}", log_fn)

        if drop:
            _log("Dropping existing MySQL table (if any)...", log_fn)
            # Inbound FKs on other tables (e.g. fi_es_th_rs → fi_xx_mh_emp_per)
            # block DROP unless checks are off for this session.
            mysql_cur.execute("SET FOREIGN_KEY_CHECKS=0")
            mysql_cur.execute(f"DROP TABLE IF EXISTS {quote_ident(table_name)}")
            mysql_conn.commit()

        if not constraints_only:
            # CREATE IF NOT EXISTS — never recreates when appending/updating.
            create_sql = build_create_table_sql(table_name, columns, primary_key)
            mysql_cur.execute(create_sql)
            mysql_conn.commit()

            if truncate and not drop and not append and not insert_ignore:
                _log("Truncating existing MySQL table...", log_fn)
                mysql_cur.execute("SET FOREIGN_KEY_CHECKS=0")
                mysql_cur.execute(f"TRUNCATE TABLE {quote_ident(table_name)}")
                mysql_conn.commit()

            if append:
                insert_mode = "append"
                _log(
                    "Append/upsert mode: keep existing rows; "
                    "INSERT ... ON DUPLICATE KEY UPDATE from Oracle",
                    log_fn,
                )
            elif insert_ignore:
                insert_mode = "ignore"
                _log(
                    "Insert-ignore mode: keep existing rows; "
                    "INSERT IGNORE (new PKs only)",
                    log_fn,
                )
            else:
                insert_mode = "insert"

            _log("Copying rows...", log_fn)
            mysql_cur.execute("SET FOREIGN_KEY_CHECKS=0")
            for batch in fetch_oracle_rows(
                ora_cur, table_name, column_names, batch_size
            ):
                inserted = insert_batch(
                    mysql_cur,
                    table_name,
                    column_names,
                    batch,
                    mode=insert_mode,
                )
                mysql_conn.commit()
                total += inserted
                if log_fn:
                    log_fn(f"  processed {total:,} rows...")
                else:
                    print(f"  processed {total:,} rows...", end="\r")
            mysql_cur.execute("SET FOREIGN_KEY_CHECKS=1")
            mysql_conn.commit()
            _log(f"Rows processed: {total:,}", log_fn)
        else:
            _log("Constraints-only mode: skipping data copy.", log_fn)
            if drop:
                mysql_cur.execute("SET FOREIGN_KEY_CHECKS=1")
                mysql_conn.commit()

        if foreign_keys and not append and not insert_ignore:
            _log("Applying foreign keys...", log_fn)
            drop_existing_foreign_keys(
                mysql_cur, table_name, foreign_keys, database=cfg["database"]
            )
            mysql_conn.commit()
            applied, pending = apply_foreign_keys(
                mysql_cur,
                table_name,
                foreign_keys,
                skip_foreign_keys=skip_foreign_keys,
                database=cfg["database"],
            )
            mysql_conn.commit()
            _log(f"FK applied    : {applied}", log_fn)
            if pending:
                _log(
                    f"FK deferred   : {pending} (see {PENDING_FK_FILE.name})",
                    log_fn,
                )
        elif foreign_keys and (append or insert_ignore):
            _log("Skipping FK rebuild in append/ignore mode.", log_fn)

        return {
            "ok": True,
            "table": table_name,
            "columns": len(column_names),
            "rows": total,
            "mysql": public_mysql_config(cfg),
            "primary_key": (
                {
                    "name": primary_key.name,
                    "columns": primary_key.columns,
                }
                if primary_key
                else None
            ),
            "fk_applied": applied,
            "fk_pending": pending,
            "fk_count": len(foreign_keys),
        }
    finally:
        ora_cur.close()
        ora_conn.close()
        mysql_cur.close()
        mysql_conn.close()


def apply_pending_foreign_keys(mysql_config=None):
    if not PENDING_FK_FILE.exists():
        print(f"No pending FK file: {PENDING_FK_FILE}")
        return

    lines = [
        line.strip()
        for line in PENDING_FK_FILE.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.strip().startswith("--")
    ]
    if not lines:
        print("Pending FK file is empty.")
        return

    cfg = resolve_mysql_config(mysql_config)
    conn = connect_mysql(mysql_config=cfg)
    cur = conn.cursor()
    remaining = []
    applied = 0

    try:
        for sql in lines:
            try:
                cur.execute(sql)
                conn.commit()
                print(f"Applied: {sql}")
                applied += 1
            except MySQLdb.Error as exc:
                print(f"Still pending: {sql}\n  -> {exc}")
                remaining.append(sql)
    finally:
        cur.close()
        conn.close()

    if remaining:
        PENDING_FK_FILE.write_text(
            "\n".join(remaining) + "\n", encoding="utf-8"
        )
    else:
        PENDING_FK_FILE.unlink(missing_ok=True)

    print(
        f"Done on {cfg['user']}@{cfg['host']}:{cfg['port']}/{cfg['database']}. "
        f"Applied {applied}, still pending {len(remaining)}."
    )


def parse_args():
    parser = argparse.ArgumentParser(
        description=(
            "Dump one Oracle FINANCE table into MySQL database finance, "
            "including primary and foreign keys."
        )
    )
    parser.add_argument(
        "table_name",
        nargs="?",
        help="Oracle table name, e.g. FI_LA_TH_LVAPPL",
    )
    parser.add_argument(
        "--drop",
        action="store_true",
        help="Drop and recreate the MySQL table before loading.",
    )
    parser.add_argument(
        "--truncate",
        action="store_true",
        help="Truncate MySQL table before loading (keeps structure).",
    )
    parser.add_argument(
        "--append",
        action="store_true",
        help=(
            "Do not truncate/drop. Upsert Oracle rows into existing table "
            "(INSERT ... ON DUPLICATE KEY UPDATE)."
        ),
    )
    parser.add_argument(
        "--insert-ignore",
        action="store_true",
        help="Do not truncate/drop. Insert only new PKs (INSERT IGNORE).",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=1000,
        help="Rows per insert batch (default: 1000).",
    )
    parser.add_argument(
        "--skip-foreign-keys",
        action="store_true",
        help="Do not create foreign keys (PK still created).",
    )
    parser.add_argument(
        "--constraints-only",
        action="store_true",
        help="Only apply PK/FK to an existing MySQL table (no data copy).",
    )
    parser.add_argument(
        "--apply-pending-fks",
        action="store_true",
        help="Retry foreign keys saved in finance_pending_foreign_keys.sql",
    )
    parser.add_argument("--mysql-host", default=None, help="MySQL host (default env/local)")
    parser.add_argument("--mysql-port", type=int, default=None, help="MySQL port")
    parser.add_argument("--mysql-user", default=None, help="MySQL user")
    parser.add_argument("--mysql-password", default=None, help="MySQL password")
    parser.add_argument("--mysql-database", default=None, help="MySQL database name")
    return parser.parse_args()


def _mysql_cfg_from_args(args) -> dict | None:
    keys = {
        "host": args.mysql_host,
        "port": args.mysql_port,
        "user": args.mysql_user,
        "password": args.mysql_password,
        "database": args.mysql_database,
    }
    if all(v is None for v in keys.values()):
        return None
    return {k: v for k, v in keys.items() if v is not None}


def main():
    args = parse_args()
    mysql_config = _mysql_cfg_from_args(args)

    if args.apply_pending_fks:
        try:
            apply_pending_foreign_keys(mysql_config=mysql_config)
        except Exception as exc:
            print(f"ERROR: {exc}", file=sys.stderr)
            sys.exit(1)
        return

    if not args.table_name:
        print("ERROR: table_name is required unless using --apply-pending-fks")
        sys.exit(1)

    try:
        dump_table(
            args.table_name,
            drop=args.drop,
            truncate=args.truncate,
            append=args.append,
            insert_ignore=args.insert_ignore,
            batch_size=max(1, args.batch_size),
            skip_foreign_keys=args.skip_foreign_keys,
            constraints_only=args.constraints_only,
            mysql_config=mysql_config,
        )
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
