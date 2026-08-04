import re
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

with open("d:/SMPK/FI_PN_BILL_ABSTRACT.rdf", "rb") as f:
    raw = f.read()

strings = re.findall(rb"[\x20-\x7e]{20,}", raw)
for s in strings:
    t = s.decode("ascii")
    if "Ord_By" in t or "EarnDedn_desc" in t or "Earn_Dedn" in t and "FI_PN" in t:
        print("---")
        print(t[:3000])
