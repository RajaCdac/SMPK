from django.shortcuts import render
from datetime import datetime
from dateutil.relativedelta import relativedelta
from datetime import timedelta
from api.views import calculate_age
from django.shortcuts import get_object_or_404
from rest_framework.views import APIView
from rest_framework.response import Response
from employee.services.oracle_service import get_oracle_connection
from rest_framework import status

from .models import PensionCase, PensionSummary, CommutationApplication

from audit.services import log_audit
from .pension_proposal_api import (
    fetch_proposal_defaults_from_oracle,
    get_pension_proposal_for_employee,
    load_proposal_defaults_from_oracle,
    merge_oracle_bank_into_proposal_data,
    serialize_pension_proposal,
)
from .pension_calculation import (
    build_amount_lookup_payload,
    round_gratuity_up_to_rupee,
    round_up_to_rupee,
)


def _format_date_for_api(value):
    if not value:
        return ""
    if hasattr(value, "strftime"):
        return value.strftime("%Y-%m-%d")
    return str(value)


def _parse_optional_date(value):
    if value is None or value == "":
        return None
    return value


def _apply_commutation_fields(obj, data, user, *, is_create=False):
    obj.application_time = data.get("application_time", obj.application_time)
    obj.comm_start_mnth = data.get("comm_start_mnth", obj.comm_start_mnth)
    obj.appcn_dt = _parse_optional_date(data.get("appcn_dt")) or obj.appcn_dt
    obj.application_rcvd_dt = _parse_optional_date(
        data.get("application_rcvd_dt") or data.get("appcn_dt")
    ) or obj.application_rcvd_dt
    obj.impl_fpen_combill = data.get("impl_fpen_combill", obj.impl_fpen_combill)
    obj.commutation_dt = _parse_optional_date(
        data.get("commutation_dt") or data.get("appcn_dt")
    ) or obj.commutation_dt
    obj.restoration_dt = _parse_optional_date(data.get("restoration_dt"))
    obj.commutation_per = data.get("commutation_per", obj.commutation_per)
    obj.mo_certificate_dt = _parse_optional_date(data.get("mo_certificate_dt"))
    obj.mo_certificate_ref = data.get("mo_certificate_ref", obj.mo_certificate_ref)
    obj.commutation_reasons = data.get(
        "commutation_reasons", obj.commutation_reasons
    )

    if is_create:
        obj.created_by = user
    elif user and user.is_authenticated:
        obj.updated_by = user

    obj.save()


def serialize_no_pay_data(case):
    return {
        "id": case.id,
        "emp_code": case.emp_code,
        "no_pay_days": case.no_pay_days,
        "dies_non_days": case.dies_non_days,
        "no_pay_more_than_240_days": case.no_pay_more_than_240_days,
        "suspension_days": case.suspension_days,
    }


def _get_pension_case_for_employee(emp_id):
    """Find row in first_pension_pensioncase by employee code."""
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


def serialize_commutation_application(app):
    """Return all commutation fields from DB for the frontend form."""
    return {
        "id": app.id,
        "emp_cd": app.emp_cd,
        "appcn_no": app.appcn_no,
        "application_time": app.application_time,
        "comm_start_mnth": app.comm_start_mnth,
        "appcn_dt": _format_date_for_api(app.appcn_dt),
        "application_rcvd_dt": _format_date_for_api(app.application_rcvd_dt),
        "impl_fpen_combill": app.impl_fpen_combill or "",
        "commutation_dt": _format_date_for_api(app.commutation_dt),
        "restoration_dt": _format_date_for_api(app.restoration_dt),
        "commutation_per": app.commutation_per,
        "mo_certificate_dt": _format_date_for_api(app.mo_certificate_dt),
        "mo_certificate_ref": app.mo_certificate_ref or "",
        "commutation_reasons": app.commutation_reasons or "",
        "status": app.status,
    }


class PensionProcessView(APIView):

    def post(self, request):

        data = request.data

        # =========================
        # CREATE PENSION CASE
        # =========================

        obj = PensionCase.objects.create(

            emp_code=data.get("emp_code"),

            name=data.get("name"),

            emp_class=data.get("class"),

            #birth_date=data.get("birth_date"),
            birth_date=datetime.strptime(data.get("birth_date"),"%d-%m-%Y"),

            #joining_date=data.get("joining_date"),
            joining_date=datetime.strptime(data.get("joining_date"),"%d-%m-%Y"),

            #retirement_date=data.get("retirement_date"),
            retirement_date=datetime.strptime(data.get("retirement_date"),"%d-%m-%Y"),

            designation=data.get("designation"),

            scale=data.get("scale"),

            last_basic=data.get("last_basic"),

            no_pay_days=data.get("no_pay_days"),

            dies_non_days=data.get("dies_non_days"),

            commutation_percent=data.get(
                "commutation_percent"
            ),

            commutation_reason=data.get(
                "commutation_reason"
            ),

            created_by=request.user
        )

        # =========================
        # DATE CALCULATION
        # =========================

        join_date = datetime.strptime(
            data.get("joining_date"),
            "%d-%m-%Y"
        )
        
        ret_date = datetime.strptime(
            data.get("retirement_date"),
            "%d-%m-%Y"
        )
        
        effective_ret_date = ret_date - timedelta(days=1)
        service_life = calculate_age(join_date,ret_date)       
        print("Service Life: ", service_life)
        service_diff = relativedelta(
            ret_date,
            join_date
        )
        
        years = service_diff.years
        months = service_diff.months
        days = service_diff.days
        print("Total service: ", years, " years ", months, " months ", days, " days")

        # total_days = (
        #     effective_ret_date - join_date
        # ).days

        # years = total_days // 365

        # months = (
        #     (total_days % 365) // 30
        # )

        # days = (
        #     (total_days % 365) % 30
        # )

        # =========================
        # TCCS
        # =========================

        dies_non = int(
            data.get("dies_non_days", 0)
        )

        tccs_date = ret_date - timedelta(
            days=dies_non
        )

        tccs_diff = relativedelta(
            tccs_date,
            join_date
        )

        tccs_years = tccs_diff.years
        tccs_months = tccs_diff.months
        tccs_days = tccs_diff.days

        # =========================
        # TQS
        # =========================

        nopay = int(
            data.get("no_pay_days", 0)
        )

        tqs_date = tccs_date - timedelta(
            days=nopay
        )

        tqs_diff = relativedelta(
            tqs_date,
            join_date
        )

        tqs_years = tqs_diff.years

        tqs_months = tqs_diff.months

        tqs_days = tqs_diff.days

        # =========================
        # FINANCIAL CALCULATION
        # =========================

        basic = float(
            data.get("last_basic")
        )

        # Pension
        pension_amount = (
            basic * 0.5
        )

        # Commutation
        commutation_amount = round_up_to_rupee(
            pension_amount * 0.4 * 98.328
        )

        # DA
        # da = (
        #     basic * 0.1851
        # )
        emp_class = data.get("class")
        if emp_class in ["I", "II"]:
            da_percent = 54.32
        else:
            da_percent = 19.07
        da = ( basic * da_percent / 100)

        # Rounded TCCS
        qualifying_years = tccs_years

        if tccs_months >= 6 or (tccs_months == 6 and tccs_days > 0):
            qualifying_years += 1
        

        gratuity_amount = (
            ((basic + da)*15* qualifying_years)/ 26
        )
        # gratuity_amount_tqs = (
        #     ((basic + da)*15* qualifying_years)/ 26
        # )
        print("Gratuity Amount: ", gratuity_amount)

        if gratuity_amount > 2000000:
            gratuity_amount = 2000000
        gratuity_amount = round_gratuity_up_to_rupee(gratuity_amount)

        # =========================
        # SAVE SUMMARY
        # =========================

        PensionSummary.objects.create(

            pension_case=obj,

            total_service_years=years,
            total_service_months=months,
            total_service_days=days,

            tccs_years=tccs_years,
            tccs_months=tccs_months,
            tccs_days=tccs_days,

            tqs_years=tqs_years,
            tqs_months=tqs_months,
            tqs_days=tqs_days,

            pension_amount=pension_amount,

            commutation_amount=commutation_amount,

            gratuity_amount=gratuity_amount,

            pension_start_date=ret_date
        )

        log_audit(
            request,
            table_name="PensionCase",
            record_id=obj.id,
            action="CREATE",
            old_data=None,
            new_data={
                "emp_code": obj.emp_code,
                "name": obj.name,
                "status": obj.status,
            },
            module="FIRST_PENSION",
        )

        return Response({

            "message": "Saved Successfully",
            "case_id": obj.id,

            "pension_amount":
                pension_amount,

            "commutation_amount":
                commutation_amount,

            "gratuity_amount":
                gratuity_amount,
        })
# Create your views here.

class PensionReportView(APIView):

    def get(self, request, id):

        case = get_object_or_404(
            PensionCase,
            id=id
        )
        summary = case.summary
        join_date = case.joining_date

        ret_date = case.retirement_date

        birth_date = case.birth_date

        effective_ret_date = (
            ret_date - timedelta(days=1)
        )

        # Age on Appointment
        app_age = relativedelta(
            join_date,
            birth_date
        )

        age_on_appointment = (
            f"{app_age.years}Y "
            f"{app_age.months}M "
            f"{app_age.days}D"
        )

        # Age on Retirement
        ret_age = relativedelta(
            effective_ret_date,
            birth_date
        )

        age_on_retirement = (
            f"{ret_age.years}Y "
            f"{ret_age.months}M "
            f"{ret_age.days}D"
        )

        # =========================
        # DA CALCULATION
        # =========================

        if case.emp_class in ["I", "II"]:

            da_percent = 54.32

        else:

            da_percent = 19.07

        da_amount = round(
            float(case.last_basic)
            * da_percent / 100,
            2
        )

        data = {

            "case_no": case.id,

            "name": case.name,

            "joining_date": case.joining_date,

            "retirement_date": case.retirement_date,

            "birth_date": case.birth_date,

            "last_basic": case.last_basic,

            "no_pay_days": case.no_pay_days,

            "dies_non_days": case.dies_non_days,

            "pension_amount":
                summary.pension_amount,

            "commutation_amount":
                summary.commutation_amount,

            "gratuity_amount":
                summary.gratuity_amount,

            "total_service":
                f"{summary.total_service_years}Y "
                f"{summary.total_service_months}M "
                f"{summary.total_service_days}D",

            "tccs":
                f"{summary.tccs_years}Y "
                f"{summary.tccs_months}M "
                f"{summary.tccs_days}D",

            "tqs":
                f"{summary.tqs_years}Y "
                f"{summary.tqs_months}M "
                f"{summary.tqs_days}D",

            "da_amount": da_amount,

            "da_percent": da_percent,

            "age_on_appointment":
                age_on_appointment,

            "age_on_retirement":
                age_on_retirement,
        }

        return Response(data)
    
class PensionCaseListView(APIView):

    def get(self, request):

        cases = PensionCase.objects.all().order_by("emp_code")

        data = []

        for case in cases:

            data.append({

                "id": case.id,
                "emp_code": case.emp_code,
                "name": case.name,
                "designation": case.designation,
                "retirement_date": case.retirement_date,
                "status": case.status,
                "last_basic": case.last_basic,
            })

        return Response(data)
    
class EmployeeSearchAPIView(APIView):

    def get(self, request, emp_id):

        try:
            with get_oracle_connection().cursor() as cursor:

                query = """
                    SELECT t1.EMP_CD,TRIM( t1.TITLE || ' ' || t1.FIRST_NAME || ' ' || NVL(t1.MIDDLE_NAME, '') || ' ' || t1.LAST_NAME ) AS full_name,
                    t2.JOIN_DT,t2.EXP_RET_DT,t1.BIRTH_DT,t3.DESIG_DESC,
                    t4.SCALE_SL,t5.BASIC_AMT,t5.CLASS
                    FROM FINANCE.FI_XX_MH_EMP_PER t1
                    LEFT JOIN FINANCE.FI_XX_MH_EMP_ADM t2 ON t1.EMP_CD = t2.EMP_CD
                    LEFT JOIN FINANCE.FI_XX_MH_DESIG t3 ON t2.DESIG_CD = t3.DESIG_CD
                    LEFT JOIN FINANCE.FI_XX_MH_EMP_FIN t4 ON t1.EMP_CD = t4.EMP_CD
                    LEFT JOIN FINANCE.FI_XX_MH_EMP_FIN_vw t5 ON t4.EMP_CD= t5.EMP_CD
                    WHERE t1.EMP_CD = :emp_id
                """
                cursor.execute(query, {'emp_id': emp_id})
                existing_commutation = None
                try:
                    existing_commutation = CommutationApplication.objects.get(emp_cd=emp_id)
                except CommutationApplication.DoesNotExist:
                    pass

                existing_no_pay = _get_pension_case_for_employee(emp_id)
                existing_proposal = get_pension_proposal_for_employee(emp_id)
                existing_amount_summary = None
                if existing_no_pay:
                    existing_amount_summary = PensionSummary.objects.filter(
                        pension_case_id=existing_no_pay.id
                    ).first()
                  
                row = cursor.fetchone()
                if row:
                    proposal_defaults = fetch_proposal_defaults_from_oracle(
                        cursor, emp_id, existing_no_pay
                    )
                    proposal_data = (
                        serialize_pension_proposal(existing_proposal)
                        if existing_proposal
                        else None
                    )
                    if proposal_data:
                        proposal_data = merge_oracle_bank_into_proposal_data(
                            proposal_data, proposal_defaults
                        )
                    employee_data = {
                        "emp_id": row[0],
                        "name": row[1],
                        "join_date": row[2].strftime("%d-%m-%Y") if row[2] else None,
                        "expected_retirement_date": row[3].strftime("%d-%m-%Y") if row[3] else None,
                        "birth_date": row[4].strftime("%d-%m-%Y") if row[4] else None,
                        "designation": row[5],
                        "scale": row[6],
                        "basic_amount": row[7],
                        "class": row[8],
                        "age_on_appointment": calculate_age(row[4], row[2]) if row[4] and row[2] else None,
                        "age_on_retirement": calculate_age(row[4], row[3]) if row[4] and row[3] else None,
                        "commutation_exists": True if existing_commutation else False,
                        "commutation_data": serialize_commutation_application(
                            existing_commutation
                        ) if existing_commutation else None,
                        "no_pay_exists": bool(existing_no_pay),
                        "no_pay_data": serialize_no_pay_data(
                            existing_no_pay
                        ) if existing_no_pay else None,
                        "proposal_exists": bool(existing_proposal),
                        "proposal_data": proposal_data,
                        "proposal_defaults": proposal_defaults,
                        "amount_exists": bool(existing_amount_summary),
                        "amount_data": (
                            build_amount_lookup_payload(emp_id).get("amount_data")
                            if existing_no_pay
                            else None
                        ),
                    }
                    return Response(employee_data)
                return Response(
                    {"error": "Employee not found"},
                    status=status.HTTP_404_NOT_FOUND
                )
        except Exception as e:

            return Response(
                {"error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        
class NoPayLookupAPIView(APIView):
    """Load no-pay / dies-non from first_pension_pensioncase for one employee."""

    def get(self, request, emp_code):
        case = _get_pension_case_for_employee(emp_code)
        if not case:
            return Response({"exists": False, "no_pay_data": None})

        return Response({
            "exists": True,
            "no_pay_data": serialize_no_pay_data(case),
        })


class NoPayEntryAPIView(APIView):

    def post(self, request):
        try:
            emp_code = request.data.get("emp_code")
            if PensionCase.objects.filter(emp_code=emp_code).exists():
                return Response(
                    {
                        "error": (
                            "No-pay entry already exists for this employee. "
                            "Use Edit to update."
                        )
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            data = request.data
            obj = PensionCase.objects.create(
                emp_code=emp_code,
                name=data.get("name"),
                emp_class=data.get("class"),
                birth_date=_parse_dd_mm_yyyy(data.get("birth_date")),
                joining_date=_parse_dd_mm_yyyy(data.get("joining_date")),
                retirement_date=_parse_dd_mm_yyyy(data.get("retirement_date")),
                designation=data.get("designation"),
                scale=data.get("scale"),
                last_basic=data.get("last_basic"),
                no_pay_days=int(data.get("no_pay_days") or 0),
                dies_non_days=int(data.get("dies_non_days") or 0),
                no_pay_more_than_240_days=int(
                    data.get("no_pay_more_than_240_days") or 0
                ),
                suspension_days=int(data.get("suspension_days") or 0),
                created_by=request.user,
            )

            log_audit(
                request,
                table_name="PensionCase",
                record_id=obj.id,
                action="CREATE",
                old_data=None,
                new_data=serialize_no_pay_data(obj),
                module="FIRST_PENSION",
            )

            return Response({
                "message": "No-Pay Entry Saved Successfully",
                "id": obj.id,
                "no_pay_data": serialize_no_pay_data(obj),
            })

        except Exception as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    def put(self, request, pk):
        try:
            obj = get_object_or_404(PensionCase, pk=pk)
            old_data = serialize_no_pay_data(obj)

            obj.no_pay_days = int(request.data.get("no_pay_days") or 0)
            obj.dies_non_days = int(request.data.get("dies_non_days") or 0)
            obj.no_pay_more_than_240_days = int(
                request.data.get("no_pay_more_than_240_days") or 0
            )
            obj.suspension_days = int(request.data.get("suspension_days") or 0)
            if request.user.is_authenticated:
                obj.updated_by = request.user
            obj.save()

            new_data = serialize_no_pay_data(obj)

            log_audit(
                request,
                table_name="PensionCase",
                record_id=obj.id,
                action="UPDATE",
                old_data=old_data,
                new_data=new_data,
                module="FIRST_PENSION",
            )

            return Response({
                "message": "No-Pay Entry Updated Successfully",
                "id": obj.id,
                "no_pay_data": new_data,
            })

        except Exception as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class CommutationCreateAPIView(APIView):
    def get(self, request):
        try:
            # =========================================
            # GET NEXT APPLICATION NUMBER FROM ORACLE
            # =========================================
            with get_oracle_connection().cursor() as cursor:
                cursor.execute(""" 
                    SELECT NVL(MAX(TO_NUMBER(APPCN_NO)),0) + 1 FROM FINANCE.FI_PN_MH_APPLICATION        
                """)

                next_appcn_no = cursor.fetchone()[0]
                print("Next Application No: ", next_appcn_no)

            return Response({
                "appcn_no": str(next_appcn_no)
            })
            
        except Exception as e:
            return Response(
                {"error": str(e)},
                status=500
            )
    def post(self, request):
        try:
            emp_cd = request.data.get("emp_cd")
            if CommutationApplication.objects.filter(emp_cd=emp_cd).exists():
                return Response(
                    {
                        "error": (
                            "Commutation application already exists for this "
                            "employee. Use Edit to update."
                        )
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            obj = CommutationApplication(
                emp_cd=emp_cd,
                appcn_no=request.data.get("appcn_no"),
            )
            _apply_commutation_fields(
                obj, request.data, request.user, is_create=True
            )

            log_audit(
                request,
                table_name="CommutationApplication",
                record_id=obj.id,
                action="CREATE",
                old_data=None,
                new_data=serialize_commutation_application(obj),
                module="FIRST_PENSION",
            )

            return Response({
                "message": "Commutation Application Saved Successfully",
                "application_no": obj.appcn_no,
                "id": obj.id,
            })

        except Exception as e:

            return Response(
                {"error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    def put(self, request, pk):
        try:
            obj = get_object_or_404(CommutationApplication, pk=pk)
            old_data = serialize_commutation_application(obj)
            _apply_commutation_fields(
                obj, request.data, request.user, is_create=False
            )
            new_data = serialize_commutation_application(obj)

            log_audit(
                request,
                table_name="CommutationApplication",
                record_id=obj.id,
                action="UPDATE",
                old_data=old_data,
                new_data=new_data,
                module="FIRST_PENSION",
            )

            return Response({
                "message": "Commutation Application Updated Successfully",
                "application_no": obj.appcn_no,
                "id": obj.id,
                "commutation_data": serialize_commutation_application(obj),
            })

        except Exception as e:

            return Response(
                {"error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    

