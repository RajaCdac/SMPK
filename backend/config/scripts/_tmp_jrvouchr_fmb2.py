import re
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

with open("d:/SMPK/FI_PN_T_H_JRVOUCHR_E.fmb", "rb") as f:
    t = f.read().decode("latin-1", errors="ignore")

# form name / window titles
for marker in [
    "MANUAL JOURNAL",
    "Manual Journal",
    "SUMMARY",
    "Summary",
    "JRVOUCHR",
    "FProc_TLB_Save",
    "FProc_TLB_Print",
    "FProc_TLB",
    "TLB_",
    "WHEN-BUTTON-PRESSED",
    "KEY-COMMIT",
    "POST-FORMS-COMMIT",
    "WHEN-NEW-FORM-INSTANCE",
    "FI_PN_T_H_JRVOUCHR",
]:
    idx = 0
    n = 0
    while n < 2:
        idx = t.find(marker, idx + 1)
        if idx < 0:
            break
        chunk = "".join(
            c if c in "\n\r\t" or 32 <= ord(c) < 127 else " " for c in t[idx - 80 : idx + 600]
        )
        chunk = re.sub(r" +", " ", chunk)
        print(f"\n===== {marker} hit {n+1} =====")
        print(chunk[:700])
        n += 1

# all FProc procedures
print("\n===== FProc units =====")
for m in re.finditer(r"FProc_[A-Za-z0-9_]+", t):
    pass
for name in sorted(set(re.findall(r"FProc_[A-Za-z0-9_]+", t))):
    print(name)

# block names from oracle forms
for name in sorted(set(re.findall(r"\b[A-Z]{2,}_[A-Z0-9_]+\b", t))):
    if any(k in name for k in ["JV", "HDR", "DTL", "TLB", "BLOCK", "VOUCH", "CTRL", "PARAM"]):
        if len(name) < 30:
            pass
blocks = sorted(
    {
        x
        for x in re.findall(
            r"(?:BLOCK|block)\s+([A-Z0-9_]+)|([A-Z]{2,15})\s+(?:BLOCK|Block)",
            t,
        )
        for x in x
        if x
    }
)
# simpler: search TH_JV TD_JV block patterns
for pat in ["TH_JV", "TD_JV", "TLB", "CONTROL", "PARAM", "TOOLBAR", "BLOCK"]:
    hits = sorted(set(re.findall(rf"[A-Z_]{{2,20}}{pat}[A-Z_]{{0,15}}", t)))
    if hits:
        print(f"\n{pat} names:", hits[:20])

# UI labels
labels = [
    "Voucher No",
    "Voucher Date",
    "Tran Type",
    "Ref No",
    "Narration",
    "Total Amount",
    "Dr/Cr",
    "Debit",
    "Credit",
    "Zonal",
    "Allocation",
    "Save",
    "Print",
    "Delete",
    "Query",
    "Exit",
    "New",
    "Summary of Journal",
    "Manual Entry",
    "Sl No",
    "Remarks",
    "Amount",
    "Year",
    "Month",
    "Fin Year",
    "Post",
]
print("\n===== UI labels =====")
for lb in labels:
    if lb.lower() in t.lower():
        print(" +", lb)

# longer SQL
strings = re.findall(rb"[\x20-\x7e]{40,}", open("d:/SMPK/FI_PN_T_H_JRVOUCHR_E.fmb", "rb").read())
seen = set()
print("\n===== SQL fragments =====")
for s in strings:
    txt = s.decode("ascii")
    if "FI_PN" in txt and any(k in txt.upper() for k in ["JV", "PNJV", "JOURN", "VOUCH"]):
        key = txt[:120]
        if key in seen:
            continue
        seen.add(key)
        if "SELECT" in txt.upper() or "INSERT" in txt.upper() or "UPDATE" in txt.upper() or "DELETE" in txt.upper():
            print("---")
            print(txt[:800])
