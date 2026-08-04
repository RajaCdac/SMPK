from django.contrib import admin
from django.utils import timezone

from .models import FiPmMhBank, FiPmMhBankAbbr


def _user_code(user):
    if not user or not getattr(user, "username", None):
        return "ADMIN"
    return str(user.username).strip()[:5].upper() or "ADMIN"


@admin.register(FiPmMhBank)
class FiPmMhBankAdmin(admin.ModelAdmin):
    list_display = (
        "bank_cd",
        "bank_desc",
        "control_bank_cd",
        "city",
        "rbi_cd",
        "created_by",
        "date_created",
    )
    search_fields = (
        "bank_cd",
        "bank_desc",
        "control_bank_cd",
        "city",
        "rbi_cd",
        "old_bank_cd",
    )
    ordering = ("bank_desc", "bank_cd")
    readonly_fields = ("date_created", "created_by", "date_modified", "modified_by")

    fieldsets = (
        (
            "Bank (FI_PM_MH_BANK)",
            {
                "fields": (
                    "bank_cd",
                    "bank_desc",
                    "bank_id",
                    "control_bank_cd",
                    "rbi_cd",
                    "old_bank_cd",
                )
            },
        ),
        (
            "Address & contact",
            {
                "fields": (
                    "addr1",
                    "addr2",
                    "ps",
                    "city",
                    "dist",
                    "state",
                    "pin",
                    "country",
                    "contact1",
                    "contact2",
                    "fax_no",
                    "email_id",
                )
            },
        ),
        (
            "Audit",
            {
                "fields": (
                    "date_created",
                    "created_by",
                    "date_modified",
                    "modified_by",
                )
            },
        ),
    )

    def save_model(self, request, obj, form, change):
        today = timezone.localdate()
        user_code = _user_code(request.user)
        if not change:
            if not obj.date_created:
                obj.date_created = today
            if not obj.created_by:
                obj.created_by = user_code
        obj.date_modified = today
        obj.modified_by = user_code
        super().save_model(request, obj, form, change)


@admin.register(FiPmMhBankAbbr)
class FiPmMhBankAbbrAdmin(admin.ModelAdmin):
    list_display = (
        "bank_type",
        "bank_name",
        "bank_short_name",
        "bank_id",
        "created_by",
        "date_created",
    )
    search_fields = ("bank_type", "bank_name", "bank_short_name", "bank_id")
    ordering = ("bank_name", "bank_type")
    readonly_fields = ("date_created", "created_by", "date_modified", "modified_by")

    fieldsets = (
        (
            "Bank abbreviation (FI_PM_MH_BANKABBR)",
            {
                "fields": (
                    "bank_type",
                    "bank_name",
                    "bank_short_name",
                    "bank_id",
                )
            },
        ),
        (
            "Audit",
            {
                "fields": (
                    "date_created",
                    "created_by",
                    "date_modified",
                    "modified_by",
                )
            },
        ),
    )

    def save_model(self, request, obj, form, change):
        today = timezone.localdate()
        user_code = _user_code(request.user)
        if not change:
            if not obj.date_created:
                obj.date_created = today
            if not obj.created_by:
                obj.created_by = user_code
        obj.date_modified = today
        obj.modified_by = user_code
        super().save_model(request, obj, form, change)
