"""Extract program units and tables from Oracle Forms .fmb binary."""
import re
import sys
from pathlib import Path


def main():
    path = Path(sys.argv[1] if len(sys.argv) > 1 else "FI_PN_FIRST_PENSION_PROCESS.fmb")
    data = path.read_bytes()
    texts = [s.decode("ascii", "ignore") for s in re.findall(rb"[\x20-\x7e]{4,}", data)]

    procs = set()
    funcs = set()
    triggers = set()
    tables = set()

    proc_re = re.compile(r"\b(FPROC_[A-Z0-9_]+)\b", re.I)
    func_re = re.compile(r"\b(FFUNC_[A-Z0-9_]+)\b", re.I)
    trig_re = re.compile(r"\b((?:PRE|POST|WHEN|ON|KEY)[-_][A-Z0-9_]+)\b", re.I)
    table_re = re.compile(r"\b(FI_[A-Z0-9_]+)\b")

    for t in texts:
        for m in proc_re.finditer(t):
            procs.add(m.group(1).upper())
        for m in func_re.finditer(t):
            funcs.add(m.group(1).upper())
        if "TRIGGER" in t.upper() and len(t) < 120:
            triggers.add(t.strip())
        for m in table_re.finditer(t):
            name = m.group(1).upper()
            if len(name) >= 8 and not name.endswith("_TYPE"):
                tables.add(name)

    # Signature blobs like "FPROC_XXX"VC_EMP_CD"...
    for t in texts:
        if t.startswith('"FPROC_') or t.startswith('"FFUNC_'):
            name = t.split('"')[1].upper()
            if name.startswith("FPROC_"):
                procs.add(name)
            elif name.startswith("FFUNC_"):
                funcs.add(name)

    print(f"FILE: {path} ({len(data)} bytes)")
    print(f"\n=== PROCEDURES ({len(procs)}) ===")
    for p in sorted(procs):
        print(p)
    print(f"\n=== FUNCTIONS ({len(funcs)}) ===")
    for f in sorted(funcs):
        print(f)
    print(f"\n=== TABLES ({len(tables)}) ===")
    for tbl in sorted(tables):
        print(tbl)

    # Dump signature lines for procedures
    print("\n=== PROCEDURE SIGNATURES ===")
    for t in texts:
        if t.startswith('"FPROC_'):
            print(t[:400])
    print("\n=== FUNCTION SIGNATURES ===")
    for t in texts:
        if t.startswith('"FFUNC_'):
            print(t[:600])

    print("\n=== MONTHLY / NOMINEE PROCS ===")
    for t in texts:
        if any(x in t for x in ("FPROC_MONTHLY", "FPROC_NOMINEE", "FI_PN_F_REFRESH")):
            if len(t) > 50:
                print(t[:700])
                print("---")

    print("\n=== FORM BLOCKS ===")
    blocks = sorted({t for t in texts if t.upper().startswith("BLK") and len(t) < 60})
    for b in blocks:
        print(b)


if __name__ == "__main__":
    main()
