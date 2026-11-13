"""
Family Pension Consolidation report (Excel).

Family cases only, from m2_oldage_arrear_consolidation. Picked by an uploaded
EMP_CD list or by the date the consolidation was saved.

Per CPI era (2017 / 2022) the employee, enhanced (50%) and family (30%)
Methodology-1 / Methodology-2 amounts come from the saved print columns.
The payment block (May 2026 – Oct 2026) comes from the Arrear calculation,
so it matches the Arrear sheet.
"""

from __future__ import annotations

from datetime import date, datetime, time, timedelta
from io import BytesIO

from django.utils import timezone
from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

from M2_oldage_arrear.models import M2OldageArrearConsolidation
from M2_oldage_arrear.services.da_service import lookup_da_pct
from methodology2.services.arrear_payment_service import (
    _money,
    calculate_consolidation_arrear,
)
from methodology2.services.arrear_sheet_service import paid_upto_label

WINDOW_FROM = (5, 2026)
WINDOW_TO = (10, 2026)
# (label, first month, last month) — fixed payment blocks of the report.
PAYMENT_BLOCKS = (
    ("May & June 2026", date(2026, 5, 1), date(2026, 6, 1)),
    ("July, Aug & Sep 2026", date(2026, 7, 1), date(2026, 9, 1)),
    ("Oct 2026", date(2026, 10, 1), date(2026, 10, 1)),
)
MAX_EMPLOYEES = 2000

_CLASS_ROMAN = {"1": "I", "2": "II", "3": "III", "4": "IV"}

FIXED_HEADERS = (
    "Sl. No.",
    "Family Pensioner Name",
    "DOB of Family Pensioner",
    "Ex-Emp Name",
    "Case No",
    "Roll No.",
    "Emp Code",
    "Retirement Date",
    "Date of Death",
    "TQS",
    "Class",
    "Designation",
    "Pay(Revised) at the time of retirement",
    "Pay Scale at the time of retirement",
)


def _era_headers(year: int, cpi: int) -> list[tuple[str, str]]:
    """(header, style) for one CPI era: employee, enhanced, family groups."""
    tag = f"{year}({cpi} CPI)"
    till_dod = f"(Jan {year} to till date of Death)"
    return [
        (f"Basic Employee Pension Amt as per M-1 in {tag} {till_dod}", "amt"),
        (f"Revised Basic Employee Pension amt as per M-2 in {tag} {till_dod}", "amt"),
        ("Beneficial under M-1 or M-2", "amt"),
        (f"Basic Employee Pension amt of Benefit(PM) excluding DA {till_dod}", "benefit"),
        (f"Basic Family Pension Amt (enhanced i.e. 50%) as per M-1 in {tag}", "amt"),
        (f"Revised Basic Family Pension Amt(enhanced i.e. 50%) as per M-2 in {tag}", "amt"),
        ("Beneficial under M-1 or M-2", "amt"),
        ("Enhanced (i.e. 50%) Basic Family Pension amt of Benefit(PM) excluding DA", "benefit"),
        (f"Basic Family Pension Amt (i.e. 30%) as per M-1 in {tag}", "amt"),
        (f"Revised Basic Family Pension Amt(i.e. 30%) as per M-2 in {tag}", "amt"),
        ("Beneficial under M-1 or M-2", "amt"),
        ("Basic Family Pension amt(i.e.30%) of Benefit(PM) excluding DA", "benefit"),
    ]


ERA_KINDS = ("employee", "enhanced", "family")

_THIN = Border(
    left=Side(style="thin", color="808080"),
    right=Side(style="thin", color="808080"),
    top=Side(style="thin", color="808080"),
    bottom=Side(style="thin", color="808080"),
)
_FILLS = {
    "amt": PatternFill("solid", fgColor="CCC0DA"),
    "benefit": PatternFill("solid", fgColor="FFC000"),
    "bill": PatternFill("solid", fgColor="558ED5"),
    "2017": PatternFill("solid", fgColor="FFFF00"),
    "2022": PatternFill("solid", fgColor="92D050"),
}
_WRAP = Alignment(wrap_text=True, vertical="center", horizontal="center")
_LEFT = Alignment(wrap_text=True, vertical="center", horizontal="left")
_RIGHT = Alignment(vertical="center", horizontal="right")


def _num(value):
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _dmy(value) -> str:
    if value in (None, ""):
        return ""
    if isinstance(value, datetime):
        value = value.date()
    if isinstance(value, date):
        return value.strftime("%d-%m-%Y")
    text = str(value).strip()[:10]
    parts = text.split("-")
    if len(parts) == 3 and len(parts[0]) == 4:
        return f"{parts[2]}-{parts[1]}-{parts[0]}"
    return text


def _scale_text(scale, retirement_date) -> str:
    from methodology2.services.class1_2_service import pay_scale_for_report

    return pay_scale_for_report(scale, retirement_date)


def _era_values(columns: list[dict], cpi: int) -> list:
    """M-1, M-2, beneficial, benefit for employee / enhanced / family at one CPI."""
    out = []
    for kind in ERA_KINDS:
        col = next(
            (
                c
                for c in columns
                if str(c.get("cpi")) == str(cpi) and c.get("kind") == kind
            ),
            None,
        )
        m1 = _num(col.get("m1")) if col else None
        m2 = None
        if col:
            m2 = _num(col.get("m2_base") if col.get("m2_base") is not None else col.get("m2"))
        if m1 is None or m2 is None:
            beneficial = "" if m1 is None and m2 is None else ("M-2" if m1 is None else "M-1")
            benefit = None
        else:
            benefit = round(m2 - m1, 2)
            beneficial = "M-2" if m2 > m1 else ("M-1" if m1 > m2 else "Equal")
        out.extend([m1, m2, beneficial, benefit])
    return out


def _payment_values(emp: str) -> tuple[list, str]:
    """Old age diff and basic+old age per block, DA, months, total bill."""
    calc = calculate_consolidation_arrear(emp, WINDOW_FROM[0], WINDOW_FROM[1], WINDOW_TO[0], WINDOW_TO[1])
    blanks = [None] * (len(PAYMENT_BLOCKS) * 2 + 3)
    if calc.get("error"):
        return blanks, str(calc["error"])
    oa_by_block = [0.0] * len(PAYMENT_BLOCKS)
    basic_by_block = [0.0] * len(PAYMENT_BLOCKS)
    months_total = 0
    for line in calc.get("lines") or []:
        # CR 03-11-2026: months with a negative benefit are not paid or counted.
        if line.get("not_payable"):
            continue
        # CR 12-11-2026: per-month amounts carry the day-split change-over
        # month (enhanced → family); older results fall back to the monthly rate.
        per_month = {
            str(m.get("month"))[:10]: m for m in (line.get("month_amounts") or [])
        }
        cursor = date.fromisoformat(str(line["from_iso"])[:10])
        last = date.fromisoformat(str(line["to_iso"])[:10])
        while cursor <= last:
            entry = per_month.get(cursor.isoformat())
            for index, (_, first, final) in enumerate(PAYMENT_BLOCKS):
                if first <= cursor <= final:
                    if entry is not None:
                        oa_by_block[index] += float(entry.get("oa") or 0)
                        basic_by_block[index] += float(entry.get("amount") or 0)
                    else:
                        oa_by_block[index] += float(line.get("oldage_benefit") or 0)
                        basic_by_block[index] += float(line.get("monthly_amount") or 0)
            months_total += 1
            cursor = date(cursor.year + (cursor.month == 12), cursor.month % 12 + 1, 1)
    values = [_money(v) for v in oa_by_block] + [_money(v) for v in basic_by_block]
    values += [calc.get("da_relief"), months_total, calc.get("total")]
    return values, ""


def _da_header(class12_present: bool, class34_present: bool) -> str:
    def rates(grp, cpi):
        return ", ".join(
            f"For {label.replace(' 2026', '')} @{lookup_da_pct(grp, cpi, first):g}%"
            for label, first, _ in PAYMENT_BLOCKS
        )

    parts = []
    if class34_present or not class12_present:
        parts.append(rates(3, "359") if not class12_present else f"Class III/IV: {rates(3, '359')}")
    if class12_present:
        parts.append(f"Class I/II: {rates(1, '277')}")
    return f"DA as per applicable % ({'; '.join(parts)})"


def _tail_headers(da_header: str) -> list[tuple[str, str]]:
    heads = [(f"Total Diff amt of Old Age benefit for {label}", "plain") for label, _, _ in PAYMENT_BLOCKS]
    heads += [(f"Total Basic & Old Age Benefit for {label}", "plain") for label, _, _ in PAYMENT_BLOCKS]
    heads += [
        (da_header, "plain"),
        ("No. of Months of Payment", "plain"),
        ("Total Bill Amount", "bill"),
        ("Phase", "plain"),
        ("Arrear to be paid upto", "plain"),
        ("Abstract No.", "plain"),
        ("Abstract Date", "plain"),
        ("Remarks", "plain"),
    ]
    return heads


def _is_family(obj) -> bool:
    return obj.is_employee_pension is False or obj.date_of_death is not None


def _rows_by_emp_codes(emp_codes) -> tuple[list, dict]:
    codes: list[str] = []
    seen: set[str] = set()
    for raw in emp_codes or []:
        emp = str(raw or "").strip()[:5]
        if emp and emp not in seen:
            seen.add(emp)
            codes.append(emp)
    if not codes:
        raise ValueError("Excel must include a column named EMP_CD.")
    if len(codes) > MAX_EMPLOYEES:
        raise ValueError(f"Upload at most {MAX_EMPLOYEES} employee codes at a time.")
    saved = {o.emp_cd: o for o in M2OldageArrearConsolidation.objects.filter(emp_cd__in=codes)}
    rows, not_saved, not_family = [], [], []
    for emp in codes:
        obj = saved.get(emp)
        if obj is None:
            not_saved.append(emp)
        elif not _is_family(obj):
            not_family.append(emp)
        else:
            rows.append(obj)
    return rows, {
        "requested": len(codes),
        "not_saved": not_saved,
        "not_family": not_family,
    }


def _rows_by_saved_date(from_date: date, to_date: date) -> tuple[list, dict]:
    if from_date > to_date:
        raise ValueError("From date cannot be after To date.")
    start = timezone.make_aware(datetime.combine(from_date, time.min))
    end = timezone.make_aware(datetime.combine(to_date + timedelta(days=1), time.min))
    rows = [
        o
        for o in M2OldageArrearConsolidation.objects.filter(
            updated_at__gte=start, updated_at__lt=end
        ).order_by("case_no", "emp_cd")
        if _is_family(o)
    ]
    return rows, {"requested": len(rows), "not_saved": [], "not_family": []}


def build_family_pension_report(
    *,
    emp_codes=None,
    from_date: date | None = None,
    to_date: date | None = None,
    phase: str = "",
) -> tuple[bytes, str, dict]:
    if emp_codes is not None:
        rows, summary = _rows_by_emp_codes(emp_codes)
    elif from_date and to_date:
        rows, summary = _rows_by_saved_date(from_date, to_date)
    else:
        raise ValueError("Upload an EMP_CD Excel, or choose a From and To date.")
    if not rows:
        raise ValueError("No saved family pension consolidation found for this selection.")

    class12_present = any(str(o.category).strip() in ("1", "2") for o in rows)
    class34_present = any(str(o.category).strip() not in ("1", "2") for o in rows)
    era_2017 = _era_headers(2017, 277)
    era_2022 = _era_headers(2022, 359)
    tail = _tail_headers(_da_header(class12_present, class34_present))

    wb = Workbook()
    ws = wb.active
    ws.title = "Family Pension Report"

    col = 1
    for title in FIXED_HEADERS:
        ws.merge_cells(start_row=1, start_column=col, end_row=2, end_column=col)
        cell = ws.cell(1, col, title)
        cell.font = Font(bold=True)
        cell.alignment = _WRAP
        cell.border = _THIN
        ws.cell(2, col).border = _THIN
        col += 1
    for era, label, fill in ((era_2017, "w.e.f. 2017", "2017"), (era_2022, "w.e.f. 2022", "2022")):
        ws.merge_cells(start_row=1, start_column=col, end_row=1, end_column=col + len(era) - 1)
        band = ws.cell(1, col, label)
        band.font = Font(bold=True, size=16)
        band.alignment = _WRAP
        for offset, (title, style) in enumerate(era):
            ws.cell(1, col + offset).fill = _FILLS[fill]
            ws.cell(1, col + offset).border = _THIN
            cell = ws.cell(2, col + offset, title)
            cell.font = Font(bold=True, size=9)
            cell.alignment = _WRAP
            cell.fill = _FILLS[style]
            cell.border = _THIN
        col += len(era)
    tail_start = col
    for title, style in tail:
        cell = ws.cell(2, col, title)
        cell.font = Font(bold=True, size=9)
        cell.alignment = _WRAP
        cell.border = _THIN
        if style in _FILLS:
            cell.fill = _FILLS[style]
        ws.cell(1, col).border = _THIN
        col += 1
    ws.row_dimensions[1].height = 30
    ws.row_dimensions[2].height = 120
    ws.freeze_panes = ws.cell(3, len(FIXED_HEADERS) + 1)

    phase_text = str(phase or "").strip()
    paid_upto = paid_upto_label(*WINDOW_FROM)
    money_cols = set()
    for idx, obj in enumerate(rows, start=1):
        cmp_ = obj.pension_comparison if isinstance(obj.pension_comparison, dict) else {}
        columns = [c for c in (cmp_.get("columns") or []) if isinstance(c, dict)]
        payment, remark = _payment_values(obj.emp_cd)
        values = [
            idx,
            obj.pensioner_name or cmp_.get("family_pensioner_name") or "",
            _dmy(cmp_.get("family_pensioner_dob")),
            obj.name or obj.wage_emp_name or "",
            obj.case_no or "",
            obj.roll_no or "",
            obj.emp_cd,
            _dmy(obj.retirement_date),
            _dmy(obj.date_of_death or cmp_.get("date_of_death")),
            obj.tqs_display,
            _CLASS_ROMAN.get(str(obj.category).strip(), obj.category or ""),
            obj.designation or "",
            _num(obj.last_pay),
            _scale_text(obj.scale, obj.retirement_date),
            *_era_values(columns, 277),
            *_era_values(columns, 359),
            *payment,
            phase_text,
            paid_upto,
            "",
            "",
            remark,
        ]
        excel_row = idx + 2
        for c, value in enumerate(values, start=1):
            cell = ws.cell(excel_row, c, value)
            cell.border = _THIN
            if isinstance(value, float):
                cell.number_format = "#,##0.00"
                cell.alignment = _RIGHT
                money_cols.add(c)
            else:
                cell.alignment = _LEFT if c in (2, 4, 12, 14) else _WRAP

    widths = {1: 6, 2: 26, 3: 12, 4: 26, 5: 9, 6: 12, 7: 9, 8: 12, 9: 12, 10: 14, 11: 7, 12: 22, 13: 12, 14: 22}
    for c in range(1, ws.max_column + 1):
        ws.column_dimensions[get_column_letter(c)].width = widths.get(c, 13 if c < tail_start else 14)

    buf = BytesIO()
    wb.save(buf)
    summary["found"] = len(rows)
    filename = f"Family_Pension_Report_{date.today():%Y%m%d}.xlsx"
    return buf.getvalue(), filename, summary
