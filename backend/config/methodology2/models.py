from django.db import models


class Methodology2Consolidation(models.Model):
    """
    One row per employee Methodology-2 consolidation print snapshot.

    Header title and footer signatories (FA & CAO / AO GR-1) are print-only
    and are not stored. Everything else needed to reprint is on this row.
    """

    emp_cd = models.CharField(max_length=5, unique=True, db_index=True)
    name = models.CharField(max_length=200, blank=True, default="")
    # From fi_pn_wage_2022_hdr_third:
    # EMP_NAME = employee name; PEN_NAME = pensioner name.
    # PENSIONER_TYPE decides the label/math:
    #   P = Employee Pension  -> Methodology-2 uses 50%
    #   F = Family Pension    -> Methodology-2 uses 30%
    wage_emp_name = models.CharField(max_length=200, blank=True, default="")
    pensioner_name = models.CharField(max_length=200, blank=True, default="")
    is_employee_pension = models.BooleanField(default=False)
    # DOD from family claim — when set, print may split 277/359 into employee+family columns.
    date_of_death = models.DateField(null=True, blank=True)
    # Print comparison columns (may be 2–4 cols when DOD splits a CPI period).
    pension_comparison = models.JSONField(default=dict, blank=True)
    case_no = models.CharField(max_length=20, blank=True, default="")
    roll_no = models.CharField(max_length=30, blank=True, default="")
    retirement_type = models.CharField(max_length=80, blank=True, default="")
    retirement_date = models.DateField(null=True, blank=True)
    category = models.CharField(max_length=20, blank=True, default="")
    designation = models.CharField(max_length=200, blank=True, default="")
    tqs_yr = models.IntegerField(null=True, blank=True)
    tqs_month = models.IntegerField(null=True, blank=True)
    tqs_days = models.IntegerField(null=True, blank=True)
    average_pay = models.DecimalField(
        max_digits=14, decimal_places=2, null=True, blank=True
    )
    last_pay = models.DecimalField(
        max_digits=14, decimal_places=2, null=True, blank=True
    )
    scale = models.CharField(max_length=100, blank=True, default="")
    start_revision = models.CharField(max_length=60, blank=True, default="")

    # Full revision A–D blocks for print (JSON list of year/CPI sections).
    revision_blocks = models.JSONField(default=list, blank=True)
    # Raw calculation rows from M2 engine (optional reprint/debug).
    calculation_rows = models.JSONField(default=list, blank=True)

    m2_basic_2017 = models.DecimalField(
        max_digits=14, decimal_places=2, null=True, blank=True
    )
    m2_basic_2022 = models.DecimalField(
        max_digits=14, decimal_places=2, null=True, blank=True
    )
    m2_pension_277 = models.DecimalField(
        max_digits=14, decimal_places=2, null=True, blank=True
    )
    m2_pension_359 = models.DecimalField(
        max_digits=14, decimal_places=2, null=True, blank=True
    )
    m2_family_pension_277 = models.DecimalField(
        max_digits=14, decimal_places=2, null=True, blank=True
    )
    m2_family_pension_359 = models.DecimalField(
        max_digits=14, decimal_places=2, null=True, blank=True
    )

    m1_family_pension_277 = models.DecimalField(
        max_digits=14, decimal_places=2, null=True, blank=True
    )
    m1_family_pension_359 = models.DecimalField(
        max_digits=14, decimal_places=2, null=True, blank=True
    )
    diff_family_pension_277 = models.DecimalField(
        max_digits=14, decimal_places=2, null=True, blank=True
    )
    diff_family_pension_359 = models.DecimalField(
        max_digits=14, decimal_places=2, null=True, blank=True
    )

    calculated_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "methodology2_consolidation"
        verbose_name = "Methodology 2 consolidation snapshot"
        ordering = ["-updated_at"]

    def __str__(self):
        return f"{self.emp_cd} — {self.name}".strip(" —")

    @property
    def tqs_display(self):
        if self.tqs_yr is None and self.tqs_month is None and self.tqs_days is None:
            return ""
        y = self.tqs_yr or 0
        m = self.tqs_month or 0
        d = self.tqs_days or 0
        return f"{y}Y {m}M {d}D"
