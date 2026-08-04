import re
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

with open("d:/SMPK/FI_PN_BILL_ABSTRACT.rdf", "rb") as f:
    t = f.read().decode("latin-1", errors="ignore")

for marker in ["FMPEN_ID", "fmpen_id", "FIRST_MONTH_PENSION c", "TH_FIRST_MONTH_PENSION c"]:
    positions = [m.start() for m in re.finditer(marker, t, re.I)]
    print(f"\n{marker}: {len(positions)}")
    for idx in positions[:8]:
        chunk = t[max(0, idx - 80) : idx + 120]
        out = re.sub(r" +", " ", "".join(c if c in "\n\r\t" or 32 <= ord(c) < 127 else " " for c in chunk))
        if "From" in out or "from" in out or "Select" in out:
            print(out)
