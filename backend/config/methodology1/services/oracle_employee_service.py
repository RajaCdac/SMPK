from employee.services.methodology_employee_lookup import (
    CLASS_3_4,
    fetch_employee_for_methodology,
)
from employee.services.oracle_service import get_oracle_connection

from methodology1.services.excel_loader import load_pay_scale_table
from methodology1.services.revision_resolver import get_revision_column
from methodology1.services.scale_parser import (
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
    """Load pay scale description from FI_PM_MH_PAYSCALE for Methodology I."""
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


def fetch_employee_for_methodology1(emp_id):
    return fetch_employee_for_methodology(
        emp_id,
        allowed_classes=CLASS_3_4,
        get_revision_column=get_revision_column,
        extract_scale_cd=extract_scale_cd,
        resolve_scale_string=resolve_scale_string,
        resolve_last_pay=resolve_last_pay,
    )
