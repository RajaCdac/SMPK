from django.shortcuts import render
from rest_framework.response import Response
from rest_framework.decorators import api_view
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework.views import APIView
from datetime import datetime
from employee.models import PensionCase
from accounts.user_auth import build_user_auth_payload

class CustomTokenSerializer(TokenObtainPairSerializer):
    def validate(self, attrs):
        data = super().validate(attrs)
        data["user"] = build_user_auth_payload(self.user)
        return data


class CustomTokenView(TokenObtainPairView):
    serializer_class = CustomTokenSerializer

class DashboardView(APIView):
    def get(self, request):
        import logging

        from employee.services.oracle_service import oracle_reads_enabled
        from first_pension.services.mirror_dashboard_service import (
            fetch_dashboard_from_mirror,
        )
        from first_pension.services.oracle_cache_service import (
            load_dashboard_from_cache,
            sync_dashboard_to_cache,
        )
        from first_pension.services.oracle_dashboard_service import (
            fetch_dashboard_payload,
        )

        logger = logging.getLogger(__name__)

        today = datetime.today()
        month = request.GET.get("month")
        year = request.GET.get("year")
        if not month or not year:
            month = today.month
            year = today.year
        month = int(month)
        year = int(year)

        from first_pension.services.dashboard_workflow_status import (
            enrich_retirement_list,
        )

        def attach_workflow(payload):
            enriched, _summary = enrich_retirement_list(
                payload.get("retirement_list") or []
            )
            payload["retirement_list"] = enriched
            return payload

        payload = None
        data_source = None

        if oracle_reads_enabled():
            try:
                payload = fetch_dashboard_payload(month, year)
                sync_dashboard_to_cache(month, year, payload)
                data_source = "oracle"
            except Exception as exc:
                logger.warning("Dashboard Oracle fetch failed: %s", exc)

        if payload is None:
            try:
                payload = fetch_dashboard_from_mirror(month, year)
                data_source = "mirror"
            except Exception as exc:
                logger.warning("Dashboard mirror fetch failed: %s", exc)

        if payload is None:
            cached = load_dashboard_from_cache(month, year)
            if cached is not None:
                payload = cached
                data_source = "cache"
                payload["cache_message"] = (
                    "Showing data last synced from Oracle."
                )

        if payload is None:
            payload = {
                "total_employees": 0,
                "retirement_count": 0,
                "retirement_list": [],
                "prev_month_count": 0,
                "next_month_count": 0,
                "prev_month_label": "",
                "this_month_label": "",
                "next_month_label": "",
            }
            data_source = "none"

        payload["data_source"] = data_source
        return Response(attach_workflow(payload))
    

class PensionProcessView(APIView):

    def post(self, request):

        data = request.data

        obj = PensionCase.objects.create(

            emp_code=data.get("emp_code"),

            name=data.get("name"),

            emp_class=data.get("class"),

            birth_date=data.get("birth_date"),

            joining_date=data.get("joining_date"),

            retirement_date=data.get("retirement_date"),

            designation=data.get("designation"),

            scale=data.get("scale"),

            last_basic=data.get("last_basic"),

            no_pay_days=data.get("no_pay_days"),

            dies_non_days=data.get("dies_non_days"),

            commutation_percent=data.get("commutation_percent"),

            commutation_reason=data.get("commutation_reason"),

        )

        return Response({
            "message": "Saved successfully",
            "case_id": obj.id
        })



