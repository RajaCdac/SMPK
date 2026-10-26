"""Consolidation dashboard API."""

from rest_framework import status
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from M2_oldage_arrear.services.dashboard_service import (
    build_consolidation_dashboard,
    delete_consolidation_m2_many,
    delete_consolidation_m2_only,
    set_consolidation_payment,
    set_consolidation_payment_many,
)
from M2_oldage_arrear.services.paid_excel_service import mark_paid_from_excel


def _actor(request) -> str:
    user = getattr(request, "user", None)
    if user is not None and getattr(user, "is_authenticated", False):
        return str(
            getattr(user, "username", None)
            or getattr(user, "email", None)
            or user.pk
            or ""
        )[:80]
    return ""


class ConsolidationDashboardView(APIView):
    """
    GET /api/m2-oldage-arrear/dashboard/

    Query:
      from_date, to_date  — filter on updated_at (YYYY-MM-DD)
      source              — all | oldage | without_oldage | enhanced
      category            — all | 12 | 34
      payment             — all | done | pending
      limit               — optional last N newest (omit or 0 = all matched)
    """

    def get(self, request):
        raw_limit = request.query_params.get("limit")
        if raw_limit is None or str(raw_limit).strip() == "":
            limit = None
        else:
            try:
                limit = int(raw_limit)
            except (TypeError, ValueError):
                return Response(
                    {"error": "limit must be an integer (0 = all)"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
        try:
            payload = build_consolidation_dashboard(
                from_date=request.query_params.get("from_date")
                or request.query_params.get("updated_from"),
                to_date=request.query_params.get("to_date")
                or request.query_params.get("updated_to"),
                source=request.query_params.get("source") or "all",
                category=request.query_params.get("category") or "all",
                limit=limit,
                payment=request.query_params.get("payment") or "all",
            )
        except ValueError as exc:
            return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as exc:
            return Response(
                {"error": str(exc)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
        return Response(payload)


class ConsolidationPaymentView(APIView):
    """
    POST /api/m2-oldage-arrear/dashboard/payment/

    Body: { emp_cd, source: oa|met2, payment_done: true|false }
    """

    parser_classes = [JSONParser, FormParser, MultiPartParser]

    def post(self, request):
        emp = (
            request.data.get("emp_cd")
            or request.data.get("emp_id")
            or ""
        )
        source = request.data.get("source") or ""
        raw = request.data.get("payment_done")
        if isinstance(raw, bool):
            done = raw
        else:
            done = str(raw).strip().lower() in ("1", "true", "yes", "y", "on")
        try:
            row = set_consolidation_payment(
                emp_cd=str(emp),
                source=str(source),
                payment_done=done,
                by_user=_actor(request),
            )
        except ValueError as exc:
            return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as exc:
            return Response(
                {"error": str(exc)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
        return Response({"ok": True, "row": row})


class ConsolidationDeleteView(APIView):
    """
    POST /api/m2-oldage-arrear/dashboard/delete/

    Body: { emp_cd, source: oa|met2 }

    Deletes m2* consolidation + related m2_consol_* for that emp/source.
    Never touches fi_* tables.
    """

    parser_classes = [JSONParser, FormParser, MultiPartParser]

    def post(self, request):
        emp = (
            request.data.get("emp_cd")
            or request.data.get("emp_id")
            or ""
        )
        source = request.data.get("source") or ""
        try:
            result = delete_consolidation_m2_only(
                emp_cd=str(emp), source=str(source)
            )
        except ValueError as exc:
            return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as exc:
            return Response(
                {"error": str(exc)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
        return Response({"ok": True, "deleted": result})


def _items_from_request(request):
    items = request.data.get("items")
    if items is None and request.data.get("emp_cd"):
        items = [
            {
                "emp_cd": request.data.get("emp_cd"),
                "source": request.data.get("source"),
            }
        ]
    return items


class ConsolidationPaymentManyView(APIView):
    """
    POST /api/m2-oldage-arrear/dashboard/payment-many/

    Body: { payment_done: true|false, items: [{ emp_cd, source }] }
    """

    parser_classes = [JSONParser, FormParser, MultiPartParser]

    def post(self, request):
        raw = request.data.get("payment_done")
        if isinstance(raw, bool):
            done = raw
        else:
            done = str(raw).strip().lower() in ("1", "true", "yes", "y", "on")
        try:
            result = set_consolidation_payment_many(
                _items_from_request(request),
                payment_done=done,
                by_user=_actor(request),
            )
        except ValueError as exc:
            return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as exc:
            return Response(
                {"error": str(exc)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
        return Response({"ok": result["error_count"] == 0, **result})


class ConsolidationPaidExcelView(APIView):
    """
    POST /api/m2-oldage-arrear/dashboard/paid-excel/

    Multipart file. Marks a saved consolidation paid when employee code,
    last pay, M1@277, M2@277, and M1@359 / M2@359 match. Returns the
    unmatched log.
    """

    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        upload = request.FILES.get("file")
        if upload is None:
            return Response(
                {"error": "Choose an Excel file."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            result = mark_paid_from_excel(upload.read(), by_user=_actor(request))
        except ValueError as exc:
            return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as exc:
            return Response(
                {"error": str(exc)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
        return Response(result)


class ConsolidationDeleteManyView(APIView):
    """
    POST /api/m2-oldage-arrear/dashboard/delete-many/

    Body: { items: [{ emp_cd, source }] }
    Paid rows are not deleted.
    """

    parser_classes = [JSONParser, FormParser, MultiPartParser]

    def post(self, request):
        try:
            result = delete_consolidation_m2_many(_items_from_request(request))
        except ValueError as exc:
            return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as exc:
            return Response(
                {"error": str(exc)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
        return Response({"ok": result["error_count"] == 0, **result})
