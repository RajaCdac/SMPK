from pathlib import Path
import re

d = Path("d:/SMPK/FI_PN_MH_PENSION_PROPOSAL_E.fmb").read_bytes().decode(
    "latin-1", errors="ignore"
)

# All BLKBT_ENTRY items
items = sorted(set(re.findall(r"BLKBT_ENTRY\.([A-Z0-9_]{3,40})", d, re.I)))
items_lower = sorted(set(re.findall(r"blkbt_entry\.([a-z0-9_]{3,40})", d)))

out = ["=== BLKBT_ENTRY items (sample held/dcr/grat) ==="]
for x in items + items_lower:
    xl = x.lower()
    if any(k in xl for k in ("held", "grat", "dcr", "withhold", "reason", "commu", "letter", "acept")):
        out.append(x)

out.append("\n=== Search DCR / REASON / WITHHOLD strings ===")
for kw in ["DCR_TYPE", "dcr_type", "REASONS_TO", "WITHHOLD", "Reasons to", "Held Up", "HELD_COMMU", "LETTER_NO", "ACEPTED"]:
    i = d.find(kw)
    out.append(f"{kw}: {i}")

# Find all form labels (readable strings 8-40 chars near list options)
out.append("\n=== Labels containing Reason or Held ===")
for m in re.finditer(r"[A-Za-z][A-Za-z0-9 /&\.]{6,45}", d):
    s = m.group()
    if "held" in s.lower() or "withhold" in s.lower() or "reason" in s.lower():
        if s not in out[-20:]:
            out.append(s)

# WHEN-VALIDATE on dcr
for m in re.finditer(r"WHEN-VALIDATE-ITEM \(BLKBT_ENTRY\.([^)]+)\)", d):
    item = m.group(1)
    if any(k in item.upper() for k in ("HELD", "DCR", "GRAT", "WITH")):
        out.append(f"VALIDATE: {item}")

Path("scripts/_tmp_items.txt").write_text("\n".join(out[:80]), encoding="utf-8")
print("lines", len(out))
