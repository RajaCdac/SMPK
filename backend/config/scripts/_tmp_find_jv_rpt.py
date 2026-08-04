import re
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# Search all FMBs for JV report references
import glob

for path in glob.glob("d:/SMPK/*.fmb"):
    with open(path, "rb") as f:
        t = f.read().decode("latin-1", errors="ignore")
    if "TD_JV" in t or "JV_RPT" in t or "JOURNAL" in t.upper():
        hits = []
        for m in re.finditer(r"FI_[A-Z0-9_]{5,40}", t):
            s = m.group(0)
            if "JV" in s or "JOUR" in s or "RPT" in s:
                hits.append(s)
        if hits:
            print(path, sorted(set(hits))[:30])
