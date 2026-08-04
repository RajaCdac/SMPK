import re
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

with open("d:/SMPK/FI_PN_BILL_ABSTRACT.rdf", "rb") as f:
    t = f.read().decode("latin-1", errors="ignore")

# all select statements mentioning billpass
seen = set()
for m in re.finditer(r"select.{20,2000}fi_pn_th_billpass.{20,1500}", t, re.I | re.S):
    s = "".join(c if c.isprintable() else " " for c in m.group(0))
    s = re.sub(r" +", " ", s).strip()
    key = s[:200]
    if key not in seen:
        seen.add(key)
        print("---")
        print(s[:1200])

# report groups
for g in sorted(set(re.findall(r"G_[A-Z0-9_]+", t))):
    if "BILL" in g or "EMP" in g or "ORD" in g or "CHEQUE" in g:
        print("group", g)

# user parameters
for p in ["V_BILL_NO", "v_bill_no", "P_BILL"]:
    i = t.find(p)
    if i >= 0:
        print(f"\nparam {p} context:", re.sub(r" +", " ", t[i : i + 120])[:120])
