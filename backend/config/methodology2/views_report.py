"""Consolidation comparison Excel report API."""

from django.http import HttpResponse
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from methodology2.services.consolidation_report_service import (
    build_consolidation_report_bytes,
    report_filename,
)


class ConsolidationReportView(APIView):
    """Download Excel built from methodology2_consolidation rows."""

    def get(self, request):
        try:
            content, count = build_consolidation_report_bytes()
        except Exception as exc:
            return Response(
                {"error": str(exc)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        if count == 0:
            return Response(
                {"error": "No consolidation data in database. Run bulk or save first."},
                status=status.HTTP_404_NOT_FOUND,
            )

        response = HttpResponse(
            content,
            content_type=(
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            ),
        )
        response["Content-Disposition"] = (
            f'attachment; filename="{report_filename()}"'
        )
        return response
