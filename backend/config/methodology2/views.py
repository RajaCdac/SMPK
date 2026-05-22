from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from methodology2.services.calculation_service import calculate_revision
from methodology2.services.oracle_employee_service import (
    fetch_employee_for_methodology2,
)
from methodology2.services.revision_resolver import get_revision_column
from methodology2.services.scale_parser import generate_pay_stages
from methodology2.services.scale_service import (
    get_available_scales,
    get_equivalent_scales_by_scale,
    is_stage_based_scale,
)

class GetScalesView(APIView):

    def get(self, request):

        retirement_date = request.GET.get(
            "retirement_date"
        )

        scales = get_available_scales(
            retirement_date
        )

        return Response(scales)
    
class GetPayStagesView(APIView):

    def get(self, request):

        scale = request.GET.get("scale")

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

        last_pay = request.data.get(
            "last_pay"
        )

        scales = get_equivalent_scales_by_scale(
            retirement_date,
            selected_scale
        )

        current_column = get_revision_column(
            retirement_date
        )

        columns = list(scales.keys())

        current_index = columns.index(
            current_column
        )

        revised_scale = scales[
            columns[current_index + 1]
        ]

        current_revision = get_revision_column(
            retirement_date
        )

        result = calculate_revision(
            scales, current_revision, last_pay
        )

        return Response({
            "rows": result.get("rows", []),
            "pension": result.get("pension", {}),
            "start_revision": current_revision,
        })
    
class ScaleTypeView(APIView):

    def get(self, request):
        retirement_date = request.GET.get(
            'retirement_date'
        )
        revision = get_revision_column(
            retirement_date
        )
        return Response({
            "revision": revision,

            "is_stage_based": is_stage_based_scale(
                revision
            )
        })


class EmployeeLookupView(APIView):
    """Fetch separation date, scale, and last pay from Oracle by employee code."""

    def get(self, request, emp_id):
        try:
            data = fetch_employee_for_methodology2(emp_id)
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

