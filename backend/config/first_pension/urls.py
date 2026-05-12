from django.urls import path

from .views import PensionProcessView,PensionReportView,PensionCaseListView

urlpatterns = [

    path(
        "process/",
        PensionProcessView.as_view(),
    ),
    path("report/<int:id>/", PensionReportView.as_view(),),
    path("cases/", PensionCaseListView.as_view(),),
]
