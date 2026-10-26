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


class M2ConsolCase(models.Model):
    """
    Systematic consolidation case header (Met2 / Old Age).

    Print snapshots stay on methodology2_consolidation /
    m2_oldage_arrear_consolidation. This row drives status, cutovers,
    verification, and bill-facing rates.
    """

    SOURCE_MET2 = "MET2"
    SOURCE_OA = "OA"
    SOURCE_CHOICES = [
        (SOURCE_MET2, "Methodology-2"),
        (SOURCE_OA, "Old Age Arrear"),
    ]

    CASE_RETIRED = "RETIRED"
    CASE_DIH = "DIE_IN_HARNESS"
    CASE_DIED_AFTER_RET = "DIED_AFTER_RET"
    CASE_FAMILY = "FAMILY"
    CASE_TYPE_CHOICES = [
        (CASE_RETIRED, "Retired employee pension"),
        (CASE_DIH, "Die in harness"),
        (CASE_DIED_AFTER_RET, "Died after retirement"),
        (CASE_FAMILY, "Family pension"),
    ]

    STATUS_CALCULATED = "CALCULATED"
    STATUS_IN_REVIEW = "IN_REVIEW"
    STATUS_ERROR = "ERROR"
    STATUS_DISPUTED = "DISPUTED"
    STATUS_VERIFIED = "VERIFIED"
    STATUS_APPROVED = "APPROVED"
    STATUS_RELEASED = "RELEASED"
    STATUS_HELD = "HELD"
    STATUS_SUPERSEDED = "SUPERSEDED"
    STATUS_CHOICES = [
        (STATUS_CALCULATED, "Calculated"),
        (STATUS_IN_REVIEW, "In review"),
        (STATUS_ERROR, "Error"),
        (STATUS_DISPUTED, "Disputed"),
        (STATUS_VERIFIED, "Verified"),
        (STATUS_APPROVED, "Approved"),
        (STATUS_RELEASED, "Released to master"),
        (STATUS_HELD, "Held"),
        (STATUS_SUPERSEDED, "Superseded"),
    ]

    emp_cd = models.CharField(max_length=5, db_index=True)
    source_app = models.CharField(
        max_length=8, choices=SOURCE_CHOICES, default=SOURCE_MET2
    )
    case_type = models.CharField(
        max_length=20, choices=CASE_TYPE_CHOICES, default=CASE_RETIRED
    )
    pensioner_type = models.CharField(max_length=1, blank=True, default="")  # P/F
    roll_no = models.CharField(max_length=30, blank=True, default="")
    case_no = models.CharField(max_length=20, blank=True, default="")
    name = models.CharField(max_length=200, blank=True, default="")
    fp_name = models.CharField(max_length=200, blank=True, default="")
    category = models.CharField(max_length=20, blank=True, default="")
    designation = models.CharField(max_length=200, blank=True, default="")
    scale = models.CharField(max_length=100, blank=True, default="")

    dob = models.DateField(null=True, blank=True)
    dod = models.DateField(null=True, blank=True)
    fp_dob = models.DateField(null=True, blank=True)
    dor = models.DateField(null=True, blank=True)

    # Last inclusive day of enhanced / double FP (50%); family starts next day.
    enhanced_upto = models.DateField(null=True, blank=True)
    family_from = models.DateField(null=True, blank=True)
    die_in_harness = models.BooleanField(default=False)

    status = models.CharField(
        max_length=16, choices=STATUS_CHOICES, default=STATUS_CALCULATED, db_index=True
    )
    status_reason = models.CharField(max_length=255, blank=True, default="")
    version_no = models.PositiveIntegerField(default=1)

    # Convenience: payable for "today" from current rate row.
    payable_basic = models.DecimalField(
        max_digits=14, decimal_places=2, null=True, blank=True
    )
    payable_with_oa = models.DecimalField(
        max_digits=14, decimal_places=2, null=True, blank=True
    )
    cpi_point = models.PositiveIntegerField(null=True, blank=True)

    snapshot_met2_id = models.PositiveIntegerField(null=True, blank=True)
    snapshot_oa_id = models.PositiveIntegerField(null=True, blank=True)

    calculated_at = models.DateTimeField(null=True, blank=True)
    calculated_by = models.CharField(max_length=80, blank=True, default="")
    status_at = models.DateTimeField(null=True, blank=True)
    status_by = models.CharField(max_length=80, blank=True, default="")
    approved_at = models.DateTimeField(null=True, blank=True)
    approved_by = models.CharField(max_length=80, blank=True, default="")
    released_at = models.DateTimeField(null=True, blank=True)
    released_by = models.CharField(max_length=80, blank=True, default="")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "m2_consol_case"
        verbose_name = "M2 consolidation case"
        ordering = ["-updated_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["emp_cd", "source_app"],
                name="uniq_m2_consol_case_emp_source",
            )
        ]

    def __str__(self):
        return f"{self.emp_cd}/{self.source_app} v{self.version_no} [{self.status}]"


class M2ConsolRate(models.Model):
    """
    Bill-facing rate period.

    Example DIH: ENHANCED_FP 50% valid_to=2026-09-30, then FAMILY 30% from next day.
    """

    KIND_EMPLOYEE = "EMPLOYEE"
    KIND_ENHANCED = "ENHANCED_FP"
    KIND_FAMILY = "FAMILY"
    KIND_CHOICES = [
        (KIND_EMPLOYEE, "Employee pension (50%)"),
        (KIND_ENHANCED, "Enhanced / double FP (50%)"),
        (KIND_FAMILY, "Family pension (30%)"),
    ]

    case = models.ForeignKey(
        M2ConsolCase, on_delete=models.CASCADE, related_name="rates"
    )
    seq_no = models.PositiveIntegerField(default=1)
    cpi_point = models.PositiveIntegerField()
    rate_kind = models.CharField(max_length=16, choices=KIND_CHOICES)
    rate_pct = models.DecimalField(max_digits=5, decimal_places=2, default=50)

    # Inclusive validity. valid_to NULL = open-ended.
    valid_from = models.DateField()
    valid_to = models.DateField(null=True, blank=True)

    m2_amount = models.DecimalField(
        max_digits=14, decimal_places=2, null=True, blank=True
    )
    m1_amount = models.DecimalField(
        max_digits=14, decimal_places=2, null=True, blank=True
    )
    payable_amount = models.DecimalField(
        max_digits=14, decimal_places=2, null=True, blank=True
    )
    beneficial = models.CharField(max_length=10, blank=True, default="")
    diff_amount = models.DecimalField(
        max_digits=14, decimal_places=2, null=True, blank=True
    )

    oa_percent = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True
    )
    oa_benefit = models.DecimalField(
        max_digits=14, decimal_places=2, null=True, blank=True
    )
    payable_with_oa = models.DecimalField(
        max_digits=14, decimal_places=2, null=True, blank=True
    )

    period_note = models.CharField(max_length=255, blank=True, default="")
    is_current = models.BooleanField(default=False, db_index=True)

    class Meta:
        db_table = "m2_consol_rate"
        verbose_name = "M2 consolidation rate period"
        ordering = ["case_id", "cpi_point", "seq_no", "valid_from"]
        indexes = [
            models.Index(
                fields=["case", "valid_from", "valid_to"],
                name="m2_rate_case_validity_idx",
            ),
        ]

    def __str__(self):
        to_s = self.valid_to.isoformat() if self.valid_to else "open"
        return (
            f"{self.rate_kind}@{self.rate_pct}% "
            f"{self.valid_from}→{to_s} CPI{self.cpi_point}"
        )


class M2ConsolCheck(models.Model):
    """Manual verification step (DOB → Met1 → payable)."""

    RESULT_PENDING = "PENDING"
    RESULT_PASS = "PASS"
    RESULT_FAIL = "FAIL"
    RESULT_NA = "NA"
    RESULT_CHOICES = [
        (RESULT_PENDING, "Pending"),
        (RESULT_PASS, "Pass"),
        (RESULT_FAIL, "Fail"),
        (RESULT_NA, "N/A"),
    ]

    case = models.ForeignKey(
        M2ConsolCase, on_delete=models.CASCADE, related_name="checks"
    )
    step_code = models.CharField(max_length=32)
    step_label = models.CharField(max_length=120)
    result = models.CharField(
        max_length=10, choices=RESULT_CHOICES, default=RESULT_PENDING
    )
    remark = models.CharField(max_length=255, blank=True, default="")
    checked_by = models.CharField(max_length=80, blank=True, default="")
    checked_at = models.DateTimeField(null=True, blank=True)
    sort_order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        db_table = "m2_consol_check"
        verbose_name = "M2 consolidation check step"
        ordering = ["case_id", "sort_order", "step_code"]
        constraints = [
            models.UniqueConstraint(
                fields=["case", "step_code"],
                name="uniq_m2_consol_check_step",
            )
        ]

    def __str__(self):
        return f"{self.step_code}={self.result}"


class M2ConsolEvent(models.Model):
    """Audit / day-wise report events."""

    case = models.ForeignKey(
        M2ConsolCase,
        on_delete=models.CASCADE,
        related_name="events",
        null=True,
        blank=True,
    )
    emp_cd = models.CharField(max_length=5, db_index=True)
    source_app = models.CharField(max_length=8, blank=True, default="")
    event_type = models.CharField(max_length=32, db_index=True)
    from_status = models.CharField(max_length=16, blank=True, default="")
    to_status = models.CharField(max_length=16, blank=True, default="")
    event_at = models.DateTimeField(db_index=True)
    event_by = models.CharField(max_length=80, blank=True, default="")
    note = models.CharField(max_length=255, blank=True, default="")
    payload_json = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = "m2_consol_event"
        verbose_name = "M2 consolidation event"
        ordering = ["-event_at", "-id"]
        indexes = [
            models.Index(
                fields=["event_at", "event_type"],
                name="m2_event_day_type_idx",
            ),
        ]

    def __str__(self):
        return f"{self.emp_cd} {self.event_type} @ {self.event_at}"


class M2ConsolReleaseLog(models.Model):
    """Audit of amounts pushed toward NABA master (ORG_PENSIO etc.)."""

    case = models.ForeignKey(
        M2ConsolCase,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="release_logs",
    )
    emp_cd = models.CharField(max_length=5, db_index=True)
    roll_no = models.CharField(max_length=30, blank=True, default="")
    old_org_pensio = models.DecimalField(
        max_digits=14, decimal_places=2, null=True, blank=True
    )
    new_org_pensio = models.DecimalField(
        max_digits=14, decimal_places=2, null=True, blank=True
    )
    old_pay_pensio = models.DecimalField(
        max_digits=14, decimal_places=2, null=True, blank=True
    )
    new_pay_pensio = models.DecimalField(
        max_digits=14, decimal_places=2, null=True, blank=True
    )
    old_cpi = models.PositiveIntegerField(null=True, blank=True)
    new_cpi = models.PositiveIntegerField(null=True, blank=True)
    naba_master_touched = models.BooleanField(default=False)
    released_at = models.DateTimeField()
    released_by = models.CharField(max_length=80, blank=True, default="")
    note = models.CharField(max_length=255, blank=True, default="")

    class Meta:
        db_table = "m2_consol_release_log"
        verbose_name = "M2 consolidation release log"
        ordering = ["-released_at", "-id"]

    def __str__(self):
        return f"{self.emp_cd} release {self.released_at}"
