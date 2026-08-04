"""
Methodology 2 - Category 1 & 2 (Executive grades E-1..E-25) revision chain.

Stages: 1984 -> 1987 -> 1992 -> 1997 -> 2007 -> 2017.
Start stage depends on separation date. Scales come from the
`Payscale_1_2` sheet; the 1997 DA uses the `DA1_1992` slab table.
Both sheets live in class1_2.xlsx.
"""

import re
from datetime import datetime

from methodology2.services.excel_loader import (
    load_class12_da1992_table,
    load_class12_payscale_table,
)
from methodology2.services.rounding_helpers import round2, round_up_to_10
from methodology2.services.scale_parser import get_next_higher_stage

# Fixed DA constants (per the pay-revision orders; same for every scale).
DA_1987_CONSTANT = 838.35   # D.A of Rs.838.35 at AICPI 685 as on 1.1.1987
DA_1992_CONSTANT = 787.75   # D.A as on 1.1.1992 at AICPI 1099

# Revision -> column name in Payscale_1_2 (note 2017 header has no closing paren).
SCALE_COLUMNS = {
    "1984": "1984(REVISED PAY SCALE)",
    "1987": "1987(REVISED PAY SCALE)",
    "1992": "1992(REVISED PAY SCALE)",
    "1997": "1997(REVISED PAY SCALE)",
    "2007": "2007(REVISED PAY SCALE)",
    "2017": "2017(REVISED PAY SCALE",
}
FITMENT_1987_COLUMN = "FITMENT AMOUNT FOR 1987"

REVISION_ORDER = ["1984", "1987", "1992", "1997", "2007", "2017"]

REVISION_TITLE = {
    "1984": "1984 (Revised Pay Scale)",
    "1987": "1987 (Revised Pay Scale)",
    "1992": "1992 (Revised Pay Scale)",
    "1997": "1997 (Revised Pay Scale)",
    "2007": "2007 (Revised Pay Scale)",
    "2017": "2017 (Revised Pay Scale)",
}


def get_class12_start_revision(separation_date):
    """Separation date -> starting revision stage."""
    if isinstance(separation_date, str):
        separation_date = datetime.strptime(separation_date, "%Y-%m-%d")

    if separation_date <= datetime(1986, 12, 31):
        return "1984"
    if separation_date <= datetime(1991, 12, 31):
        return "1987"
    if separation_date <= datetime(1996, 12, 31):
        return "1992"
    if separation_date <= datetime(2006, 12, 31):
        return "1997"
    if separation_date <= datetime(2016, 12, 31):
        return "2007"
    return "2017"


def format_class12_scale_display(scale_string):
    """Min–max band display, aligned with class 3/4 scale labels."""
    if not scale_string:
        return ""
    text = str(scale_string).strip()
    parts = [part.strip() for part in text.split("-") if part.strip()]
    numbers = []
    for part in parts:
        try:
            numbers.append(int(part))
        except ValueError:
            return text
    if len(numbers) >= 2:
        return f"{numbers[0]} - {numbers[-1]}"
    return text


def normalize_executive_grade(value):
    """Normalize executive grade input (e.g. e9 -> E-9, E24.1 -> E24.1)."""
    if not value:
        return None
    text = str(value).strip().upper().replace(" ", "")
    match = re.match(r"^E-?(\d+(?:\.\d+)?)$", text)
    if match:
        num = match.group(1)
        # Excel uses E-9 for integers and E24.1 (no hyphen) for decimals.
        if "." in num:
            return f"E{num}"
        return f"E-{num}"
    return str(value).strip()


def _grade_from_pay_band(pay_band, separation_date=None):
    """Map dept/Excel pay band (e.g. 20600-46500) to executive grade."""
    want = re.sub(r"\s+", "", str(pay_band or "").strip().upper())
    want = want.replace("–", "-").replace("—", "-")
    if not want or want.startswith("E"):
        return None
    for item in get_class12_scales(separation_date) or []:
        band = re.sub(r"\s+", "", str(item.get("pay_band") or "").upper())
        label = re.sub(r"\s+", "", str(item.get("label") or "").upper())
        band = band.replace("–", "-").replace("—", "-")
        label = label.replace("–", "-").replace("—", "-")
        if want in (band, label):
            return item.get("grade")
    return None


def validate_executive_grade(value, separation_date=None):
    """Return normalized grade (E-9) if valid, else None.

    Accepts executive grade or a pay-band string (e.g. 20600-46500).
    """
    normalized = normalize_executive_grade(value)
    if normalized and _get_scale_row(normalized) is not None:
        return normalized
    # UI may send the dropdown label (pay band) instead of grade.
    grade = _grade_from_pay_band(value, separation_date)
    if grade and _get_scale_row(grade) is not None:
        return grade
    return None


def get_class12_scales(separation_date=None):
    """
    Executive grades for category 1/2.

    When separation_date is given, each item includes the pay band at the
    start-revision column for dropdown display. Use ``grade`` (E-1, E-9, …)
    as the ``scale`` value in family_pension_calculation / calculate-class12.
    """
    df = load_class12_payscale_table()
    if not separation_date:
        return [
            {
                "grade": str(value).strip(),
                "label": str(value).strip(),
            }
            for value in df["Scale"].dropna().tolist()
        ]

    start = get_class12_start_revision(separation_date)
    column = SCALE_COLUMNS[start]
    items = []
    seen_labels = set()
    for _, row in df.iterrows():
        grade = str(row["Scale"]).strip()
        if not grade:
            continue
        pay_band = row.get(column)
        if pay_band is None or str(pay_band) == "nan":
            continue
        pay_band_string = str(pay_band).strip()
        label = format_class12_scale_display(pay_band_string)
        if label in seen_labels:
            continue
        seen_labels.add(label)
        items.append({
            "grade": grade,
            "pay_band": pay_band_string,
            "label": label,
        })
    return items


def _get_scale_row(grade):
    df = load_class12_payscale_table()
    result = df[df["Scale"].astype(str) == str(grade)]
    if result.empty:
        return None
    return result.iloc[0]


def get_class12_equivalent_scales(grade):
    """
    Pay band at each class 1/2 revision for the given executive grade.

    Keys are revision years as used by print blocks: 1984, 1987, 1992, 1997, 2007, 2017.
    Values are display bands (e.g. ``20600 - 46500``).
    """
    row = _get_scale_row(grade)
    if row is None:
        return {}
    scales = {}
    for year, column in SCALE_COLUMNS.items():
        raw = row.get(column)
        if raw is None or str(raw) == "nan":
            continue
        text = str(raw).strip()
        if not text:
            continue
        scales[year] = format_class12_scale_display(text)
    return scales


def get_class12_pay_stages(separation_date, grade):
    """Pay stages of the start-revision scale for a grade (last-pay dropdown)."""
    row = _get_scale_row(grade)
    if row is None:
        return []
    start = get_class12_start_revision(separation_date)
    scale_string = row.get(SCALE_COLUMNS[start])
    if scale_string is None or str(scale_string) == "nan":
        return []
    from methodology2.services.scale_parser import generate_pay_stages
    return generate_pay_stages(str(scale_string).strip())


def _da_slab_1992(basic):
    """1997 DA: max(basic * rate, slab) from DA1_1992 table."""
    df = load_class12_da1992_table()
    for _, r in df.iterrows():
        low, high = float(r["Min"]), float(r["Max"])
        if low <= basic <= high:
            return max(round2(basic * float(r["Rate"])), float(r["Slab"]))
    return 0


def _fix_into_scale(scale_string, amount):
    if not scale_string or str(scale_string) == "nan":
        return round_up_to_10(amount)
    return get_next_higher_stage(str(scale_string).strip(), amount)


def _block_1987(rows, row, basic_1984):
    da = DA_1987_CONSTANT
    fitment = float(row.get(FITMENT_1987_COLUMN) or 0)
    notional = round_up_to_10(basic_1984 + da + fitment)
    basic_1987 = _fix_into_scale(row.get(SCALE_COLUMNS["1987"]), notional)
    rows.append({"description": "D.A of Rs.838.35 at AICPI 685 as on 1.1.1987", "value": da})
    rows.append({"description": "Fitment", "value": fitment})
    rows.append({"description": "Notional Pay as on 01.01.1987", "value": notional})
    rows.append({"description": "Basic pay as on 01.01.1987 (minimum basic)", "value": basic_1987})
    return basic_1987


def _block_1992(rows, row, basic_1987):
    da = DA_1992_CONSTANT
    fitment = round2(basic_1987 * 0.20)
    notional = round_up_to_10(basic_1987 + da + fitment)
    basic_1992 = _fix_into_scale(row.get(SCALE_COLUMNS["1992"]), notional)
    rows.append({"description": "D.A as on 1.1.1992 at AICPI 1099", "value": da})
    rows.append({"description": "Fitment @ 20% on Basic pay", "value": fitment})
    rows.append({"description": "Notional Pay as on 01.01.1992", "value": notional})
    rows.append({"description": "Basic pay as on 01.01.1992 (minimum basic)", "value": basic_1992})
    return basic_1992


def _block_1997(rows, row, basic_1992):
    da = _da_slab_1992(basic_1992)
    fitment = round2(basic_1992 * 0.20)
    notional = round_up_to_10(basic_1992 + da + fitment)
    basic_1997 = _fix_into_scale(row.get(SCALE_COLUMNS["1997"]), notional)
    rows.append({"description": "D.A (As per Slab based lookup)", "value": da})
    rows.append({"description": "Fitment @ 20%", "value": fitment})
    rows.append({"description": "Notional basic pay over 1708 CPI", "value": notional})
    rows.append({"description": "Basic pay as on 01.01.1997 (minimum basic)", "value": basic_1997})
    return basic_1997


def _block_2007(rows, basic_1997):
    da = round2(basic_1997 * 0.782)
    fitment = round2((basic_1997 + da) * 0.30)
    basic_2007 = round_up_to_10(basic_1997 + da + fitment)
    rows.append({"description": "DA @ 78.2% on Basic", "value": da})
    rows.append({"description": "Fitment @ 30% on Basic + DA", "value": fitment})
    rows.append({"description": "Basic Pay Over 126 CPI Points (01.01.2007)", "value": basic_2007})
    return basic_2007


def _block_2017(rows, basic_2007):
    da = round2(basic_2007 * 1.198)
    fitment = round2((basic_2007 + da) * 0.15)
    basic_2017 = round_up_to_10(basic_2007 + da + fitment)
    rows.append({"description": "DA @ 119.8% on Basic", "value": da})
    rows.append({"description": "Fitment @ 15% on Basic + DA", "value": fitment})
    rows.append({"description": "Basic Pay Over 277 CPI Points (01.01.2017)", "value": basic_2017})
    return basic_2017


def calculate_class12(separation_date, grade, last_pay):
    row = _get_scale_row(grade)
    if row is None:
        return {"error": f"Scale '{grade}' not found in class 1/2 pay scales"}

    try:
        last_pay = float(last_pay)
    except (TypeError, ValueError):
        return {"error": "last_pay must be a number"}
    if last_pay <= 0:
        return {"error": "last_pay must be positive"}

    start = get_class12_start_revision(separation_date)
    start_idx = REVISION_ORDER.index(start)

    rows = [{
        "description": f"Basic Pay in the existing scale ({start} revised pay scale)",
        "value": last_pay,
    }]

    basic = last_pay
    if start_idx <= REVISION_ORDER.index("1984"):
        basic = _block_1987(rows, row, basic)
    if start_idx <= REVISION_ORDER.index("1987"):
        basic = _block_1992(rows, row, basic)
    if start_idx <= REVISION_ORDER.index("1992"):
        basic = _block_1997(rows, row, basic)
    if start_idx <= REVISION_ORDER.index("1997"):
        basic = _block_2007(rows, basic)
    if start_idx <= REVISION_ORDER.index("2007"):
        basic = _block_2017(rows, basic)

    basic_2017 = basic
    pension = round2(basic_2017 / 2)
    family_pension = round2(basic_2017 * 0.30)

    start_scale = row.get(SCALE_COLUMNS[start])
    scale_at_separation = (
        str(start_scale).strip()
        if start_scale is not None and str(start_scale) != "nan"
        else ""
    )

    return {
        "start_revision": start,
        "grade": str(grade),
        "scale_at_separation": scale_at_separation,
        "scale_display": format_class12_scale_display(scale_at_separation),
        "equivalent_scales": get_class12_equivalent_scales(grade),
        "rows": rows,
        "basic_pay_2017": basic_2017,
        "pension": pension,
        "family_pension": family_pension,
    }
