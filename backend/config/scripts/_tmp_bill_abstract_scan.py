import re
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def scan_file(path, label):
    print(f"\n{'='*60}\n{label}: {path}\n{'='*60}")
    with open(path, "rb") as f:
        t = f.read().decode("latin-1", errors="ignore")

    fields = sorted(
        set(
            re.findall(
                r"(TXT_[A-Z_]+|ABSTRACT_[A-Z]+|PB_[A-Z_]+|BILL_LOV|PARAM\.[A-Z_]+)",
                t,
            )
        )
    )
    print("FIELDS/BUTTONS:", fields)

    procs = sorted(set(re.findall(r"PROCEDURE\s+([A-Za-z0-9_]+)", t)))
    if procs:
        print("PROCEDURES:", procs)

    tables = sorted(set(re.findall(r"FI_PN_[A-Z0-9_]+", t)))
    print(f"TABLES ({len(tables)}):")
    for x in tables:
        print(" ", x)

    sqls = []
    for m in re.finditer(
        r"(SELECT[\s\S]{20,800}?FROM[\s\S]{10,400}?)(?:;|\"|WHERE|GROUP|ORDER)",
        t,
        re.I,
    ):
        s = re.sub(r"[^\x20-\x7E]", " ", m.group(1))
        s = re.sub(r"\s+", " ", s).strip()
        if s not in sqls and "FI_PN" in s.upper():
            sqls.append(s[:350])
    print(f"\nSQL snippets ({min(len(sqls), 12)}):")
    for s in sqls[:12]:
        print(" -", s)

    for kw in [
        "BILL_ABSTRACT",
        "ABSTRACT_NO",
        "ABSTRACT_DT",
        "WHEN-BUTTON-PRESSED",
        "RUN_REPORT",
        "RDF",
        "REPORT",
    ]:
        if kw.lower() in t.lower() or kw in t:
            idx = t.upper().find(kw.upper())
            if idx >= 0:
                chunk = "".join(
                    c if c.isprintable() or c == "\n" else " " for c in t[idx : idx + 400]
                )
                chunk = re.sub(r" +", " ", chunk)
                if len(chunk.strip()) > 20:
                    print(f"\n[{kw}] {chunk[:300]}")


scan_file("d:/SMPK/FI_PN_BILL_ABSTRACT_RPT.fmb", "FMB")
scan_file("d:/SMPK/FI_PN_BILL_ABSTRACT.rdf", "RDF")
