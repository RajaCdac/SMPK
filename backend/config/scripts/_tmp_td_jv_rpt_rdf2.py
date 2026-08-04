import re
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

with open("d:/SMPK/FI_PN_TD_JV_RPT.RDF", "rb") as f:
    t = f.read().decode("latin-1", errors="ignore")

# Main Q_1 query chunk
idx = t.find("SELECT C.REF_NO,DECODE(C.TRAN_TYPE")
if idx < 0:
    idx = t.find("SELECT C.REF_NO")
if idx >= 0:
    chunk = "".join(c if c in "\n\r\t" or 32 <= ord(c) < 127 else " " for c in t[idx : idx + 2500])
    print(re.sub(r" +", " ", chunk))

# CF_MONTH formula
idx = t.find("CF_MONTHFormula")
if idx >= 0:
    chunk = "".join(c if c in "\n\r\t" or 32 <= ord(c) < 127 else "\n" for c in t[idx : idx + 800])
    print("\n=== CF_MONTH ===\n", re.sub(r"\n{3,}", "\n\n", chunk)[:800])

# abstract formula
for pat in ["abstract_no", "v_abst_no", "CF_ABST", "F_ABST"]:
    idx = t.find(pat)
    if idx >= 0:
        chunk = "".join(c if c in "\n\r\t" or 32 <= ord(c) < 127 else " " for c in t[idx - 50 : idx + 400])
        if "abstract" in chunk.lower():
            print(f"\n[{pat}]", re.sub(r" +", " ", chunk)[:400])

# CPT_ZONAL_DES table join
idx = t.find("FI_MA_M_H_ZONALMAP")
if idx >= 0:
    print("\nZONALMAP ctx:", re.sub(r" +", " ", t[idx - 200 : idx + 400])[:500])
