import re
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

with open("d:/SMPK/FI_PN_T_H_JRVOUCHR_E.fmb", "rb") as f:
    t = f.read().decode("latin-1", errors="ignore")

# Find PNJV/N pattern
for m in re.finditer(r"PNJV.{0,80}", t):
    s = m.group(0)
    if "N" in s and len(s) < 100:
        clean = re.sub(r"[^\x20-\x7e]", " ", s)
        if "PNJV" in clean:
            print(clean.strip())

print("\n--- tran_type ---")
for m in re.finditer(r"tran_type|TRAN_TYPE|PNJV/[A-Z]", t, re.I):
    idx = m.start()
    chunk = re.sub(r" +", " ", "".join(c if 32 <= ord(c) < 127 else " " for c in t[idx : idx + 120]))
    if "PNJV" in chunk or "tran" in chunk.lower():
        print(chunk[:120])

# FPROC_TLB_Save
idx = t.find("FProc_TLB_Save")
if idx >= 0:
    chunk = "".join(c if c in "\n\r\t" or 32 <= ord(c) < 127 else "\n" for c in t[idx : idx + 1500])
    print("\n===== SAVE =====")
    print(re.sub(r"\n{3,}", "\n\n", chunk)[:1500])

# ref_no validation - bill lookup
for pat in ["REF_NO", "FI_PN_TH_PENSION_BILL", "FI_PN_TH_BILLPASS", "POST_NO"]:
    idx = 0
    for _ in range(2):
        idx = t.find(pat, idx + 1)
        if idx < 0:
            break
        chunk = re.sub(r" +", " ", "".join(c if 32 <= ord(c) < 127 else " " for c in t[idx - 40 : idx + 180]))
        print(f"\n[{pat}] {chunk[:200]}")
