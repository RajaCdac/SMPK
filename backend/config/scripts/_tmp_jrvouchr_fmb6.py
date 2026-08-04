import re
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

with open("d:/SMPK/FI_PN_T_H_JRVOUCHR_E.fmb", "rb") as f:
    t = f.read().decode("latin-1", errors="ignore")

# canvas text prompts
strings = re.findall(r"[\x20-\x7e]{8,80}", t)
prompts = []
for s in strings:
    if any(k in s.lower() for k in ["journal", "voucher", "debit", "credit", "summary", "manual", "allocation", "zonal", "narration", "ref no", "fin yr"]):
        if not s.startswith("BLK") and "FPROC" not in s:
            prompts.append(s.strip())
for s in sorted(set(prompts))[:60]:
    print(s)

# FPROC_TOTAMT full
idx = t.find("PROCEDURE FPROC_TotAmt")
if idx < 0:
    idx = t.find("FPROC_TOTAMT")
if idx >= 0:
    chunk = "".join(c if c in "\n\r\t" or 32 <= ord(c) < 127 else "\n" for c in t[idx : idx + 2000])
    print("\n===== FPROC_TOTAMT =====")
    print(re.sub(r"\n{3,}", "\n\n", chunk)[:2000])

# WHEN-NEW-FORM-INSTANCE for init voucher no
idx = t.find("WHEN-NEW-FORM-INSTANCE (Form)")
if idx >= 0:
    chunk = "".join(c if c in "\n\r\t" or 32 <= ord(c) < 127 else "\n" for c in t[idx : idx + 2500])
    print("\n===== WHEN-NEW-FORM-INSTANCE =====")
    print(re.sub(r"\n{3,}", "\n\n", chunk)[:2500])

# Look for journal summary report name
for pat in ["JRNL", "JOUR", "VOUCH", "PNJV", "SUMM"]:
    for m in re.finditer(rf"[A-Z_]{{5,30}}{pat}[A-Z_]{{0,20}}", t):
        s = m.group(0)
        if "FPROC" not in s and "BLKBT" not in s and len(s) < 35:
            pass

# search report names
for m in re.finditer(r"FI_[A-Z0-9_]{8,40}", t):
    s = m.group(0)
    if "JRNL" in s or "VOUCH" in s or "JV" in s:
        print("report?", s)
