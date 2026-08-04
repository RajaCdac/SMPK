import re
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

data = open(r"D:\SMPK\BILL_REPORT_Com.RDF", "rb").read().decode("latin1", "ignore")

# Long readable strings
strings = re.findall(r"[\x20-\x7e]{6,}", data)
seen = set()
for s in strings:
    if s in seen:
        continue
    seen.add(s)
    low = s.lower()
    if any(
        k in low
        for k in [
            "select",
            "from fi_",
            "where",
            "bill",
            "sepcom",
            "commut",
            "report",
            "kolkata",
            "port",
            "syama",
            "gross",
            "dedn",
            "earn",
            "nominee",
            "bank",
            "function",
            "formula",
            "parameter",
            "title",
            "page",
            "rupees",
            "sanction",
            "recommend",
            "abstract",
            "abst",
        ]
    ):
        if len(s) < 400:
            print(s)
            print("---")

print("\n=== LONG SQL ===")
for m in re.finditer(
    r"select.{10,1200}?where.{5,400}",
    data,
    re.I | re.S,
):
    s = re.sub(r"[\x00-\x1f]", " ", m.group())
    s = " ".join(s.split())
    if "FI_PN" in s.upper():
        print(s[:1200])
        print("---")
