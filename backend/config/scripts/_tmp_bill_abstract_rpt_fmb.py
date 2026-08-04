import re
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

with open("d:/SMPK/FI_PN_BILL_ABSTRACT_RPT.fmb", "rb") as f:
    t = f.read().decode("latin-1", errors="ignore")

# launcher pattern
for pat in ["WHEN-BUTTON-PRESSED", "RUN_PRODUCT", "REPORT", "report", "parameter", "voucher", "VOUCHER"]:
    idx = 0
    n = 0
    while n < 4:
        idx = t.find(pat, idx + 1)
        if idx < 0:
            break
        chunk = re.sub(
            r" +",
            " ",
            "".join(c if 32 <= ord(c) < 127 else " " for c in t[idx - 30 : idx + 200]),
        )
        if "REPORT" in chunk.upper() or "RUN" in chunk.upper() or "ABSTRACT" in chunk.upper():
            print(f"[{pat}] {chunk[:220]}")
        n += 1

print("\n=== block/item names ===")
for m in re.finditer(r"BLK[A-Z0-9_]{2,20}|block_name|Block", t):
    pass
blocks = sorted(set(re.findall(r"BLK[A-Z0-9_]+", t)))
print(blocks[:20])

labels = sorted(set(re.findall(r"[A-Za-z][A-Za-z0-9 /.'-]{8,50}", t)))
for s in labels:
    if any(k in s.lower() for k in ["abstract", "bill", "report", "print", "voucher"]):
        if len(s) < 45:
            print("label:", s)
