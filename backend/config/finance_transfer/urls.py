from django.urls import path

from .views import (
    FinanceTransferApplyFksView,
    FinanceTransferDefaultsView,
    FinanceTransferStartView,
    FinanceTransferStatusView,
    FinanceTransferTablesView,
    FinanceTransferTestMysqlView,
    SmpkSyncDefaultsView,
    SmpkSyncStartView,
    SmpkSyncStatusView,
    SmpkSyncTablesView,
    SmpkSyncTestMysqlView,
)

urlpatterns = [
    path(
        "defaults/",
        FinanceTransferDefaultsView.as_view(),
        name="finance-transfer-defaults",
    ),
    path(
        "test-mysql/",
        FinanceTransferTestMysqlView.as_view(),
        name="finance-transfer-test-mysql",
    ),
    path("tables/", FinanceTransferTablesView.as_view(), name="finance-transfer-tables"),
    path("start/", FinanceTransferStartView.as_view(), name="finance-transfer-start"),
    path("status/", FinanceTransferStatusView.as_view(), name="finance-transfer-status"),
    path(
        "apply-pending-fks/",
        FinanceTransferApplyFksView.as_view(),
        name="finance-transfer-apply-fks",
    ),
    path(
        "smpk-sync/defaults/",
        SmpkSyncDefaultsView.as_view(),
        name="smpk-sync-defaults",
    ),
    path(
        "smpk-sync/test-mysql/",
        SmpkSyncTestMysqlView.as_view(),
        name="smpk-sync-test-mysql",
    ),
    path("smpk-sync/tables/", SmpkSyncTablesView.as_view(), name="smpk-sync-tables"),
    path("smpk-sync/start/", SmpkSyncStartView.as_view(), name="smpk-sync-start"),
    path("smpk-sync/status/", SmpkSyncStatusView.as_view(), name="smpk-sync-status"),
]
