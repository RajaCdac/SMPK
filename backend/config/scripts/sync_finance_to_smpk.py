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
) -> tuple[int, str]:
    src_db = SOURCE["database"]
    tgt_db = TARGET["database"]

    if recreate and not dry_run:
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
    if dry_run:
        mode = "recreate" if recreate else "truncate"
        return src_n, f"dry-run {mode} ({src_n} rows, {len(keys)} cols)"

    col_src = ", ".join(f"`{c}`" for c in src_list)
    col_tgt = ", ".join(f"`{c}`" for c in tgt_list)
    placeholders = ", ".join(["%s"] * len(keys))
    select_sql = f"SELECT {col_src} FROM `{table}`"
    insert_sql = f"INSERT INTO `{table}` ({col_tgt}) VALUES ({placeholders})"

    tcur = tgt.cursor()
    scur = src.cursor()
    try:
        tcur.execute("SET FOREIGN_KEY_CHECKS=0")
        tcur.execute("SET sql_mode = ''")  # allow soft NULL→default on strict targets
        if not recreate:
            tcur.execute(f"TRUNCATE TABLE `{table}`")
        scur.execute(select_sql)
        copied = 0
        while True:
            rows = scur.fetchmany(batch_size)
            if not rows:
                break
            coerced = [
                _coerce_row(r, tgt_cols=tgt_list, not_null=not_null) for r in rows
            ]
            tcur.executemany(insert_sql, coerced)
            copied += len(rows)
            if copied % (batch_size * 5) == 0 or copied == src_n:
                tgt.commit()
                print(f"    … {copied}/{src_n}", flush=True)
        tgt.commit()
        tcur.execute("SET FOREIGN_KEY_CHECKS=1")
        tgt.commit()
        return copied, "ok"
    finally:
        scur.close()
        tcur.close()


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
    parser.add_argument("--table", action="append", dest="tables", default=[])
    parser.add_argument("--batch-size", type=int, default=2000)
    parser.add_argument("--yes", action="store_true")
    args = parser.parse_args()

    prefixes = ("fi_pn", "fi_pr", "fi_xx", "fi_pm", "fi_la")

    print(
        f"Source: {SOURCE['host']}:{SOURCE['port']}/{SOURCE['database']}\n"
        f"Target: {TARGET['host']}:{TARGET['port']}/{TARGET['database']}\n"
        f"Recreate DDL: {args.recreate}"
    )

    src = connect(SOURCE)
    tgt = connect(TARGET)
    try:
        src_tables = list_tables(src, SOURCE["database"], prefixes)
        tgt_tables = list_tables(tgt, TARGET["database"], prefixes)
        overlap = src_tables & tgt_tables
        selected = set(t.lower() for t in args.tables) if args.tables else set(overlap)

        if args.tables:
            unknown = selected - src_tables
            if unknown:
                print(f"ERROR: not on source: {sorted(unknown)}")
                return 1
        elif not args.include_payroll:
            skipped = selected & SKIP_BY_DEFAULT
            selected -= SKIP_BY_DEFAULT
            if skipped:
                print(
                    f"Skipping huge payroll tables (use --include-payroll): "
                    f"{', '.join(sorted(skipped))}"
                )

        if args.create_missing or args.recreate:
            for extra in EXTRA_CREATE_IF_MISSING:
                if extra in src_tables:
                    selected.add(extra)

        tables = ordered_tables(selected)
        if not tables:
            print("No tables selected.")
            return 1

        print(f"\nTables ({len(tables)}):")
        for t in tables:
            flag = ""
            if t not in tgt_tables:
                flag = " [CREATE]"
            print(f"  - {t}{flag}")

        if args.list_only:
            return 0

        if not args.yes and not args.dry_run:
            print(
                "\nWARNING: selected target tables will be replaced from finance dump."
            )
            print("SMPK-only tables (first_pension_*) are NOT touched.")
            ans = input("Continue? [y/N] ").strip().lower()
            if ans not in ("y", "yes"):
                print("Aborted.")
                return 1

        # Global FK off for the whole run (recreate order + children).
        tcur = tgt.cursor()
        tcur.execute("SET FOREIGN_KEY_CHECKS=0")
        tgt.commit()
        tcur.close()

        ok = fail = 0
        t0 = time.time()
        for table in tables:
            print(f"\n[{table}]")
            try:
                if table not in src_tables:
                    print("  skip (missing on source)")
                    continue
                n, status = sync_table(
                    src,
                    tgt,
                    table=table,
                    batch_size=args.batch_size,
                    dry_run=args.dry_run,
                    recreate=args.recreate or (table not in tgt_tables),
                )
                print(f"  {status} — {n} rows")
                ok += 1
                tgt_tables.add(table)
            except Exception as exc:
                fail += 1
                print(f"  ERROR: {exc}")
                try:
                    tgt.rollback()
                except Exception:
                    pass

        tcur = tgt.cursor()
        tcur.execute("SET FOREIGN_KEY_CHECKS=1")
        tgt.commit()
        tcur.close()

        elapsed = time.time() - t0
        print(f"\nDone in {elapsed:.1f}s — ok={ok} fail={fail}")
        return 1 if fail else 0
    finally:
        src.close()
        tgt.close()


if __name__ == "__main__":
    sys.exit(main())
