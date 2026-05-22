from django.urls import path

from .views import (
    CalculateRevisionView,
    EmployeeLookupView,
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
    path("get-scale-type/", ScaleTypeView.as_view()),
    path("employee/<str:emp_id>/", EmployeeLookupView.as_view()),
]