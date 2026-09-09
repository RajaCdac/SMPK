"""Consolidation comparison Excel report API."""

from datetime import datetime

from django.http import HttpResponse
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from methodology2.services.consolidation_report_service import (
    build_consolidation_report_bytes,
    report_filename,
)


def _parse_iso_date(value: str, field: str):
    text = str(value or "").strip()[:10]
    if not text:
        return None
    try:
        return datetime.strptime(text, "%Y-%m-%d").date()
    except ValueError as exc:
        raise ValueError(f"{field} must be YYYY-MM-DD") from exc


class ConsolidationReportView(APIView):
    """
    Download Excel built from methodology2_consolidation rows.

    Required query params:
      from_date, to_date  — filter by updated_at (inclusive dates).
    """

    def get(self, request):
        from_raw = request.query_params.get("from_date") or request.query_params.get(
            "updated_from"
        )
        to_raw = request.query_params.get("to_date") or request.query_params.get(
            "updated_to"
        )
        if not from_raw or not to_raw:
            return Response(
                {
                    "error": (
                        "from_date and to_date are required "
                        "(filter by updated date, YYYY-MM-DD)."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            from_d = _parse_iso_date(from_raw, "from_date")
            to_d = _parse_iso_date(to_raw, "to_date")
        except ValueError as exc:
            return Response(
                {"error": str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if from_d > to_d:
            return Response(
                {"error": "from_date cannot be after to_date."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            content, count = build_consolidation_report_bytes(from_d, to_d)
        except Exception as exc:
            return Response(
                {"error": str(exc)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        if count == 0:
            return Response(
                {
                    "error": (
                        "No consolidation rows updated between "
                        f"{from_d.isoformat()} and {to_d.isoformat()}."
                    )
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        response = HttpResponse(
            content,
            content_type=(
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            ),
        )
        response["Content-Disposition"] = (
            f'attachment; filename="{report_filename(from_d, to_d)}"'
        )
        return response
