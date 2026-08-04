from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from methodology1.services.calculation_service import calculate_revision
from methodology1.services.family_pension_calculation_service import (
    calculate_family_pension,
)
from methodology1.services.cpi_chain_service import calculate_277_359
from methodology1.services.oracle_employee_service import (
    fetch_employee_for_methodology1,
)
from methodology1.services.revision_resolver import (
    get_calculation_start_revision,
    get_revision_column,
)
from methodology2.services.class1_2_service import get_class12_scales
from methodology1.services.scale_parser import generate_pay_stages
from methodology1.services.scale_service import (
    get_available_scale_options,
    get_equivalent_scales_by_scale,
    is_stage_based_scale,
    resolve_full_scale,
)

class GetScalesView(APIView):

    def get(self, request):

        retirement_date = request.GET.get(
            "retirement_date"
        )
        category = str(request.GET.get("category", "")).strip()

        if category in {"1", "2"}:
            return Response(get_class12_scales(retirement_date))

        scales = get_available_scale_options(
            retirement_date
        )

        return Response(scales)
    
class GetPayStagesView(APIView):

    def get(self, request):

        scale = request.GET.get("scale")

        if scale:
            retirement_date = request.GET.get("retirement_date")
            if retirement_date:
                scale = resolve_full_scale(retirement_date, scale)

        stages = generate_pay_stages(scale)

        return Response(stages)
    
class GetEquivalentScalesView(APIView):

    def get(self, request):

        retirement_date = request.GET.get(
            "retirement_date"
        )

        selected_scale = request.GET.get(
            "scale"
        )

        if selected_scale:
            selected_scale = resolve_full_scale(
                retirement_date,
                selected_scale,
            )

        data = get_equivalent_scales_by_scale(
            retirement_date,
            selected_scale
        )

        return Response(data)
    
class CalculateRevisionView(APIView):

    def post(self, request):

        retirement_date = request.data.get(
            "retirement_date"
        )

        selected_scale = request.data.get(
            "scale"
        )

        if selected_scale:
            selected_scale = resolve_full_scale(
                retirement_date,
                selected_scale,
            )

        last_pay = request.data.get(
            "last_pay"
        )

        scales = get_equivalent_scales_by_scale(
            retirement_date,
            selected_scale
        )

        scale_revision = get_revision_column(retirement_date)
        start_revision = get_calculation_start_revision(retirement_date)

        result = calculate_revision(
            scales, start_revision, last_pay, scale_revision
        )

        return Response({
            "rows": result.get("rows", []),
            "pension": result.get("pension", {}),
            "start_revision": start_revision,
            "scale_revision": scale_revision,
            "last_pay_adjusted": result.get("last_pay_adjusted", False),
            "effective_last_pay": result.get("effective_last_pay"),
            "original_last_pay": result.get("original_last_pay"),
            "last_pay_adjustment": result.get("last_pay_adjustment"),
        })
    
class Cpi277And359View(APIView):
    """Input: separation_date + last_pay. Output: 277 CPI and 359 CPI values."""

    def post(self, request):
        separation_date = request.data.get("separation_date")
        last_pay = request.data.get("last_pay")

        if not separation_date or last_pay in (None, ""):
            return Response(
                {"error": "separation_date and last_pay are required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            result = calculate_277_359(separation_date, last_pay)
        except Exception as exc:
            return Response(
                {"error": str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if result.get("error"):
            return Response(result, status=status.HTTP_400_BAD_REQUEST)

        return Response(result)


class ScaleTypeView(APIView):

    def get(self, request):
        retirement_date = request.GET.get(
            'retirement_date'
        )
        scale_revision = get_revision_column(retirement_date)
        start_revision = get_calculation_start_revision(retirement_date)
        return Response({
            "revision": start_revision,
            "scale_revision": scale_revision,
            "is_stage_based": is_stage_based_scale(scale_revision),
        })


class FamilyPensionCalculationView(APIView):
    """Methodology I unified calculation: category 1/2 or 3/4."""

    def post(self, request):
        separation_date = request.data.get("separation_date")
        category = request.data.get("category")
        pay = request.data.get("pay", request.data.get("last_pay"))
        scale = request.data.get("scale")
        grade = request.data.get("grade")

        result = calculate_family_pension(
            separation_date=separation_date,
            category=category,
            pay=pay,
            scale=scale,
            grade=grade,
        )

        if result.get("error"):
            return Response(result, status=status.HTTP_400_BAD_REQUEST)

        return Response(result)


class EmployeeLookupView(APIView):
    """Fetch separation date, scale, and last pay from local DB by employee code."""

    def get(self, request, emp_id):
        try:
            data = fetch_employee_for_methodology1(emp_id)
            if not data:
                return Response(
                    {"error": "Employee not found"},
                    status=status.HTTP_404_NOT_FOUND,
                )
            if data.get("error"):
                return Response(
                    data,
                    status=status.HTTP_400_BAD_REQUEST,
                )
            return Response(data)
        except Exception as exc:
            return Response(
                {"error": str(exc)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

