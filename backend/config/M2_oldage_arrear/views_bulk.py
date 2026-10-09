from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path

from django.conf import settings
from rest_framework import status
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

import methodology2.services.bulk_run_service as m2_bulk
import methodology2.services.consolidation_service as m2_cs
from M2_oldage_arrear.models import M2OldageArrearConsolidation
from M2_oldage_arrear.services.bulk_run_service import (
    finish_bulk_session,
    prepare_bulk_session,
    run_bulk_from_excel,
    run_bulk_session_row,
)
from methodology2.services.consolidation_service import use_consolidation_actor

try:
    from zoneinfo import ZoneInfo

    _IST = ZoneInfo("Asia/Kolkata")
except Exception:  # pragma: no cover
    _IST = timezone(timedelta(hours=5, minutes=30), name="IST")


def _oldage_output_dir(run_at: datetime | None = None) -> Path:
    parent = Path(getattr(settings, "BULK_OUTPUT_DIR", Path.home() / "Desktop"))
    when = run_at or datetime.now(_IST)
    if when.tzinfo is None:
        when = when.replace(tzinfo=_IST)
    else:
        when = when.astimezone(_IST)
    stamp = when.strftime("%Y-%m-%d_%H%M")
    return parent / f"M2_OldAge_{stamp}"


def _apply_display_paths(summary: dict) -> dict:
    display = getattr(settings, "display_bulk_output_dir", None)
    if callable(display) and summary.get("output_dir"):
        summary["output_dir"] = display(summary["output_dir"])
        if summary.get("log_path"):
            summary["log_path"] = display(summary["log_path"])
        if summary.get("report_path"):
            summary["report_path"] = display(summary["report_path"])
    return summary


@contextmanager
def _oa_bulk_context():
    original_model = m2_cs.Methodology2Consolidation
    original_dir_fn = m2_bulk.default_run_output_dir
    m2_cs.Methodology2Consolidation = M2OldageArrearConsolidation
    m2_bulk.default_run_output_dir = _oldage_output_dir
    try:
        yield
    finally:
        m2_cs.Methodology2Consolidation = original_model
        m2_bulk.default_run_output_dir = original_dir_fn


class BulkUploadView(APIView):
    """One-shot upload (legacy). Prefer prepare/row/finish for progress UI."""

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

        try:
            with _oa_bulk_context(), use_consolidation_actor(request):
                summary = run_bulk_from_excel(upload.read(), output_dir=out)
        except ValueError as exc:
            return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as exc:
            return Response(
                {"error": str(exc)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        return Response(_apply_display_paths(summary))


class BulkPrepareView(APIView):
    """Upload Excel → session_id + total (for row-by-row progress)."""

    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        upload = request.FILES.get("file") or request.FILES.get("excel")
        if not upload:
            return Response(
                {
                    "error": (
                        "Upload an Excel file in field 'file' "
                        "(column EMP_CD required)"
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        out = _oldage_output_dir()
        raw_pdf = request.data.get("generate_pdf")
        if raw_pdf is None:
            generate_pdf = True
        else:
            generate_pdf = str(raw_pdf).strip().lower() in (
                "1",
                "true",
                "yes",
                "y",
                "on",
            )
        try:
            with _oa_bulk_context():
                meta = prepare_bulk_session(
                    upload.read(), output_dir=out, generate_pdf=generate_pdf
                )
        except ValueError as exc:
            return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as exc:
            return Response(
                {"error": str(exc)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
        return Response(_apply_display_paths(meta))


class BulkRowView(APIView):
    """Process one EMP_CD by index (0-based)."""

    parser_classes = [JSONParser, FormParser, MultiPartParser]

    def post(self, request):
        session_id = (
            request.data.get("session_id")
            or request.query_params.get("session_id")
            or ""
        ).strip()
        if not session_id:
            return Response(
                {"error": "session_id is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            index = int(request.data.get("index", request.query_params.get("index")))
        except (TypeError, ValueError):
            return Response(
                {"error": "index (0-based) is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        output_dir = request.data.get("output_dir") or _oldage_output_dir()
        try:
            with _oa_bulk_context(), use_consolidation_actor(request):
                payload = run_bulk_session_row(
                    session_id, index, output_dir=Path(output_dir)
                )
        except ValueError as exc:
            return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as exc:
            return Response(
                {"error": str(exc)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
        return Response(payload)


class BulkFinishView(APIView):
    """Write run_log; Report.xlsx only when generate_pdf was off at prepare."""

    parser_classes = [JSONParser, FormParser, MultiPartParser]

    def post(self, request):
        session_id = (
            request.data.get("session_id")
            or request.query_params.get("session_id")
            or ""
        ).strip()
        if not session_id:
            return Response(
                {"error": "session_id is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        output_dir = request.data.get("output_dir") or _oldage_output_dir()
        try:
            with _oa_bulk_context():
                summary = finish_bulk_session(
                    session_id, output_dir=Path(output_dir)
                )
        except ValueError as exc:
            return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as exc:
            return Response(
                {"error": str(exc)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
        return Response(_apply_display_paths(summary))
