import re
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

with open("d:/SMPK/FI_PN_TD_JV_RPT.fmb", "rb") as f:
    t = f.read().decode("latin-1", errors="ignore")

print("file size", len(t))

# Report / run product
for pat in ["RUN_PRODUCT", "REPORT", "report_name", "FI_PN_TD_JV", "parameter", "WHEN-BUTTON", "FProc", "FPROC"]:
    idx = 0
    n = 0
    while n < 8:
        idx = t.upper().find(pat.upper(), idx + 1)
        if idx < 0:
            break
        chunk = re.sub(
            r" +",
            " ",
            "".join(c if 32 <= ord(c) < 127 else " " for c in t[idx - 40 : idx + 280]),
        )
        if len(chunk.strip()) > 15:
            print(f"\n[{pat}] {chunk[:280]}")
        n += 1

# Blocks
blocks = sorted(set(re.findall(r"BLK[A-Z0-9_]+", t)))
print("\nBLOCKS:", blocks)

# Item/field labels
strings = re.findall(r"[\x20-\x7e]{5,80}", t)
labels = []
for s in strings:
    sl = s.strip().lower()
    if any(
        k in sl
        for k in [
            "voucher", "journal", "summary", "debit", "credit", "zonal",
            "alloc", "narration", "ref", "tran", "amount", "report", "print",
            "fa no", "post", "bill",
        ]
    ):
        if "FPROC" not in s and not s.startswith("BLK") and "SELECT" not in s:
            labels.append(s.strip())
for s in sorted(set(labels))[:80]:
    print("label:", s)

# SQL queries
for m in re.finditer(r"SELECT.{20,400}FROM.{10,80}", t, re.I | re.S):
    q = re.sub(r"\s+", " ", m.group(0))
    if "JV" in q.upper() or "JOURNAL" in q.upper():
        print("\nSQL:", q[:350])
