from pathlib import Path
import re

d = Path("d:/SMPK/FI_PN_MH_PENSION_PROPOSAL_E.fmb").read_bytes().decode(
    "latin-1", errors="ignore"
)

# Find WHEN-VALIDATE and prompts for QUARTER_STATUS
i = d.find("QUARTER_STATUS")
out = [d[i - 800 : i + 1200].replace("\x00", "|")]

# All BLKBT_ENTRY items with validate triggers
validates = re.findall(
    r"WHEN-VALIDATE-ITEM \(BLKBT_ENTRY\.([^)]+)\)", d, re.I
)
out.append("\n=== VALIDATE items ===")
out.append("\n".join(validates))

# Search quarter_status lowercase item
for m in re.finditer(r"quarter_status", d, re.I):
    out.append(f"\nquarter_status @ {m.start()}")
    out.append(d[m.start() - 100 : m.start() + 200].replace("\x00", "|"))

Path("scripts/_tmp_quarter.txt").write_text("\n".join(out[:5]), encoding="utf-8")
print("done")
