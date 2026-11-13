"""
Pay & Cash arrear sheet for a list of saved consolidations.

Does not recalculate Methodology-2 and does not mark a row as paid.
"""

from __future__ import annotations

from datetime import date
from io import BytesIO

from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

from methodology2.services.arrear_payment_service import (
    calculate_consolidation_arrear,
    validate_arrear_period,
)

MAX_EMPLOYEES = 500

_FULL_MONTH = (
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
)
_CLASS_ROMAN = {"1": "I", "2": "II", "3": "III", "4": "IV"}

_FIXED_HEADERS = (
    "Sl No",
    "Name",
    "Employee Code",
    "Retirement Date",
    "Class",
    "Designation",
    "Pay (Revised) at the time of retirement",
    "Pay Scale at the time of retirement",
    "TQS",
    "Basic Pension as per M-I",
    "Basic Pension as per M-II",
    "CPI",
    "Beneficial under",
    "Amt of Benefit (Excluding DA)",
)
_TAIL_HEADERS = (
    "Total bill amount",
    "Phase",
    "Arrear to be paid upto",
    "Abstract No.",
)

_THIN = Border(
    left=Side(style="thin", color="B0B0B0"),
    right=Side(style="thin", color="B0B0B0"),
    top=Side(style="thin", color="B0B0B0"),
    bottom=Side(style="thin", color="B0B0B0"),
)
_HEADER_FILL = PatternFill("solid", fgColor="1F4E79")
_HEADER_FONT = Font(bold=True, color="FFFFFF", size=9)
_EMP_FILL = PatternFill("solid", fgColor="FFF2CC")
_WRAP = Alignment(wrap_text=True, vertical="center", horizontal="center")
_LEFT = Alignment(wrap_text=True, vertical="center", horizontal="left")
_RIGHT = Alignment(vertical="center", horizontal="right")


def paid_upto_label(from_month, from_year) -> str:
    """Month before this payment starts. Paying from May 2026 is paid upto April 2026."""
    month = int(from_month)
    year = int(from_year)
    if month <= 1:
        month = 12
        year -= 1
    else:
        month -= 1
    return f"{_FULL_MONTH[month - 1]}, {year}"


def _pension_obj(emp: str):
    from M2_oldage_arrear.models import M2OldageArrearConsolidation
    from methodology2.models import Methodology2Consolidation

    met2 = Methodology2Consolidation.objects.filter(emp_cd=emp).first()
    oa = M2OldageArrearConsolidation.objects.filter(emp_cd=emp).first()
    # CR 12-11-2026 (emp 46913): same pick as the arrear — the one saved last.
    if met2 is not None and oa is not None:
        def saved_at(obj):
            return getattr(obj, "updated_at", None) or getattr(obj, "created_at", None)

        m2_at, oa_at = saved_at(met2), saved_at(oa)
        return oa if (oa_at and (not m2_at or oa_at > m2_at)) else met2
    return met2 or oa


def _num(value):
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _dmy(value) -> str:
    if value is None or value == "":
        return ""
    if isinstance(value, date):
        return value.strftime("%d-%m-%Y")
    text = str(value).strip()[:10]
    parts = text.split("-")
    if len(parts) == 3 and len(parts[0]) == 4:
        return f"{parts[2]}-{parts[1]}-{parts[0]}"
    return text


def _class_label(category) -> str:
    text = str(category or "").strip()
    return _CLASS_ROMAN.get(text, text)


def _scale_text(scale, retirement_date) -> str:
    from methodology2.services.class1_2_service import pay_scale_for_report

    return pay_scale_for_report(scale, retirement_date)


def _identity(emp: str) -> dict:
    obj = _pension_obj(emp)
    if obj is None:
        return {
            "name": "",
            "case_no": "",
            "roll_no": "",
            "retirement_date": "",
            "class_label": "",
            "designation": "",
            "last_pay": None,
            "scale": "",
            "tqs": "",
        }
    retired = getattr(obj, "retirement_date", None)
    return {
        "name": str(getattr(obj, "name", "") or ""),
        # CR 03-11-2026: case / roll no are columns of the class-wise arrear templates.
        "case_no": str(getattr(obj, "case_no", "") or ""),
        "roll_no": str(getattr(obj, "roll_no", "") or ""),
        "retirement_date": _dmy(retired),
        "class_label": _class_label(getattr(obj, "category", "")),
        "designation": str(getattr(obj, "designation", "") or ""),
        "last_pay": _num(getattr(obj, "last_pay", None)),
        "scale": _scale_text(getattr(obj, "scale", ""), retired),
        "tqs": str(getattr(obj, "tqs_display", "") or ""),
    }


def _beneficial(diff) -> str:
    if diff is None:
        return ""
    if diff > 0.005:
        return "M-II"
    if diff < -0.005:
        return "M-I"
    return "Same"


def _pair(lines: list[dict]) -> dict:
    """One M-I / M-II pair when every month in the window uses it."""
    if not lines:
        return {
            "split": False,
            "m1": None,
            "m2": None,
            "cpi": "",
            "benefit": None,
            "beneficial": "",
        }
    same = (
        len({line.get("m1") for line in lines}) == 1
        and len({line.get("m2") for line in lines}) == 1
        and len({line.get("pension_diff") for line in lines}) == 1
        and len({line.get("cpi") for line in lines}) == 1
    )
    if not same:
        return {
            "split": True,
            "m1": None,
            "m2": None,
            "cpi": "",
            "benefit": None,
            "beneficial": "Split",
        }
    diff = lines[0].get("pension_diff")
    return {
        "split": False,
        "m1": lines[0].get("m1"),
        "m2": lines[0].get("m2"),
        "cpi": lines[0].get("cpi") or "",
        "benefit": diff,
        "beneficial": _beneficial(diff),
    }


def _add_month(d: date) -> date:
    if d.month == 12:
        return date(d.year + 1, 1, 1)
    return date(d.year, d.month + 1, 1)


def _prev_month(d: date) -> date:
    if d.month == 1:
        return date(d.year - 1, 12, 1)
    return date(d.year, d.month - 1, 1)


def _month_end(d: date) -> date:
    from calendar import monthrange

    return date(d.year, d.month, monthrange(d.year, d.month)[1])


def _short_month(d: date) -> str:
    return f"{_FULL_MONTH[d.month - 1][:3]} {d.year}"


def _payment_periods(from_month, from_year, to_month, to_year, class_grp=None) -> list[dict]:
    """
    One block per DA change inside the payment window.

    May–Jun stays one block and Jul–Sep stays the next when DA changes in July.
    An old-age start in June does not open another block.
    class_grp: 1 (class 1/2) or 3 (class 3/4) — only that group's DA changes.
    """
    from M2_oldage_arrear.services.da_service import da_wef_dates

    start = date(int(from_year), int(from_month), 1)
    end = date(int(to_year), int(to_month), 1)
    last = _month_end(end)
    points = {start}
    # CR 03-11-2026: class-wise sheets split only at their own DA changes.
    for grp in ((class_grp,) if class_grp else (1, 3)):
        for wef in da_wef_dates(grp, start, last):
            points.add(date(wef.year, wef.month, 1))
    ordered = [p for p in sorted(points) if start <= p <= end]
    periods = []
    for index, begin in enumerate(ordered):
        finish = _prev_month(ordered[index + 1]) if index + 1 < len(ordered) else end
        if finish < begin:
            continue
        title = _short_month(begin) if begin == finish else f"{_short_month(begin)} - {_short_month(finish)}"
        periods.append(
            {
                "id": begin.isoformat(),
                "from": begin,
                "to": finish,
                "title": title,
            }
        )
    return periods


def _line_months(line: dict) -> list[date]:
    start = date.fromisoformat(str(line.get("from_iso"))[:10])
    end = date.fromisoformat(str(line.get("to_iso"))[:10])
    months = []
    cursor = start
    while cursor <= end:
        months.append(cursor)
        cursor = _add_month(cursor)
    return months


def _period_id(periods: list[dict], month: date) -> str | None:
    for period in periods:
        if period["from"] <= month <= period["to"]:
            return period["id"]
    return None


def _amounts_by_period(lines: list[dict], periods: list[dict]) -> dict:
    from methodology2.services.arrear_payment_service import _money

    totals = {period["id"]: {"oa": 0.0, "basic": 0.0, "da": 0.0} for period in periods}
    for line in lines or []:
        months = _line_months(line)
        if not months:
            continue
        ids = [_period_id(periods, month) for month in months]
        if ids and len(set(ids)) == 1 and ids[0]:
            pid = ids[0]
            count = int(line.get("months") or len(months))
            # CR 12-11-2026: oldage_arrear has the day-split change-over month
            # (enhanced → family); old-age × months only for older results.
            oa_paid = line.get("oldage_arrear")
            if oa_paid is None:
                oa_paid = float(line.get("oldage_benefit") or 0) * count
            totals[pid]["oa"] = _money(totals[pid]["oa"] + float(oa_paid))
            totals[pid]["basic"] = _money(
                totals[pid]["basic"] + float(line.get("pension_arrear") or 0)
            )
            totals[pid]["da"] = _money(
                totals[pid]["da"] + float(line.get("da_relief") or 0)
            )
    return totals


def _pct_text(value) -> str:
    number = float(value or 0)
    if number == int(number):
        return str(int(number))
    return f"{number:g}"


def _column_date(value):
    if value is None or value == "":
        return None
    if isinstance(value, date):
        return value
    return date.fromisoformat(str(value)[:10])


def _comparison_columns(emp: str) -> list[dict]:
    obj = _pension_obj(emp)
    raw = getattr(obj, "pension_comparison", None) if obj is not None else None
    if not isinstance(raw, dict):
        return []
    return [col for col in (raw.get("columns") or []) if isinstance(col, dict)]


def _column_covers_month(col: dict, month: date) -> bool:
    start = _column_date(col.get("period_from"))
    end = _column_date(col.get("period_to"))
    if start is not None and month < start:
        return False
    if end is not None and month > end:
        return False
    return True


def _slab_start(columns: list[dict], month: date, percent: float, cpi, kind):
    """When this old-age percent began, even if that month is before the payment."""
    matches = []
    for col in columns:
        try:
            col_pct = float(col.get("oldage_percent") or 0)
        except (TypeError, ValueError):
            continue
        if col_pct != percent or not _column_covers_month(col, month):
            continue
        matches.append(col)
    if not matches:
        return None

    def rank(col):
        return (
            str(col.get("cpi") or "") == str(cpi or ""),
            str(col.get("kind") or "") == str(kind or ""),
        )

    chosen = sorted(matches, key=rank)[-1]
    return _column_date(chosen.get("period_from"))


def _oab_from_note(emp: str, lines: list[dict]) -> str:
    """
    Start month and percent of each old-age rate used in the payment.

    The start can be before the payment. Emp 00130 is 30% through May–Sep 2026
    because that rate began in Nov 2025, so the cell is Nov 2025 @ 30%.
    """
    columns = _comparison_columns(emp)
    notes = []
    previous = None
    for line in lines or []:
        percent = float(line.get("oldage_percent") or 0)
        if percent == previous:
            continue
        previous = percent
        if percent <= 0:
            continue
        month = date.fromisoformat(str(line.get("from_iso"))[:10])
        started = _slab_start(
            columns, month, percent, line.get("cpi"), line.get("pension_kind")
        )
        label = _short_month(started) if started else (line.get("from_label") or "")
        notes.append(f"{label} @ {_pct_text(percent)}%")
    return ", ".join(notes)


def calculate_arrear_batch(emp_codes, from_month, from_year, to_month, to_year) -> dict:
    period_error = validate_arrear_period(from_month, from_year, to_month, to_year)
    if period_error:
        return {"error": period_error}

    codes: list[str] = []
    seen: set[str] = set()
    for raw in emp_codes or []:
        emp = str(raw or "").strip()[:5]
        if not emp or emp in seen:
            continue
        seen.add(emp)
        codes.append(emp)
    if not codes:
        return {"error": "Excel must include a column named EMP_CD."}
    if len(codes) > MAX_EMPLOYEES:
        return {"error": f"Upload at most {MAX_EMPLOYEES} employee codes at a time."}

    rows = []
    for emp in codes:
        calc = calculate_consolidation_arrear(emp, from_month, from_year, to_month, to_year)
        ident = _identity(emp)
        if calc.get("error"):
            rows.append({
                "ok": False,
                "emp_cd": emp,
                "error": calc["error"],
                **ident,
            })
            continue
        lines = calc.get("lines") or []
        rows.append({
            "ok": True,
            "error": "",
            **ident,
            "name": ident["name"] or calc.get("name") or "",
            "emp_cd": calc.get("emp_cd") or emp,
            "category": calc.get("category") or "",
            "class12": bool(calc.get("class12")),
            "pair": _pair(lines),
            "lines": lines,
            "pension_arrear": calc.get("pension_arrear"),
            "da_relief": calc.get("da_relief"),
            "total": calc.get("total"),
            "from_label": calc.get("from_label"),
            "to_label": calc.get("to_label"),
        })

    first_ok = next((row for row in rows if row.get("ok")), None)
    return {
        "from_label": first_ok.get("from_label") if first_ok else "",
        "to_label": first_ok.get("to_label") if first_ok else "",
        "paid_upto": paid_upto_label(from_month, from_year),
        "requested": len(codes),
        "ok_count": sum(1 for row in rows if row.get("ok")),
        "failed_count": sum(1 for row in rows if not row.get("ok")),
        "rows": rows,
    }


def _write_header(ws, periods: list[dict]) -> int:
    """Two header rows. Returns the first data column of the tail."""
    fixed = len(_FIXED_HEADERS)
    for col, title in enumerate(_FIXED_HEADERS, start=1):
        ws.merge_cells(start_row=1, start_column=col, end_row=2, end_column=col)
        cell = ws.cell(1, col, title)
        cell.fill = _HEADER_FILL
        cell.font = _HEADER_FONT
        cell.alignment = _WRAP
        cell.border = _THIN
        ws.cell(2, col).fill = _HEADER_FILL
        ws.cell(2, col).border = _THIN
        ws.cell(2, col).font = _HEADER_FONT

    col = fixed + 1
    ws.merge_cells(start_row=1, start_column=col, end_row=2, end_column=col)
    oab_head = ws.cell(1, col, "OAB from")
    oab_head.fill = _HEADER_FILL
    oab_head.font = _HEADER_FONT
    oab_head.alignment = _WRAP
    oab_head.border = _THIN
    ws.cell(2, col).fill = _HEADER_FILL
    ws.cell(2, col).border = _THIN
    ws.cell(2, col).font = _HEADER_FONT
    col += 1

    sub = ("Old age diff", "Basic + old age", "DA relief")
    for period in periods:
        ws.merge_cells(start_row=1, start_column=col, end_row=1, end_column=col + 2)
        head = ws.cell(1, col, period["title"])
        head.fill = _HEADER_FILL
        head.font = _HEADER_FONT
        head.alignment = _WRAP
        head.border = _THIN
        for offset, title in enumerate(sub):
            cell = ws.cell(2, col + offset, title)
            cell.fill = _HEADER_FILL
            cell.font = _HEADER_FONT
            cell.alignment = _WRAP
            cell.border = _THIN
            ws.cell(1, col + offset).border = _THIN
            ws.cell(1, col + offset).fill = _HEADER_FILL
        col += 3

    tail_at = col
    for title in _TAIL_HEADERS:
        ws.merge_cells(start_row=1, start_column=col, end_row=2, end_column=col)
        cell = ws.cell(1, col, title)
        cell.fill = _HEADER_FILL
        cell.font = _HEADER_FONT
        cell.alignment = _WRAP
        cell.border = _THIN
        ws.cell(2, col).fill = _HEADER_FILL
        ws.cell(2, col).border = _THIN
        ws.cell(2, col).font = _HEADER_FONT
        col += 1
    ws.row_dimensions[1].height = 36
    ws.row_dimensions[2].height = 30
    ws.freeze_panes = "A3"
    return tail_at


def _put_money(cell, value):
    if value is None or value == "":
        cell.value = None
        cell.alignment = _RIGHT
        return
    cell.value = float(value)
    cell.number_format = "#,##0.00"
    cell.alignment = _RIGHT


def _write_row(ws, excel_row: int, sl_no: int, row: dict, periods: list[dict], phase: str, paid_upto: str):
    pair = row.get("pair") or {}
    values = [
        sl_no,
        row.get("name") or "",
        row.get("emp_cd") or "",
        row.get("retirement_date") or "",
        row.get("class_label") or "",
        row.get("designation") or "",
    ]
    for col, value in enumerate(values, start=1):
        cell = ws.cell(excel_row, col, value)
        cell.alignment = _LEFT if col in (2, 6) else Alignment(vertical="center", horizontal="center")
        cell.border = _THIN
        if col == 3:
            cell.fill = _EMP_FILL
    _put_money(ws.cell(excel_row, 7), row.get("last_pay"))
    ws.cell(excel_row, 7).border = _THIN
    scale_cell = ws.cell(excel_row, 8, row.get("scale") or "")
    scale_cell.alignment = _LEFT
    scale_cell.border = _THIN
    tqs_cell = ws.cell(excel_row, 9, row.get("tqs") or "")
    tqs_cell.alignment = Alignment(vertical="center", horizontal="center")
    tqs_cell.border = _THIN
    _put_money(ws.cell(excel_row, 10), pair.get("m1"))
    _put_money(ws.cell(excel_row, 11), pair.get("m2"))
    ws.cell(excel_row, 10).border = _THIN
    ws.cell(excel_row, 11).border = _THIN
    cpi_cell = ws.cell(excel_row, 12, pair.get("cpi") or "")
    ben_cell = ws.cell(excel_row, 13, pair.get("beneficial") or "")
    cpi_cell.alignment = Alignment(vertical="center", horizontal="center")
    ben_cell.alignment = Alignment(vertical="center", horizontal="center")
    cpi_cell.border = _THIN
    ben_cell.border = _THIN
    _put_money(ws.cell(excel_row, 14), pair.get("benefit"))
    ws.cell(excel_row, 14).border = _THIN

    oab_cell = ws.cell(
        excel_row,
        len(_FIXED_HEADERS) + 1,
        _oab_from_note(row.get("emp_cd") or "", row.get("lines") or []),
    )
    oab_cell.alignment = Alignment(vertical="center", horizontal="center")
    oab_cell.border = _THIN

    amounts = _amounts_by_period(row.get("lines") or [], periods)
    col = len(_FIXED_HEADERS) + 2
    for period in periods:
        bucket = amounts.get(period["id"]) or {"oa": 0, "basic": 0, "da": 0}
        _put_money(ws.cell(excel_row, col), bucket["oa"])
        _put_money(ws.cell(excel_row, col + 1), bucket["basic"])
        _put_money(ws.cell(excel_row, col + 2), bucket["da"])
        for offset in range(3):
            ws.cell(excel_row, col + offset).border = _THIN
        col += 3

    _put_money(ws.cell(excel_row, col), row.get("total"))
    ws.cell(excel_row, col).border = _THIN
    phase_cell = ws.cell(excel_row, col + 1, phase or "")
    upto_cell = ws.cell(excel_row, col + 2, paid_upto)
    abstract = ws.cell(excel_row, col + 3, "")
    for cell in (phase_cell, upto_cell, abstract):
        cell.alignment = Alignment(vertical="center", horizontal="center")
        cell.border = _THIN


# ---------------------------------------------------------------------------
# CR 03-11-2026: arrear Excel in 4 report types. One uploaded list can mix
# classes and pension types, so each row is routed to its type's sheet.
# A type with "columns" uses its own template; a type without one keeps the
# generic layout above until its format is given.
# ---------------------------------------------------------------------------

_TITLE_FILL = PatternFill("solid", fgColor="1F4E79")
_TITLE_FONT = Font(bold=True, color="FFFFFF", size=12)
_COL_HEAD_FONT = Font(bold=True, color="000000", size=9)
_M1M2_FILL = PatternFill("solid", fgColor="CCC0DA")
_BENEFIT_FILL = PatternFill("solid", fgColor="FFC000")
_BILL_FILL = PatternFill("solid", fgColor="5B9BD5")


def _month_word(d: date) -> str:
    """May, June, July stay whole; longer names are cut (Aug, Sep, Oct) — as on the bill."""
    full = _FULL_MONTH[d.month - 1]
    return full if len(full) <= 4 else full[:3]


def _period_words(period: dict, with_year: bool = True) -> str:
    """'May & June 2026', 'July, Aug & Sep 2026', 'Oct 2026'."""
    months = []
    cursor = period["from"]
    while cursor <= period["to"]:
        months.append(cursor)
        cursor = _add_month(cursor)
    if len({m.year for m in months}) > 1:
        names = [f"{_month_word(m)} {m.year}" for m in months]
        year = ""
    else:
        names = [_month_word(m) for m in months]
        year = f" {months[0].year}" if with_year and months else ""
    if len(names) == 1:
        text = names[0]
    else:
        text = ", ".join(names[:-1]) + " & " + names[-1]
    return text + year


def _da_header(periods: list[dict], class_grp: int, cpi: str) -> str:
    from M2_oldage_arrear.services.da_service import lookup_da_pct

    parts = [
        f"For {_period_words(p, with_year=False)} @ {_pct_text(lookup_da_pct(class_grp, cpi, p['from']))} %"
        for p in periods
    ]
    return "DA as per applicable % (" + ", ".join(parts) + ")"


def _row_months(row: dict) -> int:
    return sum(int(line.get("months") or 0) for line in row.get("lines") or [])


def _payment_tail_values(row: dict, periods: list[dict], phase: str, paid_upto: str) -> list:
    """Old-age diff / basic+OA per DA period, DA, months, bill, phase … (all 4 types)."""
    amounts = _amounts_by_period(row.get("lines") or [], periods)
    oa = [(amounts.get(p["id"]) or {}).get("oa", 0) for p in periods]
    basic = [(amounts.get(p["id"]) or {}).get("basic", 0) for p in periods]
    return [
        *[("money", v) for v in oa],
        *[("money", v) for v in basic],
        ("money", row.get("da_relief")),
        _row_months(row),
        ("money", row.get("total")),
        phase or "",
        paid_upto,
        "",
        "",
        _not_eligible_remark(row),
    ]


def _not_eligible_remark(row: dict) -> str:
    """CR 03-11-2026: M-I above M-II (negative benefit) months are not paid.

    Whole window not payable → 'Not eligible for M2 benefit'; only some months →
    the same text with those months.
    """
    lines = row.get("lines") or []
    unpaid = [line for line in lines if line.get("not_payable")]
    if not unpaid:
        return ""
    if len(unpaid) == len(lines):
        return "Not eligible for M2 benefit"
    spans = ", ".join(
        line.get("from_label") if line.get("from_label") == line.get("to_label")
        else f"{line.get('from_label')} - {line.get('to_label')}"
        for line in unpaid
    )
    return f"Not eligible for M2 benefit ({spans})"


def _payment_tail_columns(periods: list[dict], class_grp: int, cpi: str) -> list[dict]:
    cols = [
        {"title": f"Total Diff amt of Old Age benefit for {_period_words(p)}", "width": 12}
        for p in periods
    ]
    cols += [
        {"title": f"Total Basic & Old Age Benefit for {_period_words(p)}", "width": 13, "role": "basic_oa"}
        for p in periods
    ]
    cols += [
        {"title": _da_header(periods, class_grp, cpi), "width": 24, "role": "da"},
        {"title": "No. of Months of Payment", "width": 9},
        # CR 03-11-2026: bill = ROUND(basic & old age + DA, 0) as an Excel formula.
        {"title": "Total Bill Amount", "width": 14, "fill": _BILL_FILL, "role": "bill"},
        {"title": "Phase", "width": 9},
        {"title": "Arrear to be paid upto", "width": 13},
        {"title": "Abstract No.", "width": 11},
        {"title": "Abstract Date", "width": 11},
        {"title": "Remarks", "width": 18, "align": "left"},
    ]
    return cols


def _class12_employee_values(row: dict, periods: list[dict], phase: str, paid_upto: str) -> list:
    """Cells for the class 1/2 employee-pension template (same order as its columns)."""
    pair = row.get("pair") or {}
    return [
        row.get("name") or "",
        row.get("case_no") or "",
        row.get("roll_no") or "",
        row.get("emp_cd") or "",
        row.get("retirement_date") or "",
        row.get("tqs") or "",
        row.get("class_label") or "",
        row.get("designation") or "",
        ("money", row.get("last_pay")),
        row.get("scale") or "",
        ("money", pair.get("m1")),
        ("money", pair.get("m2")),
        pair.get("beneficial") or "",
        ("money", pair.get("benefit")),
        *_payment_tail_values(row, periods, phase, paid_upto),
    ]


def _class12_employee_columns(periods: list[dict]) -> list[dict]:
    cols = [
        {"title": "Emp Name(Pensioner Name)", "width": 28, "align": "left"},
        {"title": "Case No", "width": 10},
        {"title": "Roll No.", "width": 12},
        {"title": "Emp Code", "width": 10},
        {"title": "Retirement Date", "width": 12},
        {"title": "TQS", "width": 16},
        {"title": "Class", "width": 7},
        {"title": "Designation", "width": 22, "align": "left"},
        {"title": "Pay(Revised) at the time of retirement", "width": 13},
        {"title": "Pay Scale at the time of retirement", "width": 24, "align": "left"},
        {"title": "Basic Pension amt as per M-I in 2017 (277 CPI)", "width": 15, "fill": _M1M2_FILL},
        {"title": "Revised Basic Pension amt as per M-II in 2017 (277 CPI)", "width": 15, "fill": _M1M2_FILL},
        {"title": "Beneficial under M-I or M-2", "width": 9, "fill": _M1M2_FILL},
        {"title": "Basic Pension Amt of Benefit (PM) Excluding DA", "width": 14, "fill": _BENEFIT_FILL},
    ]
    return cols + _payment_tail_columns(periods, 1, "277")


def _class34_employee_values(row: dict, periods: list[dict], phase: str, paid_upto: str) -> list:
    """Class 3/4 employee: 2017 (277) and 2022 (359) M-I / M-II blocks."""
    emp = row.get("emp_cd") or ""
    columns = _comparison_columns(emp)
    return [
        row.get("name") or "",
        row.get("case_no") or "",
        row.get("roll_no") or "",
        emp,
        row.get("retirement_date") or "",
        row.get("tqs") or "",
        row.get("class_label") or "",
        row.get("designation") or "",
        ("money", row.get("last_pay")),
        row.get("scale") or "",
        *_kind_block(columns, "employee", 277, row.get("lines")),
        *_kind_block(columns, "employee", 359, row.get("lines")),
        *_payment_tail_values(row, periods, phase, paid_upto),
    ]


def _class34_employee_columns(periods: list[dict]) -> list[dict]:
    m1m2 = {"width": 15, "fill": _M1M2_FILL}
    benefit = {"width": 14, "fill": _BENEFIT_FILL}
    ben = {"title": "Beneficial under M-1 or M-2", "width": 9, "fill": _M1M2_FILL}
    cols = [
        {"title": "Emp Name(Pensioner Name)", "width": 28, "align": "left"},
        {"title": "Case No", "width": 10},
        {"title": "Roll No.", "width": 12},
        {"title": "Emp Code", "width": 10},
        {"title": "Retirement Date", "width": 12},
        {"title": "TQS", "width": 16},
        {"title": "Class", "width": 7},
        {"title": "Designation", "width": 22, "align": "left"},
        {"title": "Pay(Revised) at the time of retirement", "width": 13},
        {"title": "Pay Scale at the time of retirement", "width": 24, "align": "left"},
        {"title": "Basic Pension amt as per M-I in 2017 (277 CPI)", **m1m2},
        {"title": "Revised Basic Pension amt as per M-II in 2017 (277 CPI)", **m1m2},
        dict(ben),
        {"title": "Basic Pension Amt of Benefit (PM) Excluding DA", **benefit},
        {"title": "Basic Pension amt as per M-I in 2022 (359 CPI)", **m1m2},
        {"title": "Revised Basic Pension amt as per M-II in 2022 (359 CPI)", **m1m2},
        dict(ben),
        {"title": "Basic Pension Amt of Benefit (PM) Excluding DA", **benefit},
    ]
    return cols + _payment_tail_columns(periods, 3, "359")


def _kind_block(columns: list[dict], kind: str, cpi: int, lines: list[dict] | None = None) -> list:
    """M-I, M-II, beneficial, benefit (M-II − M-I) of one pension kind at one CPI.

    A kind paid in this window takes the arrear line amounts, so the block
    matches the bill (15068: family M-I on the print equals the employee
    pension; the arrear pays on that × 0.6). Otherwise the consolidation
    column is used; old-age splits repeat the same M-I / M-II, so the first
    column of that kind is taken. No such period leaves the block blank.
    """
    for line in lines or []:
        if line.get("pension_kind") != kind or str(line.get("cpi")) != str(cpi):
            continue
        m1 = _num(line.get("m1"))
        m2 = _num(line.get("m2"))
        diff = _num(line.get("pension_diff"))
        if m1 is not None and m2 is not None:
            return [("money", m1), ("money", m2), _beneficial(diff), ("money", diff)]
    for col in columns:
        try:
            col_cpi = int(col.get("cpi") or 0)
        except (TypeError, ValueError):
            continue
        if col.get("kind") != kind or col_cpi != cpi:
            continue
        m1 = _num(col.get("m1"))
        m2 = _num(col.get("m2"))
        diff = round(m2 - m1, 2) if m1 is not None and m2 is not None else None
        return [("money", m1), ("money", m2), _beneficial(diff), ("money", diff)]
    return [("money", None), ("money", None), "", ("money", None)]


def _family_identity(emp: str) -> dict:
    obj = _pension_obj(emp)
    cmp_ = getattr(obj, "pension_comparison", None) if obj is not None else None
    cmp_ = cmp_ if isinstance(cmp_, dict) else {}
    return {
        "family_pensioner_name": str(
            cmp_.get("family_pensioner_name") or getattr(obj, "pensioner_name", "") or ""
        ).strip(),
        "family_pensioner_dob": _dmy(cmp_.get("family_pensioner_dob")),
        "date_of_death": _dmy(cmp_.get("date_of_death") or getattr(obj, "date_of_death", None)),
    }


def _family_detail_values(row: dict) -> list:
    """Family pensioner … pay scale cells shared by the two family templates."""
    emp = row.get("emp_cd") or ""
    fam = _family_identity(emp)
    return [
        fam["family_pensioner_name"],
        fam["family_pensioner_dob"],
        row.get("name") or "",
        row.get("case_no") or "",
        row.get("roll_no") or "",
        emp,
        row.get("retirement_date") or "",
        fam["date_of_death"],
        row.get("tqs") or "",
        row.get("class_label") or "",
        row.get("designation") or "",
        ("money", row.get("last_pay")),
        row.get("scale") or "",
    ]


def _family_detail_columns() -> list[dict]:
    return [
        {"title": "Family Pensioner Name", "width": 26, "align": "left"},
        {"title": "DOB of Family Pensioner", "width": 11},
        {"title": "Ex-Emp Name", "width": 26, "align": "left"},
        {"title": "Case No", "width": 10},
        {"title": "Roll No.", "width": 12},
        {"title": "Emp Code", "width": 10},
        {"title": "Retirement Date", "width": 12},
        {"title": "Date of Death", "width": 12},
        {"title": "TQS", "width": 16},
        {"title": "Class", "width": 7},
        {"title": "Designation", "width": 22, "align": "left"},
        {"title": "Pay(Revised) at the time of retirement", "width": 13},
        {"title": "Pay Scale at the time of retirement", "width": 24, "align": "left"},
    ]


def _family_kind_columns(year: str, cpi: int, band: dict | None = None) -> list[dict]:
    """Employee / enhanced 50% / single 30% blocks for one revision year."""
    m1m2 = {"width": 15, "fill": _M1M2_FILL}
    benefit = {"width": 15, "fill": _BENEFIT_FILL}
    ben = {"title": "Beneficial under M-1 or M-2", "width": 9, "fill": _M1M2_FILL}
    till = f"(Jan {year} to till date of Death)"
    cols = [
        {"title": f"Basic Employee Pension Amt as per M-1 in {year}({cpi} CPI) {till}", **m1m2},
        {"title": f"Revised Basic Employee Pension amt as per M-2 in {year}({cpi} CPI) {till}", **m1m2},
        dict(ben),
        {"title": f"Basic Employee Pension amt of Benefit(PM) excluding DA {till}", **benefit},
        {"title": f"Basic Family Pension Amt (enhanced i.e. 50%) as per M-1 in {year}({cpi} CPI)", **m1m2},
        {"title": f"Revised Basic Family Pension Amt(enhanced i.e. 50%) as per M-2 in {year}({cpi} CPI)", **m1m2},
        dict(ben),
        {"title": "Enhanced (i.e. 50%) Basic Family Pension amt of Benefit(PM) excluding DA", **benefit},
        {"title": f"Basic Family Pension Amt (i.e. Single Pension @30%) as per M-1 in {year}({cpi} CPI)", **m1m2},
        {"title": f"Revised Basic Family Pension Amt(i.e. Single Pension @30%) as per M-2 in {year}({cpi} CPI)", **m1m2},
        dict(ben),
        {"title": "Basic Family Pension amt of Benefit(PM) excluding DA (i.e. Single Pension @30%)", **benefit},
    ]
    if band:
        for col in cols:
            col["band"] = band
    return cols


def _family_kind_values(row: dict, cpi: int) -> list:
    columns = _comparison_columns(row.get("emp_cd") or "")
    lines = row.get("lines")
    return [
        *_kind_block(columns, "employee", cpi, lines),
        *_kind_block(columns, "enhanced", cpi, lines),
        *_kind_block(columns, "family", cpi, lines),
    ]


_BAND_2017 = {"label": "w.e.f. 2017", "fill": PatternFill("solid", fgColor="FFFF00")}
_BAND_2022 = {"label": "w.e.f. 2022", "fill": PatternFill("solid", fgColor="92D050")}


def _class34_family_values(row: dict, periods: list[dict], phase: str, paid_upto: str) -> list:
    """Class 3/4 family: employee / enhanced / single blocks for 2017 (277) and 2022 (359)."""
    return [
        *_family_detail_values(row),
        *_family_kind_values(row, 277),
        *_family_kind_values(row, 359),
        *_payment_tail_values(row, periods, phase, paid_upto),
    ]


def _class34_family_columns(periods: list[dict]) -> list[dict]:
    return (
        _family_detail_columns()
        + _family_kind_columns("2017", 277, _BAND_2017)
        + _family_kind_columns("2022", 359, _BAND_2022)
        + _payment_tail_columns(periods, 3, "359")
    )


def _class12_family_values(row: dict, periods: list[dict], phase: str, paid_upto: str) -> list:
    """Class 1/2 family: employee / enhanced (50%) / single (30%) blocks at 277 CPI."""
    emp = row.get("emp_cd") or ""
    fam = _family_identity(emp)
    columns = _comparison_columns(emp)
    return [
        fam["family_pensioner_name"],
        fam["family_pensioner_dob"],
        row.get("name") or "",
        row.get("case_no") or "",
        row.get("roll_no") or "",
        emp,
        row.get("retirement_date") or "",
        fam["date_of_death"],
        row.get("tqs") or "",
        row.get("class_label") or "",
        row.get("designation") or "",
        ("money", row.get("last_pay")),
        row.get("scale") or "",
        *_kind_block(columns, "employee", 277, row.get("lines")),
        *_kind_block(columns, "enhanced", 277, row.get("lines")),
        *_kind_block(columns, "family", 277, row.get("lines")),
        *_payment_tail_values(row, periods, phase, paid_upto),
    ]


def _class12_family_columns(periods: list[dict]) -> list[dict]:
    m1m2 = {"width": 15, "fill": _M1M2_FILL}
    benefit = {"width": 15, "fill": _BENEFIT_FILL}
    ben = {"title": "Beneficial under M-1 or M-2", "width": 9, "fill": _M1M2_FILL}
    cols = [
        {"title": "Family Pensioner Name", "width": 26, "align": "left"},
        {"title": "DOB of Family Pensioner", "width": 11},
        {"title": "Ex-Emp Name", "width": 26, "align": "left"},
        {"title": "Case No", "width": 10},
        {"title": "Roll No.", "width": 12},
        {"title": "Emp Code", "width": 10},
        {"title": "Retirement Date", "width": 12},
        {"title": "Date of Death", "width": 12},
        {"title": "TQS", "width": 16},
        {"title": "Class", "width": 7},
        {"title": "Designation", "width": 22, "align": "left"},
        {"title": "Pay(Revised) at the time of retirement", "width": 13},
        {"title": "Pay Scale at the time of retirement", "width": 24, "align": "left"},
        {"title": "Basic Employee Pension Amt as per M-1 in 2017(277 CPI) (Jan 2017 to till date of Death)", **m1m2},
        {"title": "Revised Basic Employee Pension amt as per M-2 in 2017(277 CPI) (Jan 2017 to till date of Death)", **m1m2},
        dict(ben),
        {"title": "Basic Employee Pension amt of Benefit(PM) excluding DA (Jan 2017 to till date of Death)", **benefit},
        {"title": "Basic Family Pension Amt (enhanced i.e. 50%) as per M-1 in 2017(277 CPI)", **m1m2},
        {"title": "Revised Basic Family Pension Amt(enhanced i.e. 50%) as per M-2 in 2017(277 CPI)", **m1m2},
        dict(ben),
        {"title": "Enhanced (i.e. 50%) Basic Family Pension amt of Benefit(PM) excluding DA", **benefit},
        {"title": "Basic Family Pension Amt (i.e. Single Pension @30%) as per M-1 in 2017(277 CPI)", **m1m2},
        {"title": "Revised Basic Family Pension Amt(i.e. Single Pension @30%) as per M-2 in 2017(277 CPI)", **m1m2},
        dict(ben),
        {"title": "Basic Family Pension amt of Benefit(PM) excluding DA (i.e. Single Pension @30%)", **benefit},
    ]
    return cols + _payment_tail_columns(periods, 1, "277")


# Order = sheet order. key: (class group, pension) — "12"/"34", "emp"/"fp".
REPORT_TYPES = (
    {
        "key": ("12", "emp"),
        "sheet": "Class I-II Employee",
        "title": (
            "Summary of Consolidation of 1st Pensioner (Class 1 & 2) as per "
            "Methodology-2 and comparison between M-1 & M-2 for 2017."
        ),
        "class_grp": 1,
        "columns": _class12_employee_columns,
        "values": _class12_employee_values,
    },
    {
        "key": ("12", "fp"),
        "sheet": "Class I-II Family",
        "title": (
            "Summary of Consolidation of Family Pension(Class 1 & 2) as per "
            "Methodology-2 and comparison between M-1 & M-2 for 2017."
        ),
        "class_grp": 1,
        "columns": _class12_family_columns,
        "values": _class12_family_values,
        "header_height": 120,
    },
    {
        "key": ("34", "emp"),
        "sheet": "Class III-IV Employee",
        "title": (
            "Summary of Consolidation of 1st Pensioner (Class 3 & 4) as per "
            "Methodology-2 and comparison between M-1 & M-2 for 2017 & 2022."
        ),
        "class_grp": 3,
        "columns": _class34_employee_columns,
        "values": _class34_employee_values,
    },
    {
        "key": ("34", "fp"),
        "sheet": "Class III-IV Family",
        "title": (
            "Summary of Consolidation of Family Pension as per Methodology-2 "
            "and comparison between M-1 & M-2 for 2017 & 2022."
        ),
        "class_grp": 3,
        "columns": _class34_family_columns,
        "values": _class34_family_values,
        "header_height": 120,
    },
)


def report_type_key(row: dict) -> tuple[str, str]:
    """Class group and the pension paid in this window (any family month → family)."""
    group = "12" if row.get("class12") else "34"
    kinds = {line.get("pension_kind") for line in row.get("lines") or []}
    pension = "fp" if kinds & {"family", "enhanced"} else "emp"
    return group, pension


def _write_template_sheet(ws, spec: dict, rows: list[dict], periods: list[dict], phase: str, paid_upto: str):
    columns = [{"title": "Sl. No.", "width": 6}] + spec["columns"](periods)
    last_col = len(columns)
    ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=last_col)
    title = ws.cell(1, 1, spec["title"])
    title.fill = _TITLE_FILL
    title.font = _TITLE_FONT
    title.alignment = Alignment(vertical="center", horizontal="left")
    ws.row_dimensions[1].height = 22

    # Type 4 groups its blocks under "w.e.f. 2017" / "w.e.f. 2022" bands: one
    # band row above the column titles; columns outside a band span both rows.
    banded = any(meta.get("band") for meta in columns)
    head_row = 3 if banded else 2
    if banded:
        col = 1
        while col <= last_col:
            band = columns[col - 1].get("band")
            if not band:
                ws.merge_cells(start_row=2, start_column=col, end_row=3, end_column=col)
                col += 1
                continue
            end = col
            while end + 1 <= last_col and columns[end].get("band") is band:
                end += 1
            ws.merge_cells(start_row=2, start_column=col, end_row=2, end_column=end)
            cell = ws.cell(2, col, band["label"])
            cell.font = Font(bold=True, size=16)
            cell.alignment = Alignment(vertical="center", horizontal="center")
            for c in range(col, end + 1):
                ws.cell(2, c).fill = band["fill"]
                ws.cell(2, c).border = _THIN
            col = end + 1
        ws.row_dimensions[2].height = 26

    for col, meta in enumerate(columns, start=1):
        cell = ws.cell(2 if banded and not meta.get("band") else head_row, col, meta["title"])
        cell.font = _COL_HEAD_FONT
        cell.alignment = _WRAP
        cell.border = _THIN
        if meta.get("fill"):
            cell.fill = meta["fill"]
        ws.column_dimensions[get_column_letter(col)].width = meta.get("width", 14)
    ws.row_dimensions[head_row].height = spec.get("header_height", 78)
    ws.freeze_panes = f"C{head_row + 1}"

    role_cols = {}
    for col, meta in enumerate(columns, start=1):
        if meta.get("role"):
            role_cols.setdefault(meta["role"], []).append(get_column_letter(col))

    for index, row in enumerate(rows, start=1):
        excel_row = index + head_row
        values = [index] + spec["values"](row, periods, phase, paid_upto)
        for col, value in enumerate(values, start=1):
            cell = ws.cell(excel_row, col)
            cell.border = _THIN
            role = columns[col - 1].get("role") if col - 1 < len(columns) else None
            if role == "bill" and role_cols.get("basic_oa") and role_cols.get("da"):
                first, last = role_cols["basic_oa"][0], role_cols["basic_oa"][-1]
                da = role_cols["da"][0]
                cell.value = f"=ROUND(SUM({first}{excel_row}:{last}{excel_row})+{da}{excel_row},0)"
                cell.number_format = "#,##0"
                cell.alignment = _RIGHT
                continue
            if isinstance(value, tuple) and value and value[0] == "money":
                _put_money(cell, value[1])
                continue
            cell.value = value
            align = columns[col - 1].get("align") if col - 1 < len(columns) else None
            cell.alignment = (
                _LEFT if align == "left" else Alignment(vertical="center", horizontal="center")
            )


def _write_generic_sheet(ws, rows: list[dict], periods: list[dict], phase: str, paid_upto: str):
    _write_header(ws, periods)
    for index, row in enumerate(rows, start=1):
        _write_row(ws, index + 2, index, row, periods, phase, paid_upto)
    widths = {
        1: 8, 2: 28, 3: 14, 4: 16, 5: 10, 6: 22,
        7: 18, 8: 28, 9: 16, 10: 16, 11: 16, 12: 10, 13: 16, 14: 16,
    }
    for col in range(1, ws.max_column + 1):
        ws.column_dimensions[get_column_letter(col)].width = widths.get(col, 18)


def build_arrear_payment_excel_bytes(
    emp_codes,
    from_month,
    from_year,
    to_month,
    to_year,
    phase: str = "",
) -> tuple[bytes, str]:
    batch = calculate_arrear_batch(emp_codes, from_month, from_year, to_month, to_year)
    if batch.get("error"):
        raise ValueError(batch["error"])
    # CR 12-11-2026: an employee without a consolidation (or whose arrear
    # cannot be worked out) is left out of the export instead of stopping it.
    ready = [row for row in batch["rows"] if row.get("ok")]
    if not ready:
        raise ValueError("None of the selected employees have an arrear calculation.")

    paid = batch["paid_upto"]
    phase_text = str(phase or "").strip()

    by_type: dict[tuple[str, str], list[dict]] = {}
    for row in ready:
        by_type.setdefault(report_type_key(row), []).append(row)

    wb = Workbook()
    wb.remove(wb.active)
    for spec in REPORT_TYPES:
        rows = by_type.get(spec["key"])
        if not rows:
            continue
        periods = _payment_periods(
            from_month, from_year, to_month, to_year, class_grp=spec["class_grp"]
        )
        ws = wb.create_sheet(spec["sheet"])
        if spec.get("columns"):
            _write_template_sheet(ws, spec, rows, periods, phase_text, paid)
        else:
            _write_generic_sheet(ws, rows, periods, phase_text, paid)

    buf = BytesIO()
    wb.save(buf)
    start = date(int(from_year), int(from_month), 1)
    end = date(int(to_year), int(to_month), 1)
    filename = (
        f"Arrear_{start.strftime('%b%Y')}_{end.strftime('%b%Y')}.xlsx"
    )
    return buf.getvalue(), filename
