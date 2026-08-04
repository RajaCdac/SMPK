import re
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

with open("d:/SMPK/FI_PN_BILL_ABSTRACT.rdf", "rb") as f:
    t = f.read().decode("latin-1", errors="ignore")

markers = [
    "TH_FIRST_MONTH_PENSION",
    "LIC_BANK_CD",
    "SUBSTR(B.BILL_NO",
    "FI_PN_MH_PENSIONER",
    "G_FBILL_REG_NO",
]
for marker in markers:
    positions = [m.start() for m in re.finditer(re.escape(marker), t)]
    print(f"\n{marker}: {len(positions)} hits")
    for idx in positions[:3]:
        start = max(0, idx - 600)
        chunk = t[start : idx + 2000]
        out = "".join(c if c in "\n\r\t" or 32 <= ord(c) < 127 else " " for c in chunk)
        out = re.sub(r" +", " ", out)
        if "Select" in out or "select" in out or "From" in out:
            print(out[:2200])
            print("---")
