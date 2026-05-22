from django.urls import path

from .views import (
    CommutationCreateAPIView,
    EmployeeSearchAPIView,
    NoPayEntryAPIView,
    NoPayLookupAPIView,
    PensionProcessView,
    PensionReportView,
    PensionCaseListView,
)
from .pension_proposal_api import (
    EarnDednLookupAPIView,
    PensionProposalAPIView,
    PensionProposalLookupAPIView,
)
from .pension_amount_api import (
    PensionAmountCalculateAPIView,
    PensionAmountLookupAPIView,
)

urlpatterns = [

    path("process/", PensionProcessView.as_view(), ),
    path("report/<int:id>/", PensionReportView.as_view(),),
    path("cases/", PensionCaseListView.as_view(),),
    path('employees/<str:emp_id>/', EmployeeSearchAPIView.as_view()),
    path('commutation/', CommutationCreateAPIView.as_view()),
    path('commutation/<int:pk>/', CommutationCreateAPIView.as_view()),
    path('no-pay/employee/<str:emp_code>/', NoPayLookupAPIView.as_view()),
    path('no-pay/', NoPayEntryAPIView.as_view()),
    path('no-pay/<int:pk>/', NoPayEntryAPIView.as_view()),
    path(
        'pension-proposal/employee/<str:emp_code>/',
        PensionProposalLookupAPIView.as_view(),
    ),
    path('pension-proposal/', PensionProposalAPIView.as_view()),
    path('pension-proposal/<int:pk>/', PensionProposalAPIView.as_view()),
    path('earn-dedn/<str:code>/', EarnDednLookupAPIView.as_view()),
    path(
        'amount/employee/<str:emp_code>/',
        PensionAmountLookupAPIView.as_view(),
    ),
    path('amount/calculate/', PensionAmountCalculateAPIView.as_view()),
]
