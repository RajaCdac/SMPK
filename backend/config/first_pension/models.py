from django.db import models
from django.conf import settings


class PensionCase(models.Model):

    # Employee Snapshot
    emp_code = models.CharField(
        max_length=20,
        unique=True
    )

    name = models.CharField(max_length=200)

    emp_class = models.CharField(max_length=20)

    birth_date = models.DateField()

    joining_date = models.DateField()

    retirement_date = models.DateField()

    designation = models.CharField(max_length=200)

    scale = models.CharField(max_length=100)

    last_basic = models.DecimalField(
        max_digits=12,
        decimal_places=2
    )

    # Pension Inputs
    no_pay_days = models.IntegerField(default=0)

    dies_non_days = models.IntegerField(default=0)

    commutation_percent = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=40
    )

    commutation_reason = models.CharField(
        max_length=200,
        blank=True,
        null=True
    )

    # Workflow
    status = models.CharField(
        max_length=50,
        default="INITIATED"
    )

    current_stage = models.CharField(
        max_length=50,
        default="CLERK"
    )

    # Audit
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="pension_created"
    )

    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="pension_updated"
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    def __str__(self):
        return self.emp_code


class PensionSummary(models.Model):

    pension_case = models.OneToOneField(
        PensionCase,
        on_delete=models.CASCADE,
        related_name="summary"
    )

    # Total Service
    total_service_years = models.IntegerField(default=0)

    total_service_months = models.IntegerField(default=0)

    total_service_days = models.IntegerField(default=0)

    # TCCS
    tccs_years = models.IntegerField(default=0)

    tccs_months = models.IntegerField(default=0)

    tccs_days = models.IntegerField(default=0)

    # TQS
    tqs_years = models.IntegerField(default=0)

    tqs_months = models.IntegerField(default=0)

    tqs_days = models.IntegerField(default=0)

    # Financials
    pension_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0
    )

    commutation_amount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=0
    )

    gratuity_amount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=0
    )

    pension_start_date = models.DateField()

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    def __str__(self):
        return self.pension_case.emp_code