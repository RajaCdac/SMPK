"""
Consolidation batches for OA auto / manual bulk runs.

Batch identity = IST stamp + source; Excel export later by batch_id from DB.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from io import BytesIO
from pathlib import Path

from django.db import connection

from M2_oldage_arrear.models import (
    M2OldAgeBatch,
    M2OldAgeBatchCase,
    M2OldageArrearConsolidation,
)
from M2_oldage_arrear.services.manual_run_service import (
    FORM_REPORT_HEADERS,
    FORM_REPORT_KEYS,
    _calc_fields_from_snapshot,
)

try:
    from zoneinfo import ZoneInfo

    _IST = ZoneInfo("Asia/Kolkata")
except Exception:  # pragma: no cover
    _IST = timezone(timedelta(hours=5, minutes=30), name="IST")


def _now_ist() -> datetime:
    return datetime.now(_IST)


def ensure_batch_tables() -> None:
    """Create batch tables if missing (project often runs without migrations)."""
    with connection.cursor() as cursor:
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS m2_oldage_arrear_batch (
                id BIGINT AUTO_INCREMENT PRIMARY KEY,
                batch_id VARCHAR(64) NOT NULL UNIQUE,
                source VARCHAR(20) NOT NULL,
                stamp VARCHAR(32) NOT NULL,
                run_at DATETIME(6) NOT NULL,
                case_count INT UNSIGNED NOT NULL DEFAULT 0,
                ok_count INT UNSIGNED NOT NULL DEFAULT 0,
                failed_count INT UNSIGNED NOT NULL DEFAULT 0,
                skipped_count INT UNSIGNED NOT NULL DEFAULT 0,
                output_dir VARCHAR(500) NOT NULL DEFAULT '',
                generate_pdf TINYINT(1) NOT NULL DEFAULT 1,
                status VARCHAR(20) NOT NULL DEFAULT 'running',
                created_at DATETIME(6) NOT NULL,
                updated_at DATETIME(6) NOT NULL,
                INDEX m2_oa_batch_stamp_idx (stamp),
                INDEX m2_oa_batch_source_idx (source),
                INDEX m2_oa_batch_run_at_idx (run_at)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS m2_oldage_arrear_batch_case (
                id BIGINT AUTO_INCREMENT PRIMARY KEY,
                batch_pk BIGINT NOT NULL,
                emp_cd VARCHAR(5) NOT NULL,
                case_no VARCHAR(20) NOT NULL DEFAULT '',
                roll_no VARCHAR(30) NOT NULL DEFAULT '',
                status VARCHAR(20) NOT NULL DEFAULT '',
                reason VARCHAR(500) NOT NULL DEFAULT '',
                created_at DATETIME(6) NOT NULL,
                UNIQUE KEY uniq_m2_oa_batch_case_emp (batch_pk, emp_cd),
                INDEX m2_oa_batch_case_emp_idx (emp_cd),
                CONSTRAINT fk_m2_oa_batch_case_batch
                  FOREIGN KEY (batch_pk) REFERENCES m2_oldage_arrear_batch(id)
                  ON DELETE CASCADE
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            """
        )
        # Optional column on consolidation (ignore if already present).
        try:
            cursor.execute(
                """
                ALTER TABLE m2_oldage_arrear_consolidation
                ADD COLUMN last_batch_id VARCHAR(64) NOT NULL DEFAULT ''
                """
            )
        except Exception:
            pass
        try:
            cursor.execute(
                """
                CREATE INDEX m2_oa_consol_last_batch_idx
                ON m2_oldage_arrear_consolidation (last_batch_id)
                """
            )
        except Exception:
            pass


def create_batch(
    *,
    source: str,
    case_count: int,
    output_dir: str | Path = "",
    generate_pdf: bool = True,
    run_at: datetime | None = None,
) -> M2OldAgeBatch:
    ensure_batch_tables()
    when = run_at or _now_ist()
    if when.tzinfo is None:
        when = when.replace(tzinfo=_IST)
    else:
        when = when.astimezone(_IST)
    stamp = when.strftime("%Y-%m-%d_%H%M")
    src = str(source or "").strip().lower()
    if src not in (M2OldAgeBatch.SOURCE_AUTO, M2OldAgeBatch.SOURCE_MANUAL):
        src = M2OldAgeBatch.SOURCE_AUTO
    batch_id = f"{src}_{stamp}"
    # Avoid clash if two prepares in same minute.
    base = batch_id
    n = 1
    while M2OldAgeBatch.objects.filter(batch_id=batch_id).exists():
        n += 1
        batch_id = f"{base}_{n}"

    return M2OldAgeBatch.objects.create(
        batch_id=batch_id,
        source=src,
        stamp=stamp,
        run_at=when,
        case_count=int(case_count or 0),
        output_dir=str(output_dir or ""),
        generate_pdf=bool(generate_pdf),
        status=M2OldAgeBatch.STATUS_RUNNING,
    )


def record_batch_case(
    batch_id: str,
    *,
    emp_cd: str,
    status: str = "",
    case_no: str = "",
    roll_no: str = "",
    reason: str = "",
) -> None:
    ensure_batch_tables()
    emp = str(emp_cd or "").strip()[:5]
    if not batch_id or not emp:
        return
    batch = M2OldAgeBatch.objects.filter(batch_id=batch_id).first()
    if not batch:
        return
    M2OldAgeBatchCase.objects.update_or_create(
        batch=batch,
        emp_cd=emp,
        defaults={
            "case_no": str(case_no or "")[:20],
            "roll_no": str(roll_no or "")[:30],
            "status": str(status or "")[:20],
            "reason": str(reason or "")[:500],
        },
    )
    if str(status or "").lower() == "ok":
        M2OldageArrearConsolidation.objects.filter(emp_cd=emp).update(
            last_batch_id=batch_id
        )


def finalize_batch(batch_id: str, results: list[dict] | None = None) -> M2OldAgeBatch | None:
    ensure_batch_tables()
    batch = M2OldAgeBatch.objects.filter(batch_id=batch_id).first()
    if not batch:
        return None
    rows = results or []
    if rows:
        batch.ok_count = sum(1 for r in rows if r.get("status") == "ok")
        batch.failed_count = sum(1 for r in rows if r.get("status") == "failed")
        batch.skipped_count = sum(1 for r in rows if r.get("status") == "skipped")
        batch.case_count = len(rows)
    else:
        qs = batch.cases.all()
        batch.ok_count = qs.filter(status="ok").count()
        batch.failed_count = qs.filter(status="failed").count()
        batch.skipped_count = qs.filter(status="skipped").count()
        if batch.case_count <= 0:
            batch.case_count = qs.count()
    batch.status = M2OldAgeBatch.STATUS_COMPLETED
    batch.save(
        update_fields=[
            "ok_count",
            "failed_count",
            "skipped_count",
            "case_count",
            "status",
            "updated_at",
        ]
    )
    return batch


def list_batches(limit: int = 50, source: str | None = None) -> list[dict]:
    ensure_batch_tables()
    qs = M2OldAgeBatch.objects.all().order_by("-run_at", "-id")
    if source:
        qs = qs.filter(source=str(source).strip().lower())
    out = []
    for b in qs[: max(1, min(int(limit or 50), 200))]:
        out.append(
            {
                "batch_id": b.batch_id,
                "source": b.source,
                "stamp": b.stamp,
                "run_at": b.run_at.isoformat() if b.run_at else None,
                "case_count": b.case_count,
                "ok_count": b.ok_count,
                "failed_count": b.failed_count,
                "skipped_count": b.skipped_count,
                "generate_pdf": b.generate_pdf,
                "status": b.status,
                "output_dir": b.output_dir,
                "label": (
                    f"{b.stamp} · {b.source} · {b.case_count} cases "
                    f"(ok {b.ok_count})"
                ),
            }
        )
    return out


def _report_snapshot_from_obj(obj) -> dict:
    """Fields the bulk form report reads from a saved consolidation row."""
    return {
        "emp_cd": obj.emp_cd,
        "name": obj.name,
        "pensioner_name": obj.pensioner_name,
        "wage_emp_name": getattr(obj, "wage_emp_name", "") or "",
        "case_no": obj.case_no,
        "roll_no": obj.roll_no,
        "category": obj.category,
        "designation": obj.designation,
        "retirement_date": (
            obj.retirement_date.isoformat() if obj.retirement_date else None
        ),
        "last_pay": obj.last_pay,
        "scale": obj.scale,
        "is_employee_pension": obj.is_employee_pension,
        "m1_family_pension_277": obj.m1_family_pension_277,
        "m1_family_pension_359": obj.m1_family_pension_359,
        "m2_pension_277": obj.m2_pension_277,
        "m2_pension_359": obj.m2_pension_359,
        "m2_family_pension_277": obj.m2_family_pension_277,
        "m2_family_pension_359": obj.m2_family_pension_359,
        "pension_comparison": obj.pension_comparison or {},
        "oldage_benefit": getattr(obj, "oldage_benefit", None) or {},
        "tqs_yr": obj.tqs_yr,
        "tqs_month": obj.tqs_month,
        "tqs_days": obj.tqs_days,
    }


def _saved_consolidation_for_report(emp: str):
    """Prefer the old-age save. Fall back to the Methodology 2 save."""
    from methodology2.models import Methodology2Consolidation

    obj = M2OldageArrearConsolidation.objects.filter(emp_cd=emp).first()
    if obj is not None:
        return obj
    return Methodology2Consolidation.objects.filter(emp_cd=emp).first()


def build_emp_list_report_excel_bytes(emp_codes: list[str]) -> tuple[bytes, str, dict]:
    """
    Same Report.xlsx as a bulk batch, for an uploaded EMP_CD list.

    Does not recalculate. Reads the saved consolidation. Row order follows
    the upload. An employee with no save is still listed, with blank amounts.
    """
    import pandas as pd

    from M2_oldage_arrear.services.manual_run_service import _base_result

    codes: list[str] = []
    seen: set[str] = set()
    for raw in emp_codes or []:
        emp = str(raw or "").strip()[:5]
        if not emp or emp in seen:
            continue
        seen.add(emp)
        codes.append(emp)
    if not codes:
        raise ValueError("Excel has no employee codes")

    rows_out: list[dict] = []
    found = 0
    for emp in codes:
        obj = _saved_consolidation_for_report(emp)
        if obj is None:
            calc = _base_result(emp)
        else:
            found += 1
            calc = _calc_fields_from_snapshot(_report_snapshot_from_obj(obj))
            calc["emp_cd"] = emp
        rows_out.append({k: calc.get(k) for k in FORM_REPORT_KEYS})

    if found == 0:
        raise ValueError(
            "None of these employees have a saved consolidation. "
            "Save the consolidation first, then generate the report."
        )

    df = pd.DataFrame(rows_out, columns=FORM_REPORT_KEYS)
    df.columns = FORM_REPORT_HEADERS
    buf = BytesIO()
    df.to_excel(buf, index=False)
    summary = {
        "requested": len(codes),
        "found": found,
        "missing": len(codes) - found,
    }
    return buf.getvalue(), "Report.xlsx", summary


def build_batch_report_excel_bytes(batch_id: str) -> tuple[bytes, str]:
    """
    Build form Report.xlsx for a batch from DB consolidations.

    Raises ValueError with a clear message when batch missing or no data.
    """
    import pandas as pd

    ensure_batch_tables()
    bid = str(batch_id or "").strip()
    if not bid:
        raise ValueError("batch_id is required")

    batch = M2OldAgeBatch.objects.filter(batch_id=bid).first()
    if not batch:
        raise ValueError(f"Batch not found: {bid}")

    case_emps = list(
        batch.cases.order_by("id").values_list("emp_cd", flat=True)
    )
    if not case_emps:
        raise ValueError(
            "No cases in this batch. Run consolidation first, then export Excel."
        )

    rows_out: list[dict] = []
    for emp in case_emps:
        obj = M2OldageArrearConsolidation.objects.filter(emp_cd=emp).first()
        if not obj:
            continue
        calc = _calc_fields_from_snapshot(_report_snapshot_from_obj(obj))
        calc["emp_cd"] = emp
        rows_out.append({k: calc.get(k) for k in FORM_REPORT_KEYS})

    if not rows_out:
        raise ValueError(
            "No consolidation data in DB for this batch. "
            "Run consolidation first, then export Excel."
        )

    df = pd.DataFrame(rows_out, columns=FORM_REPORT_KEYS)
    df.columns = FORM_REPORT_HEADERS
    buf = BytesIO()
    df.to_excel(buf, index=False)
    filename = f"Report_{batch.batch_id}.xlsx"
    return buf.getvalue(), filename
