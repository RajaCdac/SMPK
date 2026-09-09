"""Excel report from methodology2_consolidation (M-I vs M-II comparison)."""

from __future__ import annotations

from datetime import date, datetime, time, timedelta
from io import BytesIO

from django.utils import timezone
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font
from openpyxl.utils import get_column_letter

from methodology2.models import Methodology2Consolidation

HEADERS = [
    "Sl. NO.",
    "Pensioner Name",
    "Case NO.",
    "Roll No.",
    "Employee Code",
    "Retirement Date",
    "Class",
    "Designation",
    "Pay (Revised) at the time of retirement",
    "Pay scale at the time of Retirement",
    "Basic Pension amt as per M-I in 2017 (277 CPI)",
    "Revised Basic Pension amt as per M-II in 2017 (277 CPI)",
    "Beneficial under M-I or M-II?",
    "Amt of Benefit (PM) excluding D.A",
    "Basic Pension amt as per M-I in 2022 (359 CPI)",
    "Revised Basic Pension amt as per M-II in 2022 (359 CPI)",
    "Beneficial under M-I or M-II?",
    "Amt of Benefit (PM) excluding D.A",
]


def _num(value):
    if value is None:
        return None
    return float(value)


def _class_label(category):
    cat = str(category or "").strip()
    mapping = {"1": "I", "2": "II", "3": "III", "4": "IV"}
    return mapping.get(cat, cat)


def _display_name(row: Methodology2Consolidation) -> str:
    if row.is_employee_pension:
        return (row.name or row.wage_emp_name or "").strip()
    return (row.pensioner_name or row.name or "").strip()


def _m2_amounts(row: Methodology2Consolidation):
    if row.is_employee_pension:
        return _num(row.m2_pension_277), _num(row.m2_pension_359)
    return _num(row.m2_family_pension_277), _num(row.m2_family_pension_359)


def _beneficial(m1, m2):
    if m1 is None and m2 is None:
        return "", None
    if m1 is None:
        return "M-II", m2
    if m2 is None:
        return "M-I", m1
    if m2 > m1:
        return "M-II", round(m2 - m1, 2)
    if m1 > m2:
        return "M-I", round(m1 - m2, 2)
    return "Equal", 0


def _row_values(sl_no: int, row: Methodology2Consolidation):
    m1_277 = _num(row.m1_family_pension_277)
    m1_359 = _num(row.m1_family_pension_359)
    m2_277, m2_359 = _m2_amounts(row)
    ben_277, amt_277 = _beneficial(m1_277, m2_277)
    ben_359, amt_359 = _beneficial(m1_359, m2_359)
    ret = row.retirement_date
    return [
        sl_no,
        _display_name(row),
        row.case_no or "",
        row.roll_no or "",
        row.emp_cd,
        ret.strftime("%d-%m-%Y") if ret else "",
        _class_label(row.category),
        row.designation or "",
        _num(row.last_pay),
        row.scale or "",
        m1_277,
        m2_277,
        ben_277,
        amt_277,
        m1_359,
        m2_359,
        ben_359,
        amt_359,
    ]


def report_filename(
    from_date: date | None = None, to_date: date | None = None
) -> str:
    if from_date and to_date:
        return (
            f"M2_consolidation_report_{from_date:%Y%m%d}_{to_date:%Y%m%d}.xlsx"
        )
    return f"M2_consolidation_report_{date.today():%Y-%m-%d}.xlsx"


def _inclusive_updated_range(from_date: date, to_date: date):
    """
    Day bounds for updated_at filtering.

    Avoid __date / CONVERT_TZ: MySQL often lacks timezone tables, so
    DATE(CONVERT_TZ(...)) becomes NULL and returns zero rows.
    """
    start = timezone.make_aware(datetime.combine(from_date, time.min))
    end_excl = timezone.make_aware(
        datetime.combine(to_date + timedelta(days=1), time.min)
    )
    return start, end_excl


def build_consolidation_report_bytes(
    from_date: date, to_date: date
) -> tuple[bytes, int]:
    """
    Excel export filtered by methodology2_consolidation.updated_at date range
    (inclusive calendar days in Django TIME_ZONE).
    """
    if from_date > to_date:
        raise ValueError("from_date cannot be after to_date")

    start, end_excl = _inclusive_updated_range(from_date, to_date)
    rows = list(
        Methodology2Consolidation.objects.filter(
            updated_at__gte=start,
            updated_at__lt=end_excl,
        ).order_by("case_no", "emp_cd")
    )

    wb = Workbook()
    ws = wb.active
    ws.title = "M1 vs M2 Report"
    ws.append(HEADERS)

    header_font = Font(bold=True)
    header_align = Alignment(
        wrap_text=True, vertical="center", horizontal="center"
    )
    for cell in ws[1]:
        cell.font = header_font
        cell.alignment = header_align

    for idx, row in enumerate(rows, start=1):
        ws.append(_row_values(idx, row))

    for col_idx, header in enumerate(HEADERS, start=1):
        width = min(max(len(header) + 2, 12), 42)
        ws.column_dimensions[get_column_letter(col_idx)].width = width

    buf = BytesIO()
    wb.save(buf)
    buf.seek(0)
    return buf.getvalue(), len(rows)
