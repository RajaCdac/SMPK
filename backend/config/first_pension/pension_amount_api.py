from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from audit.services import log_audit
from .pension_proposal_api import (
    backfill_proposal_ca_number,
    resolve_proposal_ca_number,
)
from .services.first_month_pension_service import (
    FirstMonthPensionError,
    generate_first_month_pension,
)
from .pension_calculation import (
    PensionCalculationError,
    build_amount_lookup_payload,
    run_pension_calculation_for_case,
    serialize_amount_data,
)
from .services.pension_bill_service import _user_code
from .services.salout_transfer_service import (
    SaloutTransferError,
    get_salout_status,
    transfer_payroll_salout_to_pension,
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
            is_vr = amount_data.get("is_voluntary_retirement")
            if not is_vr:
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
            new_data["has_commutation_application"] = bool(
                amount_data.get("has_commutation_application")
            ) or bool(is_vr)
            new_data["is_voluntary_retirement"] = bool(is_vr)
            new_data["defer_commutation"] = bool(is_vr)
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


class FirstMonthPensionGenerateAPIView(APIView):
    """
    Generate first-month pension header (FMPEN_ID) in Oracle for the employee.

    This assumes:
      * PensionCase + PensionSummary are already calculated (amounts tab).
      * PensionProposal exists with CA number and bank details.
    """

    def post(self, request):
        emp_code = request.data.get("emp_code")
        if not emp_code:
            return Response(
                {"error": "emp_code is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            lookup = build_amount_lookup_payload(emp_code)
            if not lookup.get("exists"):
                return Response(
                    {"error": lookup.get("message")},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            amount_data = lookup["amount_data"]
            if not amount_data.get("calculated"):
                return Response(
                    {"error": "Calculate and save pension amounts before first pension generation."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            from .models import PensionCase, PensionProposal  # local import

            emp_key = str(emp_code).strip()
            case = PensionCase.objects.filter(emp_code=emp_key).first()
            if not case:
                return Response(
                    {"error": "Pension case not found for first pension generation."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            proposal = PensionProposal.objects.filter(emp_cd=emp_key).first()
            if not proposal:
                return Response(
                    {"error": "Pension proposal not found. Save proposal before first pension generation."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            if not resolve_proposal_ca_number(proposal, emp_key):
                return Response(
                    {"error": "CA number is missing in pension proposal."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            backfill_proposal_ca_number(proposal)

            result = generate_first_month_pension(emp_key, user=request.user)

            log_audit(
                request,
                table_name="FI_PN_TH_FIRST_MONTH_PENSION",
                record_id=result["fmpen_id"],
                action="CREATE",
                old_data=None,
                new_data=result,
                module="FIRST_PENSION",
            )

            return Response(
                {
                    "message": (
                        "First-month pension generated and bill posted in MySQL."
                    ),
                    **result,
                }
            )
        except FirstMonthPensionError as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_502_BAD_GATEWAY,
            )
        except Exception as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class PensionSaloutTransferAPIView(APIView):
    """PR → PN salout transfer (Oracle Forms payroll-to-pension block)."""

    def get(self, request, emp_code):
        return Response(get_salout_status(emp_code))

    def post(self, request):
        emp_code = request.data.get("emp_code")
        if not emp_code:
            return Response(
                {"error": "emp_code is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            result = transfer_payroll_salout_to_pension(
                emp_code,
                user_code=_user_code(request.user),
            )
            log_audit(
                request=request,
                table_name="fi_pn_th_salout",
                record_id=emp_code,
                action="CREATE",
                old_data=None,
                new_data=result,
                module="FIRST_PENSION",
            )
            return Response(
                {
                    "message": "Payroll salout transferred to pension tables.",
                    **result,
                }
            )
        except SaloutTransferError as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except Exception as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_502_BAD_GATEWAY,
            )
