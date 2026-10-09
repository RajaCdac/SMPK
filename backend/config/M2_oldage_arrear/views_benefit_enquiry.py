"""Old Age Benefit enquiry API — Emp + From/To month-year."""

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from M2_oldage_arrear.services.benefit_enquiry_service import (
    load_oldage_benefit_enquiry,
    run_oldage_benefit_enquiry,
    save_oldage_benefit_enquiry,
)


def _user_label(request) -> str:
    user = getattr(request, "user", None)
    if user is None or not getattr(user, "is_authenticated", False):
        return ""
    return (
        getattr(user, "username", None)
        or getattr(user, "email", None)
        or str(getattr(user, "pk", "") or "")
    )


class OldAgeBenefitEnquiryView(APIView):
    """
    GET  — load saved enquiry for emp + from/to
    POST — calculate (and optionally save=1)
    """

    def get(self, request):
        emp = request.query_params.get("emp_cd") or request.query_params.get("emp_id")
        try:
            data = load_oldage_benefit_enquiry(
                emp,
                request.query_params.get("from_month"),
                request.query_params.get("from_year"),
                request.query_params.get("to_month"),
                request.query_params.get("to_year"),
            )
        except ValueError as exc:
            return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        if not data:
            return Response(
                {"error": "No saved old-age benefit enquiry for this emp/range"},
                status=status.HTTP_404_NOT_FOUND,
            )
        return Response(data)

    def post(self, request):
        data = request.data or {}
        try:
            result = run_oldage_benefit_enquiry(
                emp_cd=data.get("emp_cd") or data.get("emp_id"),
                from_month=data.get("from_month"),
                from_year=data.get("from_year"),
                to_month=data.get("to_month"),
                to_year=data.get("to_year"),
                dob=data.get("dob") or data.get("date_of_birth"),
                category=data.get("category"),
                m1_277=data.get("m1_pension_277"),
                m1_359=data.get("m1_pension_359"),
                m2_277=data.get("m2_pension_277") or data.get("pension_277"),
                m2_359=data.get("m2_pension_359") or data.get("pension_359"),
                is_employee_pension=data.get("is_employee_pension"),
                name=data.get("name") or "",
                roll_no=data.get("roll_no") or "",
                case_no=data.get("case_no") or "",
            )
        except ValueError as exc:
            return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as exc:
            return Response(
                {"error": str(exc)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        if result.get("error") and not result.get("dob"):
            return Response(result, status=status.HTTP_400_BAD_REQUEST)

        save_flag = str(data.get("save") or "").strip().lower() in (
            "1",
            "true",
            "yes",
            "y",
        )
        if save_flag or data.get("save") is True:
            result = save_oldage_benefit_enquiry(
                result, user=_user_label(request)
            )
        return Response(result)


class OldAgeBenefitEnquirySaveView(APIView):
    """POST body = calculated enquiry payload → persist month-wise."""

    def post(self, request):
        data = request.data or {}
        if data.get("error") and not data.get("months"):
            return Response(data, status=status.HTTP_400_BAD_REQUEST)
        try:
            if not data.get("months"):
                # Recalculate then save if only keys provided.
                data = run_oldage_benefit_enquiry(
                    emp_cd=data.get("emp_cd") or data.get("emp_id"),
                    from_month=data.get("from_month"),
                    from_year=data.get("from_year"),
                    to_month=data.get("to_month"),
                    to_year=data.get("to_year"),
                    dob=data.get("dob") or data.get("date_of_birth"),
                    category=data.get("category"),
                    m1_277=data.get("m1_pension_277"),
                    m1_359=data.get("m1_pension_359"),
                    m2_277=data.get("m2_pension_277") or data.get("pension_277"),
                    m2_359=data.get("m2_pension_359") or data.get("pension_359"),
                    is_employee_pension=data.get("is_employee_pension"),
                    name=data.get("name") or "",
                    roll_no=data.get("roll_no") or "",
                    case_no=data.get("case_no") or "",
                )
            if data.get("error") and not data.get("months"):
                return Response(data, status=status.HTTP_400_BAD_REQUEST)
            saved = save_oldage_benefit_enquiry(data, user=_user_label(request))
            return Response(saved)
        except ValueError as exc:
            return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as exc:
            return Response(
                {"error": str(exc)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
