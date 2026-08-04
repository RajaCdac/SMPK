import re
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

with open("d:/SMPK/FI_PN_BILL_ABSTRACT.rdf", "rb") as f:
    t = f.read().decode("latin-1", errors="ignore")

# find Q_2 select - search for long SQL near earn dedn
patterns = [
    r"select[\s\S]{100,4000}Ord_By[\s\S]{20,800}",
    r"select[\s\S]{100,4000}EarnDedn[\s\S]{20,800}",
    r"select[\s\S]{100,4000}applicant_name[\s\S]{20,800}",
    r"select[\s\S]{100,4000}FI_PN_TD_BILLPASS[\s\S]{20,800}",
]
for i, pat in enumerate(patterns):
    m = re.search(pat, t, re.I)
    if m:
        s = "".join(c if c.isprintable() else " " for c in m.group(0))
        s = re.sub(r" +", " ", s)
        print(f"\n=== pattern {i} ===")
        print(s[:2500])

# layout section titles
for title in [
    "ABSTRACT FORM FOR PENSION BILLS",
    "Memorandum of Payment",
    "Amt in Favour of Parties",
    "Details of cheque",
    "Bill Register",
    "Bill Desc",
    "Dbill Reg No",
    "Dbill Reg Dt",
    "Fbill Reg No",
    "Financial Adviser",
    "Sr. Accounts Officer",
    "Treasurer",
    "Section Officer",
    "By Cheque",
    "By Cash",
    "Total",
    "Sanction",
    "Deduction",
    "Net Amount",
]:
    if title.lower() in t.lower():
        print("title:", title)

# column headers in report
for h in [
    "SL NO",
    "Sl No",
    "Earn Dedn",
    "Sanc Amt",
    "Deduct Amt",
    "Net Amt",
    "Bill Amt",
    "Payee",
    "Party",
    "Bank Cd",
    "Branch",
    "Account No",
    "Cheque No",
    "Cheque Dt",
]:
    if h.lower() in t.lower():
        print("header:", h)
