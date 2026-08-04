import re
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

with open("d:/SMPK/FI_PN_BILL_ABSTRACT.rdf", "rb") as f:
    t = f.read().decode("latin-1", errors="ignore")

# Q_2 fields suggest query columns - search SQL with these aliases
for needle in ["a.Emp_Name", "Earn_Dedn_Type", "Ord_By", "GRATUITY_AMT", "System_Id"]:
    idx = 0
    while True:
        idx = t.find(needle, idx + 1)
        if idx < 0:
            break
        start = max(0, idx - 1500)
        chunk = t[start : idx + 500]
        m = re.search(r"select.{50,2000}" + re.escape(needle[:10]), chunk, re.I | re.S)
        if m:
            s = re.sub(r"[^\x20-\x7e]", " ", m.group(0))
            s = re.sub(r" +", " ", s)
            if len(s) > 80:
                print(f"\n--- near {needle} ---")
                print(s[:1800])
                break

# find full Q_2 query string in compiled PL/SQL
m = re.search(
    r"select[\s\S]{50,3500}from[\s\S]{50,2000}where[\s\S]{20,800}bill_cd",
    t,
    re.I,
)
count = 0
for m in re.finditer(
    r"select[\s\S]{50,3500}from[\s\S]{50,2000}where[\s\S]{20,800}bill_cd",
    t,
    re.I,
):
    s = re.sub(r"[^\x20-\x7e]", " ", m.group(0))
    s = re.sub(r" +", " ", s)
    if "Earn_Dedn" in s or "Emp_Name" in s or "Ord_By" in s:
        count += 1
        print(f"\n=== Q2 candidate {count} ===")
        print(s[:2200])
