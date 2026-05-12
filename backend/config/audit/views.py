from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.response import Response
from .models import AuditLog

# Create your views here.
class AuditLogListView(APIView):

    def get(self, request):

        logs = AuditLog.objects.all().order_by("-changed_at")

        data = []

        for log in logs:

            data.append({

                "id": log.id,
                "table_name": log.table_name,
                "record_id": log.record_id,
                "action": log.action,
                "changed_by": log.changed_by.username,
                "timestamp": log.changed_at,
                "ip_address": log.ip_address,
                "user_agent": log.user_agent,
                "module": log.module,
            })

        return Response(data)