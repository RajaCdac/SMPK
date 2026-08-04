from django.urls import path

from .views import (
    FamilyPensionClaimAPIView,
    FamilyPensionerListAPIView,
    FamilyPensionGenerateFirstAPIView,
    FamilyPensionProposalReportAPIView,
    FamilyPensionRelationListAPIView,
)

urlpatterns = [
    path("pensioners/", FamilyPensionerListAPIView.as_view()),
    path("claim/", FamilyPensionClaimAPIView.as_view()),
    path("relations/", FamilyPensionRelationListAPIView.as_view()),
    path(
        "proposal-sanction-report/",
        FamilyPensionProposalReportAPIView.as_view(),
    ),
    path("generate-first-fp/", FamilyPensionGenerateFirstAPIView.as_view()),
]