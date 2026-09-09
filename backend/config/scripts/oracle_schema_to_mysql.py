#!/usr/bin/env python
"""
Dump many / all Oracle FINANCE tables into MySQL database `finance`.

Runs automatically (no one-by-one typing). Supports resume, logging, and
deferred foreign keys.

Usage examples:
  # Full schema (4097 tables) — long overnight job
  python oracle_schema_to_mysql.py --all --drop

  # First-pension related only (~1596 tables) — recommended start
  python oracle_schema_to_mysql.py --prefix FI_PN --prefix FI_XX --prefix FI_LA --prefix FI_PR --drop

  # Resume after interrupt (skips tables already in MySQL)
  python oracle_schema_to_mysql.py --all --drop --resume

  # After all tables loaded, apply deferred FKs
  python oracle_schema_to_mysql.py --apply-pending-fks

  # Dry-run: only list tables that would be dumped
  python oracle_schema_to_mysql.py --all --list-only
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
CONFIG_DIR = SCRIPT_DIR.parent
if str(CONFIG_DIR) not in sys.path:
    sys.path.insert(0, str(CONFIG_DIR))

from oracle_table_to_mysql import (  # noqa: E402
    ORACLE_SCHEMA,
    apply_pending_foreign_keys,
    connect_mysql,
    connect_oracle,
    dump_table,
    list_oracle_finance_tables,
)

LOG_DIR = SCRIPT_DIR / "dump_logs"
PROGRESS_FILE = LOG_DIR / "schema_dump_progress.json"


def list_oracle_tables(prefixes: list[str] | None = None) -> list[str]:
    """Table names only (CLI)."""
    return [t["name"] for t in list_oracle_finance_tables(prefixes)]


def mysql_existing_tables() -> set[str]:
    conn = connect_mysql(create_db=True)
    cur = conn.cursor()
    try:
        cur.execute(
            """
            SELECT TABLE_NAME
            FROM information_schema.tables
            WHERE table_schema = DATABASE()
            """
        )
        # MySQL may return lower-case names depending on settings.
        return {str(row[0]).upper() for row in cur.fetchall()}
    finally:
        cur.close()
        conn.close()


def load_progress() -> dict:
    if not PROGRESS_FILE.exists():
        return {"completed": [], "failed": {}}
    return json.loads(PROGRESS_FILE.read_text(encoding="utf-8"))


def save_progress(progress: dict) -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    PROGRESS_FILE.write_text(
        json.dumps(progress, indent=2),
        encoding="utf-8",
    )


def append_log(line: str) -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    path = LOG_DIR / f"schema_dump_{datetime.now().strftime('%Y%m%d')}.log"
    with path.open("a", encoding="utf-8") as fh:
        fh.write(f"[{stamp}] {line}\n")
    print(line)


def dump_many(
    tables: list[str],
    *,
    drop: bool,
    truncate: bool,
    append: bool,
    insert_ignore: bool,
    batch_size: int,
    resume: bool,
    skip_foreign_keys: bool,
    stop_on_error: bool,
) -> None:
    progress = load_progress()
    completed = set(progress.get("completed") or [])
    failed = dict(progress.get("failed") or {})

    existing = mysql_existing_tables() if resume else set()

    pending = []
    for name in tables:
        upper = name.upper()
        if resume and (upper in completed or upper in existing):
            continue
        pending.append(upper)

    total = len(tables)
    todo = len(pending)
    if drop:
        mode = "drop"
    elif append:
        mode = "append-upsert"
    elif insert_ignore:
        mode = "insert-ignore"
    elif truncate:
        mode = "truncate"
    else:
        mode = "append-upsert"
    append_log(
        f"Start dump: {todo} pending of {total} selected "
        f"(resume={resume}, mode={mode}, skip_fk={skip_foreign_keys})"
    )

    ok = 0
    err = 0
    started = time.time()

    for i, table_name in enumerate(pending, start=1):
        append_log(f"[{i}/{todo}] Dumping {table_name} ...")
        try:
            dump_table(
                table_name,
                drop=drop,
                truncate=truncate and not drop and not append and not insert_ignore,
                append=append or (not drop and not truncate and not insert_ignore),
                insert_ignore=insert_ignore,
                batch_size=batch_size,
                skip_foreign_keys=skip_foreign_keys,
                constraints_only=False,
            )
            completed.add(table_name)
            failed.pop(table_name, None)
            ok += 1
            append_log(f"[{i}/{todo}] OK {table_name}")
        except Exception as exc:
            err += 1
            failed[table_name] = str(exc)
            append_log(f"[{i}/{todo}] FAIL {table_name}: {exc}")
            if stop_on_error:
                save_progress(
                    {
                        "completed": sorted(completed),
                        "failed": failed,
                        "updated_at": datetime.now().isoformat(timespec="seconds"),
                    }
                )
                raise

        save_progress(
            {
                "completed": sorted(completed),
                "failed": failed,
                "updated_at": datetime.now().isoformat(timespec="seconds"),
            }
        )

    elapsed = time.time() - started
    append_log(
        f"Finished. ok={ok}, failed={err}, elapsed={elapsed/60:.1f} min. "
        f"Progress file: {PROGRESS_FILE}"
    )
    if failed:
        append_log(f"Failed tables ({len(failed)}): {', '.join(sorted(failed)[:30])}...")


def parse_args():
    parser = argparse.ArgumentParser(
        description="Batch dump Oracle FINANCE schema tables into MySQL finance."
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Dump all FINANCE tables (~4097).",
    )
    parser.add_argument(
        "--prefix",
        action="append",
        default=[],
        help="Table name prefix filter (repeatable), e.g. --prefix FI_PN",
    )
    parser.add_argument(
        "--drop",
        action="store_true",
        help="Drop/recreate each MySQL table before load.",
    )
    parser.add_argument(
        "--truncate",
        action="store_true",
        help="Keep structure; clear all rows then reload from Oracle.",
    )
    parser.add_argument(
        "--append",
        action="store_true",
        help=(
            "Keep existing rows. Upsert from Oracle "
            "(INSERT ... ON DUPLICATE KEY UPDATE). Default mode."
        ),
    )
    parser.add_argument(
        "--insert-ignore",
        action="store_true",
        help="Keep existing rows. Insert only new primary keys (INSERT IGNORE).",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=5000,
        help="Insert batch size (default 5000).",
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Skip tables already completed / already present in MySQL.",
    )
    parser.add_argument(
        "--with-foreign-keys",
        action="store_true",
        help=(
            "Create FKs while dumping each table. "
            "Default is skip FKs during dump, then use --apply-pending-fks."
        ),
    )
    parser.add_argument(
        "--stop-on-error",
        action="store_true",
        help="Stop immediately on first table failure.",
    )
    parser.add_argument(
        "--list-only",
        action="store_true",
        help="Only print selected table names / count.",
    )
    parser.add_argument(
        "--apply-pending-fks",
        action="store_true",
        help="Retry deferred foreign keys after tables are loaded.",
    )
    return parser.parse_args()


def main():
    args = parse_args()

    if args.apply_pending_fks:
        apply_pending_foreign_keys()
        return

    if not args.all and not args.prefix:
        print(
            "ERROR: choose --all or one/more --prefix FI_PN ...\n"
            "Tip: append/upsert without clearing tables:\n"
            "  python oracle_schema_to_mysql.py "
            "--prefix FI_PN --prefix FI_XX --prefix FI_LA --prefix FI_PR --append"
        )
        sys.exit(1)

    mode_flags = sum(
        bool(x) for x in (args.drop, args.truncate, args.append, args.insert_ignore)
    )
    if mode_flags > 1:
        print(
            "ERROR: use only one of --append / --insert-ignore / --truncate / --drop"
        )
        sys.exit(1)

    prefixes = args.prefix if args.prefix else None
    if args.all:
        prefixes = None

    tables = list_oracle_tables(prefixes)
    print(f"Selected tables: {len(tables)}")

    if args.list_only:
        for name in tables:
            print(name)
        return

    # Safer default for huge schema: load data+PK first, FKs later.
    skip_fk = not args.with_foreign_keys

    # Default = append/upsert (keep existing rows; refresh matching PKs).
    append = bool(args.append) or (
        not args.drop and not args.truncate and not args.insert_ignore
    )

    dump_many(
        tables,
        drop=args.drop,
        truncate=args.truncate,
        append=append,
        insert_ignore=args.insert_ignore,
        batch_size=max(1, args.batch_size),
        resume=args.resume,
        skip_foreign_keys=skip_fk,
        stop_on_error=args.stop_on_error,
    )

    if not skip_fk:
        return

    print(
        "\nData + primary keys done for processed tables.\n"
        "Next (after all tables finish):\n"
        "  python oracle_schema_to_mysql.py --apply-pending-fks\n"
        "Or re-run individual tables with --constraints-only / "
        "extend script to collect FKs in a second pass."
    )


if __name__ == "__main__":
    main()
