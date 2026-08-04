import re
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

with open("d:/SMPK/FI_PN_T_H_JRVOUCHR_E.fmb", "rb") as f:
    raw = f.read()

strings = re.findall(rb"[\x20-\x7e]{20,}", raw)
for s in strings:
    t = s.decode("ascii")
    if any(
        k in t.upper()
        for k in [
            "FPROC_DEBIT",
            "FPROC_INS_TO",
            "FPROC_GENERATE",
            "FPROC_TOTAMT",
            "SUMMARY",
            "MANUAL",
            "BLKBT_ENTRY",
            "BLKBT_D_JV",
            "FI_BR_T_H",
            "JRVOUCHR",
            "PNJV/",
        ]
    ):
        if "PROCEDURE" in t.upper() or "FUNCTION" in t.upper() or "BEGIN" in t.upper() or "BLKBT" in t:
            print("---")
            print(t[:1200])

# all BLKBT_ENTRY field names from string patterns
t = raw.decode("latin-1", errors="ignore")
fields = sorted(set(re.findall(r"BLKBT_ENTRY\.([A-Z0-9_]+)", t, re.I)))
print("\nBLKBT_ENTRY fields:", fields)
fields2 = sorted(set(re.findall(r"BLKBT_D_JV\.([A-Z0-9_]+)", t, re.I)))
print("BLKBT_D_JV fields:", fields2)

# canvas labels
for lb in [
    "Journal Voucher",
    "Manual",
    "Summary",
    "Debit Total",
    "Credit Total",
    "Ref No",
    "Ref Date",
    "Voucher For",
    "Bud Dep",
    "FA No",
    "Post No",
    "Tran Type",
]:
    if lb.lower() in t.lower():
        print("label:", lb)
