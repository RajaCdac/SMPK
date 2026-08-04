import re
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

with open("d:/SMPK/FI_PN_T_H_JRVOUCHR_E.fmb", "rb") as f:
    t = f.read().decode("latin-1", errors="ignore")

# BLK_CONTROL fields
print("BLK_CONTROL fields:", sorted(set(re.findall(r"BLK_CONTROL\.([A-Z0-9_]+)", t, re.I))))

# summary / print / report
for marker in ["SUMMARY", "SUMM", "JRNL_SUM", "DEBIT_AMT", "CREDIT_AMT", "TOT_DEDC", "PRINT", "REPORT"]:
    idx = 0
    n = 0
    while n < 3:
        idx = t.upper().find(marker, idx + 1)
        if idx < 0:
            break
        chunk = re.sub(
            r" +",
            " ",
            "".join(c if 32 <= ord(c) < 127 else " " for c in t[idx - 60 : idx + 200]),
        )
        if len(chunk.strip()) > 20:
            print(f"\n[{marker}] {chunk[:220]}")
        n += 1

# PRE-INSERT header - voucher no generation
idx = t.find("PRE-INSERT (BLKBT_ENTRY)")
if idx >= 0:
    chunk = "".join(c if c in "\n\r\t" or 32 <= ord(c) < 127 else "\n" for c in t[idx : idx + 3500])
    print("\n===== PRE-INSERT BLKBT_ENTRY =====")
    print(re.sub(r"\n{3,}", "\n\n", chunk)[:3500])

# parameter cparam_cond - edit mode
for m in ["cparam_cond", "CPARAM_COND", "parameter.cparam"]:
    if m.lower() in t.lower():
        idx = t.lower().find(m.lower())
        print("\nparam:", re.sub(r" +", " ", t[idx : idx + 200])[:200])

# tran types in form
print("\ntran types in form:", sorted(set(re.findall(r"PNJV/[A-Z]", t))))

# FPROC_POST_TO_CASH_HDR snippet
for proc in ["FPROC_POST_TO_CASH_HDR", "FPROC_POST_TO_CASH_DTL", "FPROC_POST_TO_CASH_ALOC"]:
    idx = t.find(proc)
    if idx >= 0:
        chunk = "".join(c if c in "\n\r\t" or 32 <= ord(c) < 127 else "\n" for c in t[idx : idx + 2500])
        print(f"\n===== {proc} =====")
        print(re.sub(r"\n{3,}", "\n\n", chunk)[:2000])
