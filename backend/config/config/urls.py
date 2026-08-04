"""
URL 
"""
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('api.urls')),
    path("api/first-pension/", include("first_pension.urls")),
    path("api/family-pension/", include("family_pension.urls")),
    path("api/audit/", include("audit.urls")),
    path("api/methodology1/", include("methodology1.urls")),
    path("api/methodology2/", include("methodology2.urls")),
    path("api/master-data/", include("master_data.urls")),
]
