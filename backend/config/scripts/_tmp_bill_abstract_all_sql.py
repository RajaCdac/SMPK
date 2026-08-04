import re
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

with open("d:/SMPK/FI_PN_BILL_ABSTRACT.rdf", "rb") as f:
    raw = f.read()

strings = re.findall(rb"[\x20-\x7e]{25,}", raw)
seen = set()
for s in strings:
    t = s.decode("ascii")
    if not any(k in t for k in ["Select ", "select ", "FROM FI_PN", "from FI_PN"]):
        continue
    if "BILLPASS" in t or "PENSION_BILL" in t or "FIRST_MONTH" in t:
        key = t[:120]
        if key in seen:
            continue
        seen.add(key)
        if len(t) > 60:
            print("---")
            print(t[:2500])
