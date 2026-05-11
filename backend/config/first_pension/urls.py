from django.urls import path

from .views import PensionProcessView

urlpatterns = [

    path(
        "process/",
        PensionProcessView.as_view(),
    ),

]
