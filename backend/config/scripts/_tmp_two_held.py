from pathlib import Path
import re

d = Path("d:/SMPK/FI_PN_MH_PENSION_PROPOSAL_E.fmb").read_bytes().decode(
    "latin-1", errors="ignore"
)

out = []

for kw in ["Reasons to Withhold", "Held Up Flg", "HELD_GRAT_FLG", "HELD_UP_FLG"]:
    i = d.find(kw)
    out.append(f"\n=== {kw} @ {i} ===")
    if i >= 0:
        seg = d[max(0, i - 300) : i + 800]
        out.append(seg.replace("\x00", "|"))

# all HELD_* column/item names
for m in re.finditer(r"HELD_[A-Z_]{3,30}", d):
    s = m.group()
    if s not in out:
        pass
held_items = sorted(set(re.findall(r"HELD_[A-Z_]{3,25}", d)))
out.append("\n=== HELD_* tokens ===")
out.append("\n".join(held_items[:40]))

# BLKBT_ENTRY items with held
for m in re.finditer(r"BLKBT_ENTRY\.(held[a-z_]{3,25})", d, re.I):
    pass
blk = sorted(set(re.findall(r"blkbt_entry\.([a-z_]{3,30})", d, re.I)))
held_blk = [x for x in blk if "held" in x.lower() or "grat" in x.lower()]
out.append("\n=== blkbt_entry held/grat items ===")
out.append("\n".join(held_blk))

Path("scripts/_tmp_two_held.txt").write_text("\n".join(out), encoding="utf-8")
print("written", len(out))
