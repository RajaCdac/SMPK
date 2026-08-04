from django.db import models
from django.conf import settings


class PensionCase(models.Model):

    # Employee Snapshot
    emp_code = models.CharField(max_length=20,unique=True)
    name = models.CharField(max_length=200)
    emp_class = models.CharField(max_length=20)
    birth_date = models.DateField()
    joining_date = models.DateField()
    retirement_date = models.DateField()
    designation = models.CharField(max_length=200)
    scale = models.CharField(max_length=100)
    last_basic = models.DecimalField(max_digits=12,decimal_places=2)

    # Pension Inputs
    no_pay_days = models.IntegerField(default=0)
    dies_non_days = models.IntegerField(default=0)
    no_pay_more_than_240_days = models.IntegerField(default=0)
    suspension_days = models.IntegerField(default=0)
    boys_serv_days = models.IntegerField(default=0)
    commutation_percent = models.DecimalField(max_digits=5, decimal_places=2, default=40)
    commutation_reason = models.CharField(max_length=200, blank=True, null=True )

    # Separation (synced with Oracle FI_XX_MH_EMP_ADM on process intake)
    separation_type = models.CharField(max_length=50, blank=True, default="")
    separation_date = models.DateField(null=True, blank=True)
    process_remarks = models.TextField(blank=True, default="")

    # Workflow
    status = models.CharField(max_length=50, default="INITIATED")
    current_stage = models.CharField(max_length=50, default="CLERK" )

    # Audit
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.SET_NULL, null=True, related_name="pension_created" )
    updated_by = models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.SET_NULL,null=True,blank=True, related_name="pension_updated" )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.emp_code


class PensionSummary(models.Model):
    pension_case = models.OneToOneField(PensionCase,on_delete=models.CASCADE,related_name="summary")
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
    pension_amount = models.DecimalField(max_digits=12,decimal_places=2,default=0)
    commutation_amount = models.DecimalField(max_digits=15,decimal_places=2,default=0)
    gratuity_amount = models.DecimalField( max_digits=15,decimal_places=2,default=0)
    pension_start_date = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.pension_case.emp_code
    
class CommutationApplication(models.Model):
    #CHOICES = ("1","At the time of Pension Proposal"),("2","After 1 Yr of Pension Proposal"),("3","Within 1 Yr of Pension Proposal"),("4","Commutation for Pay Revision")
    emp_cd = models.CharField(max_length=20,unique=True)
    appcn_no=models.IntegerField(default=0)
    application_time=models.IntegerField(default=1)
    comm_start_mnth=models.IntegerField(default=1)
    appcn_dt=models.DateField(auto_now=False)
    application_rcvd_dt=models.DateField(auto_now=False)
    impl_fpen_combill=models.CharField(max_length=50)
    commutation_dt=models.DateField(auto_now=False)
    restoration_dt=models.DateField(auto_now=False)
    commutation_per=models.IntegerField(default=0)
    mo_certificate_dt=models.DateField(auto_now=False)
    mo_certificate_ref=models.CharField(max_length=50)
    commutation_reasons=models.CharField(max_length=200)
    bank_cd = models.CharField(max_length=6, blank=True, default="")
    bank_desc = models.CharField(max_length=50, blank=True, default="")
    ca_no = models.CharField(max_length=50, blank=True, default="")
    ref_no = models.CharField(max_length=100, blank=True, default="")
    bill_no = models.CharField(max_length=50, blank=True, default="")
    sanction_parameter = models.CharField(max_length=200, blank=True, default="")
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.SET_NULL, null=True, related_name="commutation_created" )
    created_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=50, default="COMMUTATION INITIATED")
    current_stage = models.CharField(max_length=50, default="PENSION USER" )
    updated_by = models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.SET_NULL,null=True,blank=True, related_name="commutation_updated" )
    updated_at = models.DateTimeField(auto_now=True)
    def __str__(self):
        return self.emp_cd


class PensionProposal(models.Model):
    emp_cd = models.CharField(max_length=20, unique=True)
    emp_name = models.CharField(max_length=200, blank=True, default="")
    employee_status = models.CharField(max_length=50, default="EMPLOYEE")
    ca_number = models.CharField(max_length=50, blank=True, default="")
    pension_type = models.CharField(max_length=50, blank=True, default="")
    pension_proposal_no = models.CharField(max_length=50, blank=True, default="")
    eligible_double_family_pension = models.BooleanField(default=False)

    separation_type = models.CharField(max_length=50, blank=True, default="")
    separation_date = models.DateField(null=True, blank=True)
    implemented_year = models.IntegerField(null=True, blank=True)
    implemented_month = models.IntegerField(null=True, blank=True)
    service_tenure = models.CharField(max_length=100, blank=True, default="")

    pension_option = models.CharField(max_length=50, blank=True, default="")
    option_given_by = models.CharField(max_length=50, blank=True, default="")
    regn_no = models.CharField(max_length=50, blank=True, default="")
    regn_date = models.DateField(null=True, blank=True)
    start_month = models.IntegerField(null=True, blank=True)
    start_year = models.IntegerField(null=True, blank=True)
    pension_roll_no = models.CharField(max_length=50, blank=True, default="")
    pension_proposal_date = models.DateField(null=True, blank=True)
    double_family_pension_upto_date = models.DateField(null=True, blank=True)

    provisional_pension_pct = models.DecimalField(
        max_digits=7, decimal_places=2, null=True, blank=True
    )
    bank_cd = models.CharField(max_length=20, blank=True, default="")
    bank_name = models.CharField(max_length=200, blank=True, default="")
    account_no = models.CharField(max_length=50, blank=True, default="")

    vigilance_clearance_ref_no = models.CharField(max_length=100, blank=True, default="")
    vigilance_clearance_ref_dt = models.DateField(null=True, blank=True)
    lic_bank_cd = models.CharField(max_length=20, blank=True, default="")
    lic_bank_name = models.CharField(max_length=200, blank=True, default="")

    vr_ref_no = models.CharField(max_length=100, blank=True, default="")
    vr_ref_dt = models.DateField(null=True, blank=True)
    compassionate_allowance = models.CharField(max_length=50, blank=True, default="")
    quarter_status = models.CharField(max_length=50, blank=True, default="")
    nominee_eform = models.CharField(max_length=50, blank=True, default="")
    compassionate_allowance_amt = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True
    )

    port_city_resident = models.CharField(max_length=50, blank=True, default="")
    gratuity_option = models.CharField(max_length=50, blank=True, default="")
    retirement_cpi = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True
    )
    id_card_submitted = models.BooleanField(default=False)
    vigilance_cleared = models.BooleanField(default=False)
    incentive_holder = models.CharField(max_length=50, blank=True, default="")
    held_up_flag = models.CharField(max_length=50, blank=True, default="")
    held_gratuity_amt = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True
    )
    held_recovery_amt = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True
    )
    held_recovery_date = models.DateField(null=True, blank=True)
    held_recovery_ref_no = models.CharField(max_length=30, blank=True, default="")
    held_recovery_remarks = models.CharField(max_length=500, blank=True, default="")

    extra_tccs_enabled = models.BooleanField(default=False)
    extra_tccs_years = models.IntegerField(default=0)
    extra_tccs_months = models.IntegerField(default=0)
    extra_tccs_days = models.IntegerField(default=0)

    earning_deductions = models.JSONField(
        default=list,
        blank=True,
        help_text="Legacy JSON cache; canonical rows are in PensionProposalEarndedn.",
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="pension_proposal_created",
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="pension_proposal_updated",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.emp_cd} - {self.pension_proposal_no}"


class PensionProposalEarndedn(models.Model):
    """
    Proposal earn/dedn lines — Oracle FINANCE.FI_PN_MD_PENSION_PROPOSAL.
    PK: (CA_NUMBER, EARNDEDN_CD, EARN_DEDN_TYPE)
    """

    EARN = "E"
    DEDN = "D"
    TYPE_CHOICES = [
        (EARN, "Earning"),
        (DEDN, "Deduction"),
    ]

    pk = models.CompositePrimaryKey("ca_number", "earndedn_cd", "earn_dedn_type")
    ca_number = models.CharField(max_length=22, db_index=True)
    earndedn_cd = models.CharField(max_length=3)
    earn_dedn_type = models.CharField(max_length=1, choices=TYPE_CHOICES)
    amount = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    e_d_priority = models.PositiveSmallIntegerField(null=True, blank=True)
    deducted_amt = models.DecimalField(
        max_digits=14, decimal_places=2, null=True, blank=True
    )
    date_created = models.DateField(null=True, blank=True)
    created_by = models.CharField(max_length=5, blank=True, default="")
    date_modified = models.DateField(null=True, blank=True)
    modified_by = models.CharField(max_length=5, blank=True, default="")

    class Meta:
        db_table = "fi_pn_md_pension_proposal"
        verbose_name = "Pension proposal earn/dedn line"
        verbose_name_plural = "Pension proposal earn/dedn lines"
        ordering = ["ca_number", "earndedn_cd", "earn_dedn_type"]

    def __str__(self):
        return f"{self.ca_number} / {self.earndedn_cd}"


class DashboardMonthSnapshot(models.Model):
    """Month-level dashboard counts/labels synced from Oracle."""

    month = models.PositiveSmallIntegerField()
    year = models.PositiveIntegerField()
    total_employees = models.IntegerField(null=True, blank=True)
    prev_month_count = models.IntegerField(default=0)
    retirement_count = models.IntegerField(default=0)
    next_month_count = models.IntegerField(default=0)
    prev_month_label = models.CharField(max_length=64, blank=True)
    this_month_label = models.CharField(max_length=64, blank=True)
    next_month_label = models.CharField(max_length=64, blank=True)
    synced_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "first_pension_dashboard_snapshot"
        unique_together = [("month", "year")]
        indexes = [models.Index(fields=["year", "month"])]


class CachedRetirementEmployee(models.Model):
    """One retiring employee row for a given retirement month/year."""

    emp_code = models.CharField(max_length=20, db_index=True)
    retirement_month = models.PositiveSmallIntegerField()
    retirement_year = models.PositiveIntegerField()
    name = models.CharField(max_length=300, blank=True)
    joining_date = models.CharField(max_length=20, blank=True)
    retirement_date = models.CharField(max_length=20, blank=True)
    birth_date = models.CharField(max_length=20, blank=True)
    age_on_appointment = models.JSONField(null=True, blank=True)
    age_on_retirement = models.JSONField(null=True, blank=True)
    designation = models.CharField(max_length=300, blank=True)
    scale = models.CharField(max_length=100, blank=True)
    last_basic = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    emp_class = models.CharField(max_length=20, blank=True)
    row_payload = models.JSONField(default=dict)
    synced_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "first_pension_cached_retirement_emp"
        unique_together = [("emp_code", "retirement_month", "retirement_year")]
        indexes = [models.Index(fields=["retirement_year", "retirement_month"])]


class CachedEmployeeOracleDetail(models.Model):
    """Last successful Oracle employee lookup (merged with fresh MySQL on read)."""

    emp_code = models.CharField(max_length=20, unique=True, db_index=True)
    payload = models.JSONField(default=dict)
    synced_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "first_pension_cached_employee_oracle"


from .oracle_mirror import (  # noqa: E402, F401
    FiPnMhApplication,
    FiPnMhOldbillParam,
    FiPnMhPmthsetup,
    FiPnMhPensionProposal,
    FiPnMhPensioner,
    FiPnTdFirstMonthPension,
    FiPnTdSalout,
    FiPnThFirstMonthPension,
    FiPnThPensionBill,
)