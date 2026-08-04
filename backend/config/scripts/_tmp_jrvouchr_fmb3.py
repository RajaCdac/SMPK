import re
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

with open("d:/SMPK/FI_PN_T_H_JRVOUCHR_E.fmb", "rb") as f:
    t = f.read().decode("latin-1", errors="ignore")

procs = [
    "FPROC_DEBIT_CREDIT_CHECK",
    "FPROC_INS_TO_BILL",
    "FPROC_GENERATE_HDR",
    "FPROC_TOTAMT",
    "FPROC_INITIALISE_FORM",
    "FPROC_POST_TO_CASH",
    "FProc_Generate_Hdr",
    "FPROC_DUPCHECK",
    "FPROC_USER_RIGHTS",
    "FPROC_SCROLL",
]

for proc in procs:
    for marker in [proc, proc.replace("FPROC", "FProc")]:
        idx = t.find(marker)
        if idx < 0:
            continue
        end = t.find("END;", idx + 50)
        if end < 0 or end - idx > 8000:
            end = idx + 4000
        chunk = t[idx : end + 4]
        chunk = "".join(c if c in "\n\r\t" or 32 <= ord(c) < 127 else "\n" for c in chunk)
        chunk = re.sub(r"\n{3,}", "\n\n", chunk)
        print(f"\n{'='*60}\n{marker}\n{'='*60}")
        print(chunk[:4500])
        break

# block item names
for blk in ["BLKBT_ENTRY", "BLKBT_D_JV", "BLKCT_TOOLBAR", "BLK_CONTROL"]:
    idx = t.find(blk)
    if idx >= 0:
        chunk = t[idx : idx + 2000]
        items = sorted(set(re.findall(rf"{blk}\.([A-Z0-9_]+)", chunk, re.I)))
        print(f"\n{blk} items (partial):", items[:40])

# summary / print report
for marker in ["SUMMARY", "SUMM_", "JRNL", "PNJV", "Run_Product", "REPORTS", "PRINT"]:
    if marker in t.upper():
        pass
for m in re.finditer(r"Run_Product|REPORTS|SUMMARY|SUMM", t, re.I):
    start = max(0, m.start() - 100)
    chunk = re.sub(
        r" +",
        " ",
        "".join(c if 32 <= ord(c) < 127 else " " for c in t[start : start + 300]),
    )
    if "SUMM" in chunk.upper() or "REPORT" in chunk.upper() or "Run_Product" in chunk:
        print("\nreport ref:", chunk[:250])
