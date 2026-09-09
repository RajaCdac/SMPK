from datetime import date, datetime
from decimal import Decimal

from django.utils import timezone

from .models import AuditLog


def format_local_datetime(value):
    """
    Human-readable local app time: DD-MM-YYYY HH:MM:SS (no zone label).
    Uses Django TIME_ZONE (default Asia/Kolkata).
    """
    if value is None:
        return ""
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return ""
        # already plain local
        if len(text) == 19 and text[2] == "-" and text[10] == " ":
            return text
        try:
            value = datetime.fromisoformat(text.replace("Z", "+00:00"))
        except ValueError:
            return text
    if isinstance(value, datetime):
        if timezone.is_naive(value):
            value = timezone.make_aware(value, timezone.get_current_timezone())
        local = timezone.localtime(value)
        return local.strftime("%d-%m-%Y %H:%M:%S")
    if isinstance(value, date):
        return value.strftime("%d-%m-%Y")
    return str(value)


def _sanitize_for_json(value):
    if value is None:
        return None
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, datetime):
        # Store JSON times as plain local date-time (no TZ jargon)
        return format_local_datetime(value)
    if isinstance(value, date):
        return value.strftime("%d-%m-%Y")
    if isinstance(value, dict):
        return {k: _sanitize_for_json(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_sanitize_for_json(v) for v in value]
    return value


def _client_ip(request):
    if not request:
        return None
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR")
    if forwarded:
        return forwarded.split(",")[0].strip() or None
    return request.META.get("REMOTE_ADDR")


def log_audit(
    request,
    *,
    table_name,
    record_id,
    action,
    module,
    old_data=None,
    new_data=None,
    user=None,
):
    """
    Persist one audit row. Never raises — callers (login/save) stay safe.
    Pass ``user`` for LOGIN before request.user is authenticated.
    """
    try:
        if user is None and request is not None:
            cand = getattr(request, "user", None)
            if getattr(cand, "is_authenticated", False):
                user = cand

        AuditLog.objects.create(
            table_name=(table_name or "")[:100],
            record_id=str(record_id)[:100],
            action=(action or "")[:10],
            old_data=_sanitize_for_json(old_data),
            new_data=_sanitize_for_json(new_data),
            changed_by=user if getattr(user, "pk", None) else None,
            ip_address=_client_ip(request),
            user_agent=(
                (request.META.get("HTTP_USER_AGENT") or "")[:2000]
                if request is not None
                else None
            ),
            module=(module or "")[:50],
        )
    except Exception:
        # Never fail business actions because audit failed.
        return None
    return True


def log_login(request, user, *, extra=None):
    """Successful login with date/time in new_data."""
    if not user:
        return None
    now = timezone.now()
    local = format_local_datetime(now)
    payload = {
        "username": getattr(user, "username", None),
        "user_id": getattr(user, "id", None),
        "login_at": local,
    }
    if extra:
        payload.update(extra)
    return log_audit(
        request,
        table_name="accounts_user",
        record_id=getattr(user, "id", "") or getattr(user, "username", "unknown"),
        action="LOGIN",
        module="AUTH",
        old_data=None,
        new_data=payload,
        user=user,
    )


def log_logout(request, user=None, *, extra=None):
    """Explicit logout with date/time."""
    actor = user
    if actor is None and request is not None:
        cand = getattr(request, "user", None)
        if getattr(cand, "is_authenticated", False):
            actor = cand
    if not actor:
        return None
    now = timezone.now()
    local = format_local_datetime(now)
    payload = {
        "username": getattr(actor, "username", None),
        "user_id": getattr(actor, "id", None),
        "logout_at": local,
    }
    if extra:
        payload.update(extra)
    return log_audit(
        request,
        table_name="accounts_user",
        record_id=getattr(actor, "id", "") or getattr(actor, "username", "unknown"),
        action="LOGOUT",
        module="AUTH",
        old_data=None,
        new_data=payload,
        user=actor,
    )


def log_failed_login(request, username, *, reason="invalid_credentials"):
    """Failed login attempt (no changed_by user)."""
    now = timezone.now()
    local = format_local_datetime(now)
    return log_audit(
        request,
        table_name="accounts_user",
        record_id=(username or "unknown")[:100],
        action="LOGIN",
        module="AUTH",
        old_data=None,
        new_data={
            "username": username,
            "success": False,
            "reason": reason,
            "attempt_at": local,
        },
        user=None,
    )
