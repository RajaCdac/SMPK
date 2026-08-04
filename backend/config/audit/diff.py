import json


def _format_display_value(value):
    if value is None:
        return None
    if isinstance(value, (dict, list)):
        return json.dumps(value, indent=2, ensure_ascii=False)
    if isinstance(value, bool):
        return "Yes" if value else "No"
    return value


def compute_audit_changes(old_data, new_data):
    """
    Field-by-field diff for audit log display.
    Returns list of {field, old_value, new_value, changed}.
    """
    old_data = old_data if isinstance(old_data, dict) else {}
    new_data = new_data if isinstance(new_data, dict) else {}

    keys = sorted(set(old_data.keys()) | set(new_data.keys()))
    changes = []

    for field in keys:
        old_raw = old_data.get(field)
        new_raw = new_data.get(field)
        changed = old_raw != new_raw
        changes.append({
            "field": field,
            "old_value": _format_display_value(old_raw),
            "new_value": _format_display_value(new_raw),
            "changed": changed,
        })

    return changes
