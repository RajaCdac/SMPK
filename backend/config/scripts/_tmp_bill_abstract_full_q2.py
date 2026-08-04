import re
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

with open("d:/SMPK/FI_PN_BILL_ABSTRACT.rdf", "rb") as f:
    t = f.read().decode("latin-1", errors="ignore")

start = t.find("Select Ord_By,a.Bill_No")
end = t.find("a.EarnDedn_desc;ipg_help", start)
if start >= 0 and end > start:
    block = t[start:end + 20]
    out = "".join(c if c in "\n\r\t" or 32 <= ord(c) < 127 else "\n" for c in block)
    print(out)
