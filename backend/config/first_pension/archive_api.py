"""Read-only Archive APIs — MySQL finance DB (port 3307)."""

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from .services.archive_service import (
    build_archive_employee_payload,
    get_bill_detail,
    get_journal,
)


class ArchiveEmployeeLookupAPIView(APIView):
    """Search archive by emp_cd — returns prefill payload for all tabs."""

    def get(self, request, emp_code):
        try:
            payload = build_archive_employee_payload(emp_code)
        except Exception as exc:
            return Response(
                {
                    "error": (
                        "Could not read archive database (finance@3307): "
                        f"{exc}"
                    )
                },
                status=status.HTTP_502_BAD_GATEWAY,
            )

        if not payload:
            return Response(
                {
                    "exists": False,
                    "error": f"No archive record found for employee {emp_code}.",
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        return Response({"exists": True, **payload})


class ArchiveBillDetailAPIView(APIView):
    def get(self, request, bill_no):
        try:
            detail = get_bill_detail(bill_no)
        except Exception as exc:
            return Response(
                {"error": str(exc)},
                status=status.HTTP_502_BAD_GATEWAY,
            )
        if not detail:
            return Response(
                {"error": f"Bill {bill_no} not found in archive."},
                status=status.HTTP_404_NOT_FOUND,
            )
        return Response(detail)


class ArchiveJournalDetailAPIView(APIView):
    def get(self, request, voucher_no):
        try:
            detail = get_journal(voucher_no)
        except Exception as exc:
            return Response(
                {"error": str(exc)},
                status=status.HTTP_502_BAD_GATEWAY,
            )
        if not detail.get("headers") and not detail.get("details"):
            return Response(
                {"error": f"Voucher {voucher_no} not found in archive."},
                status=status.HTTP_404_NOT_FOUND,
            )
        return Response(detail)
