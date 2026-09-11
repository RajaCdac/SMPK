from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from .services.lic_claim_generation_service import (
    LicClaimGenerationError,
    load_normal_claim,
    save_normal_claim,
)
from .services.lic_claim_report_service import build_lic_normal_pen_dtls


class LicClaimGenerationNormalAPIView(APIView):
    """
    Oracle FI_PN_LIC_BILL_GEN_E — normal pension (PENSION_TYPE = N).

    GET  ?emp_cd=&claim_id=  → load row / defaults
    POST body                → save (insert/update)
    """

    def get(self, request):
        emp = request.query_params.get("emp_cd") or request.query_params.get(
            "emp_id"
        )
        claim_id = request.query_params.get("claim_id")
        try:
            data = load_normal_claim(emp, claim_id=claim_id)
            return Response(data)
        except LicClaimGenerationError as exc:
            return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as exc:
            return Response(
                {"error": str(exc)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    def post(self, request):
        try:
            data = save_normal_claim(request.data or {}, user=request.user)
            return Response(data)
        except LicClaimGenerationError as exc:
            return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as exc:
            return Response(
                {"error": str(exc)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class LicClaimNormalPrintAPIView(APIView):
    """Oracle FI_PN_LIC_NORMAL_PEN_DTLS — LIC Claim Form-Normal print data."""

    def get(self, request):
        emp = request.query_params.get("emp_cd") or request.query_params.get(
            "emp_id"
        )
        claim_id = request.query_params.get("claim_id")
        aadhar = request.query_params.get("aadhar_no")
        try:
            data = build_lic_normal_pen_dtls(
                emp, claim_id=claim_id, aadhar_no=aadhar
            )
            return Response(data)
        except LicClaimGenerationError as exc:
            return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as exc:
            return Response(
                {"error": str(exc)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
