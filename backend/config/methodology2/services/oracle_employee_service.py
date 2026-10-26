from employee.services.methodology_employee_lookup import (
    CLASS_ALL,
    fetch_employee_for_methodology,
)
from employee.services.oracle_service import get_oracle_connection

from methodology2.services.excel_loader import load_pay_scale_table
from methodology2.services.revision_resolver import get_revision_column
from methodology2.services.scale_parser import (
    expand_scale_increment_10,
    generate_pay_stages,
    get_next_higher_stage,
    normalize_scale_for_revision,
)


def _format_date_for_input(value):
    if not value:
        return None
    if hasattr(value, "strftime"):
        return value.strftime("%Y-%m-%d")
    return str(value)[:10]


def normalize_scale_text(value):
    """Ignore spaces for matching pay-scale strings."""
    if value is None:
        return ""
    return "".join(str(value).split())


def extract_scale_cd(scale_sl):
    """
    Oracle SCALE_SL e.g. '2022/RE/006/30' → scale code '2022/RE/006'
    (first three slash-separated segments).
    """
    if not scale_sl:
        return None

    parts = [p.strip() for p in str(scale_sl).strip().split("/") if p.strip()]
    if len(parts) >= 3:
        return "/".join(parts[:3])
    return str(scale_sl).strip()


def fetch_scale_desc_from_oracle(cursor, scale_cd):
    """Load pay scale description from FI_PM_MH_PAYSCALE for Methodology 2."""
    if not scale_cd:
        return None

    queries = [
        """
        SELECT SCALE_DESC
        FROM FINANCE.FI_PM_MH_PAYSCALE
        WHERE SCALE_CD = :scale_cd
        """,
        """
        SELECT SCALE_DESCRIPTION
        FROM FINANCE.FI_PM_MH_PAYSCALE
        WHERE SCALE_CD = :scale_cd
        """,
    ]

    for query in queries:
        try:
            cursor.execute(query, {"scale_cd": scale_cd})
            row = cursor.fetchone()
            if row and row[0]:
                return str(row[0]).strip()
        except Exception:
            continue

    return None


def batch_fetch_scale_desc_map(cursor, scale_cds):
    """Load SCALE_DESC for many scale codes in one round-trip."""
    codes = sorted({str(code).strip() for code in scale_cds if code})
    if not codes:
        return {}

    result = {}
    queries = [
        "SELECT SCALE_CD, SCALE_DESC FROM FINANCE.FI_PM_MH_PAYSCALE WHERE SCALE_CD IN ({})",
        "SELECT SCALE_CD, SCALE_DESCRIPTION FROM FINANCE.FI_PM_MH_PAYSCALE WHERE SCALE_CD IN ({})",
    ]
    chunk_size = 100

    for query_tpl in queries:
        try:
            for start in range(0, len(codes), chunk_size):
                chunk = codes[start : start + chunk_size]
                binds = {f"c{i}": code for i, code in enumerate(chunk)}
                placeholders = ", ".join(f":c{i}" for i in range(len(chunk)))
                cursor.execute(query_tpl.format(placeholders), binds)
                for scale_cd, scale_desc in cursor.fetchall():
                    key = str(scale_cd).strip()
                    if key and scale_desc and key not in result:
                        result[key] = str(scale_desc).strip()
            if result:
                return result
        except Exception:
            continue

    return result


def format_scale_range_display(scale_string):
    """Show min-max pay band, e.g. 10300-34800 from 10300-10-34800."""
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
        return f"{numbers[0]}-{numbers[-1]}"
    return text


def resolve_scale_display(scale_sl, retirement_date, *, cursor=None, scale_desc_map=None):
    """
    Convert Oracle SCALE_SL (e.g. 2022/RE/006/28) to pay-band text (e.g. 10300-14300).
    """
    if not scale_sl:
        return ""

    retirement_iso = _format_date_for_input(retirement_date)
    scale_cd = extract_scale_cd(scale_sl)
    scale_desc = None
    if scale_cd and scale_desc_map:
        scale_desc = scale_desc_map.get(scale_cd)
    if not scale_desc and scale_cd and cursor:
        scale_desc = fetch_scale_desc_from_oracle(cursor, scale_cd)
    if not scale_desc and scale_cd:
        from employee.services.scale_desc_service import fetch_scale_desc

        scale_desc = fetch_scale_desc(scale_cd)

    resolved = resolve_scale_string(
        scale_sl,
        retirement_iso,
        scale_desc=scale_desc,
    )
    if resolved:
        return format_scale_range_display(resolved)
    if scale_desc:
        return format_scale_range_display(scale_desc)

    return str(scale_sl).strip()


def _match_in_payscale(scale_key, retirement_date):
    if not scale_key:
        return None

    revision_column = get_revision_column(retirement_date)
    df = load_pay_scale_table()
    target = normalize_scale_text(
        normalize_scale_for_revision(scale_key, revision_column)
    )

    for _, row in df.iterrows():
        cell = row.get(revision_column)
        if cell is None:
            continue
        cell_norm = normalize_scale_text(
            normalize_scale_for_revision(str(cell).strip(), revision_column)
        )
        if cell_norm == target:
            return str(cell).strip()

    scale_codes = df["Scale"].astype(str).str.strip().str.upper()
    if str(scale_key).strip().upper() in scale_codes.values:
        match = df[scale_codes == str(scale_key).strip().upper()]
        if not match.empty:
            val = match.iloc[0][revision_column]
            return str(val).strip() if val is not None else None

    return None


def resolve_scale_string(scale_sl, retirement_date, scale_desc=None):
    """
    Map Oracle finance scale to PayScale string for the retirement revision column.
    Prefer SCALE_DESC from FI_PM_MH_PAYSCALE (via scale_cd from first 3 parts of SCALE_SL).
    """
    if scale_desc:
        matched = _match_in_payscale(scale_desc, retirement_date)
        if matched:
            return matched

    if scale_sl:
        matched = _match_in_payscale(scale_sl, retirement_date)
        if matched:
            return matched

    return None


def resolve_last_pay(scale_string, basic_amt):
    """Match Oracle basic to a valid stage in the selected scale."""
    if basic_amt is None:
        return None

    basic = int(float(basic_amt))
    stages = generate_pay_stages(scale_string)
    if not stages:
        return basic
    if basic in stages:
        return basic

    matched = get_next_higher_stage(scale_string, basic)
    return matched if matched is not None else basic


def _normalize_pay_band(value):
    """Normalize '36600 - 62000' / '36600-62000' for comparison."""
    text = str(value or "").strip().upper().replace(" ", "")
    return text.replace("–", "-").replace("—", "-")


def _band_min_amount(pay_band):
    text = _normalize_pay_band(pay_band)
    if not text or "-" not in text:
        return None
    try:
        return int(float(text.split("-", 1)[0]))
    except (TypeError, ValueError):
        return None


def _match_class12_grade_and_pay(
    separation_date, basic_amt, oracle_scale_desc=None
):
    """
    Map class 1/2 last basic to executive grade (E-n).

    Prefer Oracle FI_PM_MH_PAYSCALE band (dept scale, e.g. 36600-62000) so
    overlapping Excel bands (E-16 vs E-18) do not pick the wrong grade.
    """
    from methodology2.services.class1_2_service import get_class12_scales

    if basic_amt is None and not oracle_scale_desc:
        return None, None

    basic = None
    if basic_amt is not None:
        try:
            basic = int(float(basic_amt))
        except (TypeError, ValueError):
            basic = None

    items = get_class12_scales(separation_date) or []

    # 1) Exact match on Oracle / dept payscale description.
    want = _normalize_pay_band(oracle_scale_desc)
    if want:
        for item in items:
            band = item.get("pay_band") or ""
            label = item.get("label") or ""
            if (
                _normalize_pay_band(band) == want
                or _normalize_pay_band(label) == want
            ):
                grade = item.get("grade")
                if basic is None:
                    return grade, None
                stages = generate_pay_stages(band) or []
                if basic in stages:
                    return grade, basic
                higher = get_next_higher_stage(band, basic)
                return grade, int(higher) if higher is not None else basic

    if basic is None:
        return None, None

    # 2) Among bands that contain this basic, pick highest band start
    #    (E-18/36600 over E-16/32900 when both contain 56880).
    containing = []
    nearest = None
    nearest_gap = None
    for item in items:
        band = item.get("pay_band") or ""
        stages = generate_pay_stages(band) or []
        if basic in stages:
            containing.append(item)
            continue
        higher = get_next_higher_stage(band, basic)
        if higher is None:
            continue
        gap = abs(int(higher) - basic)
        if nearest_gap is None or gap < nearest_gap:
            nearest_gap = gap
            nearest = (item.get("grade"), int(higher))

    if containing:
        containing.sort(
            key=lambda item: _band_min_amount(item.get("pay_band")) or 0,
            reverse=True,
        )
        best = containing[0]
        return best.get("grade"), basic

    if nearest:
        return nearest
    return None, basic


def _doctor_flag_on(value) -> bool:
    if value is None or value == "":
        return False
    try:
        return int(value) == 1
    except (TypeError, ValueError):
        return str(value).strip() == "1"


def employee_is_doctor(emp_id) -> bool:
    emp = str(emp_id or "").strip()[:5]
    if not emp:
        return False
    from django.db import connection

    try:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT DOCTOR_FLG
                FROM fi_xx_mh_emp_per
                WHERE EMP_CD = %s
                LIMIT 1
                """,
                [emp],
            )
            row = cursor.fetchone()
    except Exception:
        return False
    return bool(row) and _doctor_flag_on(row[0])


def _wage_category(emp_id) -> str:
    emp = str(emp_id or "").strip()[:5]
    if not emp:
        return ""
    from django.db import connection

    for table in (
        "fi_pn_wage_2017_hdr_offi2",
        "fi_pn_wage_2017_hdr_third",
        "fi_pn_wage_2022_hdr_third",
    ):
        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    f"SELECT EMP_CLASS FROM {table} WHERE EMP_CD = %s LIMIT 1",
                    [emp],
                )
                row = cursor.fetchone()
        except Exception:
            continue
        text = str(row[0]).strip() if row and row[0] is not None else ""
        if text in ("1", "2", "3", "4"):
            return text
    return ""


def fetch_doctor_manual_header(emp_id):
    """
    Doctor whose class or pay scale is missing. The form stays open so NPA
    can be typed in Stagnation/NPA and last pay stays the basic.
    """
    emp = str(emp_id or "").strip()[:5]
    if not emp or not employee_is_doctor(emp):
        return None

    from employee.oracle_mirror import FiXxMhEmpAdm, FiXxMhEmpPer
    from employee.services.methodology_employee_lookup import (
        _format_date_for_input,
        _full_name,
    )

    per = FiXxMhEmpPer.objects.filter(emp_cd=emp).first()
    if not per:
        return None
    adm = FiXxMhEmpAdm.objects.filter(emp_cd=emp).first()
    sep = None
    if adm:
        sep = adm.separation_dt or adm.exp_ret_dt
    return {
        "emp_id": emp,
        "name": _full_name(per),
        "separation_date": _format_date_for_input(sep),
        "scale": "",
        "last_pay": None,
        "category": _wage_category(emp),
        "doctor_flg": 1,
        "data_source": "doctor_manual",
        "warning": (
            "No pay scale is on file for this doctor. "
            "Select the scale and last pay, and enter NPA in Stagnation/NPA."
        ),
    }


def _apply_doctor_npa(data):
    """
    Doctors (fi_xx_mh_emp_per.DOCTOR_FLG = 1): consolidation last pay is the
    salary basic plus that month's NPA, not the scale basic.

    Latest salary month on or before separation, earning 001 + earning 005.
    44232: 14350 + 3588 = 17938. 44346: 121730 + 24346 = 146076.
    """
    if not data:
        return data
    emp = str(data.get("emp_id") or data.get("emp_cd") or "").strip()[:5]
    if not emp:
        return data

    sep = data.get("separation_date") or data.get("retirement_date")
    sep_year = sep_month = None
    if sep:
        text = str(sep)[:10]
        parts = text.split("-")
        if len(parts) >= 2 and parts[0].isdigit() and parts[1].isdigit():
            sep_year = int(parts[0])
            sep_month = int(parts[1])

    from django.db import connection

    try:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT DOCTOR_FLG
                FROM fi_xx_mh_emp_per
                WHERE EMP_CD = %s
                LIMIT 1
                """,
                [emp],
            )
            row = cursor.fetchone()
            if not row or not _doctor_flag_on(row[0]):
                data["doctor_flg"] = 0
                return data
            data["doctor_flg"] = 1
            cursor.execute(
                """
                SELECT b.ACT_EARNDEDN_AMT, n.ACT_EARNDEDN_AMT
                FROM fi_pr_td_salout b
                INNER JOIN fi_pr_td_salout n
                  ON n.EMP_CD = b.EMP_CD
                 AND n.SAL_YR = b.SAL_YR
                 AND n.SAL_MTH = b.SAL_MTH
                 AND TRIM(n.EARNDEDN_CD) = '005'
                WHERE b.EMP_CD = %s
                  AND TRIM(b.EARNDEDN_CD) = '001'
                  AND b.ACT_EARNDEDN_AMT > 0
                  AND n.ACT_EARNDEDN_AMT > 0
                  AND (
                    %s IS NULL
                    OR b.SAL_YR < %s
                    OR (b.SAL_YR = %s AND b.SAL_MTH <= %s)
                  )
                ORDER BY b.SAL_YR DESC, b.SAL_MTH DESC
                LIMIT 1
                """,
                [emp, sep_year, sep_year, sep_year, sep_month],
            )
            hit = cursor.fetchone()
    except Exception:
        return data

    if not hit or hit[0] is None or hit[1] is None:
        return data

    from decimal import Decimal, ROUND_HALF_UP

    basic = Decimal(str(hit[0]))
    npa = Decimal(str(hit[1]))
    combined = (basic + npa).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
    data["npa_amount"] = float(npa.quantize(Decimal("1"), rounding=ROUND_HALF_UP))
    data["last_pay"] = int(combined)
    return data


def fetch_employee_for_methodology2(emp_id):
    data = fetch_employee_for_methodology(
        emp_id,
        allowed_classes=CLASS_ALL,
        get_revision_column=get_revision_column,
        extract_scale_cd=extract_scale_cd,
        resolve_scale_string=resolve_scale_string,
        resolve_last_pay=resolve_last_pay,
    )
    if not data:
        return None

    category = str(data.get("category") or "")
    if category not in ("1", "2"):
        return _apply_doctor_npa(data)

    # Class 1/2 (dept): last pay without bunching/stepping-up.
    from employee.services.methodology_employee_lookup import (
        _basic_amount,
        _select_finscale,
    )

    finscale = _select_finscale(
        data.get("emp_id"),
        data.get("oracle_scale_sl"),
        data.get("separation_date"),
        prefer_without_bunching=True,
    )
    plain_basic = _basic_amount(finscale)
    if plain_basic is not None:
        data["oracle_basic_amt"] = plain_basic
        try:
            data["last_pay"] = int(float(plain_basic))
        except (TypeError, ValueError):
            data["last_pay"] = plain_basic

    # Grade from Oracle payscale band (e.g. 36600-62000 → E-18), not first Excel hit.
    grade, last_pay = _match_class12_grade_and_pay(
        data.get("separation_date"),
        data.get("oracle_basic_amt")
        if data.get("oracle_basic_amt") is not None
        else data.get("last_pay"),
        oracle_scale_desc=data.get("oracle_scale_desc"),
    )
    if grade:
        data["scale"] = grade
        if last_pay is not None:
            data["last_pay"] = last_pay
        data.pop("error", None)
    else:
        # Still return identity + pay so consolidation/print fields can load;
        # user selects grade from class12 dropdown.
        if data.get("oracle_basic_amt") is not None and data.get("last_pay") is None:
            try:
                data["last_pay"] = int(float(data["oracle_basic_amt"]))
            except (TypeError, ValueError):
                pass
        data["scale"] = data.get("scale") if validate_like_grade(data.get("scale")) else ""
        data.pop("error", None)
        data["warning"] = (
            "Select executive grade (E-n) for Class 1/2 calculation."
        )
    return _apply_doctor_npa(data)


def validate_like_grade(value):
    text = str(value or "").strip().upper()
    return bool(text) and text.startswith("E")
