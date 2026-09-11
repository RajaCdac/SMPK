"""API views for M2 Old Age Arrear — Met2 features via import + old-age endpoints."""

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

# Re-use Met2 calculation / lookup views (no methodology2 source edits).
from methodology2.views import (  # noqa: F401
    CalculateClass12View,
    CalculateRevisionView,
    GetClass12PayStagesView,
    GetClass12ScalesView,
    GetEquivalentScalesView,
    GetPayStagesView,
    GetScalesView,
    GetSpecialDaOptionsView,
    ScaleTypeView,
)

from M2_oldage_arrear.services.consolidation_bridge import (
    fetch_employee_dob,
    get_consolidation_snapshot,
    save_consolidation_snapshot,
)
from M2_oldage_arrear.services.employee_soft_lookup import fetch_employee_for_oldage
from M2_oldage_arrear.services.oldage_service import compute_oldage_benefit
from methodology2.services.consolidation_service import fetch_print_master_fields

MODULE = "M2_OLDAGE_ARREAR"

try:
    from audit.services import log_audit
except Exception:

    def log_audit(*args, **kwargs):
        return None


class EmployeeLookupView(APIView):
    """
    Met2 employee lookup + DOB for old-age.
    Soft-falls back when Met2 returns not-found (missing emp_class/scale).
    """

    def get(self, request, emp_id):
        try:
            data = fetch_employee_for_oldage(emp_id)
            if not data:
                return Response(
                    {"error": "Employee not found"},
                    status=status.HTTP_404_NOT_FOUND,
                )
            # Soft warning OK; hard Met2 error still returned for user to fix inputs.
            if data.get("error") and not data.get("date_of_birth") and not data.get("separation_date"):
                return Response(data, status=status.HTTP_400_BAD_REQUEST)

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
            if not data.get("date_of_birth"):
                dob = fetch_employee_dob(emp_id)
                data["date_of_birth"] = dob.isoformat() if dob else None
                data["dob"] = data["date_of_birth"]
            return Response(data)
        except Exception as exc:
            return Response(
                {"error": str(exc)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class ConsolidationSnapshotView(APIView):
    """Save / load consolidation into m2_oldage_arrear_consolidation only."""

    def get(self, request, emp_id):
        snapshot = get_consolidation_snapshot(emp_id)
        if not snapshot:
            return Response(
                {"error": "No saved old-age consolidation for this employee"},
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

        if not payload.get("date_of_birth") and not payload.get("dob") and emp_key:
            dob = fetch_employee_dob(emp_key)
            if dob:
                payload["date_of_birth"] = dob.isoformat()

        result = save_consolidation_snapshot(payload)
        if result.get("error"):
            return Response(result, status=status.HTTP_400_BAD_REQUEST)

        try:
            log_audit(
                request,
                table_name="m2_oldage_arrear_consolidation",
                record_id=result.get("emp_cd") or emp_key or "unknown",
                action="UPDATE" if old_data else "CREATE",
                old_data=old_data,
                new_data=result,
                module=MODULE,
            )
        except Exception:
            pass

        return Response(result)


class OldAgeBenefitView(APIView):
    """
    POST body:
      dob (required), basic_pension (or pension_277 / pension_359),
      as_on_date (optional), emp_id (optional — fills dob from DB).
    """

    @staticmethod
    def _attach_print_comparison(result, data):
        """Attach consolidation print columns so live UI matches print."""
        if result.get("error") and not result.get("dob"):
            return result
        from M2_oldage_arrear.services.oldage_print_columns import (
            build_oldage_pension_comparison,
        )

        if "is_employee_pension" in data and data.get("is_employee_pension") is not None:
            raw = data.get("is_employee_pension")
            if isinstance(raw, bool):
                is_emp = raw
            else:
                is_emp = str(raw).strip().lower() in ("1", "true", "yes", "y")
        else:
            is_emp = True
        result["pension_comparison"] = build_oldage_pension_comparison(
            dob=result.get("dob") or data.get("dob") or data.get("date_of_birth"),
            m2_277=data.get("pension_277") or data.get("m2_pension_277"),
            m1_277=data.get("m1_pension_277"),
            m2_359=data.get("pension_359") or data.get("m2_pension_359"),
            m1_359=data.get("m1_pension_359"),
            is_employee_pension=is_emp,
            as_on_date=data.get("as_on_date"),
        )
        return result

    def post(self, request):
        data = request.data or {}
        emp_id = str(data.get("emp_id") or data.get("emp_cd") or "").strip()
        dob = data.get("dob") or data.get("date_of_birth")
        if not dob and emp_id:
            found = fetch_employee_dob(emp_id)
            dob = found.isoformat() if found else None

        result = compute_oldage_benefit(
            dob=dob,
            basic_pension=data.get("basic_pension") or data.get("benefit_359"),
            as_on_date=data.get("as_on_date"),
            pension_277=data.get("pension_277") or data.get("m2_pension_277"),
            pension_359=data.get("pension_359") or data.get("m2_pension_359"),
            m1_pension_277=data.get("m1_pension_277"),
            m1_pension_359=data.get("m1_pension_359"),
            benefit_277=data.get("benefit_277"),
            benefit_359=data.get("benefit_359"),
            category=data.get("category"),
            class_grp=data.get("class_grp"),
        )
        if result.get("error") and not result.get("dob"):
            return Response(result, status=status.HTTP_400_BAD_REQUEST)
        return Response(self._attach_print_comparison(result, {**data, "dob": dob}))

    def get(self, request):
        data = {
            "emp_id": request.GET.get("emp_id") or request.GET.get("emp_cd"),
            "dob": request.GET.get("dob") or request.GET.get("date_of_birth"),
            "as_on_date": request.GET.get("as_on_date"),
            "basic_pension": request.GET.get("basic_pension")
            or request.GET.get("benefit_359"),
            "pension_277": request.GET.get("pension_277")
            or request.GET.get("m2_pension_277"),
            "pension_359": request.GET.get("pension_359")
            or request.GET.get("m2_pension_359"),
            "m1_pension_277": request.GET.get("m1_pension_277"),
            "m1_pension_359": request.GET.get("m1_pension_359"),
            "benefit_277": request.GET.get("benefit_277"),
            "benefit_359": request.GET.get("benefit_359"),
            "category": request.GET.get("category"),
            "class_grp": request.GET.get("class_grp"),
            "is_employee_pension": request.GET.get("is_employee_pension"),
        }
        emp_id = str(data.get("emp_id") or "").strip()
        dob = data.get("dob")
        if not dob and emp_id:
            found = fetch_employee_dob(emp_id)
            dob = found.isoformat() if found else None
            data["dob"] = dob
        result = compute_oldage_benefit(
            dob=dob,
            basic_pension=data.get("basic_pension"),
            as_on_date=data.get("as_on_date"),
            pension_277=data.get("pension_277"),
            pension_359=data.get("pension_359"),
            m1_pension_277=data.get("m1_pension_277"),
            m1_pension_359=data.get("m1_pension_359"),
            benefit_277=data.get("benefit_277"),
            benefit_359=data.get("benefit_359"),
            category=data.get("category"),
            class_grp=data.get("class_grp"),
        )
        if result.get("error") and not result.get("dob"):
            return Response(result, status=status.HTTP_400_BAD_REQUEST)
        return Response(self._attach_print_comparison(result, data))
