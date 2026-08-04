import re
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

with open("d:/SMPK/FI_PN_BILL_ABSTRACT.rdf", "rb") as f:
    t = f.read().decode("latin-1", errors="ignore")

# Q_2
idx = t.find("Q_2")
if idx >= 0:
    chunk = t[idx : idx + 5000]
    chunk = "".join(c if c.isprintable() else "\n" for c in chunk)
    for m in re.finditer(r"select[\s\S]{30,2000}from[\s\S]{30,1200}", chunk, re.I):
        s = re.sub(r"\n+", " ", m.group(0))
        s = re.sub(r" +", " ", s)
        print("Q_2 SQL:", s[:1500])
        break

# main Q_1 - already found
m = re.search(
    r"seleCT A\.DBILL_REG_NO[\s\S]{20,500}v_bill_no",
    t,
    re.I,
)
if m:
    print("\nQ_1 MAIN:")
    print(re.sub(r" +", " ", m.group(0)))

# cheque / payee fields
for pat in [
    r"CHEQUE[^\"]{0,80}",
    r"F_PAYEE[^\"]{0,80}",
    r"PAYEE_NAME[^\"]{0,80}",
    r"G_FBILL[^\"]{0,80}",
    r"F_BILL_AMT[^\"]{0,80}",
    r"F_SANC_AMT[^\"]{0,80}",
    r"BILL_MONTH[^\"]{0,80}",
    r"MTH[^\"]{0,40}",
]:
    for m in re.finditer(pat, t, re.I):
        s = re.sub(r" +", " ", m.group(0))[:100]
        if s not in getattr(sys, "_seen", set()):
            print("field:", s)

# CF_rendered full text
m = re.search(r"function CF_renderedFormula[\s\S]{100,3500}end;", t, re.I)
if m:
    txt = m.group(0)
    txt = re.sub(r"[^\x20-\x7e\n]", " ", txt)
    txt = re.sub(r" +", " ", txt)
    print("\nCF_RENDERED (trunc):")
    print(txt[:2500])
