from django.urls import path

from .views import (
    FamilyPensionClaimAPIView,
    FamilyPensionerListAPIView,
    FamilyPensionRelationListAPIView,
)

urlpatterns = [
    path("pensioners/", FamilyPensionerListAPIView.as_view()),
    path("claim/", FamilyPensionClaimAPIView.as_view()),
    path("relations/", FamilyPensionRelationListAPIView.as_view()),
]
