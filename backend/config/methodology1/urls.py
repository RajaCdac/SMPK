from django.urls import path

from .views import (
    CalculateRevisionView,
    Cpi277And359View,
    EmployeeLookupView,
    FamilyPensionCalculationView,
    GetEquivalentScalesView,
    GetPayStagesView,
    GetScalesView,
    ScaleTypeView,
)


urlpatterns = [
    path("get-scales/", GetScalesView.as_view()),
    path("get-pay-stages/", GetPayStagesView.as_view()),
    path("get-equivalent-scales/", GetEquivalentScalesView.as_view()),
    path("calculate-revision/", CalculateRevisionView.as_view()),
    path("cpi-277-359/", Cpi277And359View.as_view()),
    path("family_pension_calculation/", FamilyPensionCalculationView.as_view()),
    path("get-scale-type/", ScaleTypeView.as_view()),
    path("employee/<str:emp_id>/", EmployeeLookupView.as_view()),
]