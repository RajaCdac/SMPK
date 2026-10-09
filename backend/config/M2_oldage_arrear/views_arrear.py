"""Arrear for a saved Methodology-2 / Old Age consolidation. Does not recalculate it."""

from django.http import HttpResponse
from rest_framework import status
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from methodology2.services.arrear_payment_service import (
    calculate_consolidation_arrear,
    resolve_consolidation,
)
from methodology2.services.arrear_sheet_service import (
    build_arrear_payment_excel_bytes,
    calculate_arrear_batch,
)
from methodology2.services.bulk_excel_service import read_emp_rows_from_excel


class ArrearEmployeeView(APIView):
    def get(self, request, emp_id):
        row = resolve_consolidation(emp_id)
        if not row:
            return Response(
                {"error": "No consolidation saved for this employee."},
                status=status.HTTP_404_NOT_FOUND,
            )
        return Response({"emp_cd": row["emp_cd"], "consolidation": row})


class ArrearCalculateView(APIView):
    def post(self, request):
        data = request.data or {}
        result = calculate_consolidation_arrear(
            data.get("emp_cd") or data.get("emp_id"),
            data.get("from_month"),
            data.get("from_year"),
            data.get("to_month"),
            data.get("to_year"),
            source=data.get("source") or None,
        )
        if result.get("error"):
            code = (
                status.HTTP_404_NOT_FOUND
                if "No consolidation" in result["error"]
                else status.HTTP_400_BAD_REQUEST
            )
            return Response(result, status=code)
        return Response(result)


def _period_args(data):
    return (
        data.get("from_month"),
        data.get("from_year"),
        data.get("to_month"),
        data.get("to_year"),
    )


class ArrearBatchView(APIView):
    """
    POST /api/m2-oldage-arrear/arrear/batch/

    Excel with EMP_CD, plus from/to month and year.
    Returns one calculation row per employee. Does not mark payment.
    """

    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        upload = request.FILES.get("file") or request.FILES.get("excel")
        if not upload:
            return Response(
                {"error": "Upload an Excel file with an EMP_CD column."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        data = request.data or {}
        try:
            parsed = read_emp_rows_from_excel(upload.read())
            result = calculate_arrear_batch(
                [row.get("emp_cd") for row in parsed],
                *_period_args(data),
            )
        except ValueError as exc:
            return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as exc:
            return Response(
                {"error": str(exc)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
        if result.get("error"):
            return Response(result, status=status.HTTP_400_BAD_REQUEST)
        return Response(result)


class ArrearExportView(APIView):
    """
    POST /api/m2-oldage-arrear/arrear/export/

    Selected employee codes and the same month window.
    Returns the Pay & Cash workbook. Does not mark payment.
    """

    parser_classes = [JSONParser, FormParser, MultiPartParser]

    def post(self, request):
        data = request.data or {}
        codes = data.get("emp_cds") or data.get("emp_codes") or []
        if isinstance(codes, str):
            codes = [part.strip() for part in codes.split(",") if part.strip()]
        try:
            content, filename = build_arrear_payment_excel_bytes(
                codes,
                *_period_args(data),
                phase=data.get("phase") or "",
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
        return response
