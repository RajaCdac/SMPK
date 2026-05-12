"""
URL 
"""
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('api.urls')),
    path("api/first-pension/", include("first_pension.urls")),
    path("api/audit/", include("audit.urls")),
]
