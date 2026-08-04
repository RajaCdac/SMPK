import re
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

with open("d:/SMPK/FI_PN_VOUCHER_GENRATION_INTERM.fmb", "rb") as f:
    t = f.read().decode("latin-1", errors="ignore")

for pat in ["Voucher_First", "MAP_CD", "112", "M_FinYear", "ALOC_CD2", "aloc_cd2", "000", "balance", "BALANCE"]:
    idx = 0
    n = 0
    while n < 5:
        idx = t.upper().find(pat.upper(), idx + 1)
        if idx < 0:
            break
        chunk = re.sub(
            r" +",
            " ",
            "".join(c if 32 <= ord(c) < 127 else " " for c in t[idx - 40 : idx + 180]),
        )
        if len(chunk.strip()) > 25:
            print(f"\n[{pat}] {chunk[:200]}")
        n += 1
