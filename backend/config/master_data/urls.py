from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import BankAbbrViewSet, BankViewSet, EarndednViewSet

router = DefaultRouter()
router.register("banks", BankViewSet, basename="master-banks")
router.register("bank-abbr", BankAbbrViewSet, basename="master-bank-abbr")
router.register("earn-dedn", EarndednViewSet, basename="master-earn-dedn")

urlpatterns = [
    path("", include(router.urls)),
]
