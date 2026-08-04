import re
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

with open("d:/SMPK/FI_PN_BILL_ABSTRACT.rdf", "rb") as f:
    t = f.read().decode("latin-1", errors="ignore")

for marker in ["union all", "UNION ALL", "union", "SUBSTR(B.BILL_NO,2,1)= 'P'", "SUBSTR(B.BILL_NO,2,1)='P'"]:
    positions = [m.start() for m in re.finditer(re.escape(marker), t, re.I)]
    print(f"{marker}: {len(positions)}")
    for idx in positions[:5]:
        chunk = t[max(0, idx - 200) : idx + 400]
        out = re.sub(r" +", " ", "".join(c if c in "\n\r\t" or 32 <= ord(c) < 127 else " " for c in chunk))
        print(out[:500])
        print("---")

# search pensioner in big query context
idx = t.find("FI_PN_MH_PENSIONER")
while idx >= 0:
    chunk = t[max(0, idx - 1200) : idx + 1500]
    if "Ord_By" in chunk or "Earn_Dedn" in chunk:
        out = re.sub(r" +", " ", "".join(c if c in "\n\r\t" or 32 <= ord(c) < 127 else " " for c in chunk))
        print("\n=== PENSIONER QUERY CONTEXT ===")
        print(out[:3500])
        break
    idx = t.find("FI_PN_MH_PENSIONER", idx + 1)
