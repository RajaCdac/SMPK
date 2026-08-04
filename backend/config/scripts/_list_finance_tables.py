"""List fi_* tables used via Django connections['finance'] only."""
import re
from pathlib import Path

root = Path(__file__).resolve().parent.parent
conn_re = re.compile(r"""connections\s*\[\s*['"]finance['"]\s*\]""", re.I)
table_re = re.compile(
    r"\b(?:FROM|JOIN|INTO|UPDATE)\s+(?:finance\.)?(fi_[a-z0-9_]+)",
    re.I,
)

finance_files = []
tables = set()

for py in root.rglob("*.py"):
    if "venv" in py.parts or "__pycache__" in py.parts:
        continue
    if py.name.startswith("_list_finance"):
        continue
    text = py.read_text(encoding="utf-8", errors="ignore")
    if not conn_re.search(text):
        continue
    rel = str(py.relative_to(root))
    finance_files.append(rel)
    for m in table_re.finditer(text):
        name = m.group(1).lower()
        if name not in ("fi_pr_",):
            tables.add(name)

print("=== RUNTIME: connections['finance'] ===\n")
for f in sorted(finance_files):
    print(f)

print(f"\n=== TABLES ({len(tables)}) ===\n")
for t in sorted(tables):
    print(t)

# Family pension specific subset
fp = sorted(t for t in tables if "fpen" in t or "family" in t or t == "fi_pm_mh_relation")
print(f"\n=== FAMILY PENSION RELATED ({len(fp)}) ===\n")
for t in fp:
    print(t)
