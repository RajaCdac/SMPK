from django.shortcuts import render
from datetime import datetime
from dateutil.relativedelta import relativedelta
from datetime import timedelta
from api.views import calculate_age
from django.shortcuts import get_object_or_404
from rest_framework.views import APIView
from rest_framework.response import Response

from .models import PensionCase, PensionSummary

from audit.models import AuditLog


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
        commutation_amount = (
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

        # Ceiling
        if gratuity_amount > 2000000:
            gratuity_amount = 2000000

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

        # =========================
        # AUDIT LOG
        # =========================

        AuditLog.objects.create(

            table_name="PensionCase",

            record_id=obj.id,

            action="CREATE",

            old_data=None,

            new_data={
                "emp_code": obj.emp_code,
                "name": obj.name,
                "status": obj.status
            },

            changed_by=request.user,

            ip_address=request.META.get(
                "REMOTE_ADDR"
            ),

            user_agent=request.META.get(
                "HTTP_USER_AGENT"
            ),

            module="FIRST_PENSION"
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
    

