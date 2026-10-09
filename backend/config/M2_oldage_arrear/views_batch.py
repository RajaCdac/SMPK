"""Batch list + Excel-from-DB by batch_id."""

from django.http import HttpResponse
from rest_framework import status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from M2_oldage_arrear.services.batch_service import (
    build_batch_report_excel_bytes,
    build_emp_list_report_excel_bytes,
    list_batches,
)
from methodology2.services.bulk_excel_service import read_emp_rows_from_excel


class BatchListView(APIView):
    """GET /api/m2-oldage-arrear/batches/?source=auto|manual&limit=50"""

    def get(self, request):
        try:
            source = (request.query_params.get("source") or "").strip() or None
            limit = int(request.query_params.get("limit") or 50)
            rows = list_batches(limit=limit, source=source)
        except Exception as exc:
            return Response(
                {"error": str(exc)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
        return Response({"batches": rows, "count": len(rows)})


class BatchExcelReportView(APIView):
    """
    GET /api/m2-oldage-arrear/batches/<batch_id>/report/

    Excel from DB consolidations for that batch only.
    If batch empty / no consolidations → clear error to run consolidation first.
    """

    def get(self, request, batch_id):
        try:
            content, filename = build_batch_report_excel_bytes(batch_id)
        except ValueError as exc:
            return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as exc:
            return Response(
                {"error": str(exc)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
        response = HttpResponse(
            content,
            content_type=(
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            ),
        )
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        return response


class EmpListExcelReportView(APIView):
    """
    POST /api/m2-oldage-arrear/report/excel/

    Upload an Excel with an EMP_CD column. Returns the same Report.xlsx
    a bulk batch download builds, from saved consolidations. No recalculation.
    """

    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        upload = request.FILES.get("file") or request.FILES.get("excel")
        if not upload:
            return Response(
                {"error": "Upload an Excel file with an EMP_CD column."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            rows = read_emp_rows_from_excel(upload.read())
            content, filename, summary = build_emp_list_report_excel_bytes(
                [r.get("emp_cd") for r in rows]
            )
        except ValueError as exc:
            return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as exc:
            return Response(
                {"error": str(exc)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
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
        response["X-Report-Missing"] = str(summary["missing"])
        return response
