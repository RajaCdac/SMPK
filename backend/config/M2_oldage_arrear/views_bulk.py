"""Bulk Excel upload — same Met2 engine; snapshots go to old-age table only."""

from datetime import date
from pathlib import Path

from django.conf import settings
from rest_framework import status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

import methodology2.services.bulk_run_service as m2_bulk
import methodology2.services.consolidation_service as m2_cs
from M2_oldage_arrear.models import M2OldageArrearConsolidation


def _oldage_output_dir(run_date: date | None = None) -> Path:
    parent = Path(getattr(settings, "BULK_OUTPUT_DIR", Path.home() / "Desktop"))
    d = run_date or date.today()
    return parent / f"M2_OldAge_{d.isoformat()}"


class BulkUploadView(APIView):
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
        out = Path(output_dir) if output_dir else _oldage_output_dir()

        original_model = m2_cs.Methodology2Consolidation
        original_dir_fn = m2_bulk.default_run_output_dir
        m2_cs.Methodology2Consolidation = M2OldageArrearConsolidation
        m2_bulk.default_run_output_dir = _oldage_output_dir
        try:
            summary = m2_bulk.run_bulk_from_excel(upload.read(), output_dir=out)
        except ValueError as exc:
            return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as exc:
            return Response(
                {"error": str(exc)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
        finally:
            m2_cs.Methodology2Consolidation = original_model
            m2_bulk.default_run_output_dir = original_dir_fn

        display = getattr(settings, "display_bulk_output_dir", None)
        if callable(display) and summary.get("output_dir"):
            summary["output_dir"] = display(summary["output_dir"])
            if summary.get("log_path"):
                summary["log_path"] = display(summary["log_path"])

        return Response(summary)
