from django.urls import path

from .views import AuditLogDetailView, AuditLogListView

urlpatterns = [
    path("audit-logs/", AuditLogListView.as_view()),
    path("audit-logs/<int:pk>/", AuditLogDetailView.as_view()),
]