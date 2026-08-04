import re
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

with open("d:/SMPK/FI_PN_BILL_ABSTRACT.rdf", "rb") as f:
    t = f.read().decode("latin-1", errors="ignore")

for marker in ["SUBSTR(B.BILL_NO", "LIC_BANK_CD", "Select Ord_By"]:
    idx = t.find(marker)
    if idx < 0:
        continue
    # expand backward to find Select
    start = idx
    for _ in range(20):
        prev = t.rfind("Select", max(0, start - 3000), start)
        if prev < 0:
            prev = t.rfind("select", max(0, start - 3000), start)
        if prev >= 0:
            start = prev
            break
        start = max(0, start - 500)
    chunk = t[start : idx + 3500]
    out = "".join(c if c in "\n\r\t" or 32 <= ord(c) < 127 else " " for c in chunk)
    out = re.sub(r" +", " ", out)
    print(f"\n===== from {marker} =====")
    print(out[:4000])
