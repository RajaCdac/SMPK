"""Doctor Consolidation API (m2_doctor_consolidation)."""

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from M2_doctor.services.doctor_calc import (
    calculate_doctor_class12,
    calculate_doctor_class34,
)
from M2_doctor.services.doctor_store import (
    get_doctor_consolidation,
    save_doctor_consolidation,
)
from M2_oldage_arrear.services.consolidation_bridge import fetch_employee_dob
from M2_oldage_arrear.views import EmployeeLookupView
from methodology2.services.consolidation_service import use_consolidation_actor
from methodology2.services.oracle_employee_service import employee_is_doctor

MODULE = "M2_DOCTOR"

try:
    from audit.services import log_audit
except Exception:

    def log_audit(*args, **kwargs):
        return None


def _float(value):
    try:
        return float(str(value).replace(",", ""))
    except (TypeError, ValueError):
        return None


class DoctorEmployeeView(APIView):
    """Same employee lookup as consolidation; doctors only, last pay split."""

    def get(self, request, emp_id):
        response = EmployeeLookupView().get(request, emp_id)
        if response.status_code != status.HTTP_200_OK:
            return response
        data = dict(response.data)
        emp = str(data.get("emp_id") or emp_id).strip()[:5]
        if str(data.get("doctor_flg") or "") != "1" and not employee_is_doctor(emp):
            return Response(
                {
                    "error": (
                        f"Employee {emp} is not marked as a doctor (DOCTOR_FLG). "
                        "Use Methodology 2 Consolidation."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        last_pay = _float(data.get("last_pay"))
        npa = _float(data.get("npa_amount"))
        data["doctor_flg"] = 1
        data["last_npa"] = npa
        data["last_basic"] = (
            last_pay - npa if last_pay is not None and npa is not None else last_pay
        )
        return Response(data)


class DoctorCalculateView(APIView):
    """POST: category, separation_date, scale, basic, npa (+ sda, tqs_*)."""

    def post(self, request):
        data = request.data or {}
        category = str(data.get("category") or "").strip()
        tqs = {
            "tqs_yr": data.get("tqs_yr"),
            "tqs_month": data.get("tqs_month"),
            "tqs_days": data.get("tqs_days"),
            # CR 10-11-2026 (emp 45654): death in harness → TQS/10, not cut off.
            "retirement_type": data.get("retirement_type"),
        }
        try:
            if category in ("1", "2"):
                result = calculate_doctor_class12(
                    data.get("separation_date"),
                    data.get("scale"),
                    data.get("basic"),
                    data.get("npa"),
                    **tqs,
                )
            else:
                result = calculate_doctor_class34(
                    data.get("separation_date"),
                    data.get("scale"),
                    data.get("basic"),
                    data.get("npa"),
                    sda=data.get("sda"),
                    **tqs,
                )
        except Exception as exc:
            return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        if result.get("error"):
            return Response(result, status=status.HTTP_400_BAD_REQUEST)
        return Response(result)


class DoctorConsolidationView(APIView):
    """Save / load a doctor consolidation."""

    def get(self, request, emp_id):
        snapshot = get_doctor_consolidation(emp_id)
        if not snapshot:
            return Response(
                {"error": "No saved doctor consolidation for this employee"},
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
        old_data = get_doctor_consolidation(emp_key) if emp_key else None

        if not payload.get("date_of_birth") and not payload.get("dob") and emp_key:
            dob = fetch_employee_dob(emp_key)
            if dob:
                payload["date_of_birth"] = dob.isoformat()
        payload["doctor_flg"] = 1

        with use_consolidation_actor(request):
            result = save_doctor_consolidation(payload)
        if result.get("error"):
            return Response(result, status=status.HTTP_400_BAD_REQUEST)

        try:
            log_audit(
                request,
                table_name="m2_doctor_consolidation",
                record_id=result.get("emp_cd") or emp_key or "unknown",
                action="UPDATE" if old_data else "CREATE",
                old_data=old_data,
                new_data=result,
                module=MODULE,
            )
        except Exception:
            pass
        return Response(result)
