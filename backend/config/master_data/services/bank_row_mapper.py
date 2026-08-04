def _parse_date(value):
    if value is None:
        return None
    if hasattr(value, "date"):
        return value.date()
    return value


def _clean_char(value, *, max_len=None):
    if value is None:
        return ""
    text = str(value).strip()
    if max_len:
        return text[:max_len]
    return text


def _clean_int(value):
    if value is None or value == "":
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


_BANK_FIELD_MAP = {
    "BANK_CD": ("bank_cd", lambda v: _clean_char(v, max_len=6)),
    "BANK_DESC": ("bank_desc", lambda v: _clean_char(v, max_len=50)),
    "BANK_ID": ("bank_id", lambda v: _clean_char(v, max_len=7)),
    "CONTROL_BANK_CD": ("control_bank_cd", lambda v: _clean_char(v, max_len=6)),
    "ADDR1": ("addr1", lambda v: _clean_char(v, max_len=25)),
    "ADDR2": ("addr2", lambda v: _clean_char(v, max_len=25)),
    "PS": ("ps", lambda v: _clean_char(v, max_len=30)),
    "CITY": ("city", lambda v: _clean_char(v, max_len=20)),
    "DIST": ("dist", lambda v: _clean_char(v, max_len=20)),
    "STATE": ("state", lambda v: _clean_char(v, max_len=20)),
    "PIN": ("pin", _clean_int),
    "COUNTRY": ("country", lambda v: _clean_char(v, max_len=20)),
    "CONTACT1": ("contact1", lambda v: _clean_char(v, max_len=15)),
    "CONTACT2": ("contact2", lambda v: _clean_char(v, max_len=15)),
    "FAX_NO": ("fax_no", lambda v: _clean_char(v, max_len=15)),
    "EMAIL_ID": ("email_id", lambda v: _clean_char(v, max_len=30)),
    "DATE_CREATED": ("date_created", _parse_date),
    "DATE_MODIFIED": ("date_modified", _parse_date),
    "MODIFIED_BY": ("modified_by", lambda v: _clean_char(v, max_len=5)),
    "CREATED_BY": ("created_by", lambda v: _clean_char(v, max_len=5)),
    "RBI_CD": ("rbi_cd", lambda v: _clean_char(v, max_len=9)),
    "OLD_BANK_CD": ("old_bank_cd", lambda v: _clean_char(v, max_len=6)),
}

_BANK_ABBR_FIELD_MAP = {
    "BANK_TYPE": ("bank_type", lambda v: _clean_char(v, max_len=2)),
    "BANK_NAME": ("bank_name", lambda v: _clean_char(v, max_len=60)),
    "CREATED_BY": ("created_by", lambda v: _clean_char(v, max_len=5)),
    "MODIFIED_BY": ("modified_by", lambda v: _clean_char(v, max_len=5)),
    "DATE_CREATED": ("date_created", _parse_date),
    "DATE_MODIFIED": ("date_modified", _parse_date),
    "BANK_ID": ("bank_id", lambda v: _clean_char(v, max_len=3)),
    "BANK_SHORT_NAME": ("bank_short_name", lambda v: _clean_char(v, max_len=10)),
}


def _map_row(column_names, row, field_map):
    data = {}
    for idx, col_name in enumerate(column_names):
        oracle_col = (col_name or "").upper()
        mapping = field_map.get(oracle_col)
        if not mapping:
            continue
        field_name, converter = mapping
        data[field_name] = converter(row[idx])
    return data


def oracle_bank_row_to_defaults(column_names, row):
    data = _map_row(column_names, row, _BANK_FIELD_MAP)
    if not data.get("bank_cd"):
        return None
    return data


def oracle_bank_abbr_row_to_defaults(column_names, row):
    data = _map_row(column_names, row, _BANK_ABBR_FIELD_MAP)
    if not data.get("bank_type"):
        return None
    return data
