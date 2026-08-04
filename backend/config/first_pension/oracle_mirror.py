"""MySQL mirrors of Oracle FINANCE pension workflow tables (Wave 2)."""

from django.db import models


class FiPnMhPensionProposal(models.Model):
    """Oracle FINANCE.FI_PN_MH_PENSION_PROPOSAL — proposal header (PK: CA_NUMBER)."""

    ca_number = models.CharField(max_length=22, primary_key=True)
    emp_cd = models.CharField(max_length=5, db_index=True)
    pension_type = models.CharField(max_length=1)
    pension_proposal_no = models.CharField(max_length=30)
    pension_proposal_dt = models.DateField()
    impl_month = models.IntegerField(null=True, blank=True)
    impl_yr = models.IntegerField(null=True, blank=True)
    start_month = models.IntegerField(null=True, blank=True)
    start_yr = models.IntegerField(null=True, blank=True)
    employee_status = models.CharField(max_length=1)
    vigilance_clearance_tag = models.CharField(max_length=1)
    vigilance_clearance_ref_no = models.CharField(max_length=22, blank=True, default="")
    vigilance_clearance_ref_dt = models.DateField(null=True, blank=True)
    prov_pen_percentage = models.DecimalField(
        max_digits=14, decimal_places=4, null=True, blank=True
    )
    quarter_status = models.CharField(max_length=1, blank=True, default="")
    pension_option = models.CharField(max_length=1)
    pension_roll_no = models.CharField(max_length=22, blank=True, default="")
    id_card_submitted = models.CharField(max_length=1)
    port_city_resident = models.CharField(max_length=1)
    separation_type = models.CharField(max_length=3, blank=True, default="")
    separation_dt = models.DateField()
    date_created = models.DateField(null=True, blank=True)
    created_by = models.CharField(max_length=5, blank=True, default="")
    date_modified = models.DateField(null=True, blank=True)
    modified_by = models.CharField(max_length=5, blank=True, default="")
    comp_allowance_check_tag = models.IntegerField(null=True, blank=True)
    comp_allowance = models.DecimalField(
        max_digits=14, decimal_places=2, null=True, blank=True
    )
    gratuity_option = models.IntegerField(null=True, blank=True)
    bank_cd = models.CharField(max_length=6, blank=True, default="")
    double_fpen_eligibility = models.IntegerField(null=True, blank=True)
    double_fpen_upto = models.DateField(null=True, blank=True)
    base_cpi = models.DecimalField(max_digits=14, decimal_places=4, null=True, blank=True)
    extra_grat_tccs_flg = models.CharField(max_length=1, blank=True, default="")
    extra_grat_tccs_days = models.IntegerField(null=True, blank=True)
    extra_grat_tccs_mon = models.IntegerField(null=True, blank=True)
    extra_grat_tccs_yr = models.IntegerField(null=True, blank=True)
    incentive_holder_flg = models.CharField(max_length=1, blank=True, default="")
    held_grat_flg = models.CharField(max_length=1, blank=True, default="")
    held_grat_amt = models.DecimalField(
        max_digits=14, decimal_places=2, null=True, blank=True
    )
    lic_bank_cd = models.CharField(max_length=6, blank=True, default="")
    regn_no = models.CharField(max_length=22, blank=True, default="")
    regn_date = models.DateField(null=True, blank=True)
    account_no = models.CharField(max_length=20, blank=True, default="")
    opt_given_by = models.CharField(max_length=1, blank=True, default="")
    nomin_eform_grat_flg = models.CharField(max_length=1, blank=True, default="")
    vr_ref_no = models.CharField(max_length=30, blank=True, default="")
    vr_ref_dt = models.DateField(null=True, blank=True)
    letter_no = models.CharField(max_length=15, blank=True, default="")
    acepted_dt = models.DateField(null=True, blank=True)
    dcr_type = models.CharField(max_length=10, blank=True, default="")
    held_commu_amt = models.DecimalField(
        max_digits=14, decimal_places=2, null=True, blank=True
    )

    class Meta:
        db_table = "fi_pn_mh_pension_proposal"
        verbose_name = "Pension proposal header (Oracle mirror)"
        ordering = ["-pension_proposal_dt", "emp_cd"]

    def __str__(self):
        return f"{self.ca_number} / {self.emp_cd}"


class FiPnMhApplication(models.Model):
    """Oracle FINANCE.FI_PN_MH_APPLICATION — commutation / pension application."""

    pk = models.CompositePrimaryKey("emp_cd", "appcn_no", "appcn_dt")
    emp_cd = models.CharField(max_length=5, db_index=True)
    appcn_no = models.CharField(max_length=22)
    appcn_dt = models.DateField()
    ref_no = models.CharField(max_length=22, blank=True, default="")
    pen_amt = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    commutation_per = models.DecimalField(
        max_digits=14, decimal_places=4, null=True, blank=True
    )
    sanction_particulars = models.CharField(max_length=500, blank=True, default="")
    commutation_reasons = models.CharField(max_length=500, blank=True, default="")
    prev_comm_particulars = models.CharField(max_length=500, blank=True, default="")
    avg_expected_life = models.CharField(max_length=240, blank=True, default="")
    date_created = models.DateField(null=True, blank=True)
    created_by = models.CharField(max_length=5, blank=True, default="")
    date_modified = models.DateField(null=True, blank=True)
    modified_by = models.CharField(max_length=5, blank=True, default="")
    comm_start_mnth = models.IntegerField(null=True, blank=True)
    comm_start_yr = models.IntegerField(null=True, blank=True)
    impl_bill_no = models.CharField(max_length=22, blank=True, default="")
    mo_certificate_ref = models.CharField(max_length=20, blank=True, default="")
    mo_certification_dt = models.DateField(null=True, blank=True)
    application_rcvd_dt = models.DateField(null=True, blank=True)
    commutation_date = models.DateField(null=True, blank=True)
    commutation_amt = models.DecimalField(
        max_digits=14, decimal_places=2, null=True, blank=True
    )
    impl_fpen_combill = models.CharField(max_length=3, blank=True, default="")
    bank_cd = models.CharField(max_length=6, blank=True, default="")
    ca_no = models.CharField(max_length=22, blank=True, default="")
    restoration_dt = models.DateField(null=True, blank=True)
    restoration_flg = models.IntegerField(null=True, blank=True)
    application_time = models.IntegerField(null=True, blank=True)

    class Meta:
        db_table = "fi_pn_mh_application"
        verbose_name = "Pension application (Oracle mirror)"
        ordering = ["-appcn_dt", "emp_cd"]

    def __str__(self):
        return f"{self.emp_cd} / {self.appcn_no}"


class FiPnMhOldbillParam(models.Model):
    """Oracle FINANCE.FI_PN_MH_OLDBILL_PARAM — no-pay / TQS parameters."""

    emp_cd = models.CharField(max_length=5, primary_key=True)
    appointment_dt = models.DateField(null=True, blank=True)
    retirement_dt = models.DateField(null=True, blank=True)
    boy_serv_days = models.IntegerField(null=True, blank=True)
    birth_dt = models.DateField(null=True, blank=True)
    dnon_days = models.IntegerField(null=True, blank=True)
    edn_lv_days = models.IntegerField(null=True, blank=True)
    npay_prior_10mth = models.IntegerField(null=True, blank=True)
    susp_days = models.IntegerField(null=True, blank=True)
    npay_morethan_240_dys = models.IntegerField(null=True, blank=True)

    class Meta:
        db_table = "fi_pn_mh_oldbill_param"
        verbose_name = "Old bill param (Oracle mirror)"
        ordering = ["emp_cd"]

    def __str__(self):
        return self.emp_cd


class FiPnThSalout(models.Model):
    """Oracle FINANCE.FI_PN_TH_SALOUT — pension salary output header (10-month window)."""

    pk = models.CompositePrimaryKey("emp_cd", "sal_mth", "sal_yr")
    emp_cd = models.CharField(max_length=5, db_index=True)
    sal_mth = models.IntegerField()
    sal_yr = models.IntegerField()
    fa_no = models.CharField(max_length=10, blank=True, default="")
    sal_bill_no = models.CharField(max_length=22, blank=True, default="")
    gross_earn_amt = models.DecimalField(
        max_digits=14, decimal_places=2, null=True, blank=True
    )
    gross_dedn_amt = models.DecimalField(
        max_digits=14, decimal_places=2, null=True, blank=True
    )
    net_earn_amt = models.DecimalField(
        max_digits=14, decimal_places=2, null=True, blank=True
    )
    scale_desc = models.CharField(max_length=100, blank=True, default="")
    basic_rate = models.DecimalField(
        max_digits=14, decimal_places=2, null=True, blank=True
    )
    wg_st_dt = models.DateField(null=True, blank=True)
    wg_end_dt = models.DateField(null=True, blank=True)
    date_created = models.DateField(null=True, blank=True)
    date_modified = models.DateField(null=True, blank=True)
    modified_by = models.CharField(max_length=5, blank=True, default="")
    created_by = models.CharField(max_length=5, blank=True, default="")

    class Meta:
        db_table = "fi_pn_th_salout"
        verbose_name = "Pension salout header (Oracle mirror)"
        ordering = ["emp_cd", "-sal_yr", "-sal_mth"]
        indexes = [
            models.Index(fields=["emp_cd", "sal_yr", "sal_mth"]),
        ]

    def __str__(self):
        return f"{self.emp_cd} {self.sal_mth}/{self.sal_yr} basic={self.basic_rate}"


class FiPnTdSalout(models.Model):
    """Oracle FINANCE.FI_PN_TD_SALOUT — pension salary output lines."""

    pk = models.CompositePrimaryKey("emp_cd", "sal_mth", "sal_yr", "earndedn_cd")
    emp_cd = models.CharField(max_length=5, db_index=True)
    sal_mth = models.IntegerField()
    sal_yr = models.IntegerField()
    earndedn_cd = models.CharField(max_length=3)
    earndedn_type = models.CharField(max_length=1, blank=True, default="")
    no_of_units = models.DecimalField(max_digits=14, decimal_places=4, null=True, blank=True)
    rate = models.DecimalField(max_digits=14, decimal_places=4, null=True, blank=True)
    rate_pct_flg = models.IntegerField(null=True, blank=True)
    act_earndedn_amt = models.DecimalField(
        max_digits=14, decimal_places=2, null=True, blank=True
    )
    adj_earndedn_amt = models.DecimalField(
        max_digits=14, decimal_places=2, null=True, blank=True
    )
    arr_earn_amt = models.DecimalField(
        max_digits=14, decimal_places=2, null=True, blank=True
    )
    date_created = models.DateField(null=True, blank=True)
    date_modified = models.DateField(null=True, blank=True)
    modified_by = models.CharField(max_length=5, blank=True, default="")
    created_by = models.CharField(max_length=5, blank=True, default="")
    spl_pay = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)

    class Meta:
        db_table = "fi_pn_td_salout"
        verbose_name = "Pension salout line (Oracle mirror)"
        ordering = ["emp_cd", "-sal_yr", "-sal_mth", "earndedn_cd"]
        indexes = [
            models.Index(fields=["emp_cd", "sal_yr", "sal_mth"]),
        ]

    def __str__(self):
        return f"{self.emp_cd} {self.sal_mth}/{self.sal_yr} {self.earndedn_cd}"


class FiPrThSalout(models.Model):
    """Oracle FINANCE.FI_PR_TH_SALOUT — payroll salary output header."""

    pk = models.CompositePrimaryKey("emp_cd", "sal_mth", "sal_yr")
    emp_cd = models.CharField(max_length=5, db_index=True)
    sal_mth = models.IntegerField()
    sal_yr = models.IntegerField()
    fa_no = models.CharField(max_length=5, blank=True, default="")
    sal_bill_no = models.CharField(max_length=20, blank=True, default="")
    gross_earn_amt = models.DecimalField(
        max_digits=14, decimal_places=2, null=True, blank=True
    )
    gross_dedn_amt = models.DecimalField(
        max_digits=14, decimal_places=2, null=True, blank=True
    )
    net_earn_amt = models.DecimalField(
        max_digits=14, decimal_places=2, null=True, blank=True
    )
    scale_desc = models.CharField(max_length=40, blank=True, default="")
    basic_rate = models.DecimalField(
        max_digits=14, decimal_places=2, null=True, blank=True
    )
    wg_st_dt = models.DateField(null=True, blank=True)
    wg_end_dt = models.DateField(null=True, blank=True)
    date_created = models.DateField(null=True, blank=True)
    date_modified = models.DateField(null=True, blank=True)
    modified_by = models.CharField(max_length=5, blank=True, default="")
    created_by = models.CharField(max_length=5, blank=True, default="")

    class Meta:
        db_table = "fi_pr_th_salout"
        verbose_name = "Payroll salout header (Oracle mirror)"
        ordering = ["emp_cd", "-sal_yr", "-sal_mth"]
        indexes = [
            models.Index(fields=["emp_cd", "sal_yr", "sal_mth"]),
        ]

    def __str__(self):
        return f"{self.emp_cd} {self.sal_mth}/{self.sal_yr} basic={self.basic_rate}"


class FiPrTdSalout(models.Model):
    """Oracle FINANCE.FI_PR_TD_SALOUT — payroll salary output lines."""

    pk = models.CompositePrimaryKey("emp_cd", "sal_mth", "sal_yr", "earndedn_cd")
    emp_cd = models.CharField(max_length=5, db_index=True)
    sal_mth = models.IntegerField()
    sal_yr = models.IntegerField()
    earndedn_cd = models.CharField(max_length=3)
    earndedn_type = models.CharField(max_length=1, blank=True, default="")
    no_of_units = models.DecimalField(max_digits=14, decimal_places=4, null=True, blank=True)
    rate = models.DecimalField(max_digits=14, decimal_places=4, null=True, blank=True)
    rate_pct_flg = models.IntegerField(null=True, blank=True)
    act_earndedn_amt = models.DecimalField(
        max_digits=14, decimal_places=2, null=True, blank=True
    )
    adj_earndedn_amt = models.DecimalField(
        max_digits=14, decimal_places=2, null=True, blank=True
    )
    arr_earn_amt = models.DecimalField(
        max_digits=14, decimal_places=2, null=True, blank=True
    )
    notional_amount = models.DecimalField(
        max_digits=14, decimal_places=2, null=True, blank=True
    )
    date_created = models.DateField(null=True, blank=True)
    date_modified = models.DateField(null=True, blank=True)
    modified_by = models.CharField(max_length=5, blank=True, default="")
    created_by = models.CharField(max_length=5, blank=True, default="")

    class Meta:
        db_table = "fi_pr_td_salout"
        verbose_name = "Payroll salout line (Oracle mirror)"
        ordering = ["emp_cd", "-sal_yr", "-sal_mth", "earndedn_cd"]
        indexes = [
            models.Index(fields=["emp_cd", "sal_yr", "sal_mth"]),
        ]

    def __str__(self):
        return f"{self.emp_cd} {self.sal_mth}/{self.sal_yr} {self.earndedn_cd}"


class FiPnThFirstMonthPension(models.Model):
    """Oracle FINANCE.FI_PN_TH_FIRST_MONTH_PENSION — first-month pension bill header."""

    fmpen_id = models.CharField(max_length=22, primary_key=True)
    pension_type = models.CharField(max_length=3)
    pension_month = models.IntegerField()
    pension_yr = models.IntegerField()
    ca_no = models.CharField(max_length=22, db_index=True)
    ca_date = models.DateField(null=True, blank=True)
    original_fpension_amt = models.DecimalField(
        max_digits=14, decimal_places=2, null=True, blank=True
    )
    payable_pension = models.DecimalField(
        max_digits=14, decimal_places=2, null=True, blank=True
    )
    date_of_execution = models.DateField(null=True, blank=True)
    bill_no = models.CharField(max_length=22, blank=True, default="")
    paid_month = models.IntegerField(null=True, blank=True)
    paid_year = models.IntegerField(null=True, blank=True)
    date_created = models.DateField(null=True, blank=True)
    created_by = models.CharField(max_length=5, blank=True, default="")
    date_modified = models.DateField(null=True, blank=True)
    modified_by = models.CharField(max_length=5, blank=True, default="")
    emp_cd = models.CharField(max_length=5, db_index=True)
    bank_cd = models.CharField(max_length=6, blank=True, default="")
    sys_man_tag = models.CharField(max_length=1, blank=True, default="")
    cpi_no = models.DecimalField(max_digits=14, decimal_places=4, null=True, blank=True)
    nomin_type = models.CharField(max_length=2, blank=True, default="")
    pen_proc_tag = models.CharField(max_length=1, blank=True, default="")
    nomin_srl_no = models.IntegerField(null=True, blank=True)
    base_cpi = models.DecimalField(max_digits=14, decimal_places=4, null=True, blank=True)
    payment_tag = models.CharField(max_length=2, blank=True, default="")
    lic_bank_cd = models.CharField(max_length=6, blank=True, default="")

    class Meta:
        db_table = "fi_pn_th_first_month_pension"
        verbose_name = "First-month pension header"
        ordering = ["-pension_yr", "-pension_month", "emp_cd"]
        indexes = [
            models.Index(fields=["emp_cd", "pension_yr", "pension_month"]),
        ]

    def __str__(self):
        return self.fmpen_id


class FiPnTdFirstMonthPension(models.Model):
    """Oracle FINANCE.FI_PN_TD_FIRST_MONTH_PENSION — first-month earn/dedn detail."""

    EARN = "E"
    DEDN = "D"

    pk = models.CompositePrimaryKey(
        "fmpen_id", "earn_dedn_cd", "earn_dedn_type"
    )
    fmpen_id = models.CharField(max_length=22, db_index=True)
    earn_dedn_type = models.CharField(max_length=1)
    earn_dedn_cd = models.CharField(max_length=3)
    amount = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    emp_cd = models.CharField(max_length=5, db_index=True)
    original_amt = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    # Oracle column is AREAR_AMT (legacy spelling).
    arrear_amt = models.DecimalField(
        max_digits=14, decimal_places=2, null=True, blank=True, db_column="AREAR_AMT"
    )
    date_created = models.DateField(null=True, blank=True)
    created_by = models.CharField(max_length=5, blank=True, default="")
    date_modified = models.DateField(null=True, blank=True)
    modified_by = models.CharField(max_length=5, blank=True, default="")

    class Meta:
        db_table = "fi_pn_td_first_month_pension"
        verbose_name = "First-month pension detail"
        ordering = ["fmpen_id", "earn_dedn_type", "earn_dedn_cd"]

    def __str__(self):
        return f"{self.fmpen_id} {self.earn_dedn_cd}"


class FiPnMhPensioner(models.Model):
    """Oracle FINANCE.FI_PN_MH_PENSIONER — pensioner master (PK: CA_NUMBER)."""

    ca_number = models.CharField(max_length=22, primary_key=True)
    emp_cd = models.CharField(max_length=5, db_index=True)
    original_pension_amt = models.DecimalField(
        max_digits=14, decimal_places=2, null=True, blank=True
    )
    effective_stdt_pension = models.DateField(null=True, blank=True)
    commuted_portion = models.DecimalField(
        max_digits=14, decimal_places=2, null=True, blank=True
    )
    payable_pension = models.DecimalField(
        max_digits=14, decimal_places=2, null=True, blank=True
    )
    gratuity = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    commutation_per = models.DecimalField(
        max_digits=7, decimal_places=2, null=True, blank=True
    )
    relief = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    pension_emoluments = models.DecimalField(
        max_digits=14, decimal_places=2, null=True, blank=True
    )
    gratuity_emoluments = models.DecimalField(
        max_digits=14, decimal_places=2, null=True, blank=True
    )
    tccs_yr = models.IntegerField(null=True, blank=True)
    tccs_month = models.IntegerField(null=True, blank=True)
    tccs_days = models.IntegerField(null=True, blank=True)
    tqs_yr = models.IntegerField(null=True, blank=True)
    tqs_month = models.IntegerField(null=True, blank=True)
    tqs_days = models.IntegerField(null=True, blank=True)
    name = models.CharField(max_length=62, blank=True, default="")
    pension_option = models.CharField(max_length=1, blank=True, default="")
    base_cpi = models.DecimalField(max_digits=14, decimal_places=4, null=True, blank=True)
    bank_cd = models.CharField(max_length=6, blank=True, default="")
    lic_bank_cd = models.CharField(max_length=6, blank=True, default="")
    account_no = models.CharField(max_length=20, blank=True, default="")
    pension_roll_no = models.CharField(max_length=22, blank=True, default="")
    sex = models.CharField(max_length=1, blank=True, default="")
    dob = models.DateField(null=True, blank=True)
    desig_cd = models.IntegerField(null=True, blank=True)
    emp_ret_dt = models.DateField(null=True, blank=True)
    app_class = models.IntegerField(null=True, blank=True)
    date_commutation = models.DateField(null=True, blank=True)
    date_created = models.DateField(null=True, blank=True)
    created_by = models.CharField(max_length=5, blank=True, default="")
    date_modified = models.DateField(null=True, blank=True)
    modified_by = models.CharField(max_length=5, blank=True, default="")

    class Meta:
        db_table = "fi_pn_mh_pensioner"
        verbose_name = "Pensioner master"
        ordering = ["-date_created", "emp_cd"]

    def __str__(self):
        return f"{self.ca_number} / {self.emp_cd}"


class FiPnThPensionBill(models.Model):
    """Oracle FINANCE.FI_PN_TH_PENSION_BILL — consolidated bank pension bill."""

    bill_no = models.CharField(max_length=22, primary_key=True)
    bill_type = models.CharField(max_length=3)
    bill_month = models.IntegerField()
    bill_yr = models.IntegerField()
    bank_cd = models.CharField(max_length=6, blank=True, default="")
    total_amt_earned = models.DecimalField(
        max_digits=14, decimal_places=2, null=True, blank=True
    )
    total_amt_deducted = models.DecimalField(
        max_digits=14, decimal_places=2, null=True, blank=True
    )
    bill_abstract_no = models.CharField(max_length=22, blank=True, default="")
    abstract_type = models.CharField(max_length=2, blank=True, default="")
    cheque_no = models.IntegerField(null=True, blank=True)
    cheque_dt = models.DateField(null=True, blank=True)
    cheque_amt = models.DecimalField(
        max_digits=14, decimal_places=2, null=True, blank=True
    )
    date_created = models.DateField(null=True, blank=True)
    created_by = models.CharField(max_length=5, blank=True, default="")
    date_modified = models.DateField(null=True, blank=True)
    modified_by = models.CharField(max_length=5, blank=True, default="")
    remarks = models.CharField(max_length=100, blank=True, default="")
    voucher_no = models.CharField(max_length=25, blank=True, default="")
    abstract_date = models.DateField(null=True, blank=True)
    gen_lic_tag = models.CharField(max_length=1, blank=True, default="")
    posted = models.CharField(max_length=1, blank=True, default="")
    posted_on = models.DateField(null=True, blank=True)
    posted_by = models.CharField(max_length=5, blank=True, default="")

    class Meta:
        db_table = "fi_pn_th_pension_bill"
        verbose_name = "Pension bill header"
        ordering = ["-bill_yr", "-bill_month", "bill_no"]
        indexes = [
            models.Index(fields=["bill_yr", "bill_month", "bill_type"]),
        ]

    def __str__(self):
        return self.bill_no


class FiPnMhPmthsetup(models.Model):
    """Oracle FINANCE.FI_PN_MH_PMTHSETUP — pension bill month control flags."""

    pk = models.CompositePrimaryKey("bill_type", "bill_mth", "bill_yr")
    bill_type = models.CharField(max_length=3)
    bill_mth = models.IntegerField()
    bill_yr = models.IntegerField()
    bill_process_flg = models.IntegerField(default=0)
    bill_close_flg = models.IntegerField(default=0)
    date_created = models.DateField(null=True, blank=True)
    created_by = models.CharField(max_length=5, blank=True, default="")
    date_modified = models.DateField(null=True, blank=True)
    modified_by = models.CharField(max_length=5, blank=True, default="")

    class Meta:
        db_table = "fi_pn_mh_pmthsetup"
        verbose_name = "Pension bill month setup"
        ordering = ["-bill_yr", "-bill_mth", "bill_type"]

    def __str__(self):
        return f"{self.bill_type} {self.bill_mth}/{self.bill_yr}"


class FiPnThJv(models.Model):
    """Oracle FINANCE.FI_PN_TH_JV — pension journal voucher header (MySQL)."""

    voucher_no = models.CharField(max_length=25, primary_key=True)
    yr = models.IntegerField()
    mth = models.IntegerField()
    voucher_dt = models.DateField()
    tran_type = models.CharField(max_length=10, blank=True, default="")
    ref_no = models.CharField(max_length=25, blank=True, default="", db_index=True)
    ref_dt = models.DateField(null=True, blank=True)
    narration = models.CharField(max_length=500, blank=True, default="")
    tot_amt = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    created_by = models.CharField(max_length=5, blank=True, default="")
    created_on = models.DateField(null=True, blank=True)
    voucher_for = models.CharField(max_length=1, blank=True, default="P")

    class Meta:
        db_table = "fi_pn_th_jv"
        verbose_name = "Pension journal voucher"
        ordering = ["-yr", "-mth", "voucher_no"]
        indexes = [
            models.Index(fields=["yr", "mth"]),
        ]

    def __str__(self):
        return self.voucher_no


class FiPnTdJv(models.Model):
    """Oracle FINANCE.FI_PN_TD_JV — pension journal voucher detail (MySQL)."""

    pk = models.CompositePrimaryKey("voucher_no", "sl_no")
    voucher_no = models.CharField(max_length=25, db_index=True)
    voucher_dt = models.DateField()
    yr = models.IntegerField()
    mth = models.IntegerField()
    sl_no = models.IntegerField()
    zonal_cd = models.IntegerField()
    aloc_cd1 = models.CharField(max_length=4)
    aloc_cd2 = models.CharField(max_length=4, blank=True, default="")
    aloc_cd3 = models.CharField(max_length=7, blank=True, default="")
    dr_cr_flag = models.CharField(max_length=1)
    type_cd = models.IntegerField(default=1)
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    ref = models.CharField(max_length=25, blank=True, default="")
    remarks = models.CharField(max_length=60, blank=True, default="")
    created_by = models.CharField(max_length=5, blank=True, default="")
    created_on = models.DateField(null=True, blank=True)

    class Meta:
        db_table = "fi_pn_td_jv"
        verbose_name = "Pension journal voucher line"
        ordering = ["voucher_no", "sl_no"]

    def __str__(self):
        return f"{self.voucher_no}#{self.sl_no}"


class FiPnThSepcom(models.Model):
    """Oracle FINANCE.FI_PN_TH_SEPCOM — separate commutation header (generation step)."""

    sepcom_id = models.CharField(max_length=22, primary_key=True)
    sepcom_month = models.IntegerField()
    sepcom_yr = models.IntegerField()
    ca_no = models.CharField(max_length=22, blank=True, default="")
    original_com_amt = models.DecimalField(
        max_digits=14, decimal_places=2, null=True, blank=True
    )
    bill_no = models.CharField(max_length=22, blank=True, default="")
    paid_month = models.IntegerField(null=True, blank=True)
    paid_year = models.IntegerField(null=True, blank=True)
    emp_cd = models.CharField(max_length=5, db_index=True)
    nomin_type = models.CharField(max_length=2, blank=True, default="")
    com_proc_tag = models.CharField(max_length=1, blank=True, default="C")
    nomin_srl_no = models.IntegerField(default=0)
    date_created = models.DateField(null=True, blank=True)
    created_by = models.CharField(max_length=5, blank=True, default="")
    date_modified = models.DateField(null=True, blank=True)
    modified_by = models.CharField(max_length=5, blank=True, default="")
    bank_cd = models.CharField(max_length=6, blank=True, default="")
    pen_dedn_amt = models.DecimalField(
        max_digits=14, decimal_places=2, null=True, blank=True
    )
    appcn_no = models.CharField(max_length=22, blank=True, default="")
    appcn_dt = models.DateField(null=True, blank=True)

    class Meta:
        db_table = "fi_pn_th_sepcom"
        verbose_name = "Separate commutation header"
        ordering = ["-sepcom_yr", "-sepcom_month", "sepcom_id"]
        indexes = [
            models.Index(fields=["emp_cd", "sepcom_yr", "sepcom_month"]),
            models.Index(fields=["bill_no"]),
        ]

    def __str__(self):
        return f"{self.sepcom_id} / {self.emp_cd}"


class FiPnTdSepcom(models.Model):
    """Oracle FINANCE.FI_PN_TD_SEPCOM — separate commutation earn/dedn lines."""

    pk = models.CompositePrimaryKey("sepcom_id", "earn_dedn_cd", "earn_dedn_type")
    earn_dedn_type = models.CharField(max_length=1)
    earn_dedn_cd = models.CharField(max_length=3)
    amount = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    date_created = models.DateField(null=True, blank=True)
    created_by = models.CharField(max_length=5, blank=True, default="")
    date_modified = models.DateField(null=True, blank=True)
    modified_by = models.CharField(max_length=5, blank=True, default="")
    sepcom_id = models.CharField(max_length=22, db_index=True)
    emp_cd = models.CharField(max_length=5, db_index=True)
    original_amt = models.DecimalField(
        max_digits=14, decimal_places=2, null=True, blank=True
    )
    arrear_amt = models.DecimalField(
        max_digits=14, decimal_places=2, null=True, blank=True, default=0,
        db_column="AREAR_AMT",
    )

    class Meta:
        db_table = "fi_pn_td_sepcom"
        verbose_name = "Separate commutation detail"
        ordering = ["sepcom_id", "earn_dedn_type", "earn_dedn_cd"]

    def __str__(self):
        return f"{self.sepcom_id} {self.earn_dedn_cd}"


class FiPnMdCommrateRupee(models.Model):
    """Oracle FINANCE.FI_PN_MD_COMMRATE_RUPEE — commutation rate per rupee by age."""

    pk = models.CompositePrimaryKey("age_yrs", "wef_dt")
    age_yrs = models.IntegerField(db_index=True)
    wef_dt = models.DateField()
    amt_per_rupee = models.DecimalField(
        max_digits=14, decimal_places=6, null=True, blank=True
    )
    date_created = models.DateField(null=True, blank=True)
    created_by = models.CharField(max_length=5, blank=True, default="")
    date_modified = models.DateField(null=True, blank=True)
    modified_by = models.CharField(max_length=5, blank=True, default="")

    class Meta:
        db_table = "fi_pn_md_commrate_rupee"
        managed = False
        verbose_name = "Commutation rate per rupee (age)"
        ordering = ["age_yrs", "-wef_dt"]

    def __str__(self):
        return f"age {self.age_yrs} @ {self.wef_dt}: {self.amt_per_rupee}"


class FiPrMhCalcDa(models.Model):
    """MySQL mirror of FINANCE.FI_PR_MH_CALC_DA — quarterly DA % by employee class group."""

    pk = models.CompositePrimaryKey("emp_type", "emp_class_grp", "wef_dt")
    incept_dt = models.DateTimeField(null=True, blank=True)
    emp_type = models.CharField(max_length=2)
    emp_class_grp = models.IntegerField()
    wef_dt = models.DateTimeField()
    da_pct = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    remarks = models.CharField(max_length=50, blank=True, default="")
    date_created = models.DateTimeField(null=True, blank=True)
    date_modified = models.DateTimeField(null=True, blank=True)
    modified_by = models.CharField(max_length=5, blank=True, default="")
    created_by = models.CharField(max_length=5, blank=True, default="")

    class Meta:
        db_table = "fi_pr_mh_calc_da"
        managed = False
        verbose_name = "Payroll DA % (calc_da)"
        ordering = ["-wef_dt", "emp_class_grp"]

    def __str__(self):
        return f"{self.wef_dt} {self.emp_type}/{self.emp_class_grp}: {self.da_pct}%"


class FiPrMhAdaRateVw(models.Model):
    """MySQL mirror of FINANCE.FI_PR_MH_ADA_RATE_VW (RE, class grp 1)."""

    wef_dt = models.DateField()
    emp_type = models.CharField(max_length=2, default="RE")
    emp_class_grp = models.IntegerField(default=1)
    da_pct = models.DecimalField(max_digits=10, decimal_places=4)

    class Meta:
        db_table = "fi_pr_mh_ada_rate_vw"
        verbose_name = "ADA rate (quarterly DA %)"
        ordering = ["-wef_dt"]
        constraints = [
            models.UniqueConstraint(
                fields=["wef_dt", "emp_type", "emp_class_grp"],
                name="uniq_ada_rate_wef_type_grp",
            )
        ]

    def __str__(self):
        return f"{self.wef_dt} {self.emp_type}/{self.emp_class_grp}: {self.da_pct}%"
