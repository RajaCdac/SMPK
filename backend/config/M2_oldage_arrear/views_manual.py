"""M2 manual entry — Excel upload; output Desktop/m2-manual-YYYY-MM-DD."""

import json
from contextlib import contextmanager
from pathlib import Path

from django.conf import settings
from django.http import StreamingHttpResponse
from rest_framework import status
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

import methodology2.services.consolidation_service as m2_cs
from methodology2.services.consolidation_service import use_consolidation_actor
from M2_oldage_arrear.models import M2OldageArrearConsolidation
from M2_oldage_arrear.services.manual_run_service import (
    default_manual_output_dir,
    finish_manual_session,
    prepare_manual_session,
    run_manual_from_excel,
    run_manual_session_row,
)


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
def _oa_consolidation_model():
    original_model = m2_cs.Methodology2Consolidation
    m2_cs.Methodology2Consolidation = M2OldageArrearConsolidation
    try:
        yield
    finally:
        m2_cs.Methodology2Consolidation = original_model


class ManualEntryUploadView(APIView):
    """One-shot upload (legacy). Prefer prepare/row/finish for progress UI."""

    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        upload = request.FILES.get("file") or request.FILES.get("excel")
        if not upload:
            return Response(
                {"error": "Upload Excel in field 'file'."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        out = default_manual_output_dir()
        out.mkdir(parents=True, exist_ok=True)
        file_bytes = upload.read()

        stream = str(
            request.query_params.get("stream") or request.data.get("stream") or ""
        ).lower() in ("1", "true", "yes")

        if stream:
            return self._stream_response(file_bytes, out)

        try:
            with _oa_consolidation_model(), use_consolidation_actor(request):
                summary = run_manual_from_excel(file_bytes, output_dir=out)
        except ValueError as exc:
            return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as exc:
            return Response(
                {"error": str(exc)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        return Response(_apply_display_paths(summary))

    def _stream_response(self, file_bytes: bytes, out: Path):
        def generate():
            try:
                with _oa_consolidation_model(), use_consolidation_actor(request):

                    def on_progress(current, total, emp_cd, result):
                        line = json.dumps(
                            {
                                "type": "progress",
                                "current": current,
                                "total": total,
                                "emp_cd": emp_cd,
                                "status": result.get("status"),
                            }
                        )
                        yield line + "\n"

                    summary = run_manual_from_excel(
                        file_bytes,
                        output_dir=out,
                        on_progress=on_progress,
                    )
                summary = _apply_display_paths(summary)
                yield json.dumps({"type": "done", **summary}) + "\n"
            except ValueError as exc:
                yield json.dumps({"type": "error", "error": str(exc)}) + "\n"
            except Exception as exc:
                yield json.dumps({"type": "error", "error": str(exc)}) + "\n"

        response = StreamingHttpResponse(
            generate(),
            content_type="application/x-ndjson; charset=utf-8",
        )
        response["Cache-Control"] = "no-cache"
        response["X-Accel-Buffering"] = "no"
        return response


class ManualEntryPrepareView(APIView):
    """Upload Excel → session_id + total (for row-by-row progress)."""

    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        upload = request.FILES.get("file") or request.FILES.get("excel")
        if not upload:
            return Response(
                {"error": "Upload Excel in field 'file'."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        out = default_manual_output_dir()
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
            with _oa_consolidation_model():
                meta = prepare_manual_session(
                    upload.read(), output_dir=out, generate_pdf=generate_pdf
                )
        except ValueError as exc:
            return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as exc:
            return Response(
                {"error": str(exc)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
        meta = _apply_display_paths(meta)
        return Response(meta)


class ManualEntryRowView(APIView):
    """Process one employee row by index (0-based)."""

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

        output_dir = request.data.get("output_dir") or default_manual_output_dir()
        try:
            with _oa_consolidation_model(), use_consolidation_actor(request):
                payload = run_manual_session_row(
                    session_id,
                    index,
                    output_dir=Path(output_dir),
                    header_overrides=request.data.get("header_overrides"),
                    header_answered=request.data.get("header_answered"),
                )
        except ValueError as exc:
            return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as exc:
            return Response(
                {"error": str(exc)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
        return Response(payload)


class ManualEntryFinishView(APIView):
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
        output_dir = request.data.get("output_dir") or default_manual_output_dir()
        try:
            with _oa_consolidation_model():
                summary = finish_manual_session(
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
