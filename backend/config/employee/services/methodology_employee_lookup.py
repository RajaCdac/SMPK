"""Employee lookup for Methodology I / II from MySQL Oracle mirror tables."""

from datetime import date, datetime

from employee.oracle_mirror import (
    FiXxMdFinscale,
    FiXxMhEmpAdm,
    FiXxMhEmpData,
    FiXxMhEmpFin,
    FiXxMhEmpPer,
)
from employee.services.scale_desc_service import (
    fetch_scale_desc,
    resolve_scale_from_employee_cache,
)

CLASS_3_4 = frozenset({"III", "IV", "3", "4"})
CLASS_1_2 = frozenset({"I", "II", "1", "2"})
CLASS_ALL = CLASS_1_2 | CLASS_3_4
_REV_2012_WEF = date(2012, 1, 1)


def category_from_emp_class(emp_class):
    """Normalize stored class (I/II/III/IV or 1–4) to methodology category 1–4."""
    mapping = {"I": "1", "II": "2", "III": "3", "IV": "4", "1": "1", "2": "2", "3": "3", "4": "4"}
    return mapping.get(_normalize_class(emp_class) or "", "")


def _emp_key(emp_id):
    return str(emp_id).strip()[:5]


def _as_date(value):
    if not value:
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    text = str(value).strip()[:10]
    try:
        return datetime.strptime(text, "%Y-%m-%d").date()
    except ValueError:
        return None


def _format_date_for_input(value):
    parsed = _as_date(value)
    if not parsed:
        return None
    return parsed.strftime("%Y-%m-%d")


def _scale_year(scale_sl):
    if not scale_sl:
        return None
    head = str(scale_sl).strip().split("/", 1)[0]
    try:
        return int(head)
    except (TypeError, ValueError):
        return None


def _normalize_class(value):
    if value is None or value == "":
        return ""
    text = str(value).strip().upper()
    roman = {"I": "I", "II": "II", "III": "III", "IV": "IV"}
    if text in roman:
        return text
    digit_map = {"1": "I", "2": "II", "3": "III", "4": "IV"}
    if text in digit_map:
        return digit_map[text]
    try:
        return digit_map.get(str(int(float(text))), text)
    except (TypeError, ValueError):
        return text


def _full_name(per):
    parts = [per.title, per.first_name, per.middle_name, per.last_name]
    return " ".join(str(p).strip() for p in parts if p and str(p).strip()).strip()


def _finscale_rows(emp_cd):
    return list(
        FiXxMdFinscale.objects.filter(emp_cd=emp_cd).order_by("-wef_dt", "-sl_no")
    )


def _select_finscale(
    emp_cd, target_scale_sl, separation_dt, *, prefer_without_bunching=False
):
    """
    Prefer a finscale row on the same revision year as EMP_FIN.scale_sl.
    Otherwise take the latest row at or before separation.

    Class 1/2 (dept): prefer_without_bunching=True selects the non-bunched
    basic (stag_pay_amt IS NULL) on the latest WEF for that revision — e.g.
    53210 instead of bunched/stepped-up 56880.
    """
    rows = _finscale_rows(emp_cd)
    if not rows:
        return None

    sep = _as_date(separation_dt)
    target_year = _scale_year(target_scale_sl)

    def _on_or_before_sep(row):
        wef = _as_date(row.wef_dt)
        return not sep or not wef or wef <= sep

    if prefer_without_bunching and target_year:
        candidates = [
            row
            for row in rows
            if _on_or_before_sep(row) and _scale_year(row.scale_sl) == target_year
        ]
        if candidates:
            latest_wef = max(
                (_as_date(row.wef_dt) for row in candidates if _as_date(row.wef_dt)),
                default=None,
            )
            same_wef = [
                row
                for row in candidates
                if latest_wef is None or _as_date(row.wef_dt) == latest_wef
            ]
            without = [row for row in same_wef if row.stag_pay_amt is None]
            if without:
                return max(without, key=lambda row: int(row.sl_no or 0))
            # No plain row: use lowest basic on that WEF (bunched is higher).
            return min(
                same_wef,
                key=lambda row: float(row.basic_amt or row.stag_pay_amt or 0),
            )

    if target_year:
        for row in rows:
            if _on_or_before_sep(row) and _scale_year(row.scale_sl) == target_year:
                return row

    for row in rows:
        if _on_or_before_sep(row):
            return row

    return rows[0]


def _employee_class(fin, emp_data):
    """
    Prefer FI_XX_MH_EMP_FIN.emp_class (finance / payscale class).
    EMP_DATA can be stale (e.g. III while FIN is II and scale is officer band).
    """
    if fin and fin.emp_class is not None and str(fin.emp_class).strip() != "":
        return _normalize_class(fin.emp_class)
    if emp_data and str(emp_data.emp_class or "").strip():
        return _normalize_class(emp_data.emp_class)
    return ""


def _basic_amount(finscale):
    if not finscale:
        return None
    if finscale.basic_amt is not None:
        return float(finscale.basic_amt)
    if finscale.stag_pay_amt is not None:
        return float(finscale.stag_pay_amt)
    return None


def _fitment_2007_to_2012(basic):
    """M2 2007→2012: VDA 57.14% + fitment 10.5%, ROUNDUP to next 10."""
    from methodology2.services.rounding_helpers import round2, round_up_to_10

    amount = float(basic)
    da = round2(amount * 0.5714)
    fitment = round2((amount + da) * 0.105)
    return float(round_up_to_10(amount + da + fitment))


def _convert_basic_for_target_scale(emp_cd, finscale, target_scale_sl):
    """
    EMP_FIN may already be on a newer revision while finscale still holds the
    old-scale basic (common for 01.01.2012 retirees). Convert that basic into
    the EMP_FIN revision so Methodology last_pay matches HR stage parity.

    Example (47489): 2007 basic 20600 with pre-GI 20000 → 2012 last pay 35780
    (fitment of 20000 = 34730, then × 1.03 ROUNDUP to 10).
    """
    basic = _basic_amount(finscale)
    if basic is None:
        return None

    target_year = _scale_year(target_scale_sl)
    source_year = _scale_year(finscale.scale_sl) if finscale else None
    if not target_year or not source_year or target_year <= source_year:
        return basic

    if source_year == 2007 and target_year == 2012:
        pre_basic = None
        for row in _finscale_rows(emp_cd):
            wef = _as_date(row.wef_dt)
            if (
                wef
                and wef < _REV_2012_WEF
                and _scale_year(row.scale_sl) == 2007
            ):
                pre_basic = _basic_amount(row)
                break

        wef = _as_date(finscale.wef_dt)
        if (
            pre_basic
            and pre_basic > 0
            and basic > pre_basic
            and wef
            and wef >= _REV_2012_WEF
        ):
            from methodology2.services.rounding_helpers import round_up_to_10

            return float(
                round_up_to_10(
                    _fitment_2007_to_2012(pre_basic) * (basic / pre_basic)
                )
            )
        return _fitment_2007_to_2012(basic)

    return basic


def fetch_employee_for_methodology(
    emp_id,
    *,
    allowed_classes,
    get_revision_column,
    extract_scale_cd,
    resolve_scale_string,
    resolve_last_pay,
):
    """
    Load separation date, scale, and last pay from local fi_xx_mh_emp_* mirrors.
    Returns None when the employee is missing or not in allowed_classes.
    """
    emp_key = _emp_key(emp_id)
    if not emp_key:
        return None

    per = FiXxMhEmpPer.objects.filter(emp_cd=emp_key).first()
    if not per:
        return None

    adm = FiXxMhEmpAdm.objects.filter(emp_cd=emp_key).first()
    fin = FiXxMhEmpFin.objects.filter(emp_cd=emp_key).first()
    emp_data = FiXxMhEmpData.objects.filter(emp_cd=emp_key).first()

    emp_class = _employee_class(fin, emp_data)
    allowed = {_normalize_class(value) for value in allowed_classes}
    if allowed and emp_class not in allowed:
        return None

    separation_dt = None
    if adm:
        separation_dt = adm.separation_dt or adm.exp_ret_dt
    if not separation_dt:
        return {
            "error": (
                "Separation / retirement date not found "
                "in employee admin record."
            ),
            "emp_id": emp_key,
        }

    scale_sl = ""
    if fin and str(fin.scale_sl or "").strip():
        scale_sl = str(fin.scale_sl).strip()

    finscale = _select_finscale(emp_key, scale_sl, separation_dt)
    if not scale_sl and finscale and str(finscale.scale_sl or "").strip():
        scale_sl = str(finscale.scale_sl).strip()

    oracle_basic_amt = _basic_amount(finscale)
    basic_amt = _convert_basic_for_target_scale(emp_key, finscale, scale_sl)
    name = _full_name(per)
    separation_date = _format_date_for_input(separation_dt)
    scale_cd = extract_scale_cd(scale_sl) if scale_sl else None
    scale_desc = fetch_scale_desc(scale_cd) if scale_cd else None
    scale_string = resolve_scale_string(
        scale_sl, separation_date, scale_desc=scale_desc
    )

    if not scale_string:
        scale_string = resolve_scale_from_employee_cache(emp_key)

    category = category_from_emp_class(emp_class)

    # Oracle payscale band is authoritative when Excel class3/4 mapping misses
    # (common for class 1/2 officer codes like 2007/RE/019 → 16400-40500).
    if not scale_string and scale_desc:
        scale_string = str(scale_desc).strip()

    if not scale_string:
        return {
            "error": (
                f"Could not map scale '{scale_sl}' to PayScale lookup "
                f"for retirement date {separation_date}."
                + (f" (scale_cd={scale_cd})" if scale_cd else "")
            ),
            "emp_id": emp_key,
            "name": name,
            "separation_date": separation_date,
            "oracle_scale_sl": scale_sl,
            "oracle_scale_cd": scale_cd or "",
            "oracle_scale_desc": scale_desc or "",
            "oracle_basic_amt": oracle_basic_amt,
            "emp_class": emp_class or "",
            "category": category,
            "data_source": "mysql_mirror",
        }

    last_pay = resolve_last_pay(scale_string, basic_amt)
    if last_pay is None:
        return {
            "error": "Last basic pay not found in employee finance mirror.",
            "emp_id": emp_key,
            "name": name,
            "separation_date": separation_date,
            "oracle_basic_amt": oracle_basic_amt,
            "emp_class": emp_class or "",
            "category": category,
            "data_source": "mysql_mirror",
        }

    return {
        "emp_id": emp_key,
        "name": name,
        "separation_date": separation_date,
        "scale": scale_string,
        "last_pay": last_pay,
        "oracle_scale_sl": scale_sl,
        "oracle_scale_cd": scale_cd or "",
        "oracle_scale_desc": scale_desc or "",
        "oracle_basic_amt": oracle_basic_amt,
        "revision": get_revision_column(separation_date),
        "emp_class": emp_class or "",
        "category": category,
        "data_source": "mysql_mirror",
    }
