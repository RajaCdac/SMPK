from pathlib import Path
d = Path("d:/SMPK/FI_PN_MH_PENSION_PROPOSAL_E.fmb").read_bytes().decode(
    "latin-1", errors="ignore"
)
out = []
idx = 0
while True:
    i = d.find("Withhold", idx)
    if i < 0:
        break
    out.append(f"--- {i} ---")
    out.append(d[i - 120 : i + 200].replace("\x00", "|"))
    idx = i + 1

# Search for second list item - maybe item name differs
for pat in ["REASON", "reason", "WHY", "CLR", "CLEAR"]:
    out.append(f"{pat}: {d.find(pat)}")

Path("scripts/_tmp_withhold.txt").write_text("\n".join(out), encoding="utf-8")
