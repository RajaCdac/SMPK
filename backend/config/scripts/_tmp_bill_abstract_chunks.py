import re
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

with open("d:/SMPK/FI_PN_BILL_ABSTRACT.rdf", "rb") as f:
    t = f.read().decode("latin-1", errors="ignore")

markers = [
    "Select Ord_By,a.Bill_No",
    "Select  I.Ord_By",
    "Ord_By,a.Bill_No,a.date_created",
    "seleCT A.DBILL_REG_NO",
]
for m in markers:
    idx = t.find(m)
    if idx < 0:
        print("missing", m)
        continue
    chunk = t[idx : idx + 4000]
    # keep printable
    out = []
    for c in chunk:
        if c in "\n\r\t" or 32 <= ord(c) < 127:
            out.append(c)
        else:
            out.append(" ")
    s = re.sub(r" +", " ", "".join(out))
    print(f"\n===== {m[:40]} =====")
    print(s[:3500])
