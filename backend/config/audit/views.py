from django.shortcuts import get_object_or_404
from rest_framework.response import Response
from rest_framework.views import APIView

from .diff import compute_audit_changes
from .models import AuditLog
from .services import format_local_datetime


def _serialize_audit_log(log, *, include_diff=False):
    # Plain local clock time for list/detail UI (no IST/UTC labels)
    ts_local = format_local_datetime(log.changed_at)
    payload = {
        "id": log.id,
        "table_name": log.table_name,
        "record_id": log.record_id,
        "action": log.action,
        "changed_by": log.changed_by.username if log.changed_by else None,
        "timestamp": ts_local,
        "timestamp_local": ts_local,
        "ip_address": log.ip_address,
        "user_agent": log.user_agent,
        "module": log.module,
        "old_data": log.old_data,
        "new_data": log.new_data,
    }
    if include_diff:
        payload["changes"] = compute_audit_changes(log.old_data, log.new_data)
    return payload


class AuditLogListView(APIView):

    def get(self, request):
        logs = AuditLog.objects.select_related("changed_by").order_by("-changed_at")
        data = [_serialize_audit_log(log) for log in logs]
        return Response(data)


class AuditLogDetailView(APIView):

    def get(self, request, pk):
        log = get_object_or_404(AuditLog.objects.select_related("changed_by"), pk=pk)
        return Response(_serialize_audit_log(log, include_diff=True))
