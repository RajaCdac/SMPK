from pathlib import Path
d = Path("d:/SMPK/FI_PN_MH_PENSION_PROPOSAL_E.fmb").read_bytes().decode(
    "latin-1", errors="ignore"
)

# canvas field list area
out = []
out.append("=== Field list @ 497575 ===")
out.append(d[497200:498200].replace("\x00", "|"))

out.append("\n=== Held Up area @ 499500 ===")
out.append(d[499500:500500].replace("\x00", "|"))

# Find all BLKBT_ENTRY column bindings - search DATABASE column patterns
import re
cols = sorted(set(re.findall(r"FI_PN_MH_PENSION_PROPOSAL\.([A-Z_]{3,30})", d, re.I)))
out.append("\n=== Table columns referenced in FMB ===")
out.append("\n".join(cols))

Path("scripts/_tmp_layout.txt").write_text("\n".join(out), encoding="utf-8")
