"""MACP (Class 3 into Officers' scale) endpoints. Does not call the ordinary revision view."""

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from methodology2.services.macp_calculation_service import (
    calculate_macp,
    macp_options,
)


class MacpOptionsView(APIView):
    def get(self, request):
        retirement_date = request.GET.get("retirement_date")
        if not retirement_date:
            return Response(
                {"error": "retirement_date is required", "tracks": []},
                status=status.HTTP_400_BAD_REQUEST,
            )
        result = macp_options(retirement_date)
        if result.get("error") and not result.get("tracks"):
            return Response(result, status=status.HTTP_400_BAD_REQUEST)
        return Response(result)


class MacpCalculateView(APIView):
    def post(self, request):
        result = calculate_macp(
            request.data.get("retirement_date"),
            request.data.get("track") or request.data.get("scale"),
            request.data.get("last_pay"),
            tqs_yr=request.data.get("tqs_yr"),
            tqs_month=request.data.get("tqs_month"),
            tqs_days=request.data.get("tqs_days"),
        )
        if result.get("error"):
            return Response(result, status=status.HTTP_400_BAD_REQUEST)
        return Response(result)
