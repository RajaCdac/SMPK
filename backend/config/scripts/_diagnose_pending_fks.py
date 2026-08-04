"""Diagnose pending FK failures after first-pension dump."""
import re
import sys
from pathlib import Path

import MySQLdb

SCRIPT_DIR = Path(__file__).resolve().parent
PENDING = SCRIPT_DIR / "finance_pending_foreign_keys.sql"

MYSQL = dict(
    host="localhost",
    port=3307,
    user="root",
    passwd="root123",
    db="finance",
    charset="utf8mb4",
)

FK_RE = re.compile(
    r"ALTER TABLE `([^`]+)` ADD CONSTRAINT `([^`]+)` FOREIGN KEY \(([^)]+)\) "
    r"REFERENCES `([^`]+)` \(([^)]+)\);",
    re.I,
)


def cols(s: str):
    return [c.strip().strip("`") for c in s.split(",")]


def table_exists(cur, name: str) -> bool:
    cur.execute(
        """
        SELECT COUNT(*) FROM information_schema.tables
        WHERE table_schema = DATABASE() AND table_name = %s
        """,
        (name,),
    )
    # also try lower
    if cur.fetchone()[0] > 0:
        return True
    cur.execute(
        """
        SELECT COUNT(*) FROM information_schema.tables
        WHERE table_schema = DATABASE() AND UPPER(table_name) = UPPER(%s)
        """,
        (name,),
    )
    return cur.fetchone()[0] > 0


def main():
    lines = [
        ln.strip()
        for ln in PENDING.read_text(encoding="utf-8").splitlines()
        if ln.strip() and not ln.startswith("--")
    ]
    conn = MySQLdb.connect(**MYSQL)
    cur = conn.cursor()

    missing_parent = []
    orphan_data = []
    other = []

    for sql in lines:
        m = FK_RE.match(sql)
        if not m:
            other.append(("parse_fail", sql))
            continue
        child, cname, child_cols, parent, parent_cols = m.groups()
        ccols = cols(child_cols)
        pcols = cols(parent_cols)

        if not table_exists(cur, parent):
            missing_parent.append((cname, child, parent))
            continue

        # orphan check
        on = " AND ".join(f"c.`{a}` = p.`{b}`" for a, b in zip(ccols, pcols))
        null_ok = " OR ".join(f"c.`{a}` IS NULL" for a in ccols)
        q = f"""
            SELECT COUNT(*) FROM `{child}` c
            WHERE NOT EXISTS (
              SELECT 1 FROM `{parent}` p WHERE {on}
            )
            AND NOT ({null_ok})
        """
        try:
            cur.execute(q)
            orphans = cur.fetchone()[0]
        except Exception as exc:
            other.append((cname, f"check_error: {exc}"))
            continue

        if orphans > 0:
            orphan_data.append((cname, child, parent, orphans))
        else:
            # try applying
            try:
                cur.execute(sql)
                conn.commit()
                print(f"NOW APPLIED: {cname}")
            except Exception as exc:
                other.append((cname, str(exc)))

    print("\n=== SUMMARY ===")
    print(f"Pending statements: {len(lines)}")
    print(f"Missing parent tables: {len(missing_parent)}")
    print(f"Orphan/data issues: {len(orphan_data)}")
    print(f"Other: {len(other)}")

    print("\n--- Missing parents ---")
    parents = sorted({p for _, _, p in missing_parent})
    for p in parents:
        kids = [c for _, c, pp in missing_parent if pp == p]
        print(f"  {p}  (needed by {len(kids)} FK(s)): {', '.join(sorted(set(kids))[:5])}")

    print("\n--- Orphan data ---")
    for cname, child, parent, n in orphan_data:
        print(f"  {cname}: {child} -> {parent}  orphans={n}")

    if other:
        print("\n--- Other ---")
        for a, b in other[:20]:
            print(f"  {a}: {b}")

    cur.close()
    conn.close()


if __name__ == "__main__":
    main()
