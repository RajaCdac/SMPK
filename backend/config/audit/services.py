from datetime import date, datetime
from decimal import Decimal

from .models import AuditLog


def _sanitize_for_json(value):
    if value is None:
        return None
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, dict):
        return {k: _sanitize_for_json(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_sanitize_for_json(v) for v in value]
    return value


def log_audit(
    request,
    *,
    table_name,
    record_id,
    action,
    module,
    old_data=None,
    new_data=None,
):
    user = (
        request.user
        if getattr(request.user, "is_authenticated", False)
        else None
    )

    AuditLog.objects.create(
        table_name=table_name,
        record_id=str(record_id),
        action=action,
        old_data=_sanitize_for_json(old_data),
        new_data=_sanitize_for_json(new_data),
        changed_by=user,
        ip_address=request.META.get("REMOTE_ADDR"),
        user_agent=request.META.get("HTTP_USER_AGENT"),
        module=module,
    )
