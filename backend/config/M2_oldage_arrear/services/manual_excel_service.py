"""
Parse M2 manual-entry Excel.

Employee sheet:
  EMP_CD, PENSIONER_NAME, ROLL_NO, CASE_NO, Category,
  DATE_OF_BIRTH, DATE_OF_RETIREMENT, TQS, DESG, LAST PAY,
  PAY_SCALE, M-I_277 / M1_277, M-I_359

Family pension sheet:
  EMP_CD, PENSIONER_NAME, DATE_OF_RETIREMENT, DATE_OF_BIRTH,
  DATE_OF_DEATH, FAMILY_PENSIONER_NAME, CASE_NO, ROLL_NO, Category,
  DATE_OF_BIRTH_FAMILY_PENSIONER, TQS, DESIG, LAST PAY,
  NPA (FOR DOCTORS), PAY_SCALE, M1_277
"""

from __future__ import annotations

import re
from datetime import date, datetime, timedelta
from io import BytesIO
from pathlib import Path

import pandas as pd

from methodology2.services.bulk_excel_service import _clean_emp_cd, _clean_text


def normalize_manual_emp_cd(raw) -> str | None:
    """
    Same key as manual bulk processing (5-digit EMP_CD).

    Handles Excel values like 2053, 02053, 02053K / 02053k (suffix letter).
    """
    base = _clean_emp_cd(raw)
    if not base:
        return None
    text = str(base).strip().upper()
    if text.isdigit():
        return text.zfill(5)[:5]
    m = re.match(r"^(\d{1,5})", text)
    if m:
        return m.group(1).zfill(5)[:5]
    return text[:5]


def _manual_header(name) -> str:
    """Lower-case header with punctuation and apostrophes removed."""
    text = str(name or "").strip().lower()
    text = text.replace("\u2019", "").replace("'", "").replace("`", "")
    text = re.sub(r"[^a-z0-9]+", "_", text).strip("_")
    return text


def _col_map(df: pd.DataFrame) -> dict[str, str]:
    return {_manual_header(c): c for c in df.columns}


def _find_col(cmap: dict[str, str], *keys: str) -> str | None:
    for key in keys:
        if key in cmap:
            return cmap[key]
    # fuzzy: ignore extra underscores
    compact = {k.replace("_", ""): v for k, v in cmap.items()}
    for key in keys:
        ck = key.replace("_", "")
        if ck in compact:
            return compact[ck]
    return None


def _as_date(raw) -> date | None:
    if raw is None:
        return None
    try:
        if pd.isna(raw):
            return None
    except (TypeError, ValueError):
        pass
    if isinstance(raw, datetime):
        return raw.date()
    if isinstance(raw, date):
        return raw
    if isinstance(raw, (int, float)):
        # Excel serial date
        try:
            n = int(raw)
            if n > 20000:  # ~1954+
                return (datetime(1899, 12, 30) + timedelta(days=n)).date()
        except (TypeError, ValueError, OverflowError):
            pass
        return None
    text = str(raw).strip()
    if not text or text.lower() == "nan":
        return None
    # numeric string serial
    if re.fullmatch(r"\d+(\.0+)?", text):
        try:
            n = int(float(text))
            if n > 20000:
                return (datetime(1899, 12, 30) + timedelta(days=n)).date()
        except (TypeError, ValueError, OverflowError):
            pass
    for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%Y/%m/%d", "%d-%b-%Y"):
        try:
            return datetime.strptime(text[:20], fmt).date()
        except ValueError:
            continue
    # pandas Timestamp string
    try:
        ts = pd.to_datetime(text, dayfirst=True, errors="coerce")
        if pd.notna(ts):
            return ts.date()
    except Exception:
        pass
    return None


def _as_float(raw) -> float | None:
    if raw is None or (isinstance(raw, float) and pd.isna(raw)):
        return None
    text = str(raw).strip().replace(",", "")
    if not text or text.lower() == "nan":
        return None
    try:
        return float(text)
    except ValueError:
        return None


def _parse_tqs(text: str) -> tuple[int | None, int | None, int | None]:
    raw = str(text or "").strip()
    if not raw:
        return None, None, None
    y = m = d = None
    ym = re.search(r"(\d+)\s*Y", raw, re.I)
    mm = re.search(r"(\d+)\s*M", raw, re.I)
    dm = re.search(r"(\d+)\s*D", raw, re.I)
    if ym or mm or dm:
        if ym:
            y = int(ym.group(1))
        if mm:
            m = int(mm.group(1))
        if dm:
            d = int(dm.group(1))
        return y, m, d
    parts = re.findall(r"\d+", raw)
    if len(parts) == 3 and all(len(part) <= 5 for part in parts):
        return int(parts[0]), int(parts[1]), int(parts[2])
    return None, None, None


def _normalize_category(raw) -> str:
    """Map category; Excel paste often gives 3.0 / '3.0'."""
    if raw is None:
        return ""
    try:
        if isinstance(raw, float) and raw != raw:  # NaN
            return ""
    except Exception:
        pass
    if isinstance(raw, (int, float)) and not isinstance(raw, bool):
        try:
            if float(raw) == int(raw):
                raw = int(raw)
        except (ValueError, OverflowError):
            pass

    text = str(raw or "").strip().upper()
    m = re.fullmatch(r"(\d+)\.0+", text)
    if m:
        text = m.group(1)

    mapping = {
        "1": "1",
        "I": "1",
        "2": "2",
        "II": "2",
        "3": "3",
        "III": "3",
        "4": "4",
        "IV": "4",
    }
    if text in mapping:
        return mapping[text]
    # "CLASS 3" / "Class-III" → keep leading digit only when single 1–4
    digits = re.sub(r"\D", "", text)
    if len(digits) == 1 and digits in mapping:
        return mapping[digits]
    return text


def _excel_marks_family(row: dict) -> bool:
    """Family when the sheet says so, or when a family-pensioner column is filled."""
    kind = str(row.get("pension_type") or "").strip().upper()
    if kind in {"F", "FAMILY", "FP", "FAMILY PENSION", "FAMILY PENSIONER"}:
        return True
    if kind in {
        "P",
        "E",
        "EMP",
        "EMPLOYEE",
        "EMPLOYEE PENSION",
        "EMPLOYEE PENSIONER",
    }:
        return False
    dod = row.get("date_of_death")
    fp_dob = row.get("family_pensioner_dob")
    try:
        if dod is not None and pd.isna(dod):
            dod = None
        if fp_dob is not None and pd.isna(fp_dob):
            fp_dob = None
    except (TypeError, ValueError):
        pass
    if dod:
        return True
    if str(row.get("family_pensioner_name") or "").strip():
        return True
    if fp_dob:
        return True
    return False


def read_manual_rows_from_excel(source) -> list[dict]:
    """
    Read full manual-entry rows from M2_BULK-style Excel.

    Raises ValueError when EMP_CD column missing or no usable rows.
    """
    if isinstance(source, (str, Path)):
        df = pd.read_excel(source)
    elif isinstance(source, (bytes, bytearray)):
        df = pd.read_excel(BytesIO(source))
    else:
        df = pd.read_excel(source)

    if df is None or df.empty:
        raise ValueError("Excel has no data rows")

    cmap = _col_map(df)
    emp_col = _find_col(cmap, "emp_cd")
    if not emp_col:
        raise ValueError(
            "Excel must include EMP_CD "
            f"(found: {', '.join(str(c) for c in df.columns)})"
        )

    name_col = _find_col(
        cmap,
        "employee_name",
        "pensioner_name",
        "name",
        "emp_name",
        "name_of_employee",
        "name_of_pensioner",
    )
    roll_col = _find_col(cmap, "roll_no", "pension_roll_no", "roll")
    case_col = _find_col(cmap, "case_no", "ca_number", "case", "caseno")
    cat_col = _find_col(cmap, "category", "class", "emp_class")
    dob_col = _find_col(cmap, "date_of_birth", "dob", "birth_date")
    dor_col = _find_col(
        cmap, "date_of_retirement", "retirement_date", "dor", "separation_date"
    )
    tqs_col = _find_col(cmap, "tqs", "total_qualifying_service")
    desg_col = _find_col(cmap, "desg", "desig", "designation", "designation_name")
    pay_col = _find_col(cmap, "last_pay", "lastpay", "last_basic", "last_pay_drawn")
    npa_col = _find_col(
        cmap,
        "npa_(for_doctors)",
        "npa_for_doctors",
        "npa",
        "npa_amount",
        "npa_for_doctor",
    )
    scale_col = _find_col(cmap, "pay_scale", "scale", "payscale")
    m1_277_col = _find_col(
        cmap,
        "m-i_277",
        "m-i__277",
        "mi_277",
        "m1_277",
        "m_i_277",
        "methodology1_277",
    )
    m1_359_col = _find_col(
        cmap, "m-i_359", "mi_359", "m1_359", "m_i_359", "methodology1_359"
    )
    m2_277_col = _find_col(
        cmap,
        "m-ii_277",
        "m-ii__277",
        "mii_277",
        "m2_277",
        "m_ii_277",
        "methodology2_277",
    )
    m2_359_col = _find_col(
        cmap,
        "m-ii_359",
        "m-ii__359",
        "mii_359",
        "m2_359",
        "m_ii_359",
        "methodology2_359",
    )
    dod_col = _find_col(
        cmap,
        "date_of_death",
        "dod",
        "dod_of_employee",
        "death_date",
        "date_of_death_of_employee",
    )
    fp_name_col = _find_col(
        cmap,
        "family_pensioner_name",
        "family_pensioners_name",
        "family_pensioner_s_name",
        "name_of_family_pensioner",
        "family_pensioner",
        "fp_name",
    )
    fp_dob_col = _find_col(
        cmap,
        "family_pensioner_dob",
        "date_of_birth_family_pensioner",
        "dob_of_family_pensioner",
        "date_of_birth_of_family_pensioner",
        "dob_family_pensioner",
        "family_dob",
        "fp_dob",
    )
    pension_type_col = _find_col(
        cmap, "pension_type", "pensioner_type", "type_of_pension"
    )
    # This header may mix normal pensioners and family pensioners.
    # A row is family only when that row has a family value, not because
    # the column exists for other employees.

    seen: set[str] = set()
    out: list[dict] = []
    for _, row in df.iterrows():
        emp = normalize_manual_emp_cd(row.get(emp_col))
        if not emp or emp in seen:
            continue
        seen.add(emp)
        tqs_text = _clean_text(row.get(tqs_col)) if tqs_col else ""
        tqs_yr, tqs_mo, tqs_dy = _parse_tqs(tqs_text)
        parsed = {
            "emp_cd": emp,
            "name": _clean_text(row.get(name_col)) if name_col else "",
            "roll_no": _clean_text(row.get(roll_col)) if roll_col else "",
            "case_no": _clean_text(row.get(case_col)) if case_col else "",
            "category": _normalize_category(
                row.get(cat_col) if cat_col else ""
            ),
            "date_of_birth": _as_date(row.get(dob_col) if dob_col else None),
            "retirement_date": _as_date(row.get(dor_col) if dor_col else None),
            "tqs": tqs_text,
            "tqs_yr": tqs_yr,
            "tqs_month": tqs_mo,
            "tqs_days": tqs_dy,
            "designation": _clean_text(row.get(desg_col)) if desg_col else "",
            "last_pay": _as_float(row.get(pay_col) if pay_col else None),
            "npa_amount": _as_float(row.get(npa_col) if npa_col else None),
            "scale": _clean_text(row.get(scale_col)) if scale_col else "",
            "m1_277": _as_float(row.get(m1_277_col) if m1_277_col else None),
            "m1_359": _as_float(row.get(m1_359_col) if m1_359_col else None),
            "m2_277": _as_float(row.get(m2_277_col) if m2_277_col else None),
            "m2_359": _as_float(row.get(m2_359_col) if m2_359_col else None),
            "date_of_death": _as_date(row.get(dod_col) if dod_col else None),
            "family_pensioner_name": (
                _clean_text(row.get(fp_name_col)) if fp_name_col else ""
            ),
            "family_pensioner_dob": _as_date(
                row.get(fp_dob_col) if fp_dob_col else None
            ),
            "pension_type": (
                _clean_text(row.get(pension_type_col)) if pension_type_col else ""
            ),
        }
        if _excel_marks_family(parsed):
            parsed["is_employee_pension"] = False
            if not str(parsed.get("pension_type") or "").strip():
                parsed["pension_type"] = "F"
        else:
            parsed["is_employee_pension"] = True
        out.append(parsed)

    if not out:
        raise ValueError("No EMP_CD values found in Excel")
    return out
