"""
Methodology-2 bulk runner (class 1/2 and 3/4):

Excel EMP_CD → lookup → calc → consolidation snapshot → Desktop/M2_YYYY-MM-DD/{case_no}.pdf
"""

from __future__ import annotations

import csv
from datetime import date
from pathlib import Path

from django.conf import settings

from methodology2.services.bulk_excel_service import read_emp_rows_from_excel
from methodology2.services.bulk_pdf_service import write_consolidation_files
from methodology2.services.calculation_service import calculate_revision
from methodology2.services.class1_2_service import (
    calculate_class12,
    validate_executive_grade,
)
from methodology2.services.consolidation_service import (
    fetch_print_master_fields,
    save_consolidation_snapshot,
)
from methodology2.services.oracle_employee_service import fetch_employee_for_methodology2
from methodology2.services.revision_resolver import get_revision_column
from methodology2.services.scale_service import get_equivalent_scales_by_scale


# ---------------------------------------------------------------------------
# TEMPORARY (remove when no longer needed):
# Bulk PDFs are split by TQS into two subfolders under M2_YYYY-MM-DD:
#   TEMP_TQS_GE_32Y9M  → TQS >= 32 years 9 months
#   TEMP_TQS_LT_32Y9M  → everyone else
# ---------------------------------------------------------------------------
TEMP_TQS_SPLIT_ENABLED = True
TEMP_TQS_MIN_YEARS = 32
TEMP_TQS_MIN_MONTHS = 9
TEMP_TQS_FOLDER_GE = "TEMP_TQS_GE_32Y9M"
TEMP_TQS_FOLDER_LT = "TEMP_TQS_LT_32Y9M"


def default_run_output_dir(run_date: date | None = None) -> Path:
    """Desktop/M2_YYYY-MM-DD (or BULK_OUTPUT_DIR parent)."""
    parent = Path(getattr(settings, "BULK_OUTPUT_DIR", Path.home() / "Desktop"))
    d = run_date or date.today()
    return parent / f"M2_{d.isoformat()}"


def _tqs_months_total(tqs_yr, tqs_month) -> int:
    try:
        y = int(tqs_yr or 0)
    except (TypeError, ValueError):
        y = 0
    try:
        m = int(tqs_month or 0)
    except (TypeError, ValueError):
        m = 0
    return y * 12 + m


def _tqs_meets_temp_threshold(tqs_yr, tqs_month) -> bool:
    """TEMPORARY: True when TQS >= 32 years 9 months."""
    return _tqs_months_total(tqs_yr, tqs_month) >= (
        TEMP_TQS_MIN_YEARS * 12 + TEMP_TQS_MIN_MONTHS
    )


def resolve_temp_tqs_output_dir(base_out_dir: Path, master: dict | None) -> tuple[Path, str]:
    """
    TEMPORARY: pick subfolder from TQS.
    Returns (path, folder_label).
    """
    base = Path(base_out_dir)
    if not TEMP_TQS_SPLIT_ENABLED:
        base.mkdir(parents=True, exist_ok=True)
        return base, ""

    master = master or {}
    if _tqs_meets_temp_threshold(master.get("tqs_yr"), master.get("tqs_month")):
        label = TEMP_TQS_FOLDER_GE
    else:
        label = TEMP_TQS_FOLDER_LT
    path = base / label
    path.mkdir(parents=True, exist_ok=True)
    return path, label


def _normalize_category(raw) -> str:
    text = str(raw or "").strip().upper()
    mapping = {
        "1": "1",
        "I": "1",
        "CLASS 1": "1",
        "CLASS I": "1",
        "2": "2",
        "II": "2",
        "CLASS 2": "2",
        "CLASS II": "2",
        "3": "3",
        "III": "3",
        "CLASS 3": "3",
        "CLASS III": "3",
        "4": "4",
        "IV": "4",
        "CLASS 4": "4",
        "CLASS IV": "4",
    }
    if text in mapping:
        return mapping[text]
    return str(raw or "").strip()


def _base_result(emp: str) -> dict:
    return {
        "emp_cd": emp,
        "case_no": "",
        "roll_no": "",
        "category": "",
        "status": "failed",
        "reason": "",
        "pdf": "",
        "html": "",
        "tqs": "",
        "tqs_folder": "",  # TEMPORARY split label
    }


def _master_payload_fields(
    emp: str,
    category: str,
    master: dict,
    data: dict,
    excel_case_no: str = "",
    excel_roll_no: str = "",
) -> dict:
    return {
        "case_no": (
            excel_case_no
            or master.get("case_no")
            or data.get("case_no")
            or ""
        ),
        "roll_no": (
            master.get("roll_no")
            or excel_roll_no
            or data.get("roll_no")
            or ""
        ),
        "retirement_type": master.get("retirement_type") or "",
        "designation": master.get("designation") or data.get("designation") or "",
        "tqs_yr": master.get("tqs_yr"),
        "tqs_month": master.get("tqs_month"),
        "tqs_days": master.get("tqs_days"),
        "wage_emp_name": master.get("wage_emp_name") or "",
        "pensioner_name": master.get("pensioner_name") or "",
        "is_employee_pension": master.get("is_employee_pension") or False,
        "date_of_death": master.get("date_of_death"),
        "double_fpension_upto": master.get("double_fpension_upto"),
        "enhanced_family_pension": bool(
            master.get("enhanced_family_pension")
        ),
        "die_in_harness": bool(master.get("die_in_harness")),
        "case_type": master.get("case_type"),
        "m1_family_pension_277": master.get("m1_family_pension_277"),
        "m1_family_pension_359": master.get("m1_family_pension_359"),
        "m1_old_basic_pension": master.get("m1_old_basic_pension"),
        "m1_rev_basic_pension": master.get("m1_rev_basic_pension"),
        "category": category,
        "name": data.get("name") or master.get("name") or "",
    }


def _process_class12(
    emp: str,
    data: dict,
    category: str,
    out_dir: Path,
    excel_case_no: str = "",
    excel_roll_no: str = "",
    master: dict | None = None,
) -> dict:
    result = _base_result(emp)
    result["category"] = category

    retirement_date = data.get("separation_date") or data.get("retirement_date")
    scale_raw = data.get("scale")
    last_pay = data.get("last_pay")
    if not retirement_date or not scale_raw or last_pay is None:
        result["status"] = "skipped"
        result["reason"] = (
            f"missing inputs (date={retirement_date}, scale={scale_raw}, pay={last_pay})"
        )
        return result

    grade = validate_executive_grade(scale_raw, retirement_date)
    if not grade:
        result["status"] = "skipped"
        result["reason"] = (
            f"class 1/2 needs executive grade or pay band (got scale={scale_raw!r})"
        )
        return result

    try:
        calc = calculate_class12(retirement_date, grade, last_pay)
    except Exception as exc:
        result["reason"] = f"calc error: {exc}"
        return result
    if calc.get("error"):
        result["status"] = "skipped"
        result["reason"] = str(calc.get("error"))
        return result

    if master is None:
        master = fetch_print_master_fields(emp, category=category)
    payload = {
        "emp_cd": emp,
        "retirement_date": retirement_date,
        "scale": calc.get("scale_display") or grade,
        "last_pay": last_pay,
        "average_pay": last_pay,
        "calculation_rows": calc.get("rows") or [],
        "pension": {
            "basic_pay_2017": calc.get("basic_pay_2017"),
            "basic_pay_2022": None,
            "pension_277_cpi": calc.get("pension"),
            "pension_359_cpi": None,
            "family_pension_277_cpi": calc.get("family_pension"),
            "family_pension_359_cpi": None,
            "family_pension": calc.get("family_pension"),
            "pension": calc.get("pension"),
        },
        "start_revision": calc.get("start_revision") or "",
        "equivalent_scales": calc.get("equivalent_scales") or {},
        **_master_payload_fields(
            emp, category, master, data, excel_case_no, excel_roll_no
        ),
    }

    return _save_and_write(emp, payload, out_dir, result, excel_case_no)


def _process_class34(
    emp: str,
    data: dict,
    category: str,
    out_dir: Path,
    excel_case_no: str = "",
    excel_roll_no: str = "",
    master: dict | None = None,
) -> dict:
    result = _base_result(emp)
    result["category"] = category

    retirement_date = data.get("separation_date") or data.get("retirement_date")
    scale = data.get("scale")
    last_pay = data.get("last_pay")
    if not retirement_date or not scale or last_pay is None:
        result["status"] = "skipped"
        result["reason"] = (
            f"missing inputs (date={retirement_date}, scale={scale}, pay={last_pay})"
        )
        return result

    try:
        sda = float(data.get("sda") or 0)
    except (TypeError, ValueError):
        sda = 0.0

    try:
        scales = get_equivalent_scales_by_scale(retirement_date, scale)
        current_revision = get_revision_column(retirement_date)
        calc = calculate_revision(scales, current_revision, last_pay, sda)
    except Exception as exc:
        result["reason"] = f"calc error: {exc}"
        return result

    if master is None:
        master = fetch_print_master_fields(emp, category=category)
    payload = {
        "emp_cd": emp,
        "retirement_date": retirement_date,
        "scale": scale,
        "last_pay": last_pay,
        "average_pay": last_pay,
        "calculation_rows": calc.get("rows") or [],
        "pension": calc.get("pension") or {},
        "start_revision": current_revision,
        "equivalent_scales": scales,
        **_master_payload_fields(
            emp, category, master, data, excel_case_no, excel_roll_no
        ),
    }
    return _save_and_write(emp, payload, out_dir, result, excel_case_no)


def _save_and_write(
    emp: str,
    payload: dict,
    out_dir: Path,
    result: dict,
    excel_case_no: str = "",
) -> dict:
    try:
        snapshot = save_consolidation_snapshot(payload)
    except Exception as exc:
        result["reason"] = f"consolidation save error: {exc}"
        return result
    if snapshot.get("error"):
        result["reason"] = str(snapshot.get("error"))
        return result

    case_no = (
        excel_case_no
        or snapshot.get("case_no")
        or payload.get("case_no")
        or ""
    )
    result["case_no"] = case_no
    result["roll_no"] = snapshot.get("roll_no") or payload.get("roll_no") or ""

    try:
        files = write_consolidation_files(snapshot, out_dir, emp, case_no=case_no)
    except Exception as exc:
        result["reason"] = f"file write error: {exc}"
        return result

    result["status"] = "ok"
    result["html"] = ""
    result["pdf"] = files.get("pdf") or ""
    if files.get("pdf_error") and not files.get("pdf"):
        result["reason"] = f"pdf error: {files.get('pdf_error')}"
        result["status"] = "failed"
    return result


def process_one_emp(
    emp_cd: str,
    out_dir: Path,
    excel_case_no: str = "",
    excel_roll_no: str = "",
) -> dict:
    """Process one EMP_CD for class 1/2 or 3/4."""
    emp = str(emp_cd or "").strip()
    result = _base_result(emp)
    if not emp:
        result["reason"] = "empty EMP_CD"
        return result

    try:
        data = fetch_employee_for_methodology2(emp)
    except Exception as exc:
        result["reason"] = f"lookup error: {exc}"
        return result

    if not data:
        result["status"] = "skipped"
        result["reason"] = "employee not found"
        return result
    if data.get("error"):
        result["status"] = "skipped"
        result["reason"] = str(data.get("error"))
        return result

    category = _normalize_category(data.get("category"))
    result["category"] = category

    # TEMPORARY: resolve TQS first, then choose output subfolder before calc/save.
    master = fetch_print_master_fields(emp, category=category)
    yr = master.get("tqs_yr")
    mo = master.get("tqs_month")
    days = master.get("tqs_days")
    result["tqs"] = f"{yr or 0}Y {mo or 0}M {days or 0}D"
    emp_out_dir, tqs_folder = resolve_temp_tqs_output_dir(out_dir, master)
    result["tqs_folder"] = tqs_folder

    if category in ("1", "2"):
        out = _process_class12(
            emp,
            data,
            category,
            emp_out_dir,
            excel_case_no,
            excel_roll_no,
            master=master,
        )
        out["tqs"] = result["tqs"]
        out["tqs_folder"] = tqs_folder
        return out
    if category in ("3", "4"):
        out = _process_class34(
            emp,
            data,
            category,
            emp_out_dir,
            excel_case_no,
            excel_roll_no,
            master=master,
        )
        out["tqs"] = result["tqs"]
        out["tqs_folder"] = tqs_folder
        return out

    result["status"] = "skipped"
    result["reason"] = f"unsupported category={data.get('category')!r}"
    return result


def run_bulk_from_excel(source, output_dir: Path | None = None) -> dict:
    """Full bulk run. `source` = path / bytes / file-like Excel."""
    emp_rows = read_emp_rows_from_excel(source)
    out_dir = Path(output_dir) if output_dir else default_run_output_dir()
    out_dir.mkdir(parents=True, exist_ok=True)
    # TEMPORARY subfolders created lazily per emp when TQS split is on.
    if TEMP_TQS_SPLIT_ENABLED:
        (out_dir / TEMP_TQS_FOLDER_GE).mkdir(parents=True, exist_ok=True)
        (out_dir / TEMP_TQS_FOLDER_LT).mkdir(parents=True, exist_ok=True)

    rows = []
    for item in emp_rows:
        rows.append(
            process_one_emp(
                item["emp_cd"],
                out_dir,
                excel_case_no=item.get("case_no") or "",
                excel_roll_no=item.get("roll_no") or "",
            )
        )

    log_path = out_dir / "run_log.csv"
    with open(log_path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(
            fh,
            fieldnames=[
                "emp_cd",
                "case_no",
                "roll_no",
                "category",
                "tqs",
                "tqs_folder",
                "status",
                "reason",
                "pdf",
            ],
            extrasaction="ignore",
        )
        writer.writeheader()
        writer.writerows(rows)

    return {
        "output_dir": str(out_dir),
        "log_path": str(log_path),
        "total": len(rows),
        "ok": sum(1 for r in rows if r["status"] == "ok"),
        "skipped": sum(1 for r in rows if r["status"] == "skipped"),
        "failed": sum(1 for r in rows if r["status"] == "failed"),
        "results": rows,
        # TEMPORARY flags for UI / ops
        "temp_tqs_split": TEMP_TQS_SPLIT_ENABLED,
        "temp_tqs_folder_ge": TEMP_TQS_FOLDER_GE,
        "temp_tqs_folder_lt": TEMP_TQS_FOLDER_LT,
    }
