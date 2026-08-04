import re
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

with open("d:/SMPK/FI_PN_BILL_ABSTRACT.rdf", "rb") as f:
    t = f.read().decode("latin-1", errors="ignore")

# Q_1 main query - search around Q_1
for q in ["Q_1", "Q_2"]:
    idx = 0
    hits = 0
    while hits < 3:
        idx = t.find(q, idx + 1)
        if idx < 0:
            break
        chunk = t[idx : idx + 3000]
        chunk = "".join(c if c.isprintable() else "\n" for c in chunk)
        # find select in chunk
        m = re.search(r"select[\s\S]{50,2500}from[\s\S]{50,1500}", chunk, re.I)
        if m:
            s = re.sub(r"\n+", "\n", m.group(0))
            s = re.sub(r" +", " ", s)
            print(f"\n===== {q} hit {hits+1} =====")
            print(s[:2000])
            hits += 1

# layout field labels near report
labels = [
    "Abstract No",
    "Abstract Dated",
    "Bill Register",
    "Dbill Reg No",
    "Dbill Reg Dt",
    "Fbill Reg No",
    "Bill Desc",
    "Bill Month",
    "Sanction Amt",
    "Deduct Amt",
    "Net Amt",
    "Bill Amt",
    "Payee Name",
    "Cheque No",
    "Bank",
    "Branch",
    "Account",
    "Emp Cd",
    "Ca Number",
    "Party Cd",
    "Section",
    "Financial Adviser",
    "Sr. Acc",
    "Treasurer",
]
print("\n===== LAYOUT LABELS FOUND =====")
for lb in labels:
    if lb.lower() in t.lower():
        print(" +", lb)
