from django.urls import path

from .views import DoctorCalculateView, DoctorConsolidationView, DoctorEmployeeView

urlpatterns = [
    path("employee/<str:emp_id>/", DoctorEmployeeView.as_view()),
    path("calculate/", DoctorCalculateView.as_view()),
    path("consolidation/<str:emp_id>/", DoctorConsolidationView.as_view()),
]
