from django.db import models


class FiPmMhBank(models.Model):
    """Local mirror of Oracle FINANCE.FI_PM_MH_BANK (branch-level bank master)."""

    bank_cd = models.CharField(
        max_length=6,
        primary_key=True,
        db_column="BANK_CD",
        verbose_name="Bank code",
    )
    bank_desc = models.CharField(
        max_length=50,
        blank=True,
        default="",
        db_column="BANK_DESC",
        verbose_name="Bank description",
    )
    bank_id = models.CharField(
        max_length=7,
        blank=True,
        default="",
        db_column="BANK_ID",
        verbose_name="Bank ID",
    )
    control_bank_cd = models.CharField(
        max_length=6,
        blank=True,
        default="",
        db_column="CONTROL_BANK_CD",
        verbose_name="Control bank code",
    )
    addr1 = models.CharField(
        max_length=25,
        blank=True,
        default="",
        db_column="ADDR1",
        verbose_name="Address 1",
    )
    addr2 = models.CharField(
        max_length=25,
        blank=True,
        default="",
        db_column="ADDR2",
        verbose_name="Address 2",
    )
    ps = models.CharField(
        max_length=30,
        blank=True,
        default="",
        db_column="PS",
        verbose_name="P.S.",
    )
    city = models.CharField(
        max_length=20,
        blank=True,
        default="",
        db_column="CITY",
        verbose_name="City",
    )
    dist = models.CharField(
        max_length=20,
        blank=True,
        default="",
        db_column="DIST",
        verbose_name="District",
    )
    state = models.CharField(
        max_length=20,
        blank=True,
        default="",
        db_column="STATE",
        verbose_name="State",
    )
    pin = models.IntegerField(
        null=True,
        blank=True,
        db_column="PIN",
        verbose_name="PIN",
    )
    country = models.CharField(
        max_length=20,
        blank=True,
        default="",
        db_column="COUNTRY",
        verbose_name="Country",
    )
    contact1 = models.CharField(
        max_length=15,
        blank=True,
        default="",
        db_column="CONTACT1",
        verbose_name="Contact 1",
    )
    contact2 = models.CharField(
        max_length=15,
        blank=True,
        default="",
        db_column="CONTACT2",
        verbose_name="Contact 2",
    )
    fax_no = models.CharField(
        max_length=15,
        blank=True,
        default="",
        db_column="FAX_NO",
        verbose_name="Fax no.",
    )
    email_id = models.CharField(
        max_length=30,
        blank=True,
        default="",
        db_column="EMAIL_ID",
        verbose_name="Email",
    )
    date_created = models.DateField(
        null=True,
        blank=True,
        db_column="DATE_CREATED",
        verbose_name="Date created",
    )
    date_modified = models.DateField(
        null=True,
        blank=True,
        db_column="DATE_MODIFIED",
        verbose_name="Date modified",
    )
    modified_by = models.CharField(
        max_length=5,
        blank=True,
        default="",
        db_column="MODIFIED_BY",
        verbose_name="Modified by",
    )
    created_by = models.CharField(
        max_length=5,
        blank=True,
        default="",
        db_column="CREATED_BY",
        verbose_name="Created by",
    )
    rbi_cd = models.CharField(
        max_length=9,
        blank=True,
        default="",
        db_column="RBI_CD",
        verbose_name="RBI code",
    )
    old_bank_cd = models.CharField(
        max_length=6,
        blank=True,
        default="",
        db_column="OLD_BANK_CD",
        verbose_name="Old bank code",
    )

    class Meta:
        db_table = "fi_pm_mh_bank"
        verbose_name = "Bank branch (FI_PM_MH_BANK)"
        verbose_name_plural = "Bank branches (FI_PM_MH_BANK)"
        ordering = ["bank_desc", "bank_cd"]

    def __str__(self):
        return f"{self.bank_cd} — {self.bank_desc}"


class FiPmMhBankAbbr(models.Model):
    """Local mirror of Oracle FINANCE.FI_PM_MH_BANKABBR (bank type / abbreviation master)."""

    bank_type = models.CharField(
        max_length=2,
        primary_key=True,
        db_column="BANK_TYPE",
        verbose_name="Bank type",
    )
    bank_name = models.CharField(
        max_length=60,
        blank=True,
        default="",
        db_column="BANK_NAME",
        verbose_name="Bank name",
    )
    created_by = models.CharField(
        max_length=5,
        blank=True,
        default="",
        db_column="CREATED_BY",
        verbose_name="Created by",
    )
    modified_by = models.CharField(
        max_length=5,
        blank=True,
        default="",
        db_column="MODIFIED_BY",
        verbose_name="Modified by",
    )
    date_created = models.DateField(
        null=True,
        blank=True,
        db_column="DATE_CREATED",
        verbose_name="Date created",
    )
    date_modified = models.DateField(
        null=True,
        blank=True,
        db_column="DATE_MODIFIED",
        verbose_name="Date modified",
    )
    bank_id = models.CharField(
        max_length=3,
        blank=True,
        default="",
        db_column="BANK_ID",
        verbose_name="Bank ID",
    )
    bank_short_name = models.CharField(
        max_length=10,
        blank=True,
        default="",
        db_column="BANK_SHORT_NAME",
        verbose_name="Short name",
    )

    class Meta:
        db_table = "fi_pm_mh_bankabbr"
        verbose_name = "Bank abbreviation (FI_PM_MH_BANKABBR)"
        verbose_name_plural = "Bank abbreviations (FI_PM_MH_BANKABBR)"
        ordering = ["bank_name", "bank_type"]

    def __str__(self):
        return f"{self.bank_type} — {self.bank_name}"


class FiPnMhEarndedn(models.Model):
    """Local mirror of Oracle FINANCE.FI_PN_MH_EARNDEDN (earn/dedn master)."""

    EARN = "E"
    DEDN = "D"
    TYPE_CHOICES = [
        (EARN, "Earning"),
        (DEDN, "Deduction"),
    ]

    pk = models.CompositePrimaryKey("earndedn_cd", "earndedn_type")

    earndedn_cd = models.CharField(
        max_length=3,
        db_column="EARNDEDN_CD",
        verbose_name="Earn/dedn code",
    )
    earndedn_type = models.CharField(
        max_length=1,
        choices=TYPE_CHOICES,
        db_column="EARNDEDN_TYPE",
        verbose_name="Type",
    )
    earndedn_desc = models.CharField(
        max_length=100,
        blank=True,
        default="",
        db_column="EARNDEDN_DESC",
        verbose_name="Description",
    )
    date_created = models.DateField(
        null=True,
        blank=True,
        db_column="DATE_CREATED",
        verbose_name="Date created",
    )
    date_modified = models.DateField(
        null=True,
        blank=True,
        db_column="DATE_MODIFIED",
        verbose_name="Date modified",
    )
    modified_by = models.CharField(
        max_length=5,
        blank=True,
        default="",
        db_column="MODIFIED_BY",
        verbose_name="Modified by",
    )
    created_by = models.CharField(
        max_length=5,
        blank=True,
        default="",
        db_column="CREATED_BY",
        verbose_name="Created by",
    )
    zonal_cd = models.IntegerField(
        null=True,
        blank=True,
        db_column="ZONAL_CD",
        verbose_name="Zonal code",
    )
    alloc_cd = models.CharField(
        max_length=4,
        blank=True,
        default="",
        db_column="ALLOC_CD",
        verbose_name="Allocation code",
    )

    class Meta:
        db_table = "fi_pn_mh_earndedn"
        verbose_name = "Earn/dedn code (FI_PN_MH_EARNDEDN)"
        verbose_name_plural = "Earn/dedn codes (FI_PN_MH_EARNDEDN)"
        ordering = ["earndedn_cd"]

    def __str__(self):
        return f"{self.earndedn_cd} — {self.earndedn_desc}"


class _OracleAuditMixin(models.Model):
    date_created = models.DateField(
        null=True,
        blank=True,
        db_column="DATE_CREATED",
        verbose_name="Date created",
    )
    date_modified = models.DateField(
        null=True,
        blank=True,
        db_column="DATE_MODIFIED",
        verbose_name="Date modified",
    )
    modified_by = models.CharField(
        max_length=5,
        blank=True,
        default="",
        db_column="MODIFIED_BY",
        verbose_name="Modified by",
    )
    created_by = models.CharField(
        max_length=5,
        blank=True,
        default="",
        db_column="CREATED_BY",
        verbose_name="Created by",
    )

    class Meta:
        abstract = True


class FiPnMhErndednmap(_OracleAuditMixin):
    """Oracle FINANCE.FI_PN_MH_ERNDEDNMAP — pension earn/dedn logical map."""

    map_cd = models.IntegerField(
        primary_key=True,
        db_column="MAP_CD",
        verbose_name="Map code",
    )
    e_d_type = models.CharField(
        max_length=1,
        db_column="E_D_TYPE",
        verbose_name="Earn/dedn type",
    )
    map_desc = models.CharField(
        max_length=50,
        blank=True,
        default="",
        db_column="MAP_DESC",
        verbose_name="Description",
    )
    earndedn_cd = models.CharField(
        max_length=3,
        db_column="EARNDEDN_CD",
        verbose_name="Earn/dedn code",
    )
    dedn_priority = models.IntegerField(
        null=True,
        blank=True,
        db_column="DEDN_PRIORITY",
        verbose_name="Deduction priority",
    )

    class Meta:
        db_table = "fi_pn_mh_erndednmap"
        verbose_name = "Pension earn map (FI_PN_MH_ERNDEDNMAP)"
        verbose_name_plural = "Pension earn maps (FI_PN_MH_ERNDEDNMAP)"
        ordering = ["map_cd"]

    def __str__(self):
        return f"{self.map_cd} — {self.map_desc}"


class FiPrMhErndednmap(_OracleAuditMixin):
    """Oracle FINANCE.FI_PR_MH_ERNDEDNMAP — payroll earn/dedn logical map."""

    map_cd = models.IntegerField(
        primary_key=True,
        db_column="MAP_CD",
        verbose_name="Map code",
    )
    group_type = models.CharField(
        max_length=1,
        db_column="GROUP_TYPE",
        verbose_name="Group type",
    )
    map_desc = models.CharField(
        max_length=50,
        blank=True,
        default="",
        db_column="MAP_DESC",
        verbose_name="Description",
    )
    earndedn_cd = models.CharField(
        max_length=3,
        db_column="EARNDEDN_CD",
        verbose_name="Earn/dedn code",
    )
    dedn_priority = models.IntegerField(
        null=True,
        blank=True,
        db_column="DEDN_PRIORITY",
        verbose_name="Deduction priority",
    )

    class Meta:
        db_table = "fi_pr_mh_erndednmap"
        verbose_name = "Payroll earn map (FI_PR_MH_ERNDEDNMAP)"
        verbose_name_plural = "Payroll earn maps (FI_PR_MH_ERNDEDNMAP)"
        ordering = ["map_cd"]

    def __str__(self):
        return f"{self.map_cd} — {self.map_desc}"


class FiPnMhAdaRate(_OracleAuditMixin):
    """Oracle FINANCE.FI_PN_MH_ADA_RATE — DA / CPI rates."""

    pk = models.CompositePrimaryKey("wef_dt", "emp_type", "base_cpi_no")
    emp_type = models.CharField(max_length=3, db_column="EMP_TYPE")
    wef_dt = models.DateField(db_column="WEF_DT")
    base_cpi_no = models.IntegerField(db_column="BASE_CPI_NO")
    index_pts = models.DecimalField(
        max_digits=14, decimal_places=4, null=True, blank=True, db_column="INDEX_PTS"
    )
    da_pct = models.DecimalField(
        max_digits=14, decimal_places=4, null=True, blank=True, db_column="DA_PCT"
    )
    cpi_no = models.DecimalField(
        max_digits=14, decimal_places=4, null=True, blank=True, db_column="CPI_NO"
    )
    wet_dt = models.DateField(null=True, blank=True, db_column="WET_DT")

    class Meta:
        db_table = "fi_pn_mh_ada_rate"
        verbose_name = "ADA rate (FI_PN_MH_ADA_RATE)"
        verbose_name_plural = "ADA rates (FI_PN_MH_ADA_RATE)"
        ordering = ["-wef_dt", "emp_type", "base_cpi_no"]

    def __str__(self):
        return f"{self.emp_type} @ {self.wef_dt}"


class FiPnMdMaxadmGratuity(_OracleAuditMixin):
    """Oracle FINANCE.FI_PN_MD_MAXADM_GRATUITY — gratuity emolument caps."""

    pk = models.CompositePrimaryKey("wef_dt", "gratuity_type", "ret_dt_from")
    wef_dt = models.DateField(db_column="WEF_DT")
    gratuity_type = models.IntegerField(db_column="GRATUITY_TYPE")
    ret_dt_from = models.DateField(db_column="RET_DT_FROM")
    ret_dt_to = models.DateField(null=True, blank=True, db_column="RET_DT_TO")
    max_emolument = models.DecimalField(
        max_digits=14, decimal_places=2, null=True, blank=True, db_column="MAX_EMOLUMENT"
    )
    max_adm_gratuity = models.DecimalField(
        max_digits=14, decimal_places=2, null=True, blank=True, db_column="MAX_ADM_GRATUITY"
    )

    class Meta:
        db_table = "fi_pn_md_maxadm_gratuity"
        verbose_name = "Max adm gratuity (FI_PN_MD_MAXADM_GRATUITY)"
        verbose_name_plural = "Max adm gratuity (FI_PN_MD_MAXADM_GRATUITY)"
        ordering = ["-wef_dt", "gratuity_type"]

    def __str__(self):
        return f"type {self.gratuity_type} from {self.ret_dt_from}"


class FiPnMhDeathGratchart(_OracleAuditMixin):
    """Oracle FINANCE.FI_PN_MH_DEATH_GRATCHART — death gratuity header."""

    pk = models.CompositePrimaryKey("wef_dt", "gratuity_type")
    wef_dt = models.DateField(db_column="WEF_DT")
    gratuity_type = models.IntegerField(db_column="GRATUITY_TYPE")
    inception_dt = models.DateField(db_column="INCEPTION_DT")
    before_inception_max_lt = models.IntegerField(db_column="BEFORE_INCEPTION_MAX_LT")
    after_inception_max_lt = models.IntegerField(db_column="AFTER_INCEPTION_MAX_LT")
    circular_ref_no = models.CharField(
        max_length=22, blank=True, default="", db_column="CIRCULAR_REF_NO"
    )

    class Meta:
        db_table = "fi_pn_mh_death_gratchart"
        verbose_name = "Death gratuity chart (FI_PN_MH_DEATH_GRATCHART)"
        verbose_name_plural = "Death gratuity charts (FI_PN_MH_DEATH_GRATCHART)"
        ordering = ["-wef_dt", "gratuity_type"]

    def __str__(self):
        return f"type {self.gratuity_type} @ {self.wef_dt}"


class FiPnMdDeathGratchart(_OracleAuditMixin):
    """Oracle FINANCE.FI_PN_MD_DEATH_GRATCHART — death gratuity multiples."""

    pk = models.CompositePrimaryKey("tqs_start_yrs", "wef_dt", "gratuity_type")
    wef_dt = models.DateField(db_column="WEF_DT")
    gratuity_type = models.IntegerField(db_column="GRATUITY_TYPE")
    tqs_start_yrs = models.IntegerField(db_column="TQS_START_YRS")
    tqs_end_yrs = models.IntegerField(db_column="TQS_END_YRS")
    multiple_factor = models.DecimalField(
        max_digits=14, decimal_places=4, db_column="MULTIPLE_FACTOR"
    )

    class Meta:
        db_table = "fi_pn_md_death_gratchart"
        verbose_name = "Death gratuity detail (FI_PN_MD_DEATH_GRATCHART)"
        verbose_name_plural = "Death gratuity detail (FI_PN_MD_DEATH_GRATCHART)"
        ordering = ["-wef_dt", "gratuity_type", "tqs_start_yrs"]

    def __str__(self):
        return f"TQS {self.tqs_start_yrs}-{self.tqs_end_yrs} type {self.gratuity_type}"


class FiPnMhServiceGratchart(_OracleAuditMixin):
    """Oracle FINANCE.FI_PN_MH_SERVICE_GRATCHART — service gratuity chart."""

    pk = models.CompositePrimaryKey("wef_dt", "interval_srl")
    wef_dt = models.DateField(db_column="WEF_DT")
    interval_srl = models.IntegerField(db_column="INTERVAL_SRL")
    duration_month = models.IntegerField(db_column="DURATION_MONTH")
    base_doc = models.CharField(
        max_length=15, blank=True, default="", db_column="BASE_DOC"
    )
    numerator_amt = models.DecimalField(
        max_digits=14, decimal_places=4, null=True, blank=True, db_column="NUMERATOR_AMT"
    )
    denominator_amt = models.DecimalField(
        max_digits=14, decimal_places=4, null=True, blank=True, db_column="DENOMINATOR_AMT"
    )

    class Meta:
        db_table = "fi_pn_mh_service_gratchart"
        verbose_name = "Service gratuity chart (FI_PN_MH_SERVICE_GRATCHART)"
        verbose_name_plural = "Service gratuity charts (FI_PN_MH_SERVICE_GRATCHART)"
        ordering = ["-wef_dt", "interval_srl"]

    def __str__(self):
        return f"interval {self.interval_srl} @ {self.wef_dt}"


class FiPnMdCommrateRupee(_OracleAuditMixin):
    """Oracle FINANCE.FI_PN_MD_COMMRATE_RUPEE — commutation rate per rupee by age."""

    pk = models.CompositePrimaryKey("age_yrs", "wef_dt")
    age_yrs = models.IntegerField(db_column="AGE_YRS")
    wef_dt = models.DateField(db_column="WEF_DT")
    amt_per_rupee = models.DecimalField(
        max_digits=14, decimal_places=6, null=True, blank=True, db_column="AMT_PER_RUPEE"
    )

    class Meta:
        db_table = "fi_pn_md_commrate_rupee"
        verbose_name = "Commutation rate (FI_PN_MD_COMMRATE_RUPEE)"
        verbose_name_plural = "Commutation rates (FI_PN_MD_COMMRATE_RUPEE)"
        ordering = ["-wef_dt", "age_yrs"]

    def __str__(self):
        return f"age {self.age_yrs} @ {self.wef_dt}"


class FiPnMhBaseCpi(_OracleAuditMixin):
    """Oracle FINANCE.FI_PN_MH_BASE_CPI — base CPI by employee type."""

    pk = models.CompositePrimaryKey("emp_type", "wef_dt")
    emp_type = models.CharField(max_length=2, db_column="EMP_TYPE")
    wef_dt = models.DateField(db_column="WEF_DT")
    base_cpi = models.DecimalField(max_digits=14, decimal_places=4, db_column="BASE_CPI")

    class Meta:
        db_table = "fi_pn_mh_base_cpi"
        verbose_name = "Base CPI (FI_PN_MH_BASE_CPI)"
        verbose_name_plural = "Base CPI (FI_PN_MH_BASE_CPI)"
        ordering = ["-wef_dt", "emp_type"]

    def __str__(self):
        return f"{self.emp_type} @ {self.wef_dt}"


class FiXxMhDesig(_OracleAuditMixin):
    """Oracle FINANCE.FI_XX_MH_DESIG — designation master."""

    desig_cd = models.IntegerField(primary_key=True, db_column="DESIG_CD")
    desig_desc = models.CharField(
        max_length=60, blank=True, default="", db_column="DESIG_DESC"
    )
    active_flg = models.IntegerField(db_column="ACTIVE_FLG")

    class Meta:
        db_table = "fi_xx_mh_desig"
        verbose_name = "Designation (FI_XX_MH_DESIG)"
        verbose_name_plural = "Designations (FI_XX_MH_DESIG)"
        ordering = ["desig_desc", "desig_cd"]

    def __str__(self):
        return f"{self.desig_cd} — {self.desig_desc}"


class FiXxMhDept(models.Model):
    """Oracle FINANCE.FI_XX_MH_DEPT — department master."""

    dept_cd = models.CharField(max_length=2, primary_key=True, db_column="DEPT_CD")
    dept_desc = models.CharField(max_length=100, blank=True, default="")
    dept_short_desc = models.CharField(max_length=7, blank=True, default="")
    date_created = models.DateField(null=True, blank=True)
    date_modified = models.DateField(null=True, blank=True)
    created_by = models.CharField(max_length=5, blank=True, default="")
    modified_by = models.CharField(max_length=5, blank=True, default="")

    class Meta:
        db_table = "fi_xx_mh_dept"
        verbose_name = "Department (FI_XX_MH_DEPT)"
        verbose_name_plural = "Departments (FI_XX_MH_DEPT)"
        ordering = ["dept_desc", "dept_cd"]

    def __str__(self):
        return f"{self.dept_cd} — {self.dept_desc}"


class FiXxXxMHFinCtrl(models.Model):
    """Oracle FINANCE.FI_XX_XX_M_H_FIN_CTRL — financial year header."""

    fin_yr = models.IntegerField(primary_key=True, db_column="FIN_YR")
    yr_st_dt = models.DateField(db_column="YR_ST_DT")
    yr_end_dt = models.DateField(db_column="YR_END_DT")
    year_pd = models.CharField(max_length=9, db_column="YEAR_PD")
    fin_stat = models.IntegerField(db_column="FIN_STAT")
    l_trn_no = models.IntegerField(db_column="L_TRN_NO")
    created_by = models.CharField(max_length=5, db_column="CREATED_BY")
    created_on = models.DateField(db_column="CREATED_ON")
    l_modified_by = models.CharField(
        max_length=5, blank=True, default="", db_column="L_MODIFIED_BY"
    )
    l_modified_on = models.DateField(null=True, blank=True, db_column="L_MODIFIED_ON")

    class Meta:
        db_table = "fi_xx_xx_m_h_fin_ctrl"
        verbose_name = "Financial year (FI_XX_XX_M_H_FIN_CTRL)"
        verbose_name_plural = "Financial years (FI_XX_XX_M_H_FIN_CTRL)"
        ordering = ["-fin_yr"]

    def __str__(self):
        return f"FY {self.fin_yr} ({self.year_pd})"


class FiXxXxMDFinCtrl(models.Model):
    """Oracle FINANCE.FI_XX_XX_M_D_FIN_CTRL — document serial control per FY."""

    pk = models.CompositePrimaryKey("fin_yr", "doc_abv")
    fin_yr = models.IntegerField(db_column="FIN_YR")
    doc_abv = models.CharField(max_length=4, db_column="DOC_ABV")
    doc_desc = models.CharField(max_length=60, db_column="DOC_DESC")
    l_trn_no = models.IntegerField(db_column="L_TRN_NO")
    created_by = models.CharField(max_length=5, db_column="CREATED_BY")
    created_on = models.DateField(db_column="CREATED_ON")
    l_modified_by = models.CharField(
        max_length=5, blank=True, default="", db_column="L_MODIFIED_BY"
    )
    l_modified_on = models.DateField(null=True, blank=True, db_column="L_MODIFIED_ON")
    authority = models.CharField(
        max_length=300, blank=True, default="", db_column="AUTHORITY"
    )

    class Meta:
        db_table = "fi_xx_xx_m_d_fin_ctrl"
        verbose_name = "FIN document control (FI_XX_XX_M_D_FIN_CTRL)"
        verbose_name_plural = "FIN document controls (FI_XX_XX_M_D_FIN_CTRL)"
        ordering = ["-fin_yr", "doc_abv"]

    def __str__(self):
        return f"{self.doc_abv} FY {self.fin_yr}"


class FiPmMhPayscale(_OracleAuditMixin):
    """Oracle FINANCE.FI_PM_MH_PAYSCALE — pay scale code to band description."""

    scale_cd = models.CharField(
        max_length=20,
        primary_key=True,
        db_column="SCALE_CD",
        verbose_name="Scale code",
    )
    scale_desc = models.CharField(
        max_length=100,
        blank=True,
        default="",
        db_column="SCALE_DESC",
        verbose_name="Scale description",
    )

    class Meta:
        db_table = "fi_pm_mh_payscale"
        verbose_name = "Pay scale (FI_PM_MH_PAYSCALE)"
        verbose_name_plural = "Pay scales (FI_PM_MH_PAYSCALE)"
        ordering = ["scale_cd"]

    def __str__(self):
        return f"{self.scale_cd} — {self.scale_desc}"


class FiPnMhJrnltype(_OracleAuditMixin):
    """Oracle FINANCE.FI_PN_MH_JRNLTYPE — journal voucher type header."""

    jrnal_srl_no = models.IntegerField(primary_key=True, db_column="JRNAL_SRL_NO")
    type = models.CharField(max_length=6, db_column="TYPE")
    jrnal_desc = models.CharField(
        max_length=30, blank=True, default="", db_column="JRNAL_DESC"
    )

    class Meta:
        db_table = "fi_pn_mh_jrnltype"
        verbose_name = "Journal type (FI_PN_MH_JRNLTYPE)"
        ordering = ["jrnal_srl_no"]

    def __str__(self):
        return f"{self.type} — {self.jrnal_desc}"


class FiPnMdJrnltype(_OracleAuditMixin):
    """Oracle FINANCE.FI_PN_MD_JRNLTYPE — journal GL allocation lines."""

    pk = models.CompositePrimaryKey(
        "jrnal_srl_no",
        "zonal_cd",
        "dr_cr_flg",
        "aloc_cd1",
        "aloc_cd2",
        "aloc_cd3",
    )
    jrnal_srl_no = models.IntegerField(db_column="JRNAL_SRL_NO", db_index=True)
    zonal_cd = models.IntegerField(db_column="ZONAL_CD")
    dr_cr_flg = models.CharField(max_length=1, db_column="DR_CR_FLG")
    aloc_cd1 = models.CharField(max_length=4, db_column="ALOC_CD1")
    aloc_cd2 = models.CharField(max_length=4, db_column="ALOC_CD2", blank=True, default="")
    aloc_cd3 = models.CharField(max_length=7, db_column="ALOC_CD3", blank=True, default="")
    map_cd = models.CharField(max_length=15, blank=True, default="", db_column="MAP_CD")

    class Meta:
        db_table = "fi_pn_md_jrnltype"
        verbose_name = "Journal allocation (FI_PN_MD_JRNLTYPE)"
        ordering = ["jrnal_srl_no", "zonal_cd", "aloc_cd1"]

    def __str__(self):
        return f"{self.jrnal_srl_no}/{self.zonal_cd}/{self.aloc_cd1}"
