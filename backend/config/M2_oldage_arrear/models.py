from django.db import models


class M2OldageArrearConsolidation(models.Model):
    """
    Methodology-2 consolidation snapshot for the Old-Age Arrear app only.

    Separate from methodology2_consolidation so Met2 data is never touched.
    """

    emp_cd = models.CharField(max_length=5, unique=True, db_index=True)
    name = models.CharField(max_length=200, blank=True, default="")
    wage_emp_name = models.CharField(max_length=200, blank=True, default="")
    pensioner_name = models.CharField(max_length=200, blank=True, default="")
    is_employee_pension = models.BooleanField(default=False)
    date_of_death = models.DateField(null=True, blank=True)
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

    revision_blocks = models.JSONField(default=list, blank=True)
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

    # Methodology-1 family pension only. Null while the employee is alive.
    # Employee Methodology-1 stays on the pension comparison columns.
    m1_family_pension_277 = models.DecimalField(
        max_digits=14, decimal_places=2, null=True, blank=True
    )
    m1_family_pension_359 = models.DecimalField(
        max_digits=14, decimal_places=2, null=True, blank=True
    )
    # Class 1/2 LIC BUNCH_BASIC. M1@277 on the comparison column is
    # basic + this amount. Null when there is no bunching.
    bunch_basic = models.DecimalField(
        max_digits=14, decimal_places=2, null=True, blank=True
    )
    # Signed difference of that same pension: M2 − Methodology-1.
    # Employee case uses m2_pension_*. Family case uses m2_family_pension_*.
    diff_family_pension_277 = models.DecimalField(
        max_digits=14, decimal_places=2, null=True, blank=True
    )
    diff_family_pension_359 = models.DecimalField(
        max_digits=14, decimal_places=2, null=True, blank=True
    )

    # Old-age entitlement snapshot (slabs / milestones / current %).
    oldage_benefit = models.JSONField(default=dict, blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    # Last bulk/manual batch that wrote this emp (informational).
    last_batch_id = models.CharField(max_length=64, blank=True, default="", db_index=True)

    calculated_at = models.DateTimeField(null=True, blank=True)
    # User who last saved this consolidation (same style as payment_done_by).
    consolidated_by = models.CharField(max_length=80, blank=True, default="")
    # Dashboard: mark when payment for this consolidation has been made.
    payment_done = models.BooleanField(default=False, db_index=True)
    payment_done_at = models.DateTimeField(null=True, blank=True)
    payment_done_by = models.CharField(max_length=80, blank=True, default="")
    # Filled when a paid Excel marks this row. Blank until that upload matches.
    payment_phase = models.CharField(max_length=40, blank=True, default="")
    payment_abstract_no = models.CharField(max_length=40, blank=True, default="")
    payment_ref_date = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "m2_oldage_arrear_consolidation"
        verbose_name = "M2 Old Age Arrear consolidation"
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


class M2OaThOldageBenefit(models.Model):
    """
    Old-age benefit enquiry header (From–To month/year).

    Naming mirrors legacy fi_pn_th_* transaction headers.
    Month-wise rows live in m2_oa_td_oldage_benefit_mth.
    """

    emp_cd = models.CharField(max_length=5, db_index=True)
    name = models.CharField(max_length=200, blank=True, default="")
    roll_no = models.CharField(max_length=30, blank=True, default="")
    case_no = models.CharField(max_length=20, blank=True, default="")
    category = models.CharField(max_length=20, blank=True, default="")
    is_employee_pension = models.BooleanField(default=True)

    from_year = models.PositiveIntegerField()
    from_month = models.PositiveSmallIntegerField()  # 1–12
    to_year = models.PositiveIntegerField()
    to_month = models.PositiveSmallIntegerField()  # 1–12

    dob = models.DateField(null=True, blank=True)
    as_on_date = models.DateField(null=True, blank=True)

    m1_pension_277 = models.DecimalField(
        max_digits=14, decimal_places=2, null=True, blank=True
    )
    m2_pension_277 = models.DecimalField(
        max_digits=14, decimal_places=2, null=True, blank=True
    )
    m1_pension_359 = models.DecimalField(
        max_digits=14, decimal_places=2, null=True, blank=True
    )
    m2_pension_359 = models.DecimalField(
        max_digits=14, decimal_places=2, null=True, blank=True
    )
    benefit_277 = models.DecimalField(
        max_digits=14, decimal_places=2, null=True, blank=True
    )
    benefit_359 = models.DecimalField(
        max_digits=14, decimal_places=2, null=True, blank=True
    )

    age_completed = models.PositiveSmallIntegerField(null=True, blank=True)
    applicable_percent = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True
    )
    additional_pension = models.DecimalField(
        max_digits=14, decimal_places=2, null=True, blank=True
    )
    monthly_da = models.DecimalField(
        max_digits=14, decimal_places=2, null=True, blank=True
    )
    monthly_total = models.DecimalField(
        max_digits=14, decimal_places=2, null=True, blank=True
    )
    da_pct = models.DecimalField(
        max_digits=7, decimal_places=2, null=True, blank=True
    )

    total_arrear = models.DecimalField(
        max_digits=14, decimal_places=2, null=True, blank=True
    )
    total_arrear_basic = models.DecimalField(
        max_digits=14, decimal_places=2, null=True, blank=True
    )
    total_arrear_da = models.DecimalField(
        max_digits=14, decimal_places=2, null=True, blank=True
    )

    version_no = models.PositiveIntegerField(default=1)
    calculated_at = models.DateTimeField(null=True, blank=True)
    calculated_by = models.CharField(max_length=80, blank=True, default="")
    # Full engine payload (periods / slabs) for reprint.
    payload_json = models.JSONField(default=dict, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "m2_oa_th_oldage_benefit"
        verbose_name = "M2 OA old-age benefit header"
        ordering = ["-updated_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["emp_cd", "from_year", "from_month", "to_year", "to_month"],
                name="uniq_m2_oa_th_oldage_benefit_range",
            )
        ]

    def __str__(self):
        return (
            f"{self.emp_cd} {self.from_month:02d}/{self.from_year}"
            f"-{self.to_month:02d}/{self.to_year}"
        )


class M2OaTdOldageBenefitMth(models.Model):
    """
    Month-wise old-age benefit lines (like pens_cal_* bill month rows).

    One row per calendar month inside the enquiry From–To range.
    """

    hdr = models.ForeignKey(
        M2OaThOldageBenefit,
        on_delete=models.CASCADE,
        related_name="months",
        db_column="hdr_id",
    )
    emp_cd = models.CharField(max_length=5, db_index=True)
    bill_year = models.PositiveIntegerField(db_index=True)
    bill_month = models.PositiveSmallIntegerField()  # 1–12
    bill_mth = models.CharField(max_length=3, blank=True, default="")  # JAN…DEC
    month_start = models.DateField()
    month_end = models.DateField()

    cpi_point = models.PositiveIntegerField(null=True, blank=True)
    oa_percent = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True
    )
    age_slab = models.PositiveSmallIntegerField(null=True, blank=True)
    benefit_base = models.DecimalField(
        max_digits=14, decimal_places=2, null=True, blank=True
    )
    # Pension amounts in force that month (so OA benefit = % × (M2 − M1) is clear).
    m1_pension = models.DecimalField(
        max_digits=14, decimal_places=2, null=True, blank=True
    )
    m2_pension = models.DecimalField(
        max_digits=14, decimal_places=2, null=True, blank=True
    )
    oa_basic = models.DecimalField(
        max_digits=14, decimal_places=2, null=True, blank=True
    )
    da_pct = models.DecimalField(
        max_digits=7, decimal_places=2, null=True, blank=True
    )
    oa_da = models.DecimalField(
        max_digits=14, decimal_places=2, null=True, blank=True
    )
    month_total = models.DecimalField(
        max_digits=14, decimal_places=2, null=True, blank=True
    )

    class Meta:
        db_table = "m2_oa_td_oldage_benefit_mth"
        verbose_name = "M2 OA old-age benefit month"
        ordering = ["bill_year", "bill_month", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["hdr", "bill_year", "bill_month"],
                name="uniq_m2_oa_td_oldage_benefit_mth",
            )
        ]
        indexes = [
            models.Index(
                fields=["emp_cd", "bill_year", "bill_month"],
                name="m2_oa_td_ben_mth_emp_idx",
            ),
        ]

    def __str__(self):
        return f"{self.emp_cd} {self.bill_mth}/{self.bill_year} = {self.month_total}"


class M2OldAgeBatch(models.Model):
    """
    One consolidation run (manual or auto bulk).

    stamp example: 2026-09-24_0930 (IST). Excel export later uses batch_id.
    """

    SOURCE_AUTO = "auto"
    SOURCE_MANUAL = "manual"
    SOURCE_CHOICES = (
        (SOURCE_AUTO, "Auto bulk"),
        (SOURCE_MANUAL, "Manual entry"),
    )

    STATUS_RUNNING = "running"
    STATUS_COMPLETED = "completed"
    STATUS_FAILED = "failed"

    batch_id = models.CharField(max_length=64, unique=True, db_index=True)
    source = models.CharField(max_length=20, choices=SOURCE_CHOICES, db_index=True)
    stamp = models.CharField(max_length=32, db_index=True)  # YYYY-MM-DD_HHMM IST
    run_at = models.DateTimeField()
    case_count = models.PositiveIntegerField(default=0)  # planned / uploaded
    ok_count = models.PositiveIntegerField(default=0)
    failed_count = models.PositiveIntegerField(default=0)
    skipped_count = models.PositiveIntegerField(default=0)
    output_dir = models.CharField(max_length=500, blank=True, default="")
    generate_pdf = models.BooleanField(default=True)
    status = models.CharField(max_length=20, default=STATUS_RUNNING)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "m2_oldage_arrear_batch"
        verbose_name = "M2 Old Age consolidation batch"
        ordering = ["-run_at", "-id"]

    def __str__(self):
        return f"{self.batch_id} ({self.case_count} cases)"


class M2OldAgeBatchCase(models.Model):
    """Emp membership in a consolidation batch (for Excel-by-batch)."""

    batch = models.ForeignKey(
        M2OldAgeBatch,
        on_delete=models.CASCADE,
        related_name="cases",
        db_column="batch_pk",
    )
    emp_cd = models.CharField(max_length=5, db_index=True)
    case_no = models.CharField(max_length=20, blank=True, default="")
    roll_no = models.CharField(max_length=30, blank=True, default="")
    status = models.CharField(max_length=20, blank=True, default="")
    reason = models.CharField(max_length=500, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "m2_oldage_arrear_batch_case"
        verbose_name = "M2 Old Age batch case"
        ordering = ["id"]
        constraints = [
            models.UniqueConstraint(
                fields=["batch", "emp_cd"],
                name="uniq_m2_oa_batch_case_emp",
            )
        ]

    def __str__(self):
        return f"{self.batch.batch_id} / {self.emp_cd}"

