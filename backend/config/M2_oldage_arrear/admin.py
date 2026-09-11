from django.contrib import admin

from .models import M2OldageArrearConsolidation


@admin.register(M2OldageArrearConsolidation)
class M2OldageArrearConsolidationAdmin(admin.ModelAdmin):
    list_display = ("emp_cd", "name", "case_no", "updated_at")
    search_fields = ("emp_cd", "name", "case_no", "roll_no")
