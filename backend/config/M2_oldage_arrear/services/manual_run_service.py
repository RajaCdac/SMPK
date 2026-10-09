"""
M2 manual-entry bulk: Excel supplies header + calc inputs.
Blank header cells are filled from the database, then asked one field at a time.

Output folder: Desktop/m2-manual-YYYY-MM-DD_HHMM (or BULK_OUTPUT_DIR parent).
"""

from __future__ import annotations

import csv
import json
import secrets
import shutil
import tempfile
from collections.abc import Callable
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal, ROUND_CEILING
from io import BytesIO
from pathlib import Path

import pandas as pd
from django.conf import settings

from M2_oldage_arrear.services.consolidation_bridge import (
    _attach_oldage,
    get_consolidation_snapshot,
)
from M2_oldage_arrear.services.oldage_print_columns import (
    oldage_slab_excel_dict,
    oldage_slab_excel_headers,
    oldage_slab_excel_keys,
)
from M2_oldage_arrear.services.manual_excel_service import (
    _excel_marks_family,
    normalize_manual_emp_cd,
    read_manual_rows_from_excel,
)
from methodology2.services.bulk_excel_service import _normalize_header
from methodology2.services.bulk_pdf_service import write_consolidation_files
from methodology2.services import bulk_run_service as m2_bulk

try:
    from zoneinfo import ZoneInfo

    _IST = ZoneInfo("Asia/Kolkata")
except Exception:  # pragma: no cover - Windows without tzdata
    _IST = timezone(timedelta(hours=5, minutes=30), name="IST")


def _now_ist() -> datetime:
    """Current time in Indian Standard Time (folder stamps)."""
    return datetime.now(_IST)


def _ceil_rupee_amount(value) -> int | None:
    """Match print OA rule: any fraction → next whole rupee."""
    if value is None or value == "":
        return None
    try:
        d = Decimal(str(value))
    except Exception:
        try:
            d = Decimal(str(float(value)))
        except Exception:
            return None
    return int(d.to_integral_value(rounding=ROUND_CEILING))


def default_manual_output_dir(run_at: datetime | None = None) -> Path:
    parent = Path(getattr(settings, "BULK_OUTPUT_DIR", Path.home() / "Desktop"))
    when = run_at or _now_ist()
    if when.tzinfo is None:
        when = when.replace(tzinfo=_IST)
    else:
        when = when.astimezone(_IST)
    stamp = when.strftime("%Y-%m-%d_%H%M")
    return parent / f"m2-manual-{stamp}"


# Report.xlsx — official form layout + Pension Type after Roll No
# + one old-age group per slab (from, M-I, M-II, Difference).
FORM_REPORT_HEADERS: list[str] = [
    "Name",
    "Case No (CA)",
    "Roll No.",
    "Pension Type (Employee/Family)",
    "Employee Code",
    "Retirement Date",
    "Class",
    "Designation",
    "Pay (Revised) at the time of retirement",
    "Pay Scale at the time of retirement",
    "Basic Pension amt as per M-I in 2017 (277 CPI)",
    "Revised Basic Pension amt as per M-II in 2017 (277 CPI)",
    "Beneficial under M-I or M-II? (277)",
    "Amt of Benefit (PM) Excluding DA (277)",
    "Basic Pension amt as per M-I in 2022 (359 CPI)",
    "Revised Basic Pension amt as per M-II in 2022 (359 CPI)",
    "Beneficial under M-I or M-II? (359)",
    "Amt of Benefit (PM) Excluding DA (359)",
]

# Keys on each result row matching FORM_REPORT_HEADERS order
FORM_REPORT_KEYS: list[str] = [
    "name",
    "case_no",
    "roll_no",
    "pension_type",
    "emp_cd",
    "retirement_date_display",
    "class_label",
    "designation",
    "last_pay",
    "scale",
    "m1_277",
    "m2_277",
    "beneficial_277",
    "amt_benefit_277",
    "m1_359",
    "m2_359",
    "beneficial_359",
    "amt_benefit_359",
]
FORM_REPORT_HEADERS.extend(oldage_slab_excel_headers())
FORM_REPORT_KEYS.extend(oldage_slab_excel_keys())


def _base_result(emp: str) -> dict:
    out = {
        "emp_cd": emp,
        "case_no": "",
        "roll_no": "",
        "category": "",
        "status": "failed",
        "reason": "",
        "pdf": "",
        "html": "",
        "tqs": "",
        "tqs_folder": "",
        "name": "",
        "pension_type": "",
        "retirement_date_display": "",
        "class_label": "",
        "designation": "",
        "last_pay": None,
        "scale": "",
        "m1_277": None,
        "m2_277": None,
        "beneficial_277": "",
        "amt_benefit_277": None,
        "m1_359": None,
        "m2_359": None,
        "beneficial_359": "",
        "amt_benefit_359": None,
        "old_age_benefit_m2": None,
        "old_age_benefit_m1": None,
        "old_age_benefit_diff": None,
        "old_age_benefit": None,
    }
    return out


def _class_label(category) -> str:
    cat = str(category or "").strip()
    return {"1": "I", "2": "II", "3": "III", "4": "IV"}.get(cat, cat)


def _fmt_ret_date(raw) -> str:
    d = _as_date_safe(raw)
    if d:
        return d.strftime("%d-%m-%Y")
    text = str(raw or "").strip()
    return text[:10] if text else ""


def _beneficial(m1, m2) -> tuple[str, float | None]:
    """Label which methodology is higher; amount = M2 − M1 (negative if M-I higher), as PDF."""
    if m1 is None and m2 is None:
        return "", None
    if m1 is None:
        return "M-II", None
    if m2 is None:
        return "M-I", None
    try:
        a = float(m1)
        b = float(m2)
    except (TypeError, ValueError):
        return "", None
    diff = round(b - a, 2)
    if b > a:
        return "M-II", diff
    if a > b:
        return "M-I", diff  # negative
    return "Equal", 0.0


def _signed_m2_minus_m1(m1, m2, stored_diff=None) -> float | None:
    """M2 − M1 (negative when M-I higher). Recompute when both amounts present."""
    if m1 is not None and m2 is not None:
        try:
            return round(float(m2) - float(m1), 2)
        except (TypeError, ValueError):
            pass
    return _money_or_none(stored_diff)


def _as_date_safe(raw) -> date | None:
    if raw is None or raw == "":
        return None
    if isinstance(raw, date):
        return raw
    try:
        return date.fromisoformat(str(raw)[:10])
    except Exception:
        return None


def _period_label(col: dict | None) -> str:
    """Print column header, e.g. 'In 2017 (277 CPI) — from Mar 2026 — Old age @20%'."""
    if not col:
        return ""
    lines = [str(x).strip() for x in (col.get("header_lines") or []) if str(x).strip()]
    if lines:
        return " — ".join(lines)
    header = str(col.get("header") or "").strip()
    if header:
        return header
    note = str(col.get("period_note") or "").strip()
    year = str(col.get("year_label") or "").strip()
    cpi = col.get("cpi")
    head = ""
    if year and cpi:
        head = f"In {year} ({cpi} CPI)"
    elif year:
        head = f"In {year}"
    if head and note:
        return f"{head} — {note}"
    return head or note


def _pdf_as_on_column(snapshot: dict) -> dict | None:
    """
    Same as-on comparison column used on the PDF pension table.
    Prefer the period covering as_on_date; among those, prefer one with OA fields.
    """
    pc = snapshot.get("pension_comparison") or {}
    columns = [c for c in (pc.get("columns") or []) if isinstance(c, dict)]
    if not columns:
        return None

    as_on = _as_date_safe(pc.get("as_on_date")) or date.today()

    def _covers(col: dict) -> bool:
        start = _as_date_safe(col.get("period_from"))
        end = _as_date_safe(col.get("period_to"))
        if start and as_on < start:
            return False
        if end and as_on > end:
            return False
        return True

    def _has_oa(col: dict) -> bool:
        return (
            col.get("oa_benefit_m2") is not None
            or col.get("oa_benefit_m1") is not None
            or col.get("oa_benefit") is not None
        )

    covering = [c for c in columns if _covers(c)]
    if covering:
        with_oa = [c for c in covering if _has_oa(c)]
        return (with_oa or covering)[-1]
    with_oa = [c for c in columns if _has_oa(c)]
    return with_oa[-1] if with_oa else columns[-1]


def _money_or_none(value):
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _m1_m2_for_cpi(snapshot: dict, cpi: int):
    """
    M1/M2/diff for a CPI — same source as PDF.

    Prefer pension_comparison print columns (m2_base + signed diff).
    Fall back to DB fields using is_employee_pension (m2_pension_* vs m2_family_*).

    Returns (m1, m2, signed_diff) where signed_diff is M2 − M1 (may be negative).
    """
    pc = snapshot.get("pension_comparison") or {}
    columns = [c for c in (pc.get("columns") or []) if isinstance(c, dict)]
    matching = [c for c in columns if int(c.get("cpi") or 0) == int(cpi)]
    if matching:
        as_on = _as_date_safe(pc.get("as_on_date")) or date.today()
        current = None
        for col in matching:
            start = _as_date_safe(col.get("period_from"))
            end = _as_date_safe(col.get("period_to"))
            if start and as_on < start:
                continue
            if end and as_on > end:
                continue
            current = col
            # keep scanning so the last covering column wins (OA / rate split)
        col = current or matching[-1]
        # Match PDF: prefer m2_base over m2 (payable may have been stored in m2)
        m2 = (
            col.get("m2_base")
            if col.get("m2_base") is not None
            else col.get("m2")
        )
        m1 = col.get("m1")
        # Blank placeholder column (class 1/2 empty 359) → leave empty, do not
        # fall back to employee DB amounts that PDF does not show.
        if m2 is not None or m1 is not None:
            m1n = _money_or_none(m1)
            m2n = _money_or_none(m2)
            return m1n, m2n, _signed_m2_minus_m1(m1n, m2n, col.get("diff"))
        return None, None, None

    is_emp = bool(snapshot.get("is_employee_pension", True))
    pen = snapshot.get("pension") or {}
    if cpi == 277:
        if is_emp:
            m2 = snapshot.get("m2_pension_277")
            if m2 is None:
                m2 = pen.get("pension_277_cpi") or pen.get("pension")
        else:
            m2 = snapshot.get("m2_family_pension_277")
            if m2 is None:
                m2 = pen.get("family_pension_277_cpi")
        m1 = (
            snapshot.get("m1_family_pension_277")
            or snapshot.get("m1_old_basic_pension")
        )
        if m1 is None:
            m1 = pen.get("family_pension_277_cpi") if not is_emp else None
    elif cpi == 359:
        if is_emp:
            m2 = snapshot.get("m2_pension_359")
            if m2 is None:
                m2 = pen.get("pension_359_cpi")
        else:
            m2 = snapshot.get("m2_family_pension_359")
            if m2 is None:
                m2 = pen.get("family_pension_359_cpi")
        m1 = (
            snapshot.get("m1_family_pension_359")
            or snapshot.get("m1_rev_basic_pension")
        )
    else:
        return None, None, None

    m1n = _money_or_none(m1)
    m2n = _money_or_none(m2)
    return m1n, m2n, _signed_m2_minus_m1(m1n, m2n)


def _report_pay_scale(scale, retirement_date) -> str:
    from methodology2.services.class1_2_service import pay_scale_for_report

    return pay_scale_for_report(scale, retirement_date)


def _calc_fields_from_snapshot(snapshot: dict) -> dict:
    """
    Form-report fields from consolidation snapshot + as-on OA column.
    """
    m1_277, m2_277, diff_277 = _m1_m2_for_cpi(snapshot, 277)
    m1_359, m2_359, diff_359 = _m1_m2_for_cpi(snapshot, 359)
    ben_277, _ = _beneficial(m1_277, m2_277)
    ben_359, _ = _beneficial(m1_359, m2_359)
    # Amt of Benefit = signed M2−M1 (same as PDF); do not use absolute benefit.
    amt_277 = diff_277
    amt_359 = diff_359

    is_emp = bool(snapshot.get("is_employee_pension", True))
    category = snapshot.get("category") or snapshot.get("emp_class") or ""
    ret = (
        snapshot.get("retirement_date")
        or snapshot.get("separation_date")
    )

    out: dict = {
        "name": (
            snapshot.get("name")
            or snapshot.get("pensioner_name")
            or snapshot.get("wage_emp_name")
            or ""
        ),
        "case_no": snapshot.get("case_no") or "",
        "roll_no": snapshot.get("roll_no") or "",
        "pension_type": "Employee" if is_emp else "Family",
        "emp_cd": snapshot.get("emp_cd") or "",
        "retirement_date_display": _fmt_ret_date(ret),
        "class_label": _class_label(category),
        "designation": snapshot.get("designation") or "",
        "last_pay": _money_or_none(snapshot.get("last_pay")),
        "scale": _report_pay_scale(snapshot.get("scale"), ret),
        "m1_277": m1_277,
        "m2_277": m2_277,
        "beneficial_277": ben_277,
        "amt_benefit_277": amt_277,
        "m1_359": m1_359,
        "m2_359": m2_359,
        "beneficial_359": ben_359,
        "amt_benefit_359": amt_359,
        "old_age_benefit_m2": None,
        "old_age_benefit_m1": None,
        "old_age_benefit_diff": None,
        "old_age_benefit": None,
    }
    out.update(oldage_slab_excel_dict((snapshot.get("pension_comparison") or {}).get("columns")))

    col = _pdf_as_on_column(snapshot)
    if not col:
        return out

    oa_m2 = _ceil_rupee_amount(col.get("oa_benefit_m2"))
    oa_m1 = _ceil_rupee_amount(col.get("oa_benefit_m1"))
    if oa_m2 is None and oa_m1 is None:
        both = _ceil_rupee_amount(col.get("oa_benefit"))
        out["old_age_benefit_m2"] = both
        out["old_age_benefit"] = both
    else:
        oa_m2_i = oa_m2 if oa_m2 is not None else 0
        oa_m1_i = oa_m1 if oa_m1 is not None else 0
        out["old_age_benefit_m2"] = oa_m2_i
        out["old_age_benefit_m1"] = oa_m1_i
        # Match PDF: keep signed OA diff (M2 − M1); do not ceil away the sign.
        raw_oa_diff = col.get("oa_diff")
        if raw_oa_diff is not None and raw_oa_diff != "":
            try:
                out["old_age_benefit_diff"] = round(float(raw_oa_diff), 2)
            except (TypeError, ValueError):
                out["old_age_benefit_diff"] = oa_m2_i - oa_m1_i
        else:
            out["old_age_benefit_diff"] = oa_m2_i - oa_m1_i
        out["old_age_benefit"] = max(oa_m2_i, oa_m1_i)

    return out


def _write_uploaded_manual_with_outputs(
    source: bytes | bytearray, results: list[dict], out_path: Path
) -> None:
    """
    Write Report.xlsx in official form layout (image):
      Name … Roll No | Pension Type | Emp Code … 277 block | 359 block |
      then each old-age slab: from, M-I, M-II, Difference

    Row order follows the uploaded EMP_CD order.
    """
    df_in = pd.read_excel(BytesIO(bytes(source)))
    cmap = {_normalize_header(c): c for c in df_in.columns}
    emp_col = cmap.get("emp_cd")
    by_emp: dict[str, dict] = {}
    for r in results:
        key = normalize_manual_emp_cd(r.get("emp_cd"))
        if key:
            by_emp[key] = r

    rows_out: list[dict] = []
    seen: set[str] = set()
    if emp_col:
        for _, row in df_in.iterrows():
            emp = normalize_manual_emp_cd(row.get(emp_col)) or ""
            if not emp or emp in seen:
                continue
            seen.add(emp)
            r = by_emp.get(emp) or _base_result(emp)
            rows_out.append({k: r.get(k) for k in FORM_REPORT_KEYS})
    else:
        for r in results:
            rows_out.append({k: r.get(k) for k in FORM_REPORT_KEYS})

    df = pd.DataFrame(rows_out, columns=FORM_REPORT_KEYS)
    df.columns = FORM_REPORT_HEADERS
    df.to_excel(out_path, index=False)


def _stamp_excel_m1(snapshot: dict, row: dict, *, is_employee: bool) -> None:
    """Put Excel M-I_277 / M-I_359 onto the print columns. Wage M1 does not win."""
    comparison = snapshot.get("pension_comparison") or {}
    if not isinstance(comparison, dict):
        return
    columns = comparison.get("columns") or []
    for cpi, key in ((277, "m1_277"), (359, "m1_359")):
        excel = row.get(key)
        if excel is None or excel == "":
            continue
        amount = float(excel)
        for col in columns:
            if not isinstance(col, dict):
                continue
            try:
                col_cpi = int(col.get("cpi") or 0)
            except (TypeError, ValueError):
                continue
            if col_cpi != cpi:
                continue
            kind = str(col.get("kind") or "").strip().lower()
            if is_employee and kind not in ("", "employee"):
                continue
            if not is_employee and kind not in ("", "family"):
                continue
            col["m1"] = amount
            m2 = col.get("m2_base") if col.get("m2_base") not in (None, "") else col.get("m2")
            if m2 not in (None, ""):
                col["diff"] = round(float(m2) - amount, 2)
        if cpi == 277:
            snapshot["m1_old_basic_pension"] = amount
            if not is_employee:
                snapshot["m1_family_pension_277"] = amount
        else:
            snapshot["m1_rev_basic_pension"] = amount
            if not is_employee:
                snapshot["m1_family_pension_359"] = amount
    snapshot["pension_comparison"] = comparison


def _persist_manual_excel_fields(
    emp: str,
    snapshot: dict,
    *,
    emp_dob,
    m1_277,
    m1_359,
    is_employee: bool,
) -> None:
    """Save Excel M1 and the employee DATE_OF_BIRTH (Excel, else database, else null)."""
    from M2_oldage_arrear.models import M2OldageArrearConsolidation

    obj = M2OldageArrearConsolidation.objects.filter(emp_cd=emp).first()
    if obj is None:
        return
    obj.date_of_birth = emp_dob or None
    obj.pension_comparison = snapshot.get("pension_comparison") or {}
    if not is_employee:
        if m1_277 is not None:
            obj.m1_family_pension_277 = m1_277
        if m1_359 is not None:
            obj.m1_family_pension_359 = m1_359
    obj.save(
        update_fields=[
            "date_of_birth",
            "pension_comparison",
            "m1_family_pension_277",
            "m1_family_pension_359",
            "updated_at",
        ]
    )


def process_one_manual_row(
    row: dict, out_dir: Path, *, generate_pdf: bool = True
) -> dict:
    emp = normalize_manual_emp_cd(row.get("emp_cd")) or ""
    result = _base_result(emp)
    category = m2_bulk._normalize_category(row.get("category"))
    result["category"] = category
    result["case_no"] = row.get("case_no") or ""
    result["roll_no"] = row.get("roll_no") or ""
    result["tqs"] = row.get("tqs") or ""

    if not emp:
        result["reason"] = "empty EMP_CD"
        return result

    retirement_date = row.get("retirement_date")
    scale = (row.get("scale") or "").strip()
    last_pay = row.get("last_pay")
    if not retirement_date or not scale or last_pay is None:
        result["status"] = "skipped"
        result["reason"] = (
            f"missing excel inputs "
            f"(dor={retirement_date}, scale={scale!r}, pay={last_pay})"
        )
        return result

    if category not in ("1", "2", "3", "4"):
        result["status"] = "skipped"
        result["reason"] = f"unsupported category={row.get('category')!r}"
        return result

    is_employee = row.get("is_employee_pension")
    if is_employee is None:
        is_employee = not _excel_marks_family(row)
    master = {
        "case_no": row.get("case_no") or "",
        "roll_no": row.get("roll_no") or "",
        "designation": row.get("designation") or "",
        "tqs_yr": row.get("tqs_yr"),
        "tqs_month": row.get("tqs_month"),
        "tqs_days": row.get("tqs_days"),
        "pensioner_name": row.get("family_pensioner_name")
        or row.get("name")
        or "",
        "name": row.get("name") or "",
        "is_employee_pension": bool(is_employee),
        "date_of_death": row.get("date_of_death"),
        "family_pensioner_dob": row.get("family_pensioner_dob"),
        "retirement_type": row.get("retirement_type") or "",
        "m1_old_basic_pension": row.get("m1_277"),
        "m1_rev_basic_pension": row.get("m1_359"),
        "m1_family_pension_277": row.get("m1_277"),
        "m1_family_pension_359": row.get("m1_359"),
    }

    data = {
        "name": row.get("name") or "",
        "separation_date": retirement_date,
        "retirement_date": retirement_date,
        "scale": scale,
        "last_pay": last_pay,
        "designation": row.get("designation") or "",
        "case_no": row.get("case_no") or "",
        "sda": 0,
    }

    emp_out_dir, tqs_folder = m2_bulk.resolve_temp_tqs_output_dir(out_dir, master)
    result["tqs_folder"] = tqs_folder

    if category in ("1", "2"):
        out = m2_bulk._process_class12(
            emp,
            data,
            category,
            emp_out_dir,
            excel_case_no=row.get("case_no") or "",
            excel_roll_no=row.get("roll_no") or "",
            master=master,
            generate_pdf=generate_pdf,
        )
    else:
        out = m2_bulk._process_class34(
            emp,
            data,
            category,
            emp_out_dir,
            excel_case_no=row.get("case_no") or "",
            excel_roll_no=row.get("roll_no") or "",
            master=master,
            generate_pdf=generate_pdf,
        )

    out["tqs"] = result["tqs"] or out.get("tqs") or ""
    out["tqs_folder"] = tqs_folder
    if out.get("status") != "ok":
        return out

    # Employee DATE_OF_BIRTH: Excel cell, else the database, else null.
    # Old age for a family pensioner uses DATE_OF_BIRTH OF FAMILY PENSIONER.
    emp_dob = row.get("date_of_birth")
    if not emp_dob:
        _, db_dob = _load_db_header(emp, category)
        emp_dob = db_dob
    oa_dob = emp_dob
    if not is_employee and row.get("family_pensioner_dob"):
        oa_dob = row.get("family_pensioner_dob")

    def _iso(value):
        if not value:
            return None
        return value.isoformat() if hasattr(value, "isoformat") else str(value)[:10]

    payload = {
        "date_of_birth": _iso(emp_dob),
        "dob": _iso(emp_dob),
        "oldage_dob": _iso(oa_dob),
        "m1_pension_277": row.get("m1_277"),
        "m1_pension_359": row.get("m1_359"),
    }
    snapshot = get_consolidation_snapshot(emp)
    if not snapshot or snapshot.get("error"):
        out["status"] = "failed"
        out["reason"] = (
            (snapshot or {}).get("error") or "snapshot missing after save"
        )
        return out

    _stamp_excel_m1(snapshot, row, is_employee=bool(is_employee))
    if not emp_dob:
        snapshot["date_of_birth"] = None
    snapshot = _attach_oldage(snapshot, payload) or snapshot
    _stamp_excel_m1(snapshot, row, is_employee=bool(is_employee))
    _persist_manual_excel_fields(
        emp,
        snapshot,
        emp_dob=emp_dob,
        m1_277=row.get("m1_277"),
        m1_359=row.get("m1_359"),
        is_employee=bool(is_employee),
    )

    # Ensure print header fields prefer Excel values.
    snapshot["emp_cd"] = emp
    snapshot["name"] = row.get("name") or snapshot.get("name") or ""
    snapshot["pensioner_name"] = snapshot["name"]
    snapshot["roll_no"] = row.get("roll_no") or snapshot.get("roll_no") or ""
    snapshot["case_no"] = row.get("case_no") or snapshot.get("case_no") or ""
    snapshot["designation"] = (
        row.get("designation") or snapshot.get("designation") or ""
    )
    snapshot["category"] = category or snapshot.get("category") or ""
    snapshot["last_pay"] = last_pay
    snapshot["scale"] = scale
    snapshot["retirement_date"] = retirement_date
    snapshot["retirement_type"] = (
        row.get("retirement_type") or snapshot.get("retirement_type") or ""
    )
    snapshot["is_employee_pension"] = bool(is_employee)
    if row.get("date_of_death"):
        dod = row.get("date_of_death")
        snapshot["date_of_death"] = (
            dod.isoformat() if hasattr(dod, "isoformat") else str(dod)[:10]
        )
    if row.get("family_pensioner_dob"):
        fp_dob = row.get("family_pensioner_dob")
        snapshot["family_pensioner_dob"] = (
            fp_dob.isoformat() if hasattr(fp_dob, "isoformat") else str(fp_dob)[:10]
        )
    if row.get("family_pensioner_name"):
        snapshot["pensioner_name"] = row.get("family_pensioner_name")
    if row.get("tqs"):
        snapshot["tqs"] = row.get("tqs")
    if row.get("m1_277") is not None:
        snapshot["m1_old_basic_pension"] = row.get("m1_277")
        snapshot["m1_family_pension_277"] = row.get("m1_277")
    if row.get("m1_359") is not None:
        snapshot["m1_rev_basic_pension"] = row.get("m1_359")
        snapshot["m1_family_pension_359"] = row.get("m1_359")

    pdf_path = str(out.get("pdf") or "").strip()
    write_dir = Path(pdf_path).parent if pdf_path else emp_out_dir
    case_no = out.get("case_no") or snapshot.get("case_no") or ""
    if not generate_pdf:
        out["pdf"] = ""
        calc = _calc_fields_from_snapshot(snapshot)
        out.update(calc)
        return out
    try:
        files = write_consolidation_files(
            snapshot, write_dir, emp, case_no=case_no
        )
    except Exception as exc:
        out["status"] = "failed"
        out["reason"] = f"old-age pdf error: {exc}"
        return out

    out["pdf"] = files.get("pdf") or out.get("pdf") or ""
    if files.get("pdf_error") and not files.get("pdf"):
        out["status"] = "failed"
        out["reason"] = f"old-age pdf error: {files.get('pdf_error')}"
        return out

    calc = _calc_fields_from_snapshot(snapshot)
    out.update(calc)
    return out


ProgressCallback = Callable[[int, int, str, dict], None]

LOG_FIELDNAMES = [
    "emp_cd",
    "case_no",
    "roll_no",
    "pension_type",
    "category",
    "tqs",
    "tqs_folder",
    "status",
    "reason",
    "pdf",
    "m1_277",
    "m2_277",
    "m1_359",
    "m2_359",
    "old_age_benefit_m2",
    "old_age_benefit_m1",
    "old_age_benefit_diff",
]


def _row_to_jsonable(row: dict) -> dict:
    out = {}
    for key, val in row.items():
        if isinstance(val, date):
            out[key] = val.isoformat()
        else:
            out[key] = val
    return out


def _row_from_jsonable(row: dict) -> dict:
    out = dict(row)
    for key in (
        "date_of_birth",
        "retirement_date",
        "date_of_death",
        "family_pensioner_dob",
    ):
        raw = out.get(key)
        if not raw:
            continue
        if isinstance(raw, date):
            continue
        out[key] = date.fromisoformat(str(raw)[:10])
    return out


# Header lines asked one at a time when Excel and the database are both blank.
# A later answer of null is allowed. A value must match the field type.
_HEADER_FIELDS = (
    {"key": "name", "label": "Pensioner name", "type": "text"},
    {"key": "case_no", "label": "Case No", "type": "text"},
    {"key": "roll_no", "label": "Roll No", "type": "text"},
    {"key": "tqs", "label": "TQS", "type": "tqs"},
    {"key": "designation", "label": "Designation", "type": "text"},
    {"key": "date_of_birth", "label": "Date of birth", "type": "date"},
    {"key": "retirement_date", "label": "Date of retirement", "type": "date"},
    {"key": "retirement_type", "label": "Type of retirement", "type": "text"},
    {"key": "last_pay", "label": "Last pay", "type": "number"},
    {"key": "scale", "label": "Pay scale", "type": "text"},
    {"key": "m1_277", "label": "M1@277", "type": "number"},
)
_FAMILY_HEADER_FIELDS = (
    {"key": "date_of_death", "label": "Date of death", "type": "date"},
    {
        "key": "family_pensioner_name",
        "label": "Name of family pensioner",
        "type": "text",
    },
    {
        "key": "family_pensioner_dob",
        "label": "Date of birth of family pensioner",
        "type": "date",
    },
)


def _text_blank(value) -> bool:
    return value is None or str(value).strip() == ""


def _has_tqs(row: dict) -> bool:
    if not _text_blank(row.get("tqs")):
        return True
    return any(row.get(key) is not None for key in ("tqs_yr", "tqs_month", "tqs_days"))


def _header_value_blank(row: dict, key: str) -> bool:
    if key == "tqs":
        return not _has_tqs(row)
    if key in ("last_pay", "m1_277", "m1_359"):
        return row.get(key) is None or row.get(key) == ""
    return _text_blank(row.get(key))


def _load_db_header(emp: str, category: str) -> tuple[dict, object]:
    master = {}
    dob = None
    try:
        from methodology2.services.consolidation_service import (
            fetch_print_master_fields,
            format_tqs,
        )

        master = fetch_print_master_fields(emp, category=category or None) or {}
        if _has_tqs(master) and _text_blank(master.get("tqs")):
            master["tqs"] = format_tqs(
                master.get("tqs_yr"),
                master.get("tqs_month"),
                master.get("tqs_days"),
            )
    except Exception:
        master = {}
    try:
        from django.db import connection

        with connection.cursor() as cursor:
            for table in (
                "fi_pn_wage_2017_hdr_offi2",
                "fi_pn_wage_2022_hdr_third",
            ):
                cursor.execute(
                    f"""
                    SELECT CASE_NO, ROLL_NO, DESIGNATION, DOB_PENSIONER
                    FROM {table}
                    WHERE EMP_CD = %s
                    LIMIT 1
                    """,
                    [emp],
                )
                wage = cursor.fetchone()
                if not wage:
                    continue
                if _text_blank(master.get("case_no")) and wage[0]:
                    master["case_no"] = str(wage[0]).strip()
                if _text_blank(master.get("roll_no")) and wage[1]:
                    master["roll_no"] = str(wage[1]).strip()
                if _text_blank(master.get("designation")) and wage[2]:
                    master["designation"] = str(wage[2]).strip()
                if dob is None and wage[3]:
                    dob = wage[3]
    except Exception:
        pass
    try:
        from M2_oldage_arrear.services.consolidation_bridge import (
            fetch_employee_dob,
        )

        found = fetch_employee_dob(emp)
        if found is not None:
            dob = found
    except Exception:
        pass
    if isinstance(dob, datetime):
        dob = dob.date()
    return master, dob


def _fill_header_from_db(row: dict, answered: set[str]) -> bool:
    """
    Copy header values the database already has into blank Excel cells.

    Keys the user already answered (including an explicit null) are left alone.
    Returns True when this is a family-pension header.
    """
    emp = normalize_manual_emp_cd(row.get("emp_cd")) or ""
    category = str(row.get("category") or "").strip()
    master, dob = _load_db_header(emp, category) if emp else ({}, None)

    def take(key, value):
        if key in answered or not _header_value_blank(row, key):
            return
        if value is None or (isinstance(value, str) and not value.strip()):
            return
        row[key] = value

    take("name", master.get("name"))
    take("case_no", master.get("case_no"))
    take("roll_no", master.get("roll_no"))
    take("designation", master.get("designation"))
    take("retirement_type", master.get("retirement_type"))
    take("retirement_date", master.get("retirement_date"))
    if "tqs" not in answered and not _has_tqs(row) and _has_tqs(master):
        row["tqs_yr"] = master.get("tqs_yr")
        row["tqs_month"] = master.get("tqs_month")
        row["tqs_days"] = master.get("tqs_days")
        row["tqs"] = master.get("tqs") or ""

    excel_family = _excel_marks_family(row)
    db_family = master.get("is_employee_pension") is False or bool(
        master.get("date_of_death")
    )
    family = excel_family or db_family
    if "is_employee_pension" not in answered:
        # Excel family columns win over a database employee flag.
        if excel_family:
            row["is_employee_pension"] = False
        else:
            row["is_employee_pension"] = not db_family
    if family:
        take("date_of_death", master.get("date_of_death"))
        take("family_pensioner_name", master.get("pensioner_name"))
        take("family_pensioner_dob", master.get("family_pensioner_dob"))
    # Employee DATE_OF_BIRTH: Excel cell, else the database, else null.
    take("date_of_birth", dob)
    return bool(family) or row.get("is_employee_pension") is False


def _parse_header_tqs(value) -> tuple[int, int, int]:
    if not isinstance(value, dict):
        raise ValueError("TQS must be years, months and days, or null.")
    try:
        years = int(value.get("tqs_yr"))
        months = int(value.get("tqs_month"))
        days = int(value.get("tqs_days"))
    except (TypeError, ValueError) as exc:
        raise ValueError("TQS must be years, months and days, or null.") from exc
    if years < 0 or years > 80 or months < 0 or months > 11 or days < 0 or days > 30:
        raise ValueError("TQS must be 0–80 years, 0–11 months and 0–30 days.")
    return years, months, days


def _parse_header_date(value, label: str) -> date:
    text = str(value or "").strip()[:10]
    try:
        return date.fromisoformat(text)
    except ValueError as exc:
        raise ValueError(f"{label} must be a date, or null.") from exc


def _apply_header_overrides(row: dict, overrides, answered) -> None:
    """Write popup answers. Null is stored as empty and is not asked again."""
    from methodology2.services.consolidation_service import format_tqs

    overrides = overrides if isinstance(overrides, dict) else {}
    keys = [str(k) for k in (answered or [])]
    known = {spec["key"] for spec in _HEADER_FIELDS + _FAMILY_HEADER_FIELDS}
    for key in keys:
        if key not in known:
            continue
        spec = next(item for item in (*_HEADER_FIELDS, *_FAMILY_HEADER_FIELDS) if item["key"] == key)
        raw = overrides.get(key, None)
        if raw is None or raw == "":
            if key == "tqs":
                row["tqs"] = ""
                row["tqs_yr"] = None
                row["tqs_month"] = None
                row["tqs_days"] = None
            else:
                row[key] = None if key in ("last_pay", "m1_277", "m1_359") else ""
            continue
        if spec["type"] == "tqs":
            years, months, days = _parse_header_tqs(raw)
            row["tqs_yr"] = years
            row["tqs_month"] = months
            row["tqs_days"] = days
            row["tqs"] = format_tqs(years, months, days)
        elif spec["type"] == "date":
            row[key] = _parse_header_date(raw, spec["label"])
        elif spec["type"] == "number":
            try:
                amount = float(str(raw).replace(",", "").strip())
            except (TypeError, ValueError) as exc:
                raise ValueError(f"{spec['label']} must be a number, or null.") from exc
            if amount < 0:
                raise ValueError(f"{spec['label']} cannot be negative.")
            row[key] = amount
        else:
            row[key] = str(raw).strip()[:200]


def missing_header_fields(row: dict, answered: set[str] | None = None) -> list[dict]:
    """Header fields still blank after Excel and the database."""
    answered = answered or set()
    family = _fill_header_from_db(row, answered)
    specs = list(_HEADER_FIELDS)
    if family:
        specs.extend(_FAMILY_HEADER_FIELDS)
    pending = []
    for spec in specs:
        if spec["key"] in answered:
            continue
        # Family date of birth is DOB of family pensioner, not DATE_OF_BIRTH.
        if family and spec["key"] == "date_of_birth":
            continue
        if _header_value_blank(row, spec["key"]):
            pending.append(dict(spec))
    return pending


def _sessions_root() -> Path:
    """
    Hidden progress state for prepare/row/finish APIs.

    Kept under system temp — never inside Desktop m2-manual-* output.
    """
    root = Path(tempfile.gettempdir()) / "m2_oa_manual_sessions"
    root.mkdir(parents=True, exist_ok=True)
    return root


def _session_dir(session_id: str) -> Path:
    sid = str(session_id or "").strip()
    if not sid or "/" in sid or "\\" in sid or ".." in sid:
        raise ValueError("Invalid session_id")
    return _sessions_root() / f"session_{sid}"


def _cleanup_session(sess: Path) -> None:
    try:
        if sess.is_dir():
            shutil.rmtree(sess, ignore_errors=True)
    except Exception:
        pass


def _ensure_manual_output_dirs(out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    if m2_bulk.TEMP_TQS_SPLIT_ENABLED:
        (out_dir / m2_bulk.TEMP_TQS_FOLDER_GE).mkdir(parents=True, exist_ok=True)
        (out_dir / m2_bulk.TEMP_TQS_FOLDER_LT).mkdir(parents=True, exist_ok=True)


def finalize_manual_run(
    out_dir: Path,
    source_bytes: bytes | None,
    results: list[dict],
    *,
    generate_pdf: bool = True,
) -> dict:
    """Write run_log.csv; Report.xlsx only when generate_pdf is off."""
    wrote_report = False
    if source_bytes and not generate_pdf:
        report_path = out_dir / "Report.xlsx"
        _write_uploaded_manual_with_outputs(source_bytes, results, report_path)
        wrote_report = True

    log_path = out_dir / "run_log.csv"
    with open(log_path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(
            fh, fieldnames=LOG_FIELDNAMES, extrasaction="ignore"
        )
        writer.writeheader()
        writer.writerows(results)

    return {
        "output_dir": str(out_dir),
        "log_path": str(log_path),
        "report_path": str(out_dir / "Report.xlsx") if wrote_report else "",
        "generate_pdf": bool(generate_pdf),
        "total": len(results),
        "ok": sum(1 for r in results if r["status"] == "ok"),
        "skipped": sum(1 for r in results if r["status"] == "skipped"),
        "failed": sum(1 for r in results if r["status"] == "failed"),
        "results": results,
        "manual_entry": True,
    }


def prepare_manual_session(
    source: bytes | bytearray,
    output_dir: Path | None = None,
    *,
    generate_pdf: bool = True,
) -> dict:
    """Save upload + parsed rows in temp; return session_id for row-by-row processing."""
    from M2_oldage_arrear.models import M2OldAgeBatch
    from M2_oldage_arrear.services.batch_service import create_batch

    out_dir = Path(output_dir) if output_dir else default_manual_output_dir()
    _ensure_manual_output_dirs(out_dir)

    rows_in = read_manual_rows_from_excel(source)
    if not rows_in:
        raise ValueError("No EMP_CD rows in Excel")

    batch = create_batch(
        source=M2OldAgeBatch.SOURCE_MANUAL,
        case_count=len(rows_in),
        output_dir=out_dir,
        generate_pdf=generate_pdf,
    )

    session_id = secrets.token_hex(8)
    sess = _session_dir(session_id)
    sess.mkdir(parents=True, exist_ok=False)

    source_bytes = bytes(source)
    (sess / "upload.xlsx").write_bytes(source_bytes)
    json_rows = [_row_to_jsonable(r) for r in rows_in]
    (sess / "rows.json").write_text(
        json.dumps(json_rows, ensure_ascii=False), encoding="utf-8"
    )
    (sess / "results.json").write_text("[]", encoding="utf-8")
    meta = {
        "session_id": session_id,
        "batch_id": batch.batch_id,
        "stamp": batch.stamp,
        "case_count": batch.case_count,
        "source": batch.source,
        "generate_pdf": bool(generate_pdf),
        "total": len(rows_in),
        "output_dir": str(out_dir),
    }
    (sess / "meta.json").write_text(json.dumps(meta), encoding="utf-8")
    return meta


def run_manual_session_row(
    session_id: str,
    index: int,
    output_dir: Path | None = None,
    header_overrides=None,
    header_answered=None,
) -> dict:
    """Process one row (0-based index) for UI progress."""
    from M2_oldage_arrear.services.batch_service import record_batch_case

    sess = _session_dir(session_id)
    if not sess.is_dir():
        raise ValueError("Manual session not found or expired")

    meta = json.loads((sess / "meta.json").read_text(encoding="utf-8"))
    out_dir = Path(output_dir) if output_dir else Path(meta.get("output_dir") or default_manual_output_dir())
    _ensure_manual_output_dirs(out_dir)
    generate_pdf = bool(meta.get("generate_pdf", True))
    batch_id = str(meta.get("batch_id") or "")

    rows = json.loads((sess / "rows.json").read_text(encoding="utf-8"))
    results = json.loads((sess / "results.json").read_text(encoding="utf-8"))
    total = len(rows)
    idx = int(index)

    if idx < 0 or idx >= total:
        raise ValueError(f"index out of range (0..{total - 1})")

    if idx < len(results):
        result = results[idx]
    else:
        if idx != len(results):
            raise ValueError(
                f"Rows must be processed in order (next index {len(results)}, got {idx})"
            )
        row = _row_from_jsonable(rows[idx])
        answered = {str(k) for k in (header_answered or [])}
        _apply_header_overrides(row, header_overrides, answered)
        pending = missing_header_fields(row, answered)
        if pending:
            return {
                "session_id": session_id,
                "batch_id": batch_id,
                "index": idx,
                "current": idx,
                "total": total,
                "emp_cd": row.get("emp_cd") or "",
                "name": row.get("name") or "",
                "status": "needs_header",
                "fields": pending,
                "result": None,
            }
        rows[idx] = _row_to_jsonable(row)
        (sess / "rows.json").write_text(
            json.dumps(rows, ensure_ascii=False), encoding="utf-8"
        )
        result = process_one_manual_row(row, out_dir, generate_pdf=generate_pdf)
        if batch_id:
            record_batch_case(
                batch_id,
                emp_cd=result.get("emp_cd") or row.get("emp_cd") or "",
                status=result.get("status") or "",
                case_no=result.get("case_no") or "",
                roll_no=result.get("roll_no") or "",
                reason=result.get("reason") or "",
            )
        results.append(result)
        (sess / "results.json").write_text(
            json.dumps(results, ensure_ascii=False), encoding="utf-8"
        )

    return {
        "session_id": session_id,
        "batch_id": batch_id,
        "index": idx,
        "current": idx + 1,
        "total": total,
        "emp_cd": result.get("emp_cd"),
        "status": result.get("status"),
        "result": result,
    }


def finish_manual_session(session_id: str, output_dir: Path | None = None) -> dict:
    from M2_oldage_arrear.services.batch_service import finalize_batch

    sess = _session_dir(session_id)
    if not sess.is_dir():
        raise ValueError("Manual session not found or expired")

    meta = json.loads((sess / "meta.json").read_text(encoding="utf-8"))
    out_dir = Path(output_dir) if output_dir else Path(meta.get("output_dir") or default_manual_output_dir())
    batch_id = str(meta.get("batch_id") or "")

    rows = json.loads((sess / "rows.json").read_text(encoding="utf-8"))
    results = json.loads((sess / "results.json").read_text(encoding="utf-8"))
    if len(results) != len(rows):
        raise ValueError(
            f"Not all rows processed ({len(results)}/{len(rows)}). "
            "Complete row processing before finish."
        )

    source_bytes = (sess / "upload.xlsx").read_bytes()
    generate_pdf = bool(meta.get("generate_pdf", True))
    try:
        summary = finalize_manual_run(
            out_dir, source_bytes, results, generate_pdf=generate_pdf
        )
        summary["session_id"] = session_id
        summary["batch_id"] = batch_id
        summary["stamp"] = meta.get("stamp") or ""
        summary["case_count"] = meta.get("case_count") or len(results)
        if batch_id:
            batch = finalize_batch(batch_id, results)
            if batch:
                summary["batch"] = {
                    "batch_id": batch.batch_id,
                    "stamp": batch.stamp,
                    "source": batch.source,
                    "case_count": batch.case_count,
                    "ok_count": batch.ok_count,
                    "failed_count": batch.failed_count,
                    "skipped_count": batch.skipped_count,
                }
        return summary
    finally:
        # Temp progress folder is not part of the user output.
        _cleanup_session(sess)


def run_manual_from_excel(
    source,
    output_dir: Path | None = None,
    *,
    generate_pdf: bool = True,
    on_progress: ProgressCallback | None = None,
) -> dict:
    rows_in = read_manual_rows_from_excel(source)
    out_dir = Path(output_dir) if output_dir else default_manual_output_dir()
    _ensure_manual_output_dirs(out_dir)

    source_bytes = bytes(source) if isinstance(source, (bytes, bytearray)) else None

    total = len(rows_in)
    results = []
    for idx, row in enumerate(rows_in, start=1):
        result = process_one_manual_row(row, out_dir, generate_pdf=generate_pdf)
        results.append(result)
        if on_progress:
            on_progress(idx, total, str(result.get("emp_cd") or ""), result)

    return finalize_manual_run(
        out_dir, source_bytes, results, generate_pdf=generate_pdf
    )
