from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from family_pension.services.claim_service import (
    empty_claim_form,
    find_claims_by_emp,
    get_claim_by_id,
    list_relations,
    prefill_from_emp,
    save_claim,
)
from family_pension.services.list_service import (
    datatable_family_pensioners,
    list_family_pensioners,
)


class FamilyPensionerListAPIView(APIView):
    """
    Family pensioner list from fi_pn_mh_familypensioner.

    - Default → DataTables server-side JSON
    - ?all=1 → full list (legacy)
    """

    def get(self, request):
        try:
            if str(request.query_params.get("all") or "").lower() in (
                "1",
                "true",
                "yes",
            ):
                rows = list_family_pensioners()
                return Response({"count": len(rows), "results": rows})

            payload = datatable_family_pensioners(request.query_params)
            return Response(payload)
        except Exception as exc:
            return Response(
                {
                    "error": (
                        "Could not read family pensioners "
                        f"(smpk_pension.fi_pn_mh_familypensioner): {exc}"
                    )
                },
                status=status.HTTP_502_BAD_GATEWAY,
            )


class FamilyPensionClaimAPIView(APIView):
    """Load / save Family Pension Claim (FI_PN_MH_FPENSION_CLAIM_E)."""

    def get(self, request):
        claim_id = (request.query_params.get("clmca_id") or "").strip()
        emp_cd = (request.query_params.get("emp_cd") or "").strip()
        prefill = str(request.query_params.get("prefill") or "").lower() in (
            "1",
            "true",
            "yes",
        )
        clm_ca_type = (request.query_params.get("clm_ca_type") or "").strip()

        try:
            if claim_id:
                claim = get_claim_by_id(claim_id)
                if not claim:
                    return Response(
                        {"error": f"Claim {claim_id} not found"},
                        status=status.HTTP_404_NOT_FOUND,
                    )
                return Response({"exists": True, "claim": claim})

            if emp_cd and prefill:
                result = prefill_from_emp(emp_cd, clm_ca_type=clm_ca_type)
                if result.get("error"):
                    return Response(
                        result, status=status.HTTP_404_NOT_FOUND
                    )
                return Response(result)

            if emp_cd:
                matches = find_claims_by_emp(emp_cd)
                if not matches:
                    return Response(
                        {
                            "exists": False,
                            "error": f"No claim found for employee {emp_cd}",
                            "matches": [],
                        },
                        status=status.HTTP_404_NOT_FOUND,
                    )
                if len(matches) == 1:
                    claim = get_claim_by_id(matches[0]["clmca_id"])
                    return Response(
                        {"exists": True, "claim": claim, "matches": matches}
                    )
                return Response(
                    {
                        "exists": True,
                        "matches": matches,
                        "claim": None,
                        "message": "Multiple claims found — select Claim ID",
                    }
                )

            return Response(
                {
                    "claim": empty_claim_form(),
                    "exists": False,
                    "message": "Provide clmca_id or emp_cd",
                }
            )
        except Exception as exc:
            return Response(
                {
                    "error": (
                        "Could not read family pension claim "
                        f"(smpk_pension.fi_pn_mh_fpen_caclaim): {exc}"
                    )
                },
                status=status.HTTP_502_BAD_GATEWAY,
            )

    def post(self, request):
        user = getattr(request.user, "username", None) or "SMPK"
        try:
            result = save_claim(request.data or {}, user_id=user)
        except Exception as exc:
            return Response(
                {"error": f"Could not save claim: {exc}"},
                status=status.HTTP_502_BAD_GATEWAY,
            )
        if result.get("error"):
            return Response(result, status=status.HTTP_400_BAD_REQUEST)
        return Response(result)


class FamilyPensionRelationListAPIView(APIView):
    def get(self, request):
        try:
            return Response({"results": list_relations()})
        except Exception as exc:
            return Response(
                {"error": str(exc)},
                status=status.HTTP_502_BAD_GATEWAY,
            )
