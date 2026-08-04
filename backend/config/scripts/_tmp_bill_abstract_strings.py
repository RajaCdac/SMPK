import re
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

with open("d:/SMPK/FI_PN_BILL_ABSTRACT.rdf", "rb") as f:
  raw = f.read()

# extract printable strings length >= 40
strings = re.findall(rb"[\x20-\x7e]{40,}", raw)
for s in strings:
    t = s.decode("ascii")
    if any(k in t for k in ["Ord_By", "EarnDedn", "FI_PN_TH_PENSION", "FI_PN_TD_FIRST", "bill_cd", "applicant_name"]):
        if "select" in t.lower() or "from" in t.lower() or "Ord_By" in t:
            print("---")
            print(t[:2000])
