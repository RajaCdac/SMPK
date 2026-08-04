import re
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

with open("d:/SMPK/FI_PN_TD_JV_RPT.RDF", "rb") as f:
    t = f.read().decode("latin-1", errors="ignore")

print("size", len(t))

# SQL queries
for m in re.finditer(r"SELECT.{30,800}?FROM.{10,120}", t, re.I | re.S):
    q = re.sub(r"\s+", " ", m.group(0))
    if "JV" in q.upper() or "JOURNAL" in q.upper() or "PN_" in q.upper():
        print("\nSQL:", q[:500])

# Parameters
for pat in ["P_YR", "P_MTH", "P_REF", "P_BILL", "parameter"]:
    idx = 0
    n = 0
    while n < 5:
        idx = t.upper().find(pat.upper(), idx + 1)
        if idx < 0:
            break
        chunk = re.sub(
            r" +",
            " ",
            "".join(c if 32 <= ord(c) < 127 else " " for c in t[idx - 40 : idx + 120]),
        )
        print(f"\n[{pat}] {chunk[:200]}")
        n += 1

# Field labels / boilerplate text
strings = re.findall(r"[\x20-\x7e]{6,100}", t)
labels = []
for s in strings:
    sl = s.strip()
    if any(
        k in sl.upper()
        for k in [
            "SUMMARY", "JOURNAL", "ZONAL", "ALLOC", "NARRATION", "VOUCHER",
            "ABSTRACT", "BILL", "SUSPENSE", "REVENUE", "TOTAL", "MONTH",
            "FAMILY", "MANUAL", "PENSION", "SENIOR", "F.A", "BEING",
        ]
    ):
        if "SELECT" not in sl and "FUNCTION" not in sl:
            labels.append(sl)
for s in sorted(set(labels))[:100]:
    print("txt:", s)

# Report groups / query names
for m in re.finditer(r"Q_[0-9A-Z_]+|G_[0-9A-Z_]+|CF_[0-9A-Z_]+", t):
    pass
queries = sorted(set(re.findall(r"Q_[0-9]+", t)))
groups = sorted(set(re.findall(r"G_[A-Z0-9_]+", t)))[:30]
formulas = sorted(set(re.findall(r"CF_[0-9A-Z_]+", t)))[:30]
print("\nqueries", queries)
print("groups", groups[:25])
print("formulas", formulas[:25])
