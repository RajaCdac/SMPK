from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from .services.lic_claim_generation_service import (
    FamilyLicClaimError,
    load_family_claim,
    save_family_claim,
)
from .services.lic_claim_report_service import build_lic_family_pen_dtls


class FamilyLicClaimGenerationAPIView(APIView):
    """
    Oracle FI_PN_LIC_BILL_GEN_E — family pension (PENSION_TYPE = F).

    GET  ?emp_cd=&claim_id=  → load row / defaults + claim list
    POST body                → save (insert/update)
    """

    def get(self, request):
        emp = request.query_params.get("emp_cd") or request.query_params.get(
            "emp_id"
        )
        claim_id = request.query_params.get("claim_id")
        try:
            return Response(load_family_claim(emp, claim_id=claim_id))
        except FamilyLicClaimError as exc:
            return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as exc:
            return Response(
                {"error": str(exc)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    def post(self, request):
        try:
            data = save_family_claim(request.data or {}, user=request.user)
            return Response(data)
        except FamilyLicClaimError as exc:
            return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as exc:
            return Response(
                {"error": str(exc)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class FamilyLicClaimPrintAPIView(APIView):
    """Oracle FI_PN_LIC_FAMILY_PEN_DTLS print data (+ P_DA)."""

    def get(self, request):
        emp = request.query_params.get("emp_cd") or request.query_params.get(
            "emp_id"
        )
        claim_id = request.query_params.get("claim_id")
        aadhar = request.query_params.get("aadhar_no")
        da_pct = request.query_params.get("da_pct")
        try:
            data = build_lic_family_pen_dtls(
                emp,
                claim_id=claim_id,
                aadhar_no=aadhar,
                da_pct=da_pct,
            )
            return Response(data)
        except FamilyLicClaimError as exc:
            return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as exc:
            return Response(
                {"error": str(exc)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
