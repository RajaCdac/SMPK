from employee.services.oracle_service import get_oracle_connection


def _normalize_type(value):
    text = str(value or "").strip().upper()
    if text in ("E", "EARN", "EARNNG"):
        return "E"
    if text in ("D", "DEDN", "DEDUCTION"):
        return "D"
    return text[:1] if text else "E"


def oracle_earndedn_row_to_defaults(column_names, row):
    data = dict(zip(column_names, row))
    code = str(data.get("EARNDEDN_CD") or "").strip()
    if not code:
        return None
    return {
        "earndedn_cd": code[:3],
        "earndedn_type": _normalize_type(data.get("EARNDEDN_TYPE")),
        "earndedn_desc": str(data.get("EARNDEDN_DESC") or "").strip()[:100],
        "date_created": data.get("DATE_CREATED"),
        "date_modified": data.get("DATE_MODIFIED"),
        "created_by": str(data.get("CREATED_BY") or "").strip()[:5],
        "modified_by": str(data.get("MODIFIED_BY") or "").strip()[:5],
    }


def fetch_oracle_earndedn_rows_for_sync():
    with get_oracle_connection().cursor() as cursor:
        cursor.execute(
            "SELECT * FROM FINANCE.FI_PN_MH_EARNDEDN ORDER BY EARNDEDN_CD"
        )
        column_names = [d[0] for d in cursor.description]
        rows = cursor.fetchall()

    result = []
    for row in rows:
        item = oracle_earndedn_row_to_defaults(column_names, row)
        if item:
            result.append(item)
    return result
