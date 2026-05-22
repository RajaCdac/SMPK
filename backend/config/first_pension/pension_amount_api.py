from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from audit.services import log_audit
from .pension_calculation import (
    PensionCalculationError,
    build_amount_lookup_payload,
    run_pension_calculation_for_case,
    serialize_amount_data,
)


class PensionAmountLookupAPIView(APIView):
    """Load current DB inputs and any saved summary (fresh read every request)."""

    def get(self, request, emp_code):
        return Response(build_amount_lookup_payload(emp_code))


class PensionAmountCalculateAPIView(APIView):
    def post(self, request):
        try:
            emp_code = request.data.get("emp_code")
            if not emp_code:
                return Response(
                    {"error": "emp_code is required"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            lookup = build_amount_lookup_payload(emp_code)
            if not lookup.get("exists"):
                return Response(
                    {"error": lookup.get("message")},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            amount_data = lookup["amount_data"]
            if not amount_data.get("has_commutation_application"):
                return Response(
                    {
                        "error": (
                            "Commutation application not found. "
                            "Save commutation entry first."
                        )
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            if not amount_data.get("inputs_ready"):
                return Response(
                    {
                        "error": (
                            "Commutation % is not set in commutation application."
                        )
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            old_data = (
                amount_data
                if amount_data.get("calculated")
                else None
            )

            case, summary, calc, commutation_percent = (
                run_pension_calculation_for_case(emp_code, request.user)
            )

            new_data = serialize_amount_data(
                case,
                summary,
                calc,
                commutation_percent_from_app=commutation_percent,
            )
            new_data["has_commutation_application"] = True
            new_data["inputs_ready"] = True

            log_audit(
                request,
                table_name="PensionCase",
                record_id=case.id,
                action="UPDATE" if old_data else "CREATE",
                old_data=old_data,
                new_data=new_data,
                module="FIRST_PENSION",
            )

            return Response({
                "message": "Pension amounts calculated and saved successfully",
                "amount_data": new_data,
            })

        except PensionCalculationError as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except Exception as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
