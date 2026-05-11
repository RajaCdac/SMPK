from django.shortcuts import render
from datetime import datetime
from dateutil.relativedelta import relativedelta
from datetime import timedelta
from api.views import calculate_age

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
        da = (
            basic * 0.1851
        )

        # Rounded TCCS
        qualifying_years = tccs_years

        if tccs_months >= 6:
            qualifying_years += 1
        print("QY= ,", qualifying_years)

        gratuity_amount = (
            ((basic + da)*15* qualifying_years)/ 26
        )

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

            "pension_amount":
                pension_amount,

            "commutation_amount":
                commutation_amount,

            "gratuity_amount":
                gratuity_amount,
        })
# Create your views here.
