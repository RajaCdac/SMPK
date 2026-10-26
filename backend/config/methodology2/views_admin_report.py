"""Admin-only consolidation activity by the user who saved it."""

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.permissions import IsAdminRole
from methodology2.services.admin_consolidation_report import (
    _parse_date,
    build_admin_consolidation_report,
)


class AdminConsolidationByUserView(APIView):
    """
    Who saved Methodology-2 and Old age consolidations.

    Query:
      username   optional login; date totals and the rows that user saved
      q          emp code, case no, or name; rows include who created them
      from_date, to_date   optional, filter by the save date (YYYY-MM-DD)
    """

    permission_classes = [IsAdminRole]

    def get(self, request):
        from_raw = request.query_params.get("from_date") or ""
        to_raw = request.query_params.get("to_date") or ""
        try:
            from_d = _parse_date(from_raw, "from_date")
            to_d = _parse_date(to_raw, "to_date")
        except ValueError as exc:
            return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        if from_d and to_d and from_d > to_d:
            return Response(
                {"error": "from_date cannot be after to_date."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        # Search shows the creator, so it is not limited to the chosen user.
        q = str(request.query_params.get("q") or "").strip()
        username = "" if q else str(request.query_params.get("username") or "").strip()
        try:
            payload = build_admin_consolidation_report(
                username=username,
                q=q,
                from_date=from_d,
                to_date=to_d,
            )
        except Exception as exc:
            return Response(
                {"error": str(exc)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
        return Response(payload)
