from django.urls import path

from .views import (
    CalculateClass12View,
    CalculateRevisionView,
    ConsolidationSnapshotView,
    EmployeeLookupView,
    GetClass12PayStagesView,
    GetClass12ScalesView,
    GetEquivalentScalesView,
    GetPayStagesView,
    GetScalesView,
    GetSpecialDaOptionsView,
    OldAgeBenefitView,
    ScaleTypeView,
)
from .views_bulk import (
    BulkFinishView,
    BulkPrepareView,
    BulkRowView,
    BulkUploadView,
)
from .views_manual import (
    ManualEntryFinishView,
    ManualEntryPrepareView,
    ManualEntryRowView,
    ManualEntryUploadView,
)
from .views_report import ConsolidationReportView
from .views_benefit_enquiry import (
    OldAgeBenefitEnquirySaveView,
    OldAgeBenefitEnquiryView,
)
from .views_dashboard import (
    ConsolidationDashboardView,
    ConsolidationDeleteManyView,
    ConsolidationDeleteView,
    ConsolidationPaymentManyView,
    ConsolidationPaymentView,
)
from .views_batch import (
    BatchExcelReportView,
    BatchListView,
    EmpListExcelReportView,
)
from .views_macp import MacpCalculateView, MacpOptionsView
from .views_arrear import (
    ArrearBatchView,
    ArrearCalculateView,
    ArrearEmployeeView,
    ArrearExportView,
)

urlpatterns = [
    path("get-scales/", GetScalesView.as_view()),
    path("get-pay-stages/", GetPayStagesView.as_view()),
    path("get-equivalent-scales/", GetEquivalentScalesView.as_view()),
    path("get-special-da-options/", GetSpecialDaOptionsView.as_view()),
    path("calculate-revision/", CalculateRevisionView.as_view()),
    path("macp/options/", MacpOptionsView.as_view()),
    path("macp/calculate/", MacpCalculateView.as_view()),
    path("arrear/employee/<str:emp_id>/", ArrearEmployeeView.as_view()),
    path("arrear/calculate/", ArrearCalculateView.as_view()),
    path("arrear/batch/", ArrearBatchView.as_view()),
    path("arrear/export/", ArrearExportView.as_view()),
    path("get-scales-class12/", GetClass12ScalesView.as_view()),
    path("get-pay-stages-class12/", GetClass12PayStagesView.as_view()),
    path("calculate-class12/", CalculateClass12View.as_view()),
    path("get-scale-type/", ScaleTypeView.as_view()),
    path("employee/<str:emp_id>/", EmployeeLookupView.as_view()),
    path("consolidation/", ConsolidationSnapshotView.as_view()),
    path("consolidation/<str:emp_id>/", ConsolidationSnapshotView.as_view()),
    path("bulk/", BulkUploadView.as_view()),
    path("bulk/prepare/", BulkPrepareView.as_view()),
    path("bulk/row/", BulkRowView.as_view()),
    path("bulk/finish/", BulkFinishView.as_view()),
    path("manual/", ManualEntryUploadView.as_view()),
    path("manual/prepare/", ManualEntryPrepareView.as_view()),
    path("manual/row/", ManualEntryRowView.as_view()),
    path("manual/finish/", ManualEntryFinishView.as_view()),
    path("report/", ConsolidationReportView.as_view()),
    path("report/excel/", EmpListExcelReportView.as_view()),
    path("batches/", BatchListView.as_view()),
    path("batches/<str:batch_id>/report/", BatchExcelReportView.as_view()),
    path("dashboard/", ConsolidationDashboardView.as_view()),
    path("dashboard/payment/", ConsolidationPaymentView.as_view()),
    path("dashboard/payment-many/", ConsolidationPaymentManyView.as_view()),
    path("dashboard/delete/", ConsolidationDeleteView.as_view()),
    path("dashboard/delete-many/", ConsolidationDeleteManyView.as_view()),
    path("oldage/", OldAgeBenefitView.as_view()),
    path("oldage/calculate/", OldAgeBenefitView.as_view()),
    path("oldage-benefit/", OldAgeBenefitEnquiryView.as_view()),
    path("oldage-benefit/calculate/", OldAgeBenefitEnquiryView.as_view()),
    path("oldage-benefit/save/", OldAgeBenefitEnquirySaveView.as_view()),
]
