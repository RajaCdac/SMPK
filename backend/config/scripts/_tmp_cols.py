from pathlib import Path
import re

raw = Path("d:/SMPK/FI_PN_MH_PENSION_PROPOSAL_E.fmb").read_bytes()
d = raw.decode("latin-1", errors="ignore")

# Oracle forms often stores column names as uppercase near item names
cols = sorted(set(re.findall(rb"[A-Z][A-Z0-9_]{4,28}", raw)))
held_cols = [c.decode() for c in cols if b"HELD" in c or b"DCR" in c or b"GRAT" in c or b"WITH" in c]
print("HELD/DCR cols in binary:", held_cols)

# item to column mapping patterns
for m in re.finditer(r"(held[a-z_]{3,20})", d, re.I):
    pass

# Search popup list item names
items = re.findall(r"\|([A-Z][A-Z0-9_]{2,25})\|", d[196000:200000])
print("items near HELD_GRAT:", items[:30])

# Look for two list definitions - count list elements for held
i = d.find("Held Up Flg")
chunk = d[i : i + 2000]
# split labels in chunk
labels = [
    "Not Appl", "Gratuity Full", "Gratuity Partial", "Pension", "Relief",
    "Commutation", "Quater Clearence", "Electricity Clearence",
    "Co-Operative Credit Society", "Court Attachement",
]
for lab in labels:
    print(lab, chunk.find(lab))
