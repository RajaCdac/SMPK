"""
Assemble / persist Methodology-2 consolidation print snapshots (one row per emp).

Field sources:
- case_no, roll_no  → fi_pn_mh_pension_proposal (CA_NUMBER, PENSION_ROLL_NO)
- tqs               → fi_pn_mh_pensioner (TQS_YR / TQS_MONTH / TQS_DAYS)
- designation       → fi_xx_mh_emp_adm.DESIG_CD → fi_xx_mh_desig.DESIG_DESC
- M1 pension (print):
    Class 3/4 → fi_pn_wage_2022_hdr_third
      OLD_BASIC_PENSION  → 2017 (277 CPI)
      REV_BASIC_PENSION  → 2022 (359 CPI)
    Class 1/2 → fi_pn_wage_2017_hdr_offi2
      REV_BASIC_PENSION  → 2017 (277 CPI); 2022 column blank
- name / dates / pay / scale / revision amounts → M2 calc + employee lookup
"""

import re
from datetime import datetime
from decimal import Decimal, InvalidOperation

from django.db import connection
from django.utils import timezone

from methodology2.models import Methodology2Consolidation
from methodology2.services.oracle_employee_service import format_scale_range_display

REVISION_ORDER = [
    "1979(REVISED PAY SCALE)",
    "1984(REVISED PAY SCALE)",
    "1988(607 CPI)",
    "1993(1030 CPI)",
    "1997(1708 CPI)",
    "2007(126 CPI)",
    "2012(198 CPI)",
    "2017(277 CPI)",
    "2022(359 CPI)",
]

REVISION_CARD_GROUPS = [
    {"revision_key": "1979(REVISED PAY SCALE)", "rows": [27, 28, 29, 30]},
    {"revision_key": "1984(REVISED PAY SCALE)", "rows": [31, 32, 33, 34, 35]},
    {"revision_key": "1988(607 CPI)", "rows": [36, 37, 38, 39, 40, 41]},
    {"revision_key": "1993(1030 CPI)", "rows": [42, 43, 44, 45, 46, 47]},
    {"revision_key": "1997(1708 CPI)", "rows": [48, 49, 50, 51]},
    {"revision_key": "2007(126 CPI)", "rows": [200701, 200702, 200703, 200704, 200705]},
    {"revision_key": "2012(198 CPI)", "rows": [201201, 201202, 201203, 201204, 201205, 201206]},
    {"revision_key": "2017(277 CPI)", "rows": [201701, 201702, 201703, 201704, 201705, 201706]},
    {"revision_key": "2022(359 CPI)", "rows": [202201]},
]


def _emp_key(emp_id):
    return str(emp_id or "").strip()[:5]


def _as_decimal(value):
    if value is None or value == "":
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return None


def _as_date(value):
    if not value:
        return None
    if hasattr(value, "date") and callable(value.date):
        try:
            return value.date()
        except Exception:
            pass
    if hasattr(value, "year") and not hasattr(value, "hour"):
        return value
    text = str(value).strip()[:10]
    try:
        return datetime.strptime(text, "%Y-%m-%d").date()
    except ValueError:
        return None


def format_tqs(years, months, days):
    if years is None and months is None and days is None:
        return ""
    return f"{years or 0}Y {months or 0}M {days or 0}D"


def _row_has_value(row):
    value = row.get("value") if isinstance(row, dict) else None
    if value is None or value == "":
        return False
    try:
        return float(value) != 0
    except (TypeError, ValueError):
        return True


def _format_print_block_title(revision_key, scale_band=""):
    """e.g. 2007(126 CPI) + 11000-29400 → Year 2007 - CPI 126 (11000-29400)."""
    text = str(revision_key or "")
    year_cpi = re.match(r"^(\d{4})\((\d+)\s*CPI\)$", text, re.I)
    year_label = re.match(r"^(\d{4})\((.+)\)$", text)
    if year_cpi:
        title = f"Detailed Calculation Breakdown Year {year_cpi.group(1)} - CPI {year_cpi.group(2)}"
    elif year_label:
        title = f"Year {year_label.group(1)} - {year_label.group(2)}"
    else:
        title = text or "Revision"

    band = format_scale_range_display(scale_band) if scale_band else ""
    if band:
        return f"{title} ({band})"
    return title


def build_revision_blocks(calculation_rows, start_revision, equivalent_scales=None):
    """
    Persistable A–D revision blocks for print (JSON on the consolidation row).
    Class 3/4 rows have numeric ``row`` keys; class 1/2 uses flat description rows.
    """
    if not calculation_rows:
        return []

    has_row_numbers = any(
        isinstance(r, dict) and r.get("row") is not None for r in calculation_rows
    )
    if not has_row_numbers:
        return build_class12_revision_blocks(
            calculation_rows, start_revision, equivalent_scales
        )

    row_map = {
        int(r["row"]): r
        for r in calculation_rows
        if isinstance(r, dict) and r.get("row") is not None
    }
    try:
        start_index = REVISION_ORDER.index(start_revision)
    except ValueError:
        start_index = 0

    scales = equivalent_scales or {}
    blocks = []
    for group_index, group in enumerate(REVISION_CARD_GROUPS):
        if group_index < start_index:
            continue
        key = group["revision_key"]
        lines = []
        for row_num in group["rows"]:
            row = row_map.get(row_num)
            if not row:
                continue
            lines.append(
                {
                    "row": row_num,
                    "code": row.get("code") or "",
                    "description": row.get("description") or f"Row {row_num}",
                    "value": row.get("value"),
                }
            )
        if not lines or not any(_row_has_value(line) for line in lines):
            continue

        scale_raw = scales.get(key) or ""
        if isinstance(scale_raw, dict):
            scale_raw = scale_raw.get("scale") or scale_raw.get("pay_band") or ""
        scale_band = format_scale_range_display(scale_raw) if scale_raw else ""

        blocks.append(
            {
                "revision_key": key,
                "title": _format_print_block_title(key, scale_band),
                "scale_band": scale_band,
                "rows": lines,
            }
        )
    return blocks


def _class12_block_title(last_description, start_revision=""):
    desc = str(last_description or "")
    if re.search(r"277\s*CPI|01\.01\.2017", desc, re.I):
        return "Detailed Calculation Breakdown Year 2017 - CPI 277", "2017"
    if re.search(r"126\s*CPI|01\.01\.2007", desc, re.I):
        return "Detailed Calculation Breakdown Year 2007 - CPI 126", "2007"
    if re.search(r"1708|01\.01\.1997", desc, re.I):
        return "Year 1997 (Revised Pay Scale)", "1997"
    if re.search(r"01\.01\.1992", desc, re.I):
        return "Year 1992 (Revised Pay Scale)", "1992"
    if re.search(r"01\.01\.1987", desc, re.I):
        return "Year 1987 (Revised Pay Scale)", "1987"
    if re.search(r"01\.01\.1984|1984", desc, re.I):
        return "Year 1984 (Revised Pay Scale)", "1984"
    start = str(start_revision or "").strip() or "start"
    return f"Year {start} (Revised Pay Scale)", start


def build_class12_revision_blocks(
    calculation_rows, start_revision="", equivalent_scales=None
):
    """
    Split class 1/2 flat calculation rows into year blocks for print.
    Each stage ends on a 'Basic pay as on…' / 'Basic Pay Over…' / minimum-basic line.
    Titles include equivalent scale in braces, same pattern as class 3/4.
    """
    rows = [r for r in (calculation_rows or []) if isinstance(r, dict)]
    if not rows:
        return []

    scales = equivalent_scales or {}
    blocks = []
    current = []

    def _scale_for(key):
        raw = scales.get(key) or scales.get(str(key)) or ""
        if isinstance(raw, dict):
            raw = raw.get("scale") or raw.get("pay_band") or raw.get("label") or ""
        return format_scale_range_display(raw) if raw else str(raw or "").strip()

    def _title_with_scale(title, key):
        band = _scale_for(key)
        if band and f"({band})" not in title:
            return f"{title} ({band})"
        return title

    def flush():
        nonlocal current
        if not current:
            return
        last_desc = current[-1].get("description") or ""
        title, key = _class12_block_title(last_desc, start_revision)
        # Opening-only block (just starting basic before first transition)
        if len(current) == 1 and "existing scale" in last_desc.lower():
            title = f"Year {start_revision or 'start'} (opening basic)"
            key = str(start_revision or "start")
        title = _title_with_scale(title, key)
        scale_band = _scale_for(key)
        blocks.append(
            {
                "revision_key": key,
                "title": title,
                "scale_band": scale_band,
                "rows": [
                    {
                        "row": idx + 1,
                        "code": r.get("code") or "",
                        "description": r.get("description") or f"Row {idx + 1}",
                        "value": r.get("value"),
                    }
                    for idx, r in enumerate(current)
                ],
            }
        )
        current = []

    for row in rows:
        current.append(row)
        desc = str(row.get("description") or "")
        ends_stage = bool(
            re.search(r"minimum basic", desc, re.I)
            or re.search(r"Basic Pay Over", desc, re.I)
            or (
                re.search(r"Basic pay as on", desc, re.I)
                and "existing scale" not in desc.lower()
            )
        )
        if ends_stage:
            flush()

    flush()
    return blocks


def _is_class12_category(category):
    return str(category or "").strip() in {"1", "2"}


def _apply_wage_m1_row(result, row, *, class12=False):
    """Map a wage-header row into m1_* print fields."""
    wage_emp_name = str(row[0] or "").strip()
    pensioner_name = str(row[1] or "").strip()
    pensioner_type = str(row[2] or "").strip().upper()
    old_basic = _as_decimal(row[3])
    rev_basic = _as_decimal(row[4])

    result["wage_emp_name"] = wage_emp_name
    result["pensioner_name"] = pensioner_name
    result["pensioner_type"] = pensioner_type
    result["is_employee_pension"] = pensioner_type == "P"
    result["m1_old_basic_pension"] = (
        float(old_basic) if old_basic is not None else None
    )
    result["m1_rev_basic_pension"] = (
        float(rev_basic) if rev_basic is not None else None
    )
    if class12:
        # Officers: 2017 hdr REV_BASIC_PENSION is M1 pension at 277 CPI.
        result["m1_family_pension_277"] = result["m1_rev_basic_pension"]
        result["m1_family_pension_359"] = None
    else:
        # Class 3/4: 2022 hdr OLD=277, REV=359.
        result["m1_family_pension_277"] = result["m1_old_basic_pension"]
        result["m1_family_pension_359"] = result["m1_rev_basic_pension"]
    return result


def _fetch_wage_row_class34(emp):
    """Class 3/4 M1 row from mirrored wage_2022_hdr_third (default DB)."""
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT EMP_NAME, PEN_NAME, PENSIONER_TYPE,
                   OLD_BASIC_PENSION, REV_BASIC_PENSION
            FROM fi_pn_wage_2022_hdr_third
            WHERE EMP_CD = %s
            LIMIT 1
            """,
            [emp],
        )
        return cursor.fetchone()


def _fetch_wage_row_class12(emp):
    """Class 1/2 M1 row from smpk_pension fi_pn_wage_2017_hdr_offi2."""
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT EMP_NAME, PEN_NAME, PENSIONER_TYPE,
                   OLD_BASIC_PENSION, REV_BASIC_PENSION
            FROM fi_pn_wage_2017_hdr_offi2
            WHERE EMP_CD = %s
            LIMIT 1
            """,
            [emp],
        )
        return cursor.fetchone()


def fetch_methodology1_pension_from_wage(emp_id, category=None):
    """
    Pension fixed as per Methodology-1 for consolidation print comparison.

    Class 3/4 — fi_pn_wage_2022_hdr_third (smpk_pension):
      OLD_BASIC_PENSION  → In 2017 (277 CPI)
      REV_BASIC_PENSION  → In 2022 (359 CPI)

    Class 1/2 — fi_pn_wage_2017_hdr_offi2 (smpk_pension):
      REV_BASIC_PENSION  → In 2017 (277 CPI)
      2022 (359 CPI) left blank
    """
    emp = _emp_key(emp_id)
    result = {
        "m1_family_pension_277": None,
        "m1_family_pension_359": None,
        "m1_old_basic_pension": None,
        "m1_rev_basic_pension": None,
        "wage_emp_name": "",
        "pensioner_name": "",
        "pensioner_type": "",
        "is_employee_pension": False,
    }
    if not emp:
        return result

    if _is_class12_category(category):
        row = _fetch_wage_row_class12(emp)
        if row:
            return _apply_wage_m1_row(result, row, class12=True)
        return result

    row = _fetch_wage_row_class34(emp)
    if row:
        return _apply_wage_m1_row(result, row, class12=False)

    # Fallback when category unknown / officer not in third table.
    row = _fetch_wage_row_class12(emp)
    if row:
        return _apply_wage_m1_row(result, row, class12=True)
    return result


def fetch_print_master_fields(emp_id, category=None):
    """
    Load case no, roll no, TQS, designation (and name fallback) for print header.
    """
    emp = _emp_key(emp_id)
    result = {
        "emp_cd": emp,
        "case_no": "",
        "roll_no": "",
        "name": "",
        "designation": "",
        "desig_cd": None,
        "tqs_yr": None,
        "tqs_month": None,
        "tqs_days": None,
        "tqs": "",
        "retirement_date": None,
    }
    if not emp:
        return result

    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT CA_NUMBER, PENSION_ROLL_NO, SEPARATION_DT
            FROM fi_pn_mh_pension_proposal
            WHERE EMP_CD = %s
            LIMIT 1
            """,
            [emp],
        )
        row = cursor.fetchone()
        if row:
            result["case_no"] = str(row[0] or "").strip()
            result["roll_no"] = str(row[1] or "").strip()
            result["retirement_date"] = _as_date(row[2])

        cursor.execute(
            """
            SELECT NAME, PENSION_ROLL_NO, TQS_YR, TQS_MONTH, TQS_DAYS, DESIG_CD
            FROM fi_pn_mh_pensioner
            WHERE EMP_CD = %s
            LIMIT 1
            """,
            [emp],
        )
        row = cursor.fetchone()
        if row:
            result["name"] = str(row[0] or "").strip()
            if not result["roll_no"]:
                result["roll_no"] = str(row[1] or "").strip()
            result["tqs_yr"] = row[2]
            result["tqs_month"] = row[3]
            result["tqs_days"] = row[4]
            result["tqs"] = format_tqs(row[2], row[3], row[4])
            if row[5] is not None:
                result["desig_cd"] = int(row[5])

        cursor.execute(
            """
            SELECT a.DESIG_CD, d.DESIG_DESC
            FROM fi_xx_mh_emp_adm a
            LEFT JOIN fi_xx_mh_desig d ON d.DESIG_CD = a.DESIG_CD
            WHERE a.EMP_CD = %s
            LIMIT 1
            """,
            [emp],
        )
        row = cursor.fetchone()
        if row:
            if row[0] is not None:
                result["desig_cd"] = int(row[0])
            desc = str(row[1] or "").strip()
            if desc:
                result["designation"] = desc

        if not result["designation"] and result["desig_cd"] is not None:
            cursor.execute(
                "SELECT DESIG_DESC FROM fi_xx_mh_desig WHERE DESIG_CD = %s LIMIT 1",
                [result["desig_cd"]],
            )
            drow = cursor.fetchone()
            if drow and drow[0]:
                result["designation"] = str(drow[0]).strip()

        if not result["name"]:
            cursor.execute(
                """
                SELECT TITLE, FIRST_NAME, MIDDLE_NAME, LAST_NAME
                FROM fi_xx_mh_emp_per
                WHERE EMP_CD = %s
                LIMIT 1
                """,
                [emp],
            )
            prow = cursor.fetchone()
            if prow:
                parts = [p for p in prow if p and str(p).strip()]
                result["name"] = " ".join(str(p).strip() for p in parts)

    result.update(fetch_methodology1_pension_from_wage(emp, category=category))
    return result


def snapshot_to_dict(obj):
    if not obj:
        return None
    return {
        "emp_cd": obj.emp_cd,
        "name": obj.name,
        "wage_emp_name": obj.wage_emp_name,
        "pensioner_name": obj.pensioner_name,
        "is_employee_pension": obj.is_employee_pension,
        "case_no": obj.case_no,
        "roll_no": obj.roll_no,
        "retirement_date": (
            obj.retirement_date.isoformat() if obj.retirement_date else None
        ),
        "category": obj.category,
        "designation": obj.designation,
        "tqs_yr": obj.tqs_yr,
        "tqs_month": obj.tqs_month,
        "tqs_days": obj.tqs_days,
        "tqs": obj.tqs_display,
        "average_pay": (
            float(obj.average_pay) if obj.average_pay is not None else None
        ),
        "last_pay": float(obj.last_pay) if obj.last_pay is not None else None,
        "scale": obj.scale,
        "start_revision": obj.start_revision,
        "revision_blocks": obj.revision_blocks or [],
        "calculation_rows": obj.calculation_rows or [],
        "m2_basic_2017": (
            float(obj.m2_basic_2017) if obj.m2_basic_2017 is not None else None
        ),
        "m2_basic_2022": (
            float(obj.m2_basic_2022) if obj.m2_basic_2022 is not None else None
        ),
        "m2_pension_277": (
            float(obj.m2_pension_277) if obj.m2_pension_277 is not None else None
        ),
        "m2_pension_359": (
            float(obj.m2_pension_359) if obj.m2_pension_359 is not None else None
        ),
        "m2_family_pension_277": (
            float(obj.m2_family_pension_277)
            if obj.m2_family_pension_277 is not None
            else None
        ),
        "m2_family_pension_359": (
            float(obj.m2_family_pension_359)
            if obj.m2_family_pension_359 is not None
            else None
        ),
        "m1_family_pension_277": (
            float(obj.m1_family_pension_277)
            if obj.m1_family_pension_277 is not None
            else None
        ),
        "m1_family_pension_359": (
            float(obj.m1_family_pension_359)
            if obj.m1_family_pension_359 is not None
            else None
        ),
        "diff_family_pension_277": (
            float(obj.diff_family_pension_277)
            if obj.diff_family_pension_277 is not None
            else None
        ),
        "diff_family_pension_359": (
            float(obj.diff_family_pension_359)
            if obj.diff_family_pension_359 is not None
            else None
        ),
        "calculated_at": (
            obj.calculated_at.isoformat() if obj.calculated_at else None
        ),
        "updated_at": obj.updated_at.isoformat() if obj.updated_at else None,
    }


def save_consolidation_snapshot(payload):
    """
    Upsert one consolidation row for an employee.

    Expected payload keys match Methodology2Consolidation fields plus optional
    revision_blocks / calculation_rows / pension summary values.
    """
    emp = _emp_key(payload.get("emp_cd") or payload.get("emp_id"))
    if not emp:
        return {"error": "emp_cd is required"}

    master = fetch_print_master_fields(emp, category=payload.get("category"))

    name = (payload.get("name") or master["name"] or "").strip()
    case_no = (payload.get("case_no") or master["case_no"] or "").strip()
    roll_no = (payload.get("roll_no") or master["roll_no"] or "").strip()
    designation = (
        payload.get("designation") or master["designation"] or ""
    ).strip()
    retirement_date = _as_date(
        payload.get("retirement_date") or master["retirement_date"]
    )

    tqs_yr = payload.get("tqs_yr", master["tqs_yr"])
    tqs_month = payload.get("tqs_month", master["tqs_month"])
    tqs_days = payload.get("tqs_days", master["tqs_days"])

    pension = payload.get("pension") or {}
    calculation_rows = payload.get("calculation_rows") or []
    start_revision = str(payload.get("start_revision") or "").strip()
    equivalent_scales = payload.get("equivalent_scales") or {}
    revision_blocks = payload.get("revision_blocks")
    if not revision_blocks:
        revision_blocks = build_revision_blocks(
            calculation_rows, start_revision, equivalent_scales
        )

    m2_fp_277 = _as_decimal(
        payload.get(
            "m2_family_pension_277",
            pension.get("family_pension_277_cpi", pension.get("family_pension")),
        )
    )
    m2_fp_359 = _as_decimal(
        payload.get("m2_family_pension_359", pension.get("family_pension_359_cpi"))
    )
    wage_m1 = fetch_methodology1_pension_from_wage(
        emp, category=payload.get("category")
    )
    # Wage tables are source of truth for M1; payload is fallback only.
    m1_fp_277 = _as_decimal(wage_m1.get("m1_family_pension_277"))
    if m1_fp_277 is None:
        m1_fp_277 = _as_decimal(payload.get("m1_family_pension_277"))
    m1_fp_359 = _as_decimal(wage_m1.get("m1_family_pension_359"))
    if m1_fp_359 is None:
        m1_fp_359 = _as_decimal(payload.get("m1_family_pension_359"))

    diff_277 = payload.get("diff_family_pension_277")
    diff_359 = payload.get("diff_family_pension_359")
    if diff_277 is None and m2_fp_277 is not None:
        diff_277 = m2_fp_277 - (m1_fp_277 or Decimal("0"))
    if diff_359 is None and m2_fp_359 is not None:
        diff_359 = m2_fp_359 - (m1_fp_359 or Decimal("0"))

    defaults = {
        "name": name,
        "wage_emp_name": str(
            payload.get("wage_emp_name", master.get("wage_emp_name", ""))
            or ""
        ).strip(),
        "pensioner_name": str(
            payload.get("pensioner_name", master.get("pensioner_name", ""))
            or ""
        ).strip(),
        "is_employee_pension": bool(
            payload.get(
                "is_employee_pension",
                master.get("is_employee_pension", False),
            )
        ),
        "case_no": case_no,
        "roll_no": roll_no,
        "retirement_date": retirement_date,
        "category": str(payload.get("category") or "").strip(),
        "designation": designation,
        "tqs_yr": tqs_yr,
        "tqs_month": tqs_month,
        "tqs_days": tqs_days,
        "average_pay": _as_decimal(
            payload.get("average_pay", payload.get("last_pay"))
        ),
        "last_pay": _as_decimal(payload.get("last_pay")),
        "scale": str(payload.get("scale") or "").strip(),
        "start_revision": start_revision,
        "revision_blocks": revision_blocks or [],
        "calculation_rows": calculation_rows,
        "m2_basic_2017": _as_decimal(
            payload.get("m2_basic_2017", pension.get("basic_pay_2017"))
        ),
        "m2_basic_2022": _as_decimal(
            payload.get("m2_basic_2022", pension.get("basic_pay_2022"))
        ),
        "m2_pension_277": _as_decimal(
            payload.get(
                "m2_pension_277",
                pension.get("pension_277_cpi", pension.get("pension")),
            )
        ),
        "m2_pension_359": _as_decimal(
            payload.get("m2_pension_359", pension.get("pension_359_cpi"))
        ),
        "m2_family_pension_277": m2_fp_277,
        "m2_family_pension_359": m2_fp_359,
        "m1_family_pension_277": m1_fp_277,
        "m1_family_pension_359": m1_fp_359,
        "diff_family_pension_277": _as_decimal(diff_277),
        "diff_family_pension_359": _as_decimal(diff_359),
        "calculated_at": timezone.now(),
    }

    obj, _created = Methodology2Consolidation.objects.update_or_create(
        emp_cd=emp,
        defaults=defaults,
    )
    # Keep exactly one row per emp (clean any duplicates from older auto-saves).
    Methodology2Consolidation.objects.filter(emp_cd=emp).exclude(pk=obj.pk).delete()
    return snapshot_to_dict(obj)


def get_consolidation_snapshot(emp_id):
    emp = _emp_key(emp_id)
    if not emp:
        return None
    obj = Methodology2Consolidation.objects.filter(emp_cd=emp).first()
    return snapshot_to_dict(obj)
