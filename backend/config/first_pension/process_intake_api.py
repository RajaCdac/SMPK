from datetime import datetime

from django.conf import settings
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from audit.services import log_audit
from employee.services.employee_mirror_service import resolve_pension_case_snapshot
from employee.services.oracle_emp_adm_service import (
    fetch_emp_adm_separation,
    process_intake_is_complete_in_oracle,
    update_emp_adm_separation,
)
from .models import PensionCase
from .pension_proposal_api import get_pension_proposal_for_employee


def _get_pension_case_for_employee(emp_id):
    emp_key = str(emp_id).strip()
    case = PensionCase.objects.filter(emp_code=emp_key).first()
    if case:
        return case
    if emp_key.isdigit():
        normalized = str(int(emp_key))
        case = PensionCase.objects.filter(emp_code=normalized).first()
        if case:
            return case
    return PensionCase.objects.filter(emp_code__iexact=emp_key).first()


def _parse_dd_mm_yyyy(value):
    if not value:
        return None
    return datetime.strptime(value, "%d-%m-%Y").date()


def _parse_separation_date(value):
    if not value:
        return None
    if hasattr(value, "strftime") and not isinstance(value, str):
        return value if hasattr(value, "day") else value
    text = str(value).strip()
    for fmt in ("%Y-%m-%d", "%d-%m-%Y"):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    return None


def serialize_process_intake(case=None, emp_code=None):
    """Prefer PensionCase; fall back to Oracle if case has no separation saved."""
    if case and (case.separation_type or "").strip() and case.separation_date:
        return {
            "separation_type": case.separation_type or "",
            "separation_date": case.separation_date.strftime("%Y-%m-%d"),
            "remarks": case.process_remarks or "",
        }
    if emp_code:
        try:
            return fetch_emp_adm_separation(emp_code)
        except Exception:
            pass
    if case:
        return {
            "separation_type": case.separation_type or "",
            "separation_date": (
                case.separation_date.strftime("%Y-%m-%d")
                if case.separation_date
                else ""
            ),
            "remarks": case.process_remarks or "",
        }
    return None


def serialize_process_intake_from_oracle(emp_code):
    return serialize_process_intake(emp_code=emp_code)


def process_intake_is_complete(emp_code):
    case = _get_pension_case_for_employee(emp_code)
    if case and (case.separation_type or "").strip() and case.separation_date:
        return True
    try:
        return process_intake_is_complete_in_oracle(emp_code)
    except Exception:
        return False


def _apply_employee_snapshot(case, data):
    snapshot = resolve_pension_case_snapshot(case.emp_code, data)
    case.name = snapshot["name"] or case.name
    case.emp_class = snapshot["emp_class"] or case.emp_class
    if snapshot["birth_date"]:
        case.birth_date = snapshot["birth_date"]
    if snapshot["joining_date"]:
        case.joining_date = snapshot["joining_date"]
    if snapshot["retirement_date"]:
        case.retirement_date = snapshot["retirement_date"]
    case.designation = snapshot["designation"] or case.designation
    case.scale = snapshot["scale"] or case.scale
    if snapshot["last_basic"] is not None:
        case.last_basic = snapshot["last_basic"]


def _apply_separation_to_case(case, separation_type, separation_date, remarks):
    case.separation_type = separation_type
    case.separation_date = separation_date
    case.process_remarks = remarks


def _oracle_sync_required():
    return getattr(settings, "ORACLE_SYNC_REQUIRED", False)


def sync_process_intake_to_oracle(emp_code, separation_type, separation_date, remarks):
    """Update FI_XX_MH_EMP_ADM. Returns (synced, error_message)."""
    try:
        update_emp_adm_separation(
            emp_code, separation_type, separation_date, remarks
        )
        return True, None
    except Exception as e:
        return False, str(e)


class ProcessIntakeLookupAPIView(APIView):
    def get(self, request, emp_code):
        case = _get_pension_case_for_employee(emp_code)
        completed = process_intake_is_complete(emp_code)
        intake_data = serialize_process_intake(case=case, emp_code=emp_code)
        return Response({
            "exists": bool(case) or completed,
            "completed": completed,
            "intake_data": intake_data,
        })


class ProcessIntakeAPIView(APIView):
    def post(self, request):
        try:
            data = request.data
            emp_code = str(data.get("emp_code", "")).strip()
            if not emp_code:
                return Response(
                    {"error": "Employee code is required."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            separation_type = (data.get("separation_type") or "").strip().upper()
            separation_date = _parse_separation_date(data.get("separation_date"))
            remarks = (data.get("remarks") or "").strip()

            if not separation_type:
                return Response(
                    {"error": "Separation type is required."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            if not separation_date:
                return Response(
                    {"error": "Separation date is required."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            case = _get_pension_case_for_employee(emp_code)
            old_data = serialize_process_intake(case=case, emp_code=emp_code)
            snapshot = resolve_pension_case_snapshot(emp_code, data)
            if not snapshot["birth_date"] or not snapshot["joining_date"] or not snapshot["retirement_date"]:
                return Response(
                    {
                        "error": (
                            "Employee master dates are missing. Sync Wave-2 mirror "
                            f"for {emp_code} (fi_xx_mh_emp_per / emp_adm) or connect Oracle."
                        ),
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            if case:
                _apply_employee_snapshot(case, data)
                _apply_separation_to_case(
                    case, separation_type, separation_date, remarks
                )
                if request.user.is_authenticated:
                    case.updated_by = request.user
                case.save()
                action = "UPDATE"
            else:
                case = PensionCase.objects.create(
                    emp_code=emp_code,
                    name=snapshot["name"],
                    emp_class=snapshot["emp_class"],
                    birth_date=snapshot["birth_date"],
                    joining_date=snapshot["joining_date"],
                    retirement_date=snapshot["retirement_date"],
                    designation=snapshot["designation"],
                    scale=snapshot["scale"],
                    last_basic=snapshot["last_basic"],
                    separation_type=separation_type,
                    separation_date=separation_date,
                    process_remarks=remarks,
                    created_by=request.user,
                )
                action = "CREATE"

            proposal = get_pension_proposal_for_employee(emp_code)
            if proposal:
                proposal.separation_type = separation_type
                proposal.separation_date = separation_date
                if request.user.is_authenticated:
                    proposal.updated_by = request.user
                proposal.save()

            # ORACLE WRITE DISABLED — MySQL-only mode. Uncomment to sync intake to Oracle.
            # synced, oracle_error = sync_process_intake_to_oracle(
            #     emp_code, separation_type, separation_date, remarks
            # )
            # if not synced and _oracle_sync_required():
            #     return Response(
            #         {
            #             "error": (
            #                 "Could not update Oracle (FI_XX_MH_EMP_ADM): "
            #                 f"{oracle_error}"
            #             ),
            #             "oracle_synced": False,
            #             "completed": True,
            #             "intake_data": serialize_process_intake(case=case),
            #         },
            #         status=status.HTTP_502_BAD_GATEWAY,
            #     )

            new_data = serialize_process_intake(case=case)
            log_audit(
                request,
                table_name="PensionCase",
                record_id=case.id,
                action=action,
                old_data=old_data,
                new_data=new_data,
                module="FIRST_PENSION",
            )

            return Response({
                "message": "Separation details saved successfully.",
                "completed": True,
                "intake_data": new_data,
            })
        except Exception as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
