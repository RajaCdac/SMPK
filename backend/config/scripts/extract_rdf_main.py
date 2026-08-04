import os
import re
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

data = open(r"D:\SMPK\BILL_REPORT_Com.RDF", "rb").read().decode("latin1", "ignore")

# pull the main query blob
idx = data.lower().find("select 1 as tag")
if idx >= 0:
    chunk = data[idx : idx + 2500]
    chunk = re.sub(r"[\x00-\x1f]", " ", chunk)
    chunk = " ".join(chunk.split())
    print("MAIN QUERY CHUNK:")
    print(chunk[:2000])

print("\n=== LABELS / FRAMES ===")
for s in re.findall(r"[\x20-\x7e]{4,}", data):
    if any(
        x in s
        for x in [
            "Total",
            "Gross",
            "Dedn",
            "Earn",
            "Commut",
            "Nominee",
            "Relation",
            "Amount",
            "Original",
            "Arear",
            "Page",
            "Run Date",
            "Financial",
            "Sr.",
            "Officer",
            "KOLKATA",
            "SYAMA",
            "MOOKERJEE",
        ]
    ):
        if len(s) < 80 and "function" not in s.lower():
            print(s)
