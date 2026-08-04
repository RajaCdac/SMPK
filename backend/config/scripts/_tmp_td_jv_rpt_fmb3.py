import re
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

with open("d:/SMPK/FI_PN_TD_JV_RPT.fmb", "rb") as f:
    t = f.read().decode("latin-1", errors="ignore")

keywords = [
    "ZONAL", "ALLOC", "DEBIT", "CREDIT", "NARRATION", "VOUCHER",
    "FA_NO", "POST", "AMOUNT", "DR_CR", "SUMMARY", "COMP_NAME",
    "Q_1", "QUERY", "GROUP", "FRAME", "REPEATING",
]
for kw in keywords:
    matches = sorted(set(re.findall(rf"[A-Z0-9_]*{kw}[A-Z0-9_]*", t)))
    if matches:
        print(kw, matches[:25])

# search readable phrases
for m in re.finditer(r"[A-Z][A-Za-z0-9 ,./()-]{10,80}", t):
    s = m.group(0).strip()
    if any(k in s.upper() for k in ["JOURNAL", "VOUCHER", "ALLOC", "ZONAL", "DEBIT", "CREDIT", "SUMMARY"]):
        if "SELECT" not in s and "PARAM" not in s:
            print("phrase:", s)
