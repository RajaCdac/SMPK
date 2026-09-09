from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from methodology2.services.calculation_service import calculate_revision
from methodology2.services.class1_2_service import (
    calculate_class12,
    get_class12_pay_stages,
    get_class12_scales,
    validate_executive_grade,
)
from methodology2.services.consolidation_service import (
    fetch_print_master_fields,
    get_consolidation_snapshot,
    save_consolidation_snapshot,
)
from methodology2.services.oracle_employee_service import (
    fetch_employee_for_methodology2,
)
from methodology2.services.revision_resolver import get_revision_column
from methodology2.services.scale_parser import generate_pay_stages
from methodology2.services.sda_service import get_special_da_options
from methodology2.services.scale_service import (
    get_available_scales,
    get_equivalent_scales_by_scale,
    is_stage_based_scale,
)

METHODOLOGY2_MODULE = "METHODOLOGY2"

try:
    from audit.services import log_audit
except Exception:  # standalone deploy may not include audit app
    def log_audit(*args, **kwargs):
        return None

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
    
class GetSpecialDaOptionsView(APIView):

    def get(self, request):
        return Response(get_special_da_options())


class GetClass12ScalesView(APIView):
    """Executive grade list for category 1/2 (pay band at separation CPI)."""

    def get(self, request):
        separation_date = request.GET.get("separation_date") or request.GET.get(
            "retirement_date"
        )
        return Response(get_class12_scales(separation_date))


class GetClass12PayStagesView(APIView):
    """Pay stages of the start-revision scale for a category 1/2 grade."""

    def get(self, request):
        separation_date = request.GET.get("separation_date") or request.GET.get(
            "retirement_date"
        )
        grade = request.GET.get("scale")
        return Response(get_class12_pay_stages(separation_date, grade))


class CalculateClass12View(APIView):
    """Category 1/2 calculation: separation_date + scale (grade) + last_pay."""

    def post(self, request):
        separation_date = request.data.get("separation_date") or request.data.get(
            "retirement_date"
        )
        grade = request.data.get("scale")
        last_pay = request.data.get("last_pay")

        if not separation_date or not grade or last_pay in (None, ""):
            return Response(
                {"error": "separation_date, scale and last_pay are required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        grade = validate_executive_grade(grade, separation_date=separation_date)
        if not grade:
            return Response(
                {
                    "error": (
                        "scale must be executive grade (e.g. E-9), "
                        "not pay band value"
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            result = calculate_class12(separation_date, grade, last_pay)
        except Exception as exc:
            return Response(
                {"error": str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if result.get("error"):
            return Response(result, status=status.HTTP_400_BAD_REQUEST)

        return Response(result)


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

        try:
            sda_override = float(request.data.get("sda") or 0)
        except (TypeError, ValueError):
            sda_override = 0

        # Category (3 or 4); class 3/4 calculation only, does not affect math.
        category = request.data.get("category")

        scales = get_equivalent_scales_by_scale(
            retirement_date,
            selected_scale
        )

        current_revision = get_revision_column(
            retirement_date
        )

        result = calculate_revision(
            scales, current_revision, last_pay, sda_override
        )

        return Response({
            "rows": result.get("rows", []),
            "pension": result.get("pension", {}),
            "start_revision": current_revision,
            "category": category,
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
    """Fetch separation date, scale, and last pay from local DB by employee code."""

    def get(self, request, emp_id):
        try:
            data = fetch_employee_for_methodology2(emp_id)
            if not data:
                return Response(
                    {"error": "Employee not found"},
                    status=status.HTTP_404_NOT_FOUND,
                )
            # Soft warning (e.g. class 1/2 grade pick) is OK; hard error is not.
            if data.get("error"):
                return Response(
                    data,
                    status=status.HTTP_400_BAD_REQUEST,
                )
            master = fetch_print_master_fields(
                emp_id, category=data.get("category")
            )
            data.update(
                {
                    "case_no": master.get("case_no") or "",
                    "roll_no": master.get("roll_no") or "",
                    "retirement_type": master.get("retirement_type") or "",
                    "designation": master.get("designation") or "",
                    "tqs_yr": master.get("tqs_yr"),
                    "tqs_month": master.get("tqs_month"),
                    "tqs_days": master.get("tqs_days"),
                    "tqs": master.get("tqs") or "",
                    "wage_emp_name": master.get("wage_emp_name") or "",
                    "pensioner_name": master.get("pensioner_name") or "",
                    "is_employee_pension": master.get("is_employee_pension") or False,
                    "date_of_death": (
                        master.get("date_of_death").isoformat()
                        if hasattr(master.get("date_of_death"), "isoformat")
                        else master.get("date_of_death")
                    ),
                    "double_fpension_upto": (
                        master.get("double_fpension_upto").isoformat()
                        if hasattr(master.get("double_fpension_upto"), "isoformat")
                        else master.get("double_fpension_upto")
                    ),
                    "enhanced_family_pension": bool(
                        master.get("enhanced_family_pension")
                    ),
                    "die_in_harness": bool(master.get("die_in_harness")),
                    "case_type": master.get("case_type"),
                    "m1_family_pension_277": master.get("m1_family_pension_277"),
                    "m1_family_pension_359": master.get("m1_family_pension_359"),
                    "m1_old_basic_pension": master.get("m1_old_basic_pension"),
                    "m1_rev_basic_pension": master.get("m1_rev_basic_pension"),
                }
            )
            if master.get("name") and not data.get("name"):
                data["name"] = master["name"]
            return Response(data)
        except Exception as exc:
            return Response(
                {"error": str(exc)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class ConsolidationSnapshotView(APIView):
    """Save / load one-row Methodology-2 consolidation print snapshot."""

    def get(self, request, emp_id):
        snapshot = get_consolidation_snapshot(emp_id)
        if not snapshot:
            return Response(
                {"error": "No saved consolidation for this employee"},
                status=status.HTTP_404_NOT_FOUND,
            )
        return Response(snapshot)

    def post(self, request, emp_id=None):
        payload = dict(request.data or {})
        if emp_id and not payload.get("emp_cd") and not payload.get("emp_id"):
            payload["emp_cd"] = emp_id

        emp_key = str(
            payload.get("emp_cd") or payload.get("emp_id") or emp_id or ""
        ).strip()[:5]
        old_data = get_consolidation_snapshot(emp_key) if emp_key else None

        result = save_consolidation_snapshot(payload)
        if result.get("error"):
            return Response(result, status=status.HTTP_400_BAD_REQUEST)

        try:
            log_audit(
                request,
                table_name="methodology2_consolidation",
                record_id=result.get("emp_cd") or emp_key or "unknown",
                action="UPDATE" if old_data else "CREATE",
                old_data=old_data,
                new_data=result,
                module=METHODOLOGY2_MODULE,
            )
        except Exception:
            # Never fail the save because audit logging failed.
            pass

        return Response(result)

