from .models import AuditLog


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
        old_data=old_data,
        new_data=new_data,
        changed_by=user,
        ip_address=request.META.get("REMOTE_ADDR"),
        user_agent=request.META.get("HTTP_USER_AGENT"),
        module=module,
    )
