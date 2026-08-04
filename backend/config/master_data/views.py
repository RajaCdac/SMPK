from django.utils import timezone
from rest_framework.viewsets import ModelViewSet

from accounts.permissions import IsAdminRole
from audit.services import log_audit

from .models import FiPmMhBank, FiPmMhBankAbbr, FiPnMhEarndedn
from .serializers import (
    FiPmMhBankAbbrSerializer,
    FiPmMhBankSerializer,
    FiPnMhEarndednSerializer,
)

MASTER_DATA_MODULE = "MASTER_DATA"


def _user_code(user):
    if not user or not getattr(user, "username", None):
        return "ADMIN"
    return str(user.username).strip()[:5].upper() or "ADMIN"


def _apply_audit_fields(instance, user, *, is_create):
    today = timezone.localdate()
    code = _user_code(user)
    if is_create:
        if not instance.date_created:
            instance.date_created = today
        if not instance.created_by:
            instance.created_by = code
    instance.date_modified = today
    instance.modified_by = code


class BankViewSet(ModelViewSet):
    """Admin CRUD for FI_PM_MH_BANK (pension admin UI)."""

    queryset = FiPmMhBank.objects.all().order_by("bank_desc", "bank_cd")
    serializer_class = FiPmMhBankSerializer
    permission_classes = [IsAdminRole]
    lookup_field = "bank_cd"
    lookup_value_regex = r"[^/]+"

    def perform_create(self, serializer):
        instance = serializer.save()
        _apply_audit_fields(instance, self.request.user, is_create=True)
        instance.save()
        log_audit(
            self.request,
            table_name="FI_PM_MH_BANK",
            record_id=instance.bank_cd,
            action="CREATE",
            old_data=None,
            new_data=FiPmMhBankSerializer(instance).data,
            module=MASTER_DATA_MODULE,
        )

    def perform_update(self, serializer):
        old_data = FiPmMhBankSerializer(self.get_object()).data
        instance = serializer.save()
        _apply_audit_fields(instance, self.request.user, is_create=False)
        instance.save()
        log_audit(
            self.request,
            table_name="FI_PM_MH_BANK",
            record_id=instance.bank_cd,
            action="UPDATE",
            old_data=old_data,
            new_data=FiPmMhBankSerializer(instance).data,
            module=MASTER_DATA_MODULE,
        )

    def perform_destroy(self, instance):
        old_data = FiPmMhBankSerializer(instance).data
        bank_cd = instance.bank_cd
        instance.delete()
        log_audit(
            self.request,
            table_name="FI_PM_MH_BANK",
            record_id=bank_cd,
            action="DELETE",
            old_data=old_data,
            new_data=None,
            module=MASTER_DATA_MODULE,
        )


class BankAbbrViewSet(ModelViewSet):
    """Admin CRUD for FI_PM_MH_BANKABBR (pension admin UI)."""

    queryset = FiPmMhBankAbbr.objects.all().order_by("bank_name", "bank_type")
    serializer_class = FiPmMhBankAbbrSerializer
    permission_classes = [IsAdminRole]
    lookup_field = "bank_type"
    lookup_value_regex = r"[^/]+"

    def perform_create(self, serializer):
        instance = serializer.save()
        _apply_audit_fields(instance, self.request.user, is_create=True)
        instance.save()
        log_audit(
            self.request,
            table_name="FI_PM_MH_BANKABBR",
            record_id=instance.bank_type,
            action="CREATE",
            old_data=None,
            new_data=FiPmMhBankAbbrSerializer(instance).data,
            module=MASTER_DATA_MODULE,
        )

    def perform_update(self, serializer):
        old_data = FiPmMhBankAbbrSerializer(self.get_object()).data
        instance = serializer.save()
        _apply_audit_fields(instance, self.request.user, is_create=False)
        instance.save()
        log_audit(
            self.request,
            table_name="FI_PM_MH_BANKABBR",
            record_id=instance.bank_type,
            action="UPDATE",
            old_data=old_data,
            new_data=FiPmMhBankAbbrSerializer(instance).data,
            module=MASTER_DATA_MODULE,
        )

    def perform_destroy(self, instance):
        old_data = FiPmMhBankAbbrSerializer(instance).data
        bank_type = instance.bank_type
        instance.delete()
        log_audit(
            self.request,
            table_name="FI_PM_MH_BANKABBR",
            record_id=bank_type,
            action="DELETE",
            old_data=old_data,
            new_data=None,
            module=MASTER_DATA_MODULE,
        )


class EarndednViewSet(ModelViewSet):
    """Admin CRUD for FI_PN_MH_EARNDEDN (pension admin UI)."""

    queryset = FiPnMhEarndedn.objects.all().order_by("earndedn_cd")
    serializer_class = FiPnMhEarndednSerializer
    permission_classes = [IsAdminRole]
    lookup_field = "earndedn_cd"
    lookup_value_regex = r"[^/]+"

    def perform_create(self, serializer):
        instance = serializer.save()
        _apply_audit_fields(instance, self.request.user, is_create=True)
        instance.save()
        log_audit(
            self.request,
            table_name="FI_PN_MH_EARNDEDN",
            record_id=instance.earndedn_cd,
            action="CREATE",
            old_data=None,
            new_data=FiPnMhEarndednSerializer(instance).data,
            module=MASTER_DATA_MODULE,
        )

    def perform_update(self, serializer):
        old_data = FiPnMhEarndednSerializer(self.get_object()).data
        instance = serializer.save()
        _apply_audit_fields(instance, self.request.user, is_create=False)
        instance.save()
        log_audit(
            self.request,
            table_name="FI_PN_MH_EARNDEDN",
            record_id=instance.earndedn_cd,
            action="UPDATE",
            old_data=old_data,
            new_data=FiPnMhEarndednSerializer(instance).data,
            module=MASTER_DATA_MODULE,
        )

    def perform_destroy(self, instance):
        old_data = FiPnMhEarndednSerializer(instance).data
        code = instance.earndedn_cd
        instance.delete()
        log_audit(
            self.request,
            table_name="FI_PN_MH_EARNDEDN",
            record_id=code,
            action="DELETE",
            old_data=old_data,
            new_data=None,
            module=MASTER_DATA_MODULE,
        )
