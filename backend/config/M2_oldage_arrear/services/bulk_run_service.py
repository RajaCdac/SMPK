"""
Old Age bulk Excel runner.

Reuses Met2 calc/save, then attaches DOB + old-age print columns and rewrites PDF.
"""

from __future__ import annotations

import csv
from pathlib import Path

from M2_oldage_arrear.services.consolidation_bridge import (
    _attach_oldage,
    fetch_employee_dob,
    get_consolidation_snapshot,
)
from methodology2.services.bulk_excel_service import read_emp_rows_from_excel
from methodology2.services.bulk_pdf_service import write_consolidation_files
from methodology2.services import bulk_run_service as m2_bulk


def _rewrite_pdf_with_oldage(emp: str, result: dict) -> dict:
    """Reload snapshot with OA columns and overwrite the PDF from Met2 bulk."""
    if result.get("status") != "ok":
        return result

    dob = fetch_employee_dob(emp)
    payload = {
        "date_of_birth": dob.isoformat() if dob else None,
        "dob": dob.isoformat() if dob else None,
    }
    snapshot = get_consolidation_snapshot(emp)
    if not snapshot or snapshot.get("error"):
        result["status"] = "failed"
        result["reason"] = (
            (snapshot or {}).get("error")
            or "old-age snapshot missing after save"
        )
        return result

    snapshot = _attach_oldage(snapshot, payload) or snapshot
    if not snapshot.get("date_of_birth") and dob:
        snapshot["date_of_birth"] = dob.isoformat()

    pdf_path = str(result.get("pdf") or "").strip()
    if pdf_path:
        out_dir = Path(pdf_path).parent
    else:
        out_dir = Path(result.get("output_dir") or ".")

    case_no = result.get("case_no") or snapshot.get("case_no") or ""
    try:
        files = write_consolidation_files(
            snapshot, out_dir, emp, case_no=case_no
        )
    except Exception as exc:
        result["status"] = "failed"
        result["reason"] = f"old-age pdf error: {exc}"
        return result

    result["pdf"] = files.get("pdf") or result.get("pdf") or ""
    if files.get("pdf_error") and not files.get("pdf"):
        result["status"] = "failed"
        result["reason"] = f"old-age pdf error: {files.get('pdf_error')}"
    return result


def process_one_emp_oldage(
    emp_cd: str,
    out_dir: Path,
    excel_case_no: str = "",
    excel_roll_no: str = "",
) -> dict:
    result = m2_bulk.process_one_emp(
        emp_cd, out_dir, excel_case_no=excel_case_no, excel_roll_no=excel_roll_no
    )
    return _rewrite_pdf_with_oldage(str(emp_cd or "").strip()[:5], result)


def run_bulk_from_excel(source, output_dir: Path | None = None) -> dict:
    """Full old-age bulk run. Same Excel shape as Met2; PDFs include OA tables."""
    emp_rows = read_emp_rows_from_excel(source)
    out_dir = Path(output_dir) if output_dir else m2_bulk.default_run_output_dir()
    out_dir.mkdir(parents=True, exist_ok=True)
    if m2_bulk.TEMP_TQS_SPLIT_ENABLED:
        (out_dir / m2_bulk.TEMP_TQS_FOLDER_GE).mkdir(parents=True, exist_ok=True)
        (out_dir / m2_bulk.TEMP_TQS_FOLDER_LT).mkdir(parents=True, exist_ok=True)

    rows = []
    for item in emp_rows:
        rows.append(
            process_one_emp_oldage(
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
        "temp_tqs_split": m2_bulk.TEMP_TQS_SPLIT_ENABLED,
        "temp_tqs_folder_ge": m2_bulk.TEMP_TQS_FOLDER_GE,
        "temp_tqs_folder_lt": m2_bulk.TEMP_TQS_FOLDER_LT,
        "oldage_bulk": True,
    }
