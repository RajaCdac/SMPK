#!/usr/bin/env python
"""
Copy first-pension Oracle-shaped tables from MySQL finance (3307) → smpk_pension (3306).

Does NOT touch SMPK-only tables (first_pension_pensioncase, accounts_*, etc.).

By default recreates each target table from finance DDL so structure matches Oracle
(dump), then reloads all rows. Column names are matched case-insensitively.

Usage:
  python sync_finance_to_smpk.py --list-only
  python sync_finance_to_smpk.py --dry-run
  python sync_finance_to_smpk.py --yes
  python sync_finance_to_smpk.py --yes --no-recreate   # keep 3306 DDL, map columns
  python sync_finance_to_smpk.py --yes --insert-ignore --no-recreate
      # new rows only — existing smpk_pension rows are never updated or deleted
  python sync_finance_to_smpk.py --yes --append --no-recreate
      # upsert — refresh existing PKs from finance + insert new PKs
"""

from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path

import MySQLdb

SCRIPT_DIR = Path(__file__).resolve().parent

# Huge payroll tables — skip by default (use --include-payroll to sync).
SKIP_BY_DEFAULT = frozenset(
    {
        "fi_pr_th_salout",
        "fi_pr_td_salout",
    }
)

EXTRA_CREATE_IF_MISSING = (
    "fi_pn_mh_billtype",
    "fi_pn_md_edbilltype_map",
    "fi_pn_th_billpass",
    "fi_pn_td_billpass",
    "fi_pn_mh_bill_print",
)

PREFERRED_ORDER = (
    "fi_xx_xx_m_h_fin_ctrl",
    "fi_xx_xx_m_d_fin_ctrl",
    "fi_xx_mh_dept",
    "fi_xx_mh_desig",
    "fi_xx_mh_emp_per",
    "fi_xx_mh_emp_adm",
    "fi_xx_mh_emp_fin",
    "fi_xx_mh_emp_data",
    "fi_xx_md_finscale",
    "fi_pm_mh_bankabbr",
    "fi_pm_mh_bank",
    "fi_pm_mh_payscale",
    "fi_pm_mh_earndedn",
    "fi_pn_mh_earndedn",
    "fi_pn_mh_erndednmap",
    "fi_pn_mh_jrnltype",
    "fi_pn_md_jrnltype",
    "fi_pn_mh_ada_rate",
    "fi_pn_mh_base_cpi",
    "fi_pn_md_commrate_rupee",
    "fi_pn_mh_death_gratchart",
    "fi_pn_md_death_gratchart",
    "fi_pn_mh_service_gratchart",
    "fi_pn_md_maxadm_gratuity",
    "fi_pn_mh_billtype",
    "fi_pn_md_edbilltype_map",
    "fi_pn_mh_pmthsetup",
    "fi_pn_mh_oldbill_param",
    "fi_pn_mh_application",
    "fi_pn_mh_pension_proposal",
    "fi_pn_md_pension_proposal",
    "fi_pn_mh_pensioner",
    "fi_pn_th_salout",
    "fi_pn_td_salout",
    "fi_pr_th_salout",
    "fi_pr_td_salout",
    "fi_pr_mh_erndednmap",
    "fi_pn_th_first_month_pension",
    "fi_pn_td_first_month_pension",
    "fi_pn_th_pension_bill",
    "fi_pn_th_billpass",
    "fi_pn_td_billpass",
    "fi_pn_mh_bill_print",
    "fi_pn_th_jv",
    "fi_pn_td_jv",
    "fi_pn_th_sepcom",
    "fi_pn_td_sepcom",
)

SOURCE = {
    "host": os.environ.get("FINANCE_MYSQL_HOST", os.environ.get("MYSQL_HOST", "localhost")),
    "port": int(os.environ.get("FINANCE_MYSQL_PORT", "3307")),
    "user": os.environ.get(
        "FINANCE_MYSQL_USER", os.environ.get("MYSQL_USER", "root")
    ),
    "password": os.environ.get(
        "FINANCE_MYSQL_PASSWORD", os.environ.get("MYSQL_PASSWORD", "root123")
    ),
    "database": os.environ.get("FINANCE_MYSQL_DATABASE", "finance"),
}

TARGET = {
    "host": os.environ.get("TARGET_MYSQL_HOST", "localhost"),
    "port": int(os.environ.get("TARGET_MYSQL_PORT", "3306")),
    "user": os.environ.get("TARGET_MYSQL_USER", os.environ.get("MYSQL_USER", "root")),
    "password": os.environ.get(
        "TARGET_MYSQL_PASSWORD", os.environ.get("MYSQL_PASSWORD", "root123")
    ),
    "database": os.environ.get("TARGET_MYSQL_DATABASE", "smpk_pension"),
}

TABLE_PREFIXES = ("fi_pn", "fi_pr", "fi_xx", "fi_pm", "fi_la")

SALARY_TABLES = (
    "fi_pr_th_salout",
    "fi_pr_td_salout",
    "fi_pm_mh_earndedn",
    "fi_pn_mh_earndedn",
    "fi_pr_mh_erndednmap",
)

SYNC_MODES = frozenset({"insert_ignore", "append", "recreate", "truncate"})


def _merge_mysql_cfg(cfg: dict, raw: dict | None) -> dict:
    out = dict(cfg)
    if not raw:
        return out
    key_map = {
        "host": ("host", "mysql_host"),
        "port": ("port", "mysql_port"),
        "user": ("user", "mysql_user"),
        "password": ("password", "mysql_password"),
        "database": ("database", "mysql_database"),
    }
    for key, aliases in key_map.items():
        val = None
        for alias in aliases:
            if alias in raw and raw[alias] not in (None, ""):
                val = raw[alias]
                break
        if val not in (None, ""):
            out[key] = int(val) if key == "port" else val
    return out


def resolve_source_config(raw: dict | None = None) -> dict:
    return _merge_mysql_cfg(SOURCE, raw)


def resolve_target_config(raw: dict | None = None) -> dict:
    return _merge_mysql_cfg(TARGET, raw)


def public_mysql_config(cfg: dict) -> dict:
    return {
        "host": cfg.get("host"),
        "port": cfg.get("port"),
        "user": cfg.get("user"),
        "database": cfg.get("database"),
    }


def connect(cfg: dict):
    return MySQLdb.connect(
        host=cfg["host"],
        port=cfg["port"],
        user=cfg["user"],
        passwd=cfg["password"],
        db=cfg["database"],
        charset="utf8mb4",
    )


def list_tables(conn, schema: str, prefixes: tuple[str, ...]) -> set[str]:
    cur = conn.cursor()
    try:
        like_parts = " OR ".join(["table_name LIKE %s"] * len(prefixes))
        params = [schema] + [f"{p}%" for p in prefixes]
        cur.execute(
            f"""
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = %s
              AND table_type = 'BASE TABLE'
              AND ({like_parts})
            """,
            params,
        )
        return {str(r[0]).lower() for r in cur.fetchall()}
    finally:
        cur.close()


def table_columns(conn, schema: str, table: str) -> list[str]:
    cur = conn.cursor()
    try:
        cur.execute(
            """
            SELECT column_name
            FROM information_schema.columns
            WHERE table_schema = %s AND table_name = %s
            ORDER BY ordinal_position
            """,
            (schema, table),
        )
        return [str(r[0]) for r in cur.fetchall()]
    finally:
        cur.close()


def not_null_columns(conn, schema: str, table: str) -> set[str]:
    cur = conn.cursor()
    try:
        cur.execute(
            """
            SELECT column_name, data_type, column_default, extra
            FROM information_schema.columns
            WHERE table_schema = %s
              AND table_name = %s
              AND is_nullable = 'NO'
            """,
            (schema, table),
        )
        out = set()
        for name, data_type, default, extra in cur.fetchall():
            # Skip auto-increment / columns with explicit defaults.
            if extra and "auto_increment" in str(extra).lower():
                continue
            if default is not None:
                continue
            out.add(str(name).lower())
        return out
    finally:
        cur.close()


def row_count(conn, table: str) -> int:
    cur = conn.cursor()
    try:
        cur.execute(f"SELECT COUNT(*) FROM `{table}`")
        return int(cur.fetchone()[0])
    finally:
        cur.close()


def ordered_tables(names: set[str]) -> list[str]:
    ordered = [t for t in PREFERRED_ORDER if t in names]
    rest = sorted(names - set(ordered))
    return ordered + rest


def create_table_like(src, tgt, table: str) -> None:
    scur = src.cursor()
    tcur = tgt.cursor()
    try:
        tcur.execute("SET FOREIGN_KEY_CHECKS=0")
        scur.execute(f"SHOW CREATE TABLE `{table}`")
        row = scur.fetchone()
        if not row:
            raise RuntimeError(f"Cannot read CREATE TABLE for {table}")
        ddl = row[1]
        tcur.execute(f"DROP TABLE IF EXISTS `{table}`")
        tcur.execute(ddl)
        tgt.commit()
    finally:
        scur.close()
        tcur.close()


def _coerce_row(row, *, tgt_cols: list[str], not_null: set[str]):
    """Replace NULL with '' for NOT NULL string-ish target columns."""
    out = []
    for i, val in enumerate(row):
        col = tgt_cols[i].lower()
        if val is None and col in not_null:
            out.append("")
        else:
            out.append(val)
    return tuple(out)


def sync_table(
    src,
    tgt,
    *,
    table: str,
    batch_size: int,
    dry_run: bool,
    recreate: bool,
    append: bool = False,
    insert_ignore: bool = False,
    src_db: str | None = None,
    tgt_db: str | None = None,
) -> tuple[int, str]:
    src_db = src_db or SOURCE["database"]
    tgt_db = tgt_db or TARGET["database"]

    if recreate and not dry_run and not append and not insert_ignore:
        create_table_like(src, tgt, table)

    src_cols = table_columns(src, src_db, table)
    tgt_cols = table_columns(tgt, tgt_db, table)
    if not src_cols:
        return 0, "skip (missing on source)"
    if not tgt_cols:
        return 0, "skip (missing on target)"

    src_map = {c.lower(): c for c in src_cols}
    tgt_map = {c.lower(): c for c in tgt_cols}
    keys = [k for k in src_map if k in tgt_map]
    if not keys:
        return 0, "skip (no common columns)"

    src_list = [src_map[k] for k in keys]
    tgt_list = [tgt_map[k] for k in keys]
    not_null = not_null_columns(tgt, tgt_db, table)

    src_n = row_count(src, table)
    tgt_n = row_count(tgt, table)
    if dry_run:
        if insert_ignore:
            mode = "insert-ignore"
        elif append:
            mode = "append-upsert"
        elif recreate:
            mode = "recreate"
        else:
            mode = "truncate"
        return src_n, (
            f"dry-run {mode} (source={src_n}, target={tgt_n}, {len(keys)} cols)"
        )

    col_src = ", ".join(f"`{c}`" for c in src_list)
    col_tgt = ", ".join(f"`{c}`" for c in tgt_list)
    placeholders = ", ".join(["%s"] * len(keys))
    select_sql = f"SELECT {col_src} FROM `{table}`"
    if insert_ignore:
        insert_sql = (
            f"INSERT IGNORE INTO `{table}` ({col_tgt}) VALUES ({placeholders})"
        )
    elif append:
        assignments = ", ".join(f"`{c}`=VALUES(`{c}`)" for c in tgt_list)
        insert_sql = (
            f"INSERT INTO `{table}` ({col_tgt}) VALUES ({placeholders}) "
            f"ON DUPLICATE KEY UPDATE {assignments}"
        )
    else:
        insert_sql = f"INSERT INTO `{table}` ({col_tgt}) VALUES ({placeholders})"

    tcur = tgt.cursor()
    scur = src.cursor()
    try:
        tcur.execute("SET FOREIGN_KEY_CHECKS=0")
        tcur.execute("SET sql_mode = ''")  # allow soft NULL→default on strict targets
        if not recreate and not append and not insert_ignore:
            tcur.execute(f"TRUNCATE TABLE `{table}`")
        scur.execute(select_sql)
        processed = 0
        inserted = 0
        while True:
            rows = scur.fetchmany(batch_size)
            if not rows:
                break
            coerced = [
                _coerce_row(r, tgt_cols=tgt_list, not_null=not_null) for r in rows
            ]
            tcur.executemany(insert_sql, coerced)
            batch_n = len(rows)
            processed += batch_n
            if insert_ignore:
                inserted += tcur.rowcount
            elif append:
                inserted += batch_n
            else:
                inserted += batch_n
            if processed % (batch_size * 5) == 0 or processed == src_n:
                tgt.commit()
                if insert_ignore:
                    print(
                        f"    … scanned {processed}/{src_n}, inserted {inserted} new",
                        flush=True,
                    )
                else:
                    print(f"    … {processed}/{src_n}", flush=True)
        tgt.commit()
        tcur.execute("SET FOREIGN_KEY_CHECKS=1")
        tgt.commit()
        if insert_ignore:
            return inserted, f"ok-insert-ignore ({inserted} new of {src_n} source rows)"
        if append:
            return processed, "ok-append-upsert"
        return inserted, "ok"
    finally:
        scur.close()
        tcur.close()


def select_tables_for_sync(
    src_tables: set[str],
    tgt_tables: set[str],
    *,
    tables: list[str] | None = None,
    include_payroll: bool = False,
    create_missing: bool = False,
    recreate: bool = False,
) -> list[str]:
    overlap = src_tables & tgt_tables
    if tables:
        selected = {str(t).lower().strip() for t in tables if str(t).strip()}
        unknown = selected - src_tables
        if unknown:
            raise ValueError(f"Not on finance source: {sorted(unknown)}")
    else:
        selected = set(overlap)

    if not include_payroll:
        selected -= SKIP_BY_DEFAULT

    if create_missing or recreate:
        for extra in EXTRA_CREATE_IF_MISSING:
            if extra in src_tables:
                selected.add(extra)

    return ordered_tables(selected)


def resolve_sync_flags(mode: str) -> dict:
    if mode not in SYNC_MODES:
        raise ValueError(f"Invalid sync mode: {mode}")
    if mode == "insert_ignore":
        return {
            "append": False,
            "insert_ignore": True,
            "recreate": False,
            "incremental": True,
            "label": "insert-ignore (new rows only)",
        }
    if mode == "append":
        return {
            "append": True,
            "insert_ignore": False,
            "recreate": False,
            "incremental": True,
            "label": "append-upsert (insert + update existing PKs)",
        }
    if mode == "recreate":
        return {
            "append": False,
            "insert_ignore": False,
            "recreate": True,
            "incremental": False,
            "label": "recreate (DROP+CREATE+reload — destructive)",
        }
    return {
        "append": False,
        "insert_ignore": False,
        "recreate": False,
        "incremental": False,
        "label": "truncate+reload (destructive)",
    }


def run_sync(
    *,
    source_cfg: dict | None = None,
    target_cfg: dict | None = None,
    tables: list[str] | None = None,
    mode: str = "insert_ignore",
    include_payroll: bool = False,
    batch_size: int = 2000,
    dry_run: bool = False,
    log_fn=None,
    on_table_done=None,
) -> dict:
    """Sync finance MySQL tables into smpk_pension (callable from Django admin job)."""

    def _log(msg: str):
        if log_fn:
            log_fn(msg)
        else:
            print(msg, flush=True)

    src_cfg = resolve_source_config(source_cfg)
    tgt_cfg = resolve_target_config(target_cfg)
    flags = resolve_sync_flags(mode)
    prefixes = TABLE_PREFIXES

    src = connect(src_cfg)
    tgt = connect(tgt_cfg)
    results: dict[str, dict] = {}
    ok = fail = 0

    try:
        src_tables = list_tables(src, src_cfg["database"], prefixes)
        tgt_tables = list_tables(tgt, tgt_cfg["database"], prefixes)
        table_list = select_tables_for_sync(
            src_tables,
            tgt_tables,
            tables=tables,
            include_payroll=include_payroll,
            create_missing=True,
            recreate=flags["recreate"],
        )
        if not table_list:
            raise ValueError("No tables selected for sync.")

        if dry_run:
            for table in table_list:
                src_n = row_count(src, table) if table in src_tables else 0
                tgt_n = row_count(tgt, table) if table in tgt_tables else 0
                results[table] = {
                    "rows": src_n,
                    "status": f"dry-run {flags['label']} (source={src_n}, target={tgt_n})",
                }
            return {
                "ok": len(table_list),
                "fail": 0,
                "results": results,
                "mode": mode,
                "source": public_mysql_config(src_cfg),
                "target": public_mysql_config(tgt_cfg),
            }

        tcur = tgt.cursor()
        tcur.execute("SET FOREIGN_KEY_CHECKS=0")
        tgt.commit()
        tcur.close()

        for index, table in enumerate(table_list, start=1):
            _log(f"--- [{index}/{len(table_list)}] {table} ---")
            try:
                if table not in src_tables:
                    results[table] = {"rows": 0, "status": "skip (missing on source)"}
                    continue
                if (
                    table not in tgt_tables
                    and flags["incremental"]
                ):
                    _log(f"creating missing table {table} from finance DDL …")
                    create_table_like(src, tgt, table)
                    tgt_tables.add(table)
                n, status = sync_table(
                    src,
                    tgt,
                    table=table,
                    batch_size=batch_size,
                    dry_run=False,
                    recreate=(flags["recreate"] or (table not in tgt_tables))
                    and not flags["incremental"],
                    append=flags["append"],
                    insert_ignore=flags["insert_ignore"],
                    src_db=src_cfg["database"],
                    tgt_db=tgt_cfg["database"],
                )
                results[table] = {"rows": n, "status": status}
                ok += 1
                tgt_tables.add(table)
                _log(f"OK {table}: {status} ({n})")
                if on_table_done:
                    on_table_done(table, index, len(table_list), results[table])
            except Exception as exc:
                fail += 1
                results[table] = {"rows": 0, "status": f"error: {exc}"}
                _log(f"FAIL {table}: {exc}")
                if on_table_done:
                    on_table_done(table, index, len(table_list), results[table])
                try:
                    tgt.rollback()
                except Exception:
                    pass

        tcur = tgt.cursor()
        tcur.execute("SET FOREIGN_KEY_CHECKS=1")
        tgt.commit()
        tcur.close()
    finally:
        src.close()
        tgt.close()

    return {
        "ok": ok,
        "fail": fail,
        "results": results,
        "mode": mode,
        "source": public_mysql_config(src_cfg),
        "target": public_mysql_config(tgt_cfg),
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Sync first-pension fi_* tables from finance@3307 to smpk_pension@3306"
    )
    parser.add_argument("--list-only", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument(
        "--create-missing",
        action="store_true",
        help="Include EXTRA tables that exist only on 3307",
    )
    parser.add_argument(
        "--recreate",
        dest="recreate",
        action="store_true",
        default=True,
        help="DROP+CREATE each table from finance DDL before load (default)",
    )
    parser.add_argument(
        "--no-recreate",
        dest="recreate",
        action="store_false",
        help="Keep existing 3306 table DDL; truncate + insert only",
    )
    parser.add_argument(
        "--include-payroll",
        action="store_true",
        help="Also sync huge FI_PR_*_SALOUT tables (~1M / ~13M rows)",
    )
    parser.add_argument(
        "--append",
        action="store_true",
        help=(
            "Do not drop/truncate. Upsert rows into existing smpk_pension tables "
            "(INSERT ... ON DUPLICATE KEY UPDATE). Updates existing PKs from finance."
        ),
    )
    parser.add_argument(
        "--insert-ignore",
        action="store_true",
        help=(
            "Do not drop/truncate/update existing rows. Insert only brand-new PKs "
            "from finance (INSERT IGNORE). Recommended for incremental sync."
        ),
    )
    parser.add_argument("--table", action="append", dest="tables", default=[])
    parser.add_argument("--batch-size", type=int, default=2000)
    parser.add_argument("--yes", action="store_true")
    args = parser.parse_args()

    if args.append and args.insert_ignore:
        print("ERROR: use only one of --append / --insert-ignore")
        return 1

    if args.insert_ignore:
        mode = "insert_ignore"
    elif args.append:
        mode = "append"
    elif args.recreate:
        mode = "recreate"
    else:
        mode = "truncate"

    src_cfg = resolve_source_config()
    tgt_cfg = resolve_target_config()
    flags = resolve_sync_flags(mode)
    print(
        f"Source: {src_cfg['host']}:{src_cfg['port']}/{src_cfg['database']}\n"
        f"Target: {tgt_cfg['host']}:{tgt_cfg['port']}/{tgt_cfg['database']}\n"
        f"Mode: {flags['label']}"
    )

    if args.list_only:
        src = connect(src_cfg)
        tgt = connect(tgt_cfg)
        try:
            src_tables = list_tables(src, src_cfg["database"], TABLE_PREFIXES)
            tgt_tables = list_tables(tgt, tgt_cfg["database"], TABLE_PREFIXES)
            table_list = select_tables_for_sync(
                src_tables,
                tgt_tables,
                tables=args.tables or None,
                include_payroll=args.include_payroll,
                create_missing=args.create_missing or args.recreate,
                recreate=flags["recreate"],
            )
            print(f"\nTables ({len(table_list)}):")
            for t in table_list:
                flag = " [CREATE]" if t not in tgt_tables else ""
                print(f"  - {t}{flag}")
        finally:
            src.close()
            tgt.close()
        return 0

    if not args.yes and not args.dry_run:
        if args.insert_ignore:
            print(
                "\nINSERT IGNORE — only new PKs from finance will be added."
                "\nExisting smpk_pension rows will NOT be updated or deleted."
            )
        elif args.append:
            print(
                "\nAPPEND/UPSERT — new PKs insert; matching PKs refresh from finance."
            )
        else:
            print(
                "\nWARNING: selected target tables will be replaced from finance dump."
            )
        print("SMPK-only tables (first_pension_*) are NOT touched.")
        ans = input("Continue? [y/N] ").strip().lower()
        if ans not in ("y", "yes"):
            print("Aborted.")
            return 1

    t0 = time.time()
    summary = run_sync(
        source_cfg=src_cfg,
        target_cfg=tgt_cfg,
        tables=args.tables or None,
        mode=mode,
        include_payroll=args.include_payroll,
        batch_size=args.batch_size,
        dry_run=args.dry_run,
    )
    elapsed = time.time() - t0
    print(f"\nDone in {elapsed:.1f}s — ok={summary['ok']} fail={summary['fail']}")
    for table, info in summary.get("results", {}).items():
        print(f"  {table}: {info.get('status')} ({info.get('rows')})")
    return 1 if summary["fail"] else 0


if __name__ == "__main__":
    sys.exit(main())
