from django.urls import path

from .archive_api import (
    ArchiveBillDetailAPIView,
    ArchiveEmployeeLookupAPIView,
    ArchiveJournalDetailAPIView,
)
from .views import (
    CommutationCreateAPIView,
    EmployeeSearchAPIView,
    NoPayEntryAPIView,
    NoPayLeaveDetailsAPIView,
    NoPayLookupAPIView,
    PensionProcessView,
    PensionReportView,
    PensionCaseListView,
)
from .pension_proposal_api import (
    BankAbbrAPIView,
    BankAbbrLookupAPIView,
    BankLookupAPIView,
    BankMasterAPIView,
    EarnDednListAPIView,
    EarnDednLookupAPIView,
    PensionProposalAPIView,
    PensionProposalLookupAPIView,
)
from .pension_amount_api import (
    FirstMonthPensionGenerateAPIView,
    PensionAmountCalculateAPIView,
    PensionAmountLookupAPIView,
    PensionSaloutTransferAPIView,
)
from .pension_bill_api import (
    PensionBillAbstractReportAPIView,
    PensionBillCandidatesAPIView,
    PensionBillCloseMonthAPIView,
    PensionBillGenerateAPIView,
    PensionBillMonthStatusAPIView,
    PensionBillPpnListAPIView,
    PensionSepcomStatusAPIView,
    PensionSepcomGenerateAPIView,
    PensionSepCommReportAPIView,
    PensionSeparateCommutationBillReportAPIView,
    PensionPpcBillCandidatesAPIView,
    PensionPpcBillGenerateAPIView,
    PensionPpcBillListAPIView,
    PensionPpcBillStatusAPIView,
    PensionBillReprocessAPIView,
    PensionBillReprocessCandidatesAPIView,
    PensionBillStatusAPIView,
    PensionCommutationBillReportAPIView,
    PensionJournalSummaryBillsAPIView,
    PensionJournalSummaryReportAPIView,
    PensionLicReportAPIView,
    PensionProposalSanctionReportAPIView,
    PensionFirstPensionAdviceReportAPIView,
    PensionManualJournalListAPIView,
    PensionManualJournalSaveAPIView,
    PensionManualJournalSummaryAPIView,
    PensionManualJournalTemplateAPIView,
    PensionVoucherGenerateAPIView,
    PensionVoucherPreviewAPIView,
    PensionVoucherStatusAPIView,
)
from .process_intake_api import (
    ProcessIntakeAPIView,
    ProcessIntakeLookupAPIView,
)
from .lic_claim_api import (
    LicClaimGenerationNormalAPIView,
    LicClaimNormalPrintAPIView,
)

urlpatterns = [

    path("process/", PensionProcessView.as_view(), ),
    path("report/<int:id>/", PensionReportView.as_view(),),
    path("cases/", PensionCaseListView.as_view(),),
    path('employees/<str:emp_id>/', EmployeeSearchAPIView.as_view()),
    path('commutation/', CommutationCreateAPIView.as_view()),
    path('commutation/<int:pk>/', CommutationCreateAPIView.as_view()),
    path('no-pay/employee/<str:emp_code>/', NoPayLookupAPIView.as_view()),
    path(
        'no-pay/leave-details/employee/<str:emp_code>/',
        NoPayLeaveDetailsAPIView.as_view(),
    ),
    path('no-pay/', NoPayEntryAPIView.as_view()),
    path('no-pay/<int:pk>/', NoPayEntryAPIView.as_view()),
    path(
        'pension-proposal/employee/<str:emp_code>/',
        PensionProposalLookupAPIView.as_view(),
    ),
    path('pension-proposal/', PensionProposalAPIView.as_view()),
    path('pension-proposal/<int:pk>/', PensionProposalAPIView.as_view()),
    path('earn-dedn-list/', EarnDednListAPIView.as_view()),
    path('earn-dedn/<str:code>/', EarnDednLookupAPIView.as_view()),
    path('banks/', BankMasterAPIView.as_view()),
    path('banks/<str:bank_cd>/', BankLookupAPIView.as_view()),
    path('bank-abbr/', BankAbbrAPIView.as_view()),
    path('bank-abbr/<str:bank_type>/', BankAbbrLookupAPIView.as_view()),
    path(
        'amount/employee/<str:emp_code>/',
        PensionAmountLookupAPIView.as_view(),
    ),
    path('amount/calculate/', PensionAmountCalculateAPIView.as_view()),
    path(
        'amount/salout-transfer/employee/<str:emp_code>/',
        PensionSaloutTransferAPIView.as_view(),
    ),
    path('amount/salout-transfer/', PensionSaloutTransferAPIView.as_view()),
    path('amount/first-month-generate/', FirstMonthPensionGenerateAPIView.as_view()),
    path(
        'pension-bill/status/employee/<str:emp_code>/',
        PensionBillStatusAPIView.as_view(),
    ),
    path('pension-bill/candidates/', PensionBillCandidatesAPIView.as_view()),
    path('pension-bill/generate/', PensionBillGenerateAPIView.as_view()),
    path('pension-bill/reprocess/candidates/', PensionBillReprocessCandidatesAPIView.as_view()),
    path('pension-bill/reprocess/', PensionBillReprocessAPIView.as_view()),
    path('pension-bill/close-month/', PensionBillCloseMonthAPIView.as_view()),
    path('pension-bill/month-status/', PensionBillMonthStatusAPIView.as_view()),
    path('pension-bill/ppn/', PensionBillPpnListAPIView.as_view()),
    path(
        'pension-bill/ppc/status/employee/<str:emp_code>/',
        PensionPpcBillStatusAPIView.as_view(),
    ),
    path('pension-bill/ppc/candidates/', PensionPpcBillCandidatesAPIView.as_view()),
    path('pension-bill/ppc/generate/', PensionPpcBillGenerateAPIView.as_view()),
    path('pension-bill/ppc/list/', PensionPpcBillListAPIView.as_view()),
    path(
        'pension-bill/sepcom/status/employee/<str:emp_code>/',
        PensionSepcomStatusAPIView.as_view(),
    ),
    path('pension-bill/sepcom/generate/', PensionSepcomGenerateAPIView.as_view()),
    path('pension-bill/sep-comm-report/', PensionSepCommReportAPIView.as_view()),
    path(
        'pension-bill/separate-commutation-bill-report/',
        PensionSeparateCommutationBillReportAPIView.as_view(),
    ),
    path('pension-bill/lic-report/', PensionLicReportAPIView.as_view()),
    path(
        'pension-bill/bill-abstract-report/',
        PensionBillAbstractReportAPIView.as_view(),
    ),
    path(
        'pension-bill/journal-summary-report/',
        PensionJournalSummaryReportAPIView.as_view(),
    ),
    path(
        'pension-bill/journal-summary-bills/',
        PensionJournalSummaryBillsAPIView.as_view(),
    ),
    path(
        'pension-bill/proposal-sanction-report/',
        PensionProposalSanctionReportAPIView.as_view(),
    ),
    path(
        'pension-bill/first-pension-advice-report/',
        PensionFirstPensionAdviceReportAPIView.as_view(),
    ),
    path(
        'pension-bill/commutation-report/',
        PensionCommutationBillReportAPIView.as_view(),
    ),
    path(
        'pension-bill/voucher/status/',
        PensionVoucherStatusAPIView.as_view(),
    ),
    path(
        'pension-bill/voucher/preview/',
        PensionVoucherPreviewAPIView.as_view(),
    ),
    path(
        'pension-bill/voucher/generate/',
        PensionVoucherGenerateAPIView.as_view(),
    ),
    path(
        'pension-bill/manual-journal/template/',
        PensionManualJournalTemplateAPIView.as_view(),
    ),
    path(
        'pension-bill/manual-journal/summary/',
        PensionManualJournalSummaryAPIView.as_view(),
    ),
    path(
        'pension-bill/manual-journal/list/',
        PensionManualJournalListAPIView.as_view(),
    ),
    path(
        'pension-bill/manual-journal/save/',
        PensionManualJournalSaveAPIView.as_view(),
    ),
    path(
        'process-intake/employee/<str:emp_code>/',
        ProcessIntakeLookupAPIView.as_view(),
    ),
    path('process-intake/', ProcessIntakeAPIView.as_view()),
    path(
        'archive/employee/<str:emp_code>/',
        ArchiveEmployeeLookupAPIView.as_view(),
    ),
    path(
        'archive/bill/<str:bill_no>/',
        ArchiveBillDetailAPIView.as_view(),
    ),
    path(
        'archive/journal/<str:voucher_no>/',
        ArchiveJournalDetailAPIView.as_view(),
    ),
    path(
        'lic-claim-generation/normal/',
        LicClaimGenerationNormalAPIView.as_view(),
    ),
    path(
        'lic-claim-generation/normal/print/',
        LicClaimNormalPrintAPIView.as_view(),
    ),
]
