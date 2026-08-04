"""Parse bulk Excel: require EMP_CD; optional case_no / roll_no."""

from __future__ import annotations

from io import BytesIO
from pathlib import Path

import pandas as pd


def _normalize_header(name) -> str:
    return str(name or "").strip().lower().replace(" ", "_")


def _clean_emp_cd(raw) -> str | None:
    if raw is None or (isinstance(raw, float) and pd.isna(raw)):
        return None
    emp = str(raw).strip()
    if not emp or emp.lower() == "nan":
        return None
    if emp.endswith(".0") and emp[:-2].isdigit():
        emp = emp[:-2]
    if emp.isdigit() and len(emp) < 5:
        emp = emp.zfill(5)
    if emp.isdigit() and len(emp) > 5:
        emp = emp[:5]
    return emp


def _clean_text(raw) -> str:
    if raw is None or (isinstance(raw, float) and pd.isna(raw)):
        return ""
    text = str(raw).strip()
    if not text or text.lower() == "nan":
        return ""
    if text.endswith(".0") and text[:-2].replace("-", "").isdigit():
        text = text[:-2]
    return text


def read_emp_rows_from_excel(source) -> list[dict]:
    """
    Read unique EMP_CD rows from Excel.

    Returns list of {"emp_cd": str, "case_no": str, "roll_no": str}.
    Optional columns: case_no / CA_NUMBER, roll_no.
    Raises ValueError if EMP_CD column is missing or no usable rows.
    """
    if isinstance(source, (str, Path)):
        df = pd.read_excel(source, dtype=str)
    elif isinstance(source, (bytes, bytearray)):
        df = pd.read_excel(BytesIO(source), dtype=str)
    else:
        df = pd.read_excel(source, dtype=str)

    if df is None or df.empty:
        raise ValueError("Excel has no data rows")

    rename = {_normalize_header(c): c for c in df.columns}
    if "emp_cd" not in rename:
        raise ValueError(
            "Excel must include a column named EMP_CD "
            f"(found: {', '.join(str(c) for c in df.columns)})"
        )

    emp_col = rename["emp_cd"]
    case_col = None
    for key in ("case_no", "ca_number", "case", "caseno"):
        if key in rename:
            case_col = rename[key]
            break
    roll_col = None
    for key in ("roll_no", "pension_roll_no", "roll"):
        if key in rename:
            roll_col = rename[key]
            break

    seen = set()
    out: list[dict] = []
    for _, row in df.iterrows():
        emp = _clean_emp_cd(row.get(emp_col))
        if not emp or emp in seen:
            continue
        seen.add(emp)
        out.append(
            {
                "emp_cd": emp,
                "case_no": _clean_text(row.get(case_col)) if case_col else "",
                "roll_no": _clean_text(row.get(roll_col)) if roll_col else "",
            }
        )

    if not out:
        raise ValueError("No EMP_CD values found in Excel")
    return out


def read_emp_cds_from_excel(source) -> list[str]:
    """Backward-compatible list of EMP_CD strings."""
    return [r["emp_cd"] for r in read_emp_rows_from_excel(source)]
