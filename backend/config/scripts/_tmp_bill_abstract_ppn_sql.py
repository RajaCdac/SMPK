import re
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

with open("d:/SMPK/FI_PN_BILL_ABSTRACT.rdf", "rb") as f:
    t = f.read().decode("latin-1", errors="ignore")

for marker in [
    "FI_PN_TH_FIRST_MONTH_PENSION c",
    "SUBSTR(B.BILL_NO,2,1)= 'P'",
    "SUBSTR(B.BILL_NO,2,1)= 'N'",
    "LIC_BANK_CD is not null",
    "FI_PN_TH_FIRST_MONTH_EXG",
]:
    idx = 0
    n = 0
    while n < 2:
        idx = t.find(marker, idx + 1)
        if idx < 0:
            break
        start = max(0, idx - 800)
        chunk = t[start : idx + 2500]
        out = "".join(c if c in "\n\r\t" or 32 <= ord(c) < 127 else " " for c in chunk)
        out = re.sub(r" +", " ", out)
        print(f"\n===== {marker} hit {n+1} =====")
        print(out[:2800])
        n += 1
