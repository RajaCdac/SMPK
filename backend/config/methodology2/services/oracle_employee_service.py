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


def fetch_employee_for_methodology2(emp_id):
    emp_key = str(emp_id).strip()

    query = """
        SELECT
            TRIM(t1.TITLE || ' ' || t1.FIRST_NAME || ' ' ||
                NVL(t1.MIDDLE_NAME, '') || ' ' || t1.LAST_NAME) AS full_name,
            t2.SEPARATION_DT,
            t2.EXP_RET_DT,
            t4.SCALE_SL,
            t5.BASIC_AMT
        FROM FINANCE.FI_XX_MH_EMP_PER t1
        LEFT JOIN FINANCE.FI_XX_MH_EMP_ADM t2 ON t1.EMP_CD = t2.EMP_CD
        LEFT JOIN FINANCE.FI_XX_MH_EMP_FIN t4 ON t1.EMP_CD = t4.EMP_CD
        LEFT JOIN FINANCE.FI_XX_MH_EMP_FIN_VW t5 ON t4.EMP_CD = t5.EMP_CD
        WHERE t1.EMP_CD = :emp_id
        and t5.class='III'
    """

    with get_oracle_connection().cursor() as cursor:
        cursor.execute(query, {"emp_id": emp_key})
        row = cursor.fetchone()

        if not row:
            return None

        name = (row[0] or "").strip()
        separation_dt = row[1]
        exp_ret_dt = row[2]
        scale_sl = row[3]
        basic_amt = row[4]

        retirement_dt = separation_dt or exp_ret_dt
        if not retirement_dt:
            return {
                "error": (
                    "Separation / retirement date not found "
                    "in employee admin record."
                ),
                "emp_id": emp_key,
            }

        separation_date = _format_date_for_input(retirement_dt)
        scale_cd = extract_scale_cd(scale_sl)
        scale_desc = fetch_scale_desc_from_oracle(cursor, scale_cd)
        scale_string = resolve_scale_string(
            scale_sl,
            separation_date,
            scale_desc=scale_desc,
        )

    if not scale_string:
        return {
            "error": (
                f"Could not map scale '{scale_sl}' to PayScale lookup "
                f"for retirement date {separation_date}."
                + (
                    f" (scale_cd={scale_cd}, scale_desc={scale_desc})"
                    if scale_cd
                    else ""
                )
            ),
            "emp_id": emp_key,
            "name": name,
            "separation_date": separation_date,
            "oracle_scale_sl": str(scale_sl) if scale_sl else "",
            "oracle_scale_cd": scale_cd or "",
            "oracle_scale_desc": scale_desc or "",
            "oracle_basic_amt": float(basic_amt) if basic_amt else None,
        }

    last_pay = resolve_last_pay(scale_string, basic_amt)
    if last_pay is None:
        return {
            "error": "Last basic pay not found in employee finance view.",
            "emp_id": emp_key,
            "name": name,
            "separation_date": separation_date,
        }

    return {
        "emp_id": emp_key,
        "name": name,
        "separation_date": separation_date,
        "scale": scale_string,
        "last_pay": last_pay,
        "oracle_scale_sl": str(scale_sl).strip() if scale_sl else "",
        "oracle_scale_cd": scale_cd or "",
        "oracle_scale_desc": scale_desc or "",
        "oracle_basic_amt": float(basic_amt) if basic_amt is not None else None,
        "revision": get_revision_column(separation_date),
    }
