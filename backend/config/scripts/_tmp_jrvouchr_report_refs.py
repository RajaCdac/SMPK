import re
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

with open("d:/SMPK/FI_PN_T_H_JRVOUCHR_E.fmb", "rb") as f:
    t = f.read().decode("latin-1", errors="ignore")

for pat in ["RPT", "RUN_PRODUCT", "REPORT", "FI_PN_TD", "FI_BR_JOUR", "SUMMARY", "PRINT", "voucher_no", "VOUCHER_NO"]:
    idx = 0
    n = 0
    while n < 6:
        idx = t.upper().find(pat.upper(), idx + 1)
        if idx < 0:
            break
        chunk = re.sub(
            r" +",
            " ",
            "".join(c if 32 <= ord(c) < 127 else " " for c in t[idx - 50 : idx + 220]),
        )
        if len(chunk.strip()) > 20:
            print(f"\n[{pat}] {chunk[:240]}")
        n += 1

# canvas labels
strings = re.findall(r"[\x20-\x7e]{6,60}", t)
for s in sorted(set(strings)):
    sl = s.lower()
    if any(k in sl for k in ["summary", "journal", "voucher", "debit", "credit", "allocation", "report"]):
        if "FPROC" not in s and "BLKBT" not in s:
            print("txt:", s.strip())
