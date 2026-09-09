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
from datetime import date, datetime, timedelta
from decimal import Decimal, InvalidOperation

from django.db import connection
from django.utils import timezone

from methodology2.models import Methodology2Consolidation
from methodology2.services.oracle_employee_service import format_scale_range_display

# Official CPI windows for DOD period splits on consolidation print.
CPI_277_START = date(2017, 1, 1)
CPI_359_START = date(2022, 1, 1)

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
    {"revision_key": "1979(REVISED PAY SCALE)", "rows": [197901, 197902, 197903, 197904, 197905]},
    {"revision_key": "1984(REVISED PAY SCALE)", "rows": [198401, 198402, 198403, 198404, 198405, 198406]},
    {"revision_key": "1988(607 CPI)", "rows": [198801, 198802, 198803, 198804, 198805, 198806, 198807]},
    {"revision_key": "1993(1030 CPI)", "rows": [199301, 199302, 199303, 199304, 199305, 199306, 199307]},
    {"revision_key": "1997(1708 CPI)", "rows": [199701, 199702, 199703, 199704, 199705]},
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


def _separation_type_label(code) -> str:
    """Display Type of Retirement from fi_xx_mh_emp_adm.SEPARATION_TYPE."""
    key = str(code or "").strip().upper()
    if not key:
        return ""
    labels = {
        "RT": "Retirement",
        "DT": "Death",
        "VR": "Voluntary retirement",
        "TN": "Termination",
        "TF": "Transfer",
        "RG": "Resignation",
        "CR": "Compulsory retirement",
        "RI": "Invalidation",
        "CO": "Contract end",
        "RD": "Redundancy",
        "WH": "Without notice",
        "RR": "Reversion",
        "SU": "Superannuation",
        "SD": "Superannuation",
    }
    return labels.get(key, key)


def _fetch_latest_roll_no(cursor, emp: str) -> str:
    """
    Latest roll: family pension roll when present (e.g. LIC-49/F),
    else employee pension / proposal roll (LIC-49).
    """
    cursor.execute(
        """
        SELECT FPENSION_ROLL_NO
        FROM fi_pn_mh_familypensioner
        WHERE EMP_CD = %s
          AND FPENSION_ROLL_NO IS NOT NULL
          AND TRIM(FPENSION_ROLL_NO) <> ''
        ORDER BY WEF_DT DESC, DATE_CREATED DESC, CLMCA_ID DESC
        LIMIT 1
        """,
        [emp],
    )
    row = cursor.fetchone()
    if row and str(row[0] or "").strip():
        return str(row[0]).strip()

    cursor.execute(
        """
        SELECT PENSION_ROLL_NO
        FROM fi_pn_mh_pension_proposal
        WHERE EMP_CD = %s
          AND PENSION_ROLL_NO IS NOT NULL
          AND TRIM(PENSION_ROLL_NO) <> ''
        LIMIT 1
        """,
        [emp],
    )
    row = cursor.fetchone()
    if row and str(row[0] or "").strip():
        return str(row[0]).strip()

    cursor.execute(
        """
        SELECT PENSION_ROLL_NO
        FROM fi_pn_mh_pensioner
        WHERE EMP_CD = %s
          AND PENSION_ROLL_NO IS NOT NULL
          AND TRIM(PENSION_ROLL_NO) <> ''
        LIMIT 1
        """,
        [emp],
    )
    row = cursor.fetchone()
    if row and str(row[0] or "").strip():
        return str(row[0]).strip()
    return ""


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
    scales = equivalent_scales or {}
    start_key = str(start_revision or "").strip()
    start_idx = (
        REVISION_ORDER.index(start_key) if start_key in REVISION_ORDER else 0
    )
    blocks = []
    for group in REVISION_CARD_GROUPS:
        key = group["revision_key"]
        if key in REVISION_ORDER and REVISION_ORDER.index(key) < start_idx:
            continue
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


def _format_dod_display(value):
    d = _as_date(value)
    if not d:
        return ""
    return f"{d.day}/{d.month}/{d.year}"


def _float_or_none(value):
    dec = _as_decimal(value)
    return float(dec) if dec is not None else None


def _diff_amounts(m2, m1):
    if m2 is None or m1 is None:
        return None
    try:
        return float(m2) - float(m1)
    except (TypeError, ValueError):
        return None


# Die-in-harness: 10-year enhanced FP if death on/after this date (rule notified
# ~2010 but effective from 01/01/2007); earlier deaths use 7 years.
_DIH_ENHANCED_10Y_FROM = date(2007, 1, 1)
_DIH_SEP_TYPES = frozenset({"DT", "DH", "DIH"})


def _add_years(d, years: int):
    """Add whole years to a date (clamp 29 Feb → 28 Feb)."""
    if not d:
        return None
    try:
        return d.replace(year=d.year + years)
    except ValueError:
        return d.replace(year=d.year + years, month=2, day=28)


def _day_before(d):
    """Inclusive 'upto' end date = day before an anniversary."""
    if not d:
        return None
    return d - timedelta(days=1)


def _is_class12_category_code(category) -> bool:
    c = str(category or "").strip()
    return c in ("1", "2", "I", "II")


def _is_die_in_harness(sep_type, dod, dor) -> bool:
    """Death while in service: DT/DH, or separation date coincides with DOD."""
    st = str(sep_type or "").strip().upper()
    if st in _DIH_SEP_TYPES:
        return True
    if dod and dor and dod == dor:
        return True
    return False


def compute_enhanced_fpension_upto(
    *,
    date_of_death,
    date_of_birth,
    retirement_date,
    category,
    separation_type=None,
):
    """
    Enhanced (50%) family-pension end date.

    Die-in-harness:
      DOD on/after 01/01/2007 → DOD + 10 years (else DOD + 7).
      (10-year rule effective from 2007; older DB rows may still show 7.)

    Died after retirement (−1 day on each anniversary):
      Class 1/2 → earlier of (DOB+67 − 1 day) and (DOR+7 − 1 day)
      Class 3/4 → earlier of (DOB+65 − 1 day) and (DOR+7 − 1 day)
      Enhanced after death only if that date is after DOD.
    """
    dod = _as_date(date_of_death)
    if not dod:
        return {
            "enhanced_upto": None,
            "enhanced_family_pension": False,
            "case_type": None,
            "rate_cutover": None,
        }

    dob = _as_date(date_of_birth)
    dor = _as_date(retirement_date)
    dih = _is_die_in_harness(separation_type, dod, dor)

    if dih:
        years = 10 if dod >= _DIH_ENHANCED_10Y_FROM else 7
        enhanced_upto = _add_years(dod, years)
        return {
            "enhanced_upto": enhanced_upto,
            "enhanced_family_pension": True,
            "case_type": "die_in_harness",
            "rate_cutover": enhanced_upto,
        }

    # Died after retirement — earlier of age-limit and DOR+7, each −1 day.
    if dob and dor:
        age_yrs = 67 if _is_class12_category_code(category) else 65
        age_end = _day_before(_add_years(dob, age_yrs))
        dor_end = _day_before(_add_years(dor, 7))
        enhanced_upto = min(age_end, dor_end)
        if enhanced_upto > dod:
            return {
                "enhanced_upto": enhanced_upto,
                "enhanced_family_pension": True,
                "case_type": "died_after_retirement",
                "rate_cutover": enhanced_upto,
            }
        # Enhanced window already ended while employee was alive →
        # after death only normal family (30%); emp→family cut-over at DOD.
        return {
            "enhanced_upto": enhanced_upto,
            "enhanced_family_pension": False,
            "case_type": "died_after_retirement",
            "rate_cutover": dod,
        }

    return {
        "enhanced_upto": None,
        "enhanced_family_pension": False,
        "case_type": "died_after_retirement",
        "rate_cutover": dod,
    }


def fetch_date_of_death(emp_id):
    """DOD_EMP_PENSIONER from family pension claim (if any)."""
    ctx = fetch_family_pension_rate_context(emp_id)
    return ctx.get("date_of_death")


def fetch_family_pension_rate_context(emp_id, category=None) -> dict:
    """
    Family-pension rate cut-over for M2 print columns.

    Computes enhanced FP end date from rules (DIH / died-after-ret). Falls back
    to fi_pn_mh_familypensioner.DOUBLE_FPENSION_UPTO when computation is incomplete.
    """
    emp = _emp_key(emp_id)
    out = {
        "date_of_death": None,
        "date_of_birth": None,
        "retirement_date": None,
        "separation_type": "",
        "category": str(category or "").strip(),
        "double_fpension_upto": None,
        "double_fpension_upto_db": None,
        "rate_cutover": None,
        "enhanced_family_pension": False,
        "case_type": None,
        "die_in_harness": False,
    }
    if not emp:
        return out

    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT DOD_EMP_PENSIONER
            FROM fi_pn_mh_fpen_caclaim
            WHERE EMP_CD = %s
              AND DOD_EMP_PENSIONER IS NOT NULL
            ORDER BY APPCN_DATE DESC, CLMCA_ID DESC
            LIMIT 1
            """,
            [emp],
        )
        row = cursor.fetchone()
        out["date_of_death"] = _as_date(row[0]) if row else None

        cursor.execute(
            """
            SELECT DOUBLE_FPENSION_UPTO
            FROM fi_pn_mh_familypensioner
            WHERE EMP_CD = %s
              AND DOUBLE_FPENSION_UPTO IS NOT NULL
            ORDER BY WEF_DT DESC, DATE_CREATED DESC, CLMCA_ID DESC
            LIMIT 1
            """,
            [emp],
        )
        row = cursor.fetchone()
        out["double_fpension_upto_db"] = _as_date(row[0]) if row else None

        cursor.execute(
            """
            SELECT BIRTH_DT
            FROM fi_xx_mh_emp_per
            WHERE EMP_CD = %s
            LIMIT 1
            """,
            [emp],
        )
        row = cursor.fetchone()
        out["date_of_birth"] = _as_date(row[0]) if row else None

        cursor.execute(
            """
            SELECT a.SEPARATION_DT, a.SEPARATION_TYPE,
                   COALESCE(f.EMP_CLASS, d.CLASS) AS EMP_CLASS
            FROM fi_xx_mh_emp_adm a
            LEFT JOIN fi_xx_mh_emp_fin f ON f.EMP_CD = a.EMP_CD
            LEFT JOIN fi_xx_mh_emp_data d ON d.EMP_CD = a.EMP_CD
            WHERE a.EMP_CD = %s
            LIMIT 1
            """,
            [emp],
        )
        row = cursor.fetchone()
        if row:
            out["retirement_date"] = _as_date(row[0])
            out["separation_type"] = str(row[1] or "").strip().upper()
            if not out["category"] and row[2] is not None:
                from employee.services.methodology_employee_lookup import (
                    category_from_emp_class,
                )

                out["category"] = category_from_emp_class(row[2]) or ""

        if not out["retirement_date"]:
            cursor.execute(
                """
                SELECT SEPARATION_DT
                FROM fi_pn_mh_pension_proposal
                WHERE EMP_CD = %s
                LIMIT 1
                """,
                [emp],
            )
            row = cursor.fetchone()
            out["retirement_date"] = _as_date(row[0]) if row else None

    out["die_in_harness"] = _is_die_in_harness(
        out["separation_type"], out["date_of_death"], out["retirement_date"]
    )

    computed = compute_enhanced_fpension_upto(
        date_of_death=out["date_of_death"],
        date_of_birth=out["date_of_birth"],
        retirement_date=out["retirement_date"],
        category=out["category"],
        separation_type=out["separation_type"],
    )
    out["case_type"] = computed.get("case_type")
    out["enhanced_family_pension"] = bool(computed.get("enhanced_family_pension"))
    # Display / print "Enhanced FP upto" only when enhanced period applies after death.
    out["double_fpension_upto"] = (
        computed.get("enhanced_upto")
        if out["enhanced_family_pension"]
        else None
    )
    out["rate_cutover"] = computed.get("rate_cutover")

    # Fallback to stored DOUBLE_FPENSION_UPTO when rule inputs incomplete.
    if out["rate_cutover"] is None and out["double_fpension_upto_db"]:
        out["double_fpension_upto"] = out["double_fpension_upto_db"]
        out["rate_cutover"] = out["double_fpension_upto_db"]
        out["enhanced_family_pension"] = True
    elif out["rate_cutover"] is None and out["date_of_death"]:
        out["rate_cutover"] = out["date_of_death"]

    if out["double_fpension_upto"] is None and out["enhanced_family_pension"]:
        out["double_fpension_upto"] = out["double_fpension_upto_db"]

    return out


def _row_to_wage_dict(row, *, class12=False):
    if not row:
        return None
    old_basic = _as_decimal(row[3])
    rev_basic = _as_decimal(row[4])
    old_single = _as_decimal(row[5]) if len(row) > 5 else None
    rev_single = _as_decimal(row[6]) if len(row) > 6 else None
    ptype = str(row[2] or "").strip().upper()
    if class12:
        m1_277 = _float_or_none(rev_basic)
        m1_359 = None
        m1_single_277 = _float_or_none(rev_single)
        m1_single_359 = None
    else:
        m1_277 = _float_or_none(old_basic)
        m1_359 = _float_or_none(rev_basic)
        m1_single_277 = _float_or_none(old_single)
        m1_single_359 = _float_or_none(rev_single)
    return {
        "wage_emp_name": str(row[0] or "").strip(),
        "pensioner_name": str(row[1] or "").strip(),
        "pensioner_type": ptype,
        "m1_old_basic_pension": _float_or_none(old_basic),
        "m1_rev_basic_pension": _float_or_none(rev_basic),
        "m1_old_single_basic_pension": _float_or_none(old_single),
        "m1_rev_single_basic_pension": _float_or_none(rev_single),
        "m1_277": m1_277,
        "m1_359": m1_359,
        "m1_single_277": m1_single_277,
        "m1_single_359": m1_single_359,
    }


def _fetch_wage_rows_class34(emp):
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT EMP_NAME, PEN_NAME, PENSIONER_TYPE,
                   OLD_BASIC_PENSION, REV_BASIC_PENSION,
                   OLD_SINGLE_BASIC_PENSION, REV_SINGLE_BASIC_PENSION
            FROM fi_pn_wage_2022_hdr_third
            WHERE EMP_CD = %s
            ORDER BY CASE UPPER(COALESCE(PENSIONER_TYPE, ''))
                       WHEN 'P' THEN 1
                       WHEN 'F' THEN 2
                       ELSE 3
                     END, PEN_NAME
            """,
            [emp],
        )
        return cursor.fetchall()


def _fetch_wage_rows_class12(emp):
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT EMP_NAME, PEN_NAME, PENSIONER_TYPE,
                   OLD_BASIC_PENSION, REV_BASIC_PENSION,
                   OLD_SINGLE_BASIC_PENSION, REV_SINGLE_BASIC_PENSION
            FROM fi_pn_wage_2017_hdr_offi2
            WHERE EMP_CD = %s
            ORDER BY CASE UPPER(COALESCE(PENSIONER_TYPE, ''))
                       WHEN 'P' THEN 1
                       WHEN 'F' THEN 2
                       ELSE 3
                     END, PEN_NAME
            """,
            [emp],
        )
        return cursor.fetchall()


def _wage_rows_by_type(rows, *, class12=False):
    by_type = {}
    for row in rows or []:
        parsed = _row_to_wage_dict(row, class12=class12)
        if not parsed:
            continue
        ptype = parsed["pensioner_type"] or "P"
        # Prefer first of each type (ordered P then F).
        by_type.setdefault(ptype, parsed)
    return by_type


def _apply_wage_m1_row(result, row, *, class12=False):
    """Map a single wage-header row into legacy m1_* print fields."""
    parsed = _row_to_wage_dict(row, class12=class12)
    if not parsed:
        return result
    result["wage_emp_name"] = parsed["wage_emp_name"]
    result["pensioner_name"] = parsed["pensioner_name"]
    result["pensioner_type"] = parsed["pensioner_type"]
    result["is_employee_pension"] = parsed["pensioner_type"] == "P"
    result["m1_old_basic_pension"] = parsed["m1_old_basic_pension"]
    result["m1_rev_basic_pension"] = parsed["m1_rev_basic_pension"]
    result["m1_family_pension_277"] = parsed["m1_277"]
    result["m1_family_pension_359"] = parsed["m1_359"]
    return result


def _cpi_kind_segments(
    period_start,
    period_end_exclusive,
    *,
    dod=None,
    enhanced_upto=None,
    rate_cutover=None,
    enhanced_family_pension=False,
    die_in_harness=False,
):
    """
    Split one CPI window into employee / enhanced / family segments.

    Die-in-harness: enhanced (50%) until enhanced_upto, then family (30%).
    Died after retirement with active enhanced window:
      employee until DOD, enhanced until enhanced_upto, then family.
    Died after retirement, enhanced already expired: employee until DOD, then family.
    """
    if not period_start:
        return [{"kind": "employee", "period_note": ""}]

    dod = _as_date(dod)
    enhanced_upto = _as_date(enhanced_upto)
    cutover = _as_date(rate_cutover) or enhanced_upto or dod
    if not cutover and not dod:
        return None

    # Each boundary is the LAST inclusive day of that kind.
    boundaries = []
    if die_in_harness and enhanced_upto:
        boundaries.append((enhanced_upto, "enhanced"))
    elif enhanced_family_pension and enhanced_upto and dod and enhanced_upto > dod:
        boundaries.append((dod, "employee"))
        boundaries.append((enhanced_upto, "enhanced"))
    elif dod:
        boundaries.append((dod, "employee"))
    elif enhanced_upto and enhanced_family_pension:
        boundaries.append((enhanced_upto, "enhanced"))
    elif cutover:
        kind = "enhanced" if enhanced_family_pension else "employee"
        boundaries.append((cutover, kind))
    else:
        return None

    def note_for(kind, from_d, to_d, *, open_end=False):
        if kind == "employee":
            if to_d and not open_end:
                return f"Employee pension up to {_format_dod_display(to_d)}"
            return "Employee pension"
        if kind == "enhanced":
            if to_d and not open_end:
                return (
                    f"Enhanced family pension (50%) up to "
                    f"{_format_dod_display(to_d)}"
                )
            return "Enhanced family pension (50%)"
        if from_d:
            return f"Family pension (30%) from {_format_dod_display(from_d)}"
        return "Family pension (30%)"

    segments = []
    cursor = period_start
    period_end = period_end_exclusive

    for last_day, kind in boundaries:
        if period_end and last_day < period_start:
            continue
        if cursor and period_end and cursor >= period_end:
            break
        if last_day < cursor:
            continue

        if period_end and last_day >= period_end:
            segments.append(
                {
                    "kind": kind,
                    "period_note": note_for(kind, cursor, None, open_end=True),
                }
            )
            return segments

        segments.append(
            {
                "kind": kind,
                "period_note": note_for(kind, cursor, last_day, open_end=False),
            }
        )
        cursor = last_day + timedelta(days=1)

    if not period_end or not cursor or cursor < period_end:
        if not segments:
            segments.append(
                {"kind": "family", "period_note": "Family pension (30%)"}
            )
        else:
            segments.append(
                {
                    "kind": "family",
                    "period_note": note_for("family", cursor, None),
                }
            )

    return segments


def build_pension_comparison(
    *,
    date_of_death,
    wage_by_type,
    m2_emp_277,
    m2_emp_359,
    m2_fam_277,
    m2_fam_359,
    family_pensioner_name="",
    double_fpension_upto=None,
    enhanced_family_pension=False,
    rate_cutover=None,
    die_in_harness=False,
    case_type=None,
):
    """
    Build print comparison columns.

    Rate cut-over (50% → 30%) from computed enhanced_upto / DOD rules.
    Without cut-over: one column per CPI from wage type.
    """
    dod = _as_date(date_of_death)
    double_upto = _as_date(double_fpension_upto)
    cutover = _as_date(rate_cutover) or double_upto or dod
    enhanced = bool(enhanced_family_pension) or (
        bool(double_upto) and (not dod or (double_upto and double_upto > dod))
    )
    dih = bool(die_in_harness) or case_type == "die_in_harness"

    p_row = wage_by_type.get("P") or {}
    f_row = wage_by_type.get("F") or {}

    fam_name = (
        family_pensioner_name
        or (f_row.get("pensioner_name") if f_row else "")
        or ""
    ).strip()

    def amounts_for(kind, cpi):
        # employee + enhanced both use M2 50%; family uses 30%.
        if kind in ("employee", "enhanced"):
            m2 = m2_emp_277 if cpi == 277 else m2_emp_359
            if kind == "enhanced":
                # Enhanced FP M1 = double/basic on F wage row.
                m1 = None
                if f_row:
                    m1 = f_row.get("m1_277") if cpi == 277 else f_row.get("m1_359")
                if m1 is None and p_row:
                    m1 = p_row.get("m1_277") if cpi == 277 else p_row.get("m1_359")
            else:
                m1 = p_row.get("m1_277") if cpi == 277 else p_row.get("m1_359")
                if m1 is None and f_row:
                    m1 = f_row.get("m1_277") if cpi == 277 else f_row.get("m1_359")
        else:
            m2 = m2_fam_277 if cpi == 277 else m2_fam_359
            m1 = None
            if f_row:
                m1 = (
                    f_row.get("m1_single_277")
                    if cpi == 277
                    else f_row.get("m1_single_359")
                )
                if m1 is None:
                    m1 = (
                        f_row.get("m1_277")
                        if cpi == 277
                        else f_row.get("m1_359")
                    )
            if m1 is None and p_row and not f_row:
                m1 = (
                    p_row.get("m1_single_277")
                    if cpi == 277
                    else p_row.get("m1_single_359")
                )
                if m1 is None:
                    m1 = (
                        p_row.get("m1_277")
                        if cpi == 277
                        else p_row.get("m1_359")
                    )
        m2f = _float_or_none(m2)
        m1f = _float_or_none(m1)
        return m2f, m1f, _diff_amounts(m2f, m1f)

    def make_col(cpi, kind, period_note, year_label):
        m2, m1, diff = amounts_for(kind, cpi)
        top = f"In {year_label} ({cpi} CPI)"
        header_lines = [top]
        if period_note:
            header_lines.append(period_note)
        return {
            "key": f"{cpi}_{kind}",
            "cpi": cpi,
            "kind": kind,
            "year_label": year_label,
            "period_note": period_note or "",
            "header_lines": header_lines,
            "header": " — ".join(header_lines),
            "m2": m2,
            "m1": m1,
            "diff": diff,
        }

    columns = []
    has_death_split = False

    if cutover or dod:
        seg_kwargs = dict(
            dod=dod,
            enhanced_upto=double_upto,
            rate_cutover=cutover,
            enhanced_family_pension=enhanced,
            die_in_harness=dih,
        )
        seg_277 = _cpi_kind_segments(CPI_277_START, CPI_359_START, **seg_kwargs)
        seg_359 = _cpi_kind_segments(CPI_359_START, None, **seg_kwargs)
        if not seg_277 or not seg_359:
            seg_277 = seg_277 or [{"kind": "employee", "period_note": ""}]
            seg_359 = seg_359 or [{"kind": "employee", "period_note": ""}]
        if len(seg_277) > 1 or len(seg_359) > 1:
            has_death_split = True
        for seg in seg_277:
            columns.append(
                make_col(277, seg["kind"], seg["period_note"], "2017")
            )
        for seg in seg_359:
            columns.append(
                make_col(359, seg["kind"], seg["period_note"], "2022")
            )
        section_title = "PENSION COMPARISON"
        is_employee_pension = False
    else:
        if p_row and not f_row:
            kind = "employee"
        elif f_row and not p_row:
            kind = "family"
        elif p_row:
            kind = "employee"
        else:
            kind = "family"
        is_employee_pension = kind == "employee"
        columns.append(make_col(277, kind, "", "2017"))
        columns.append(make_col(359, kind, "", "2022"))
        section_title = (
            "EMPLOYEE PENSION" if is_employee_pension else "FAMILY PENSION"
        )

    legacy_m1_277 = None
    legacy_m1_359 = None
    legacy_m2_277 = None
    legacy_m2_359 = None
    for col in columns:
        if col["cpi"] == 277:
            legacy_m1_277 = col["m1"]
            legacy_m2_277 = col["m2"]
        elif col["cpi"] == 359:
            legacy_m1_359 = col["m1"]
            legacy_m2_359 = col["m2"]

    return {
        "date_of_death": dod.isoformat() if dod else None,
        "date_of_death_display": _format_dod_display(dod) if dod else "",
        "double_fpension_upto": (
            double_upto.isoformat() if double_upto else None
        ),
        "double_fpension_upto_display": (
            _format_dod_display(double_upto) if double_upto else ""
        ),
        "rate_cutover": cutover.isoformat() if cutover else None,
        "enhanced_family_pension": enhanced,
        "die_in_harness": dih,
        "case_type": case_type,
        "family_pensioner_name": fam_name,
        "has_death_split": has_death_split,
        "section_title": section_title,
        "is_employee_pension": is_employee_pension,
        "columns": columns,
        "m1_family_pension_277": legacy_m1_277,
        "m1_family_pension_359": legacy_m1_359,
        "display_m2_277": legacy_m2_277,
        "display_m2_359": legacy_m2_359,
    }


def fetch_methodology1_pension_from_wage(emp_id, category=None):
    """
    Pension fixed as per Methodology-1 for consolidation print comparison.

    Loads P and F wage rows when both exist. Also returns date_of_death,
    double_fpension_upto / rate_cutover, and wage_by_type for print columns.

    Class 3/4 — fi_pn_wage_2022_hdr_third:
      OLD_BASIC_PENSION / REV_BASIC_PENSION → enhanced/double M1 (277 / 359)
      OLD_SINGLE_BASIC_PENSION / REV_SINGLE_BASIC_PENSION → normal family M1

    Class 1/2 — fi_pn_wage_2017_hdr_offi2:
      REV_BASIC_PENSION → In 2017 (277 CPI)
      REV_SINGLE_BASIC_PENSION → single-rate M1 when family (30%)
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
        "date_of_death": None,
        "double_fpension_upto": None,
        "rate_cutover": None,
        "enhanced_family_pension": False,
        "die_in_harness": False,
        "case_type": None,
        "wage_by_type": {},
        "has_p_and_f": False,
    }
    if not emp:
        return result

    class12 = _is_class12_category(category)
    if class12:
        rows = _fetch_wage_rows_class12(emp)
    else:
        rows = _fetch_wage_rows_class34(emp)
        if not rows:
            rows = _fetch_wage_rows_class12(emp)
            class12 = True

    by_type = _wage_rows_by_type(rows, class12=class12)
    result["wage_by_type"] = by_type
    result["has_p_and_f"] = "P" in by_type and "F" in by_type
    fp_ctx = fetch_family_pension_rate_context(emp, category=category)
    result["date_of_death"] = fp_ctx.get("date_of_death")
    result["double_fpension_upto"] = fp_ctx.get("double_fpension_upto")
    result["rate_cutover"] = fp_ctx.get("rate_cutover")
    result["enhanced_family_pension"] = bool(
        fp_ctx.get("enhanced_family_pension")
    )
    result["die_in_harness"] = bool(fp_ctx.get("die_in_harness"))
    result["case_type"] = fp_ctx.get("case_type")

    # Default single-row legacy fields: prefer P when both exist (no DOD yet).
    chosen = by_type.get("P") or by_type.get("F")
    if chosen:
        result["wage_emp_name"] = chosen["wage_emp_name"]
        result["pensioner_name"] = chosen["pensioner_name"]
        result["pensioner_type"] = chosen["pensioner_type"]
        result["is_employee_pension"] = chosen["pensioner_type"] == "P"
        result["m1_old_basic_pension"] = chosen["m1_old_basic_pension"]
        result["m1_rev_basic_pension"] = chosen["m1_rev_basic_pension"]
        result["m1_family_pension_277"] = chosen["m1_277"]
        result["m1_family_pension_359"] = chosen["m1_359"]

    # Family pensioner display name when F row exists.
    if by_type.get("F"):
        result["pensioner_name"] = by_type["F"]["pensioner_name"] or result[
            "pensioner_name"
        ]
        if by_type.get("P"):
            result["wage_emp_name"] = by_type["P"]["wage_emp_name"] or result[
                "wage_emp_name"
            ]

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
        "retirement_type": "",
        "date_of_death": None,
    }
    if not emp:
        return result

    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT CA_NUMBER, SEPARATION_DT
            FROM fi_pn_mh_pension_proposal
            WHERE EMP_CD = %s
            LIMIT 1
            """,
            [emp],
        )
        row = cursor.fetchone()
        if row:
            result["case_no"] = str(row[0] or "").strip()
            result["retirement_date"] = _as_date(row[1])

        result["roll_no"] = _fetch_latest_roll_no(cursor, emp)

        cursor.execute(
            """
            SELECT NAME, TQS_YR, TQS_MONTH, TQS_DAYS, DESIG_CD
            FROM fi_pn_mh_pensioner
            WHERE EMP_CD = %s
            LIMIT 1
            """,
            [emp],
        )
        row = cursor.fetchone()
        if row:
            result["name"] = str(row[0] or "").strip()
            result["tqs_yr"] = row[1]
            result["tqs_month"] = row[2]
            result["tqs_days"] = row[3]
            result["tqs"] = format_tqs(row[1], row[2], row[3])
            if row[4] is not None:
                result["desig_cd"] = int(row[4])

        cursor.execute(
            """
            SELECT a.DESIG_CD, d.DESIG_DESC, a.SEPARATION_TYPE, a.SEPARATION_DT, a.EXP_RET_DT
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
            result["retirement_type"] = _separation_type_label(row[2])
            if not result["retirement_date"]:
                result["retirement_date"] = _as_date(row[3] or row[4])

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
        "date_of_death": (
            obj.date_of_death.isoformat() if obj.date_of_death else None
        ),
        "pension_comparison": obj.pension_comparison or {},
        "case_no": obj.case_no,
        "roll_no": obj.roll_no,
        "retirement_type": getattr(obj, "retirement_type", "") or "",
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
        "stagnation_amount": (obj.pension_comparison or {}).get(
            "stagnation_amount"
        ),
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
    roll_no = (
        str(payload.get("roll_no") or "").strip()
        or str(master.get("roll_no") or "").strip()
    )
    retirement_type = (
        str(payload.get("retirement_type") or "").strip()
        or str(master.get("retirement_type") or "").strip()
    )
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
    m2_emp_277 = _as_decimal(
        payload.get(
            "m2_pension_277",
            pension.get("pension_277_cpi", pension.get("pension")),
        )
    )
    m2_emp_359 = _as_decimal(
        payload.get("m2_pension_359", pension.get("pension_359_cpi"))
    )

    wage_m1 = fetch_methodology1_pension_from_wage(
        emp, category=payload.get("category")
    )
    date_of_death = _as_date(
        payload.get("date_of_death") or wage_m1.get("date_of_death")
    )
    double_fpension_upto = _as_date(
        payload.get("double_fpension_upto")
        or wage_m1.get("double_fpension_upto")
    )
    rate_cutover = _as_date(
        payload.get("rate_cutover")
        or wage_m1.get("rate_cutover")
        or double_fpension_upto
        or date_of_death
    )
    enhanced_family_pension = bool(
        payload.get("enhanced_family_pension")
        if payload.get("enhanced_family_pension") is not None
        else wage_m1.get("enhanced_family_pension")
    )
    die_in_harness = bool(
        payload.get("die_in_harness")
        if payload.get("die_in_harness") is not None
        else wage_m1.get("die_in_harness")
    )
    case_type = (
        payload.get("case_type")
        or wage_m1.get("case_type")
    )
    pensioner_name = str(
        payload.get("pensioner_name", wage_m1.get("pensioner_name", ""))
        or master.get("pensioner_name", "")
        or ""
    ).strip()
    wage_emp_name = str(
        payload.get("wage_emp_name", wage_m1.get("wage_emp_name", ""))
        or master.get("wage_emp_name", "")
        or ""
    ).strip()

    comparison = build_pension_comparison(
        date_of_death=date_of_death,
        wage_by_type=wage_m1.get("wage_by_type") or {},
        m2_emp_277=m2_emp_277,
        m2_emp_359=m2_emp_359,
        m2_fam_277=m2_fp_277,
        m2_fam_359=m2_fp_359,
        family_pensioner_name=pensioner_name,
        double_fpension_upto=double_fpension_upto,
        enhanced_family_pension=enhanced_family_pension,
        rate_cutover=rate_cutover,
        die_in_harness=die_in_harness,
        case_type=case_type,
    )

    # Wage / comparison are source of truth for M1; payload is fallback only.
    m1_fp_277 = _as_decimal(comparison.get("m1_family_pension_277"))
    if m1_fp_277 is None:
        m1_fp_277 = _as_decimal(wage_m1.get("m1_family_pension_277"))
    if m1_fp_277 is None:
        m1_fp_277 = _as_decimal(payload.get("m1_family_pension_277"))
    m1_fp_359 = _as_decimal(comparison.get("m1_family_pension_359"))
    if m1_fp_359 is None:
        m1_fp_359 = _as_decimal(wage_m1.get("m1_family_pension_359"))
    if m1_fp_359 is None:
        m1_fp_359 = _as_decimal(payload.get("m1_family_pension_359"))

    is_employee_pension = bool(
        payload.get(
            "is_employee_pension",
            comparison.get(
                "is_employee_pension",
                master.get("is_employee_pension", False),
            ),
        )
    )
    # Rate cut-over (DOD / double FP) overrides the simple P/F flag.
    if (
        comparison.get("date_of_death")
        or comparison.get("double_fpension_upto")
        or comparison.get("rate_cutover")
        or comparison.get("has_death_split")
    ):
        is_employee_pension = bool(comparison.get("is_employee_pension"))

    # Legacy single-column diffs: use comparison display M2 vs M1 for last col per CPI.
    display_m2_277 = comparison.get("display_m2_277")
    display_m2_359 = comparison.get("display_m2_359")
    if is_employee_pension and not comparison.get("has_death_split"):
        display_m2_277 = _float_or_none(m2_emp_277)
        display_m2_359 = _float_or_none(m2_emp_359)
    elif not comparison.get("has_death_split"):
        display_m2_277 = _float_or_none(m2_fp_277)
        display_m2_359 = _float_or_none(m2_fp_359)

    diff_277 = payload.get("diff_family_pension_277")
    diff_359 = payload.get("diff_family_pension_359")
    if diff_277 is None and display_m2_277 is not None:
        diff_277 = _diff_amounts(display_m2_277, m1_fp_277)
    if diff_359 is None and display_m2_359 is not None:
        diff_359 = _diff_amounts(display_m2_359, m1_fp_359)

    stagnation_amount = _float_or_none(payload.get("stagnation_amount"))
    if stagnation_amount is not None:
        comparison["stagnation_amount"] = stagnation_amount

    defaults = {
        "name": name,
        "wage_emp_name": wage_emp_name,
        "pensioner_name": pensioner_name,
        "is_employee_pension": is_employee_pension,
        "date_of_death": date_of_death,
        "pension_comparison": comparison,
        "case_no": case_no,
        "roll_no": roll_no,
        "retirement_type": retirement_type,
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
        "m2_pension_277": m2_emp_277,
        "m2_pension_359": m2_emp_359,
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
