"""Consolidation Excel report from m2_oldage_arrear_consolidation (with OA columns)."""

from datetime import datetime

from django.http import HttpResponse
from rest_framework import status
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from M2_oldage_arrear.models import M2OldageArrearConsolidation
from methodology2.models import M2ConsolCase
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


class FamilyPensionReportView(APIView):
    """
    POST /api/m2-oldage-arrear/family-report/

    Either an Excel file with an EMP_CD column, or from_date + to_date
    (date the consolidation was saved). Optional phase text.
    Family pension consolidations only.
    """

    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def post(self, request):
        from M2_oldage_arrear.services.family_report_service import (
            build_family_pension_report,
        )
        from methodology2.services.bulk_excel_service import read_emp_rows_from_excel

        upload = request.FILES.get("file")
        phase = request.data.get("phase") or ""
        try:
            if upload:
                rows = read_emp_rows_from_excel(upload.read())
                content, filename, summary = build_family_pension_report(
                    emp_codes=[r.get("emp_cd") for r in rows], phase=phase
                )
            else:
                from_d = _parse_iso_date(request.data.get("from_date"), "from_date")
                to_d = _parse_iso_date(request.data.get("to_date"), "to_date")
                content, filename, summary = build_family_pension_report(
                    from_date=from_d, to_date=to_d, phase=phase
                )
        except ValueError as exc:
            return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as exc:
            return Response(
                {"error": str(exc)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        response = HttpResponse(
            content,
            content_type=(
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            ),
        )
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        response["X-Report-Requested"] = str(summary["requested"])
        response["X-Report-Found"] = str(summary["found"])
        response["X-Report-Not-Saved"] = ",".join(summary["not_saved"])
        response["X-Report-Not-Family"] = ",".join(summary["not_family"])
        response["Access-Control-Expose-Headers"] = (
            "Content-Disposition, X-Report-Requested, X-Report-Found, "
            "X-Report-Not-Saved, X-Report-Not-Family"
        )
        return response


class ConsolidationReportView(APIView):
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
            content, count = build_consolidation_report_bytes(
                from_d,
                to_d,
                include_oldage=True,
                include_enhanced=True,
                model=M2OldageArrearConsolidation,
                source_app=M2ConsolCase.SOURCE_OA,
            )
            filename = report_filename(from_d, to_d, include_oldage=True)
        except Exception as exc:
            return Response(
                {"error": str(exc)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        if count == 0:
            return Response(
                {
                    "error": (
                        "No old-age consolidation rows updated between "
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
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        return response
