from django.urls import path,include
from .views import AuditLogListView
urlpatterns = [
    path("audit-logs/", AuditLogListView.as_view(),),
]