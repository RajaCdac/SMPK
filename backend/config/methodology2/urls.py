from django.urls import path

from .views import (
    CalculateClass12View,
    CalculateRevisionView,
    ConsolidationSnapshotView,
    EmployeeLookupView,
    GetClass12PayStagesView,
    GetClass12ScalesView,
    GetEquivalentScalesView,
    GetPayStagesView,
    GetScalesView,
    GetSpecialDaOptionsView,
    ScaleTypeView,
)
from .views_bulk import BulkUploadView


urlpatterns = [
    path("get-scales/", GetScalesView.as_view()),
    path("get-pay-stages/", GetPayStagesView.as_view()),
    path("get-equivalent-scales/", GetEquivalentScalesView.as_view()),
    path("get-special-da-options/", GetSpecialDaOptionsView.as_view()),
    path("calculate-revision/", CalculateRevisionView.as_view()),
    path("get-scales-class12/", GetClass12ScalesView.as_view()),
    path("get-pay-stages-class12/", GetClass12PayStagesView.as_view()),
    path("calculate-class12/", CalculateClass12View.as_view()),
    path("get-scale-type/", ScaleTypeView.as_view()),
    path("employee/<str:emp_id>/", EmployeeLookupView.as_view()),
    path("consolidation/", ConsolidationSnapshotView.as_view()),
    path("consolidation/<str:emp_id>/", ConsolidationSnapshotView.as_view()),
    path("bulk/", BulkUploadView.as_view()),
]