import re
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

with open("d:/SMPK/FI_PN_BILL_ABSTRACT.rdf", "rb") as f:
    t = f.read().decode("latin-1", errors="ignore")

marker = "From FI_PN_TH_PENSION_BILL"
positions = [m.start() for m in re.finditer(marker, t, re.I)]
print("hits", len(positions))
for idx in positions:
    start = max(0, idx - 400)
    chunk = t[start : idx + 2200]
    out = re.sub(r" +", " ", "".join(c if c in "\n\r\t" or 32 <= ord(c) < 127 else " " for c in chunk))
    print("\n---")
    print(out[:2400])
