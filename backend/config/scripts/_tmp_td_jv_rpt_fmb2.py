import re
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

with open("d:/SMPK/FI_PN_TD_JV_RPT.fmb", "rb") as f:
    t = f.read().decode("latin-1", errors="ignore")

# PARAM block fields
for m in re.finditer(r"PARAM\.([A-Z0-9_]+)", t):
    pass
print("PARAM fields:", sorted(set(re.findall(r"PARAM\.([A-Z0-9_]+)", t, re.I))))

# FinYr Mth
for pat in ["FinYr", "FINYR", "Fin_Yr", ":PARAM.YR", ":PARAM.MTH", "P_YR", "P_MTH", "P_REF"]:
    idx = t.find(pat)
    if idx >= 0:
        chunk = re.sub(r" +", " ", t[idx - 30 : idx + 120])
        print(pat, ":", chunk[:140])

# Full RG_BILL query
idx = t.find("RG_BILL")
if idx >= 0:
    chunk = "".join(c if 32 <= ord(c) < 127 else " " for c in t[idx : idx + 500])
    print("\nRG_BILL:", chunk)

# WHEN-NEW-FORM-INSTANCE
idx = t.find("WHEN-NEW-FORM-INSTANCE")
if idx >= 0:
    chunk = "".join(c if c in "\n\r\t" or 32 <= ord(c) < 127 else "\n" for c in t[idx : idx + 1500])
    import re as R
    print("\nFORM INIT:\n", R.sub(r"\n{3,}", "\n\n", chunk)[:1200])

# canvas text
for s in sorted(set(re.findall(r"[\x20-\x7e]{4,50}", t))):
    if any(k in s for k in ["Summary", "Journal", "Year", "Month", "Bill", "Voucher", "FA No"]):
        if "PARAM" not in s and "SELECT" not in s:
            print("txt:", s)
