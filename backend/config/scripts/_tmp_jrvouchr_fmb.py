import re
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

with open("d:/SMPK/FI_PN_T_H_JRVOUCHR_E.fmb", "rb") as f:
    t = f.read().decode("latin-1", errors="ignore")

print("=== FORM TITLE / MODULE ===")
for s in [
    "MANUAL",
    "JOURNAL",
    "VOUCHER",
    "SUMMARY",
    "PNJV",
    "FI_PN_TH_JV",
    "FI_PN_TD_JV",
    "JRVOUCHR",
]:
    if s.lower() in t.lower():
        print(" +", s)

# blocks
blocks = sorted(set(re.findall(r"BLOCK_[A-Z0-9_]+", t)))
print("\n=== BLOCKS ===", blocks[:40])

# parameters / items
for pat in [
    r"PARAM\.[A-Z0-9_]+",
    r"VOUCHER_NO",
    r"VOUCHER_DT",
    r"TRAN_TYPE",
    r"REF_NO",
    r"NARRATION",
    r"DR_CR",
    r"ALOC",
    r"ZONAL",
    r"TOT_AMT",
    r"SL_NO",
    r"PB_[A-Z_]+",
    r"WHEN-BUTTON",
    r"WHEN-NEW-FORM",
    r"KEY-COMMIT",
    r"PRE-INSERT",
    r"PRE-UPDATE",
    r"POST-FORMS-COMMIT",
]:
    hits = sorted(set(re.findall(pat, t, re.I)))
    if hits:
        print(f"\n=== {pat} ({len(hits)}) ===")
        for h in hits[:25]:
            print(" ", h)

# procedures / program units
for m in re.finditer(
    r"(procedure|function)\s+([A-Za-z0-9_]+)",
    t,
    re.I,
):
    name = m.group(2)
    if any(
        k in name.upper()
        for k in ["JV", "VOUCH", "JOURN", "SAVE", "DELETE", "PRINT", "SUMM", "MANUAL", "QUERY"]
    ):
        print("unit:", name)

# SQL strings
strings = re.findall(rb"[\x20-\x7e]{30,}", open("d:/SMPK/FI_PN_T_H_JRVOUCHR_E.fmb", "rb").read())
seen = set()
print("\n=== SQL (sample) ===")
for s in strings:
    t2 = s.decode("ascii")
    if "FI_PN" in t2 and ("select" in t2.lower() or "from" in t2.lower() or "insert" in t2.lower()):
        key = t2[:100]
        if key not in seen:
            seen.add(key)
            if any(k in t2.upper() for k in ["JV", "VOUCH", "JOURN", "PNJV"]):
                print("---")
                print(t2[:500])
