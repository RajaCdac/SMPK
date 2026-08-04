from django.contrib import admin

from methodology2.models import Methodology2Consolidation


@admin.register(Methodology2Consolidation)
class Methodology2ConsolidationAdmin(admin.ModelAdmin):
    list_display = (
        "emp_cd",
        "name",
        "case_no",
        "roll_no",
        "category",
        "retirement_date",
        "m2_family_pension_277",
        "m2_family_pension_359",
        "updated_at",
    )
    search_fields = ("emp_cd", "name", "case_no", "roll_no")
    list_filter = ("category",)
    readonly_fields = ("created_at", "updated_at", "calculated_at")
