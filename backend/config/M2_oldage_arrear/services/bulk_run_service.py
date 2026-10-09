"""
Old Age bulk Excel runner.

Reuses Met2 calc/save, then attaches DOB + old-age print columns and rewrites PDF.
Supports prepare / row / finish (progress UI).
When generate_pdf is on: PDFs only. When off: form-layout Report.xlsx
(Excel is also available later via batch download from DB).
"""

from __future__ import annotations

import csv
import json
import secrets
import shutil
import tempfile
from collections.abc import Callable
from pathlib import Path

from M2_oldage_arrear.services.consolidation_bridge import (
    _attach_oldage,
    fetch_employee_dob,
    get_consolidation_snapshot,
)
from M2_oldage_arrear.services.manual_run_service import (
    FORM_REPORT_KEYS,
    _calc_fields_from_snapshot,
    _write_uploaded_manual_with_outputs,
)
from methodology2.services.bulk_excel_service import read_emp_rows_from_excel
from methodology2.services.bulk_pdf_service import write_consolidation_files
from methodology2.services import bulk_run_service as m2_bulk

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


def _sessions_root() -> Path:
    root = Path(tempfile.gettempdir()) / "m2_oa_bulk_sessions"
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


def _ensure_bulk_output_dirs(out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    if m2_bulk.TEMP_TQS_SPLIT_ENABLED:
        (out_dir / m2_bulk.TEMP_TQS_FOLDER_GE).mkdir(parents=True, exist_ok=True)
        (out_dir / m2_bulk.TEMP_TQS_FOLDER_LT).mkdir(parents=True, exist_ok=True)


def _enrich_result_for_report(emp: str, result: dict, snapshot: dict | None) -> dict:
    """Attach form-report fields (M1/M2/OA) used by Report.xlsx — match PDF."""
    if not snapshot or snapshot.get("error"):
        return result
    snap = dict(snapshot)
    snap.setdefault("emp_cd", emp)
    if result.get("case_no"):
        snap["case_no"] = result.get("case_no")
    if result.get("roll_no"):
        snap["roll_no"] = result.get("roll_no")
    if result.get("category"):
        snap["category"] = result.get("category")
    calc = _calc_fields_from_snapshot(snap)
    for key in FORM_REPORT_KEYS:
        if key == "emp_cd":
            result[key] = emp
            continue
        # Always take calc (same source as PDF columns); do not keep stale keys.
        result[key] = calc.get(key)
    return result


def _jsonable(value):
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, dict):
        return {str(k): _jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(v) for v in value]
    # Decimal / date / Path / etc.
    try:
        from decimal import Decimal

        if isinstance(value, Decimal):
            return float(value)
    except Exception:
        pass
    try:
        from datetime import date, datetime

        if isinstance(value, (date, datetime)):
            return value.isoformat()
    except Exception:
        pass
    return str(value)


def _rewrite_pdf_with_oldage(
    emp: str, result: dict, *, generate_pdf: bool = True
) -> dict:
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

    if not generate_pdf:
        result["pdf"] = ""
        return _enrich_result_for_report(emp, result, snapshot)

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

    return _enrich_result_for_report(emp, result, snapshot)


def process_one_emp_oldage(
    emp_cd: str,
    out_dir: Path,
    excel_case_no: str = "",
    excel_roll_no: str = "",
    generate_pdf: bool = True,
) -> dict:
    result = m2_bulk.process_one_emp(
        emp_cd,
        out_dir,
        excel_case_no=excel_case_no,
        excel_roll_no=excel_roll_no,
        generate_pdf=generate_pdf,
    )
    return _rewrite_pdf_with_oldage(
        str(emp_cd or "").strip()[:5], result, generate_pdf=generate_pdf
    )


def finalize_bulk_run(
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
        "temp_tqs_split": m2_bulk.TEMP_TQS_SPLIT_ENABLED,
        "temp_tqs_folder_ge": m2_bulk.TEMP_TQS_FOLDER_GE,
        "temp_tqs_folder_lt": m2_bulk.TEMP_TQS_FOLDER_LT,
        "oldage_bulk": True,
    }


def prepare_bulk_session(
    source: bytes | bytearray,
    output_dir: Path | None = None,
    *,
    generate_pdf: bool = True,
) -> dict:
    """Save upload + EMP list in temp; return session_id for row-by-row processing."""
    from M2_oldage_arrear.models import M2OldAgeBatch
    from M2_oldage_arrear.services.batch_service import create_batch

    out_dir = Path(output_dir) if output_dir else m2_bulk.default_run_output_dir()
    _ensure_bulk_output_dirs(out_dir)

    emp_rows = read_emp_rows_from_excel(source)
    if not emp_rows:
        raise ValueError("No EMP_CD rows in Excel")

    batch = create_batch(
        source=M2OldAgeBatch.SOURCE_AUTO,
        case_count=len(emp_rows),
        output_dir=out_dir,
        generate_pdf=generate_pdf,
    )

    session_id = secrets.token_hex(8)
    sess = _session_dir(session_id)
    sess.mkdir(parents=True, exist_ok=False)

    source_bytes = bytes(source)
    (sess / "upload.xlsx").write_bytes(source_bytes)
    (sess / "rows.json").write_text(
        json.dumps(emp_rows, ensure_ascii=False), encoding="utf-8"
    )
    (sess / "results.json").write_text("[]", encoding="utf-8")
    meta = {
        "session_id": session_id,
        "batch_id": batch.batch_id,
        "stamp": batch.stamp,
        "case_count": batch.case_count,
        "source": batch.source,
        "generate_pdf": bool(generate_pdf),
        "total": len(emp_rows),
        "output_dir": str(out_dir),
    }
    (sess / "meta.json").write_text(json.dumps(meta), encoding="utf-8")
    return meta


def run_bulk_session_row(
    session_id: str, index: int, output_dir: Path | None = None
) -> dict:
    """Process one EMP_CD row (0-based) for UI progress."""
    from M2_oldage_arrear.services.batch_service import record_batch_case

    sess = _session_dir(session_id)
    if not sess.is_dir():
        raise ValueError("Bulk session not found or expired")

    meta = json.loads((sess / "meta.json").read_text(encoding="utf-8"))
    out_dir = (
        Path(output_dir)
        if output_dir
        else Path(meta.get("output_dir") or m2_bulk.default_run_output_dir())
    )
    _ensure_bulk_output_dirs(out_dir)
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
        item = rows[idx]
        result = process_one_emp_oldage(
            item.get("emp_cd") or "",
            out_dir,
            excel_case_no=item.get("case_no") or "",
            excel_roll_no=item.get("roll_no") or "",
            generate_pdf=generate_pdf,
        )
        if batch_id:
            record_batch_case(
                batch_id,
                emp_cd=result.get("emp_cd") or item.get("emp_cd") or "",
                status=result.get("status") or "",
                case_no=result.get("case_no") or "",
                roll_no=result.get("roll_no") or "",
                reason=result.get("reason") or "",
            )
        results.append(result)
        (sess / "results.json").write_text(
            json.dumps(_jsonable(results), ensure_ascii=False), encoding="utf-8"
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


def finish_bulk_session(session_id: str, output_dir: Path | None = None) -> dict:
    from M2_oldage_arrear.services.batch_service import finalize_batch

    sess = _session_dir(session_id)
    if not sess.is_dir():
        raise ValueError("Bulk session not found or expired")

    meta = json.loads((sess / "meta.json").read_text(encoding="utf-8"))
    out_dir = (
        Path(output_dir)
        if output_dir
        else Path(meta.get("output_dir") or m2_bulk.default_run_output_dir())
    )
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
        summary = finalize_bulk_run(
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
        _cleanup_session(sess)


def run_bulk_from_excel(
    source,
    output_dir: Path | None = None,
    *,
    generate_pdf: bool = True,
    on_progress: ProgressCallback | None = None,
) -> dict:
    """Full old-age bulk run. Same Excel shape as Met2; PDFs include OA tables."""
    emp_rows = read_emp_rows_from_excel(source)
    out_dir = Path(output_dir) if output_dir else m2_bulk.default_run_output_dir()
    _ensure_bulk_output_dirs(out_dir)

    source_bytes = bytes(source) if isinstance(source, (bytes, bytearray)) else None
    if source_bytes is None and hasattr(source, "read"):
        source_bytes = source.read()

    total = len(emp_rows)
    rows = []
    for idx, item in enumerate(emp_rows, start=1):
        result = process_one_emp_oldage(
            item["emp_cd"],
            out_dir,
            excel_case_no=item.get("case_no") or "",
            excel_roll_no=item.get("roll_no") or "",
            generate_pdf=generate_pdf,
        )
        rows.append(result)
        if on_progress:
            on_progress(idx, total, str(result.get("emp_cd") or ""), result)

    return finalize_bulk_run(
        out_dir, source_bytes, rows, generate_pdf=generate_pdf
    )
