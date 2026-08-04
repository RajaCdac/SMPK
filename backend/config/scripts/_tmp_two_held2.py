from pathlib import Path
import re

d = Path("d:/SMPK/FI_PN_MH_PENSION_PROPOSAL_E.fmb").read_bytes().decode(
    "latin-1", errors="ignore"
)

# Reasons to Withhold section
i = d.find("Reasons to Withhold")
print("Reasons to Withhold context:")
print(d[i : i + 1200].replace("\x00", "|")[:1200])

print("\n\nHeld Up Flg context:")
i2 = d.find("Held Up Flg")
print(d[i2 - 100 : i2 + 600].replace("\x00", "|"))

# Find item names bound to columns
for pat in [
    r"held_grat_flg",
    r"held_up_flg",
    r"reasons_to_withhold",
    r"withhold",
    r"held_grat_amt",
    r"dcr_type",
]:
    print(f"\n{pat} occurrences:", len(re.findall(pat, d, re.I)))

# PL/SQL referencing both
for m in re.finditer(r".{0,40}(held_up|held_grat|withhold).{0,60}", d, re.I):
    s = m.group().replace("\n", " ")
    if "BLKBT" in s or "FPROC" in s or "set_item" in s.lower() or " in (" in s:
        print("PLSQL:", s[:140])
