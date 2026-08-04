"""Bulk Excel upload API (Methodology 2 — class 1/2 and 3/4)."""

from pathlib import Path

from rest_framework import status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from methodology2.services.bulk_run_service import (
    default_run_output_dir,
    run_bulk_from_excel,
)


class BulkUploadView(APIView):
    """Upload Excel with EMP_CD; calculate/save; write Desktop/M2_date/{roll_no}.pdf."""

    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        upload = request.FILES.get("file") or request.FILES.get("excel")
        if not upload:
            return Response(
                {
                    "error": (
                        "Upload an Excel file in field 'file' "
                        "(column EMP_CD required; name/roll_no optional)"
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        output_dir = (request.data.get("output_dir") or "").strip()
        out = Path(output_dir) if output_dir else default_run_output_dir()

        try:
            summary = run_bulk_from_excel(upload.read(), output_dir=out)
        except ValueError as exc:
            return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as exc:
            return Response(
                {"error": str(exc)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        return Response(summary)
