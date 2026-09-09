"""MySQL mirrors of Oracle FINANCE employee reference tables (Wave 2)."""

from django.db import models


class FiXxMhEmpAdm(models.Model):
    """Oracle FINANCE.FI_XX_MH_EMP_ADM — employee administration."""

    emp_cd = models.CharField(max_length=5, primary_key=True)
    mo_cert_ref = models.CharField(max_length=30, blank=True, default="")
    join_dt = models.DateField(null=True, blank=True)
    emp_origin_tag = models.CharField(max_length=1, blank=True, default="")
    confirm_dt = models.DateField(null=True, blank=True)
    app_quota = models.CharField(max_length=3, blank=True, default="")
    separation_type = models.CharField(max_length=3, blank=True, default="")
    separation_dt = models.DateField(null=True, blank=True)
    termin_remark = models.CharField(max_length=800, blank=True, default="")
    exp_ret_dt = models.DateField(null=True, blank=True)
    pf_type = models.CharField(max_length=1, blank=True, default="")
    hindi_flg = models.IntegerField(null=True, blank=True)
    dlypaid_years = models.IntegerField(null=True, blank=True)
    date_created = models.DateField(null=True, blank=True)
    date_modified = models.DateField(null=True, blank=True)
    modified_by = models.CharField(max_length=5, blank=True, default="")
    created_by = models.CharField(max_length=5, blank=True, default="")
    vig_cert_no = models.CharField(max_length=20, blank=True, default="")
    vig_cert_dt = models.DateField(null=True, blank=True)
    order_no = models.CharField(max_length=20, blank=True, default="")
    order_dt = models.DateField(null=True, blank=True)
    order_issued_by = models.CharField(max_length=20, blank=True, default="")
    desig_cd = models.IntegerField(null=True, blank=True)
    union_cd = models.IntegerField(null=True, blank=True)
    mc_reg_no = models.CharField(max_length=5, blank=True, default="")
    mc_reg_dt = models.DateField(null=True, blank=True)
    known_flg = models.IntegerField(null=True, blank=True)
    known_details = models.CharField(max_length=100, blank=True, default="")
    pan_no = models.CharField(max_length=10, blank=True, default="")

    class Meta:
        db_table = "fi_xx_mh_emp_adm"
        verbose_name = "Employee ADM (Oracle mirror)"
        ordering = ["emp_cd"]

    def __str__(self):
        return self.emp_cd


class FiXxMhEmpPer(models.Model):
    """Oracle FINANCE.FI_XX_MH_EMP_PER — employee personal details."""

    emp_cd = models.CharField(max_length=5, primary_key=True)
    title = models.CharField(max_length=8, blank=True, default="")
    first_name = models.CharField(max_length=20, blank=True, default="")
    middle_name = models.CharField(max_length=20, blank=True, default="")
    last_name = models.CharField(max_length=20, blank=True, default="")
    perm_addr1 = models.CharField(max_length=25, blank=True, default="")
    perm_addr2 = models.CharField(max_length=25, blank=True, default="")
    perm_ps = models.CharField(max_length=30, blank=True, default="")
    perm_city = models.CharField(max_length=20, blank=True, default="")
    perm_dist = models.CharField(max_length=20, blank=True, default="")
    perm_state = models.CharField(max_length=20, blank=True, default="")
    perm_pin = models.IntegerField(null=True, blank=True)
    perm_country = models.CharField(max_length=20, blank=True, default="")
    perm_contact1 = models.CharField(max_length=15, blank=True, default="")
    perm_contact2 = models.CharField(max_length=15, blank=True, default="")
    perm_fax_no = models.CharField(max_length=15, blank=True, default="")
    perm_email_id = models.CharField(max_length=30, blank=True, default="")
    pres_addr1 = models.CharField(max_length=25, blank=True, default="")
    pres_addr2 = models.CharField(max_length=25, blank=True, default="")
    pres_ps = models.CharField(max_length=30, blank=True, default="")
    pres_city = models.CharField(max_length=20, blank=True, default="")
    pres_dist = models.CharField(max_length=20, blank=True, default="")
    pres_state = models.CharField(max_length=20, blank=True, default="")
    pres_pin = models.IntegerField(null=True, blank=True)
    pres_country = models.CharField(max_length=20, blank=True, default="")
    pres_contact1 = models.CharField(max_length=15, blank=True, default="")
    pres_contact2 = models.CharField(max_length=15, blank=True, default="")
    pres_fax_no = models.CharField(max_length=15, blank=True, default="")
    pres_email_id = models.CharField(max_length=30, blank=True, default="")
    f_h_flg = models.CharField(max_length=1, blank=True, default="")
    f_h_name = models.CharField(max_length=50, blank=True, default="")
    birth_dt = models.DateField(null=True, blank=True)
    dob_evidence = models.CharField(max_length=100, blank=True, default="")
    sex = models.CharField(max_length=1, blank=True, default="")
    edu_qual = models.CharField(max_length=80, blank=True, default="")
    prof_qual = models.CharField(max_length=80, blank=True, default="")
    other_qual = models.CharField(max_length=80, blank=True, default="")
    awards = models.CharField(max_length=80, blank=True, default="")
    religion = models.CharField(max_length=15, blank=True, default="")
    nationality = models.CharField(max_length=15, blank=True, default="")
    height_cm = models.IntegerField(null=True, blank=True)
    id_marks = models.CharField(max_length=100, blank=True, default="")
    category = models.CharField(max_length=3, blank=True, default="")
    handicap_flg = models.IntegerField(null=True, blank=True)
    marital_status = models.CharField(max_length=1, blank=True, default="")
    date_created = models.DateField(null=True, blank=True)
    date_modified = models.DateField(null=True, blank=True)
    modified_by = models.CharField(max_length=5, blank=True, default="")
    created_by = models.CharField(max_length=5, blank=True, default="")
    status = models.CharField(max_length=2, blank=True, default="")
    f_h_addr = models.CharField(max_length=140, blank=True, default="")
    doctor_flg = models.IntegerField(null=True, blank=True)
    remarks = models.CharField(max_length=300, blank=True, default="")

    class Meta:
        db_table = "fi_xx_mh_emp_per"
        verbose_name = "Employee PER (Oracle mirror)"
        ordering = ["emp_cd"]

    def __str__(self):
        name = " ".join(
            p for p in (self.first_name, self.middle_name, self.last_name) if p
        ).strip()
        return f"{self.emp_cd} — {name}" if name else self.emp_cd


class FiXxMhEmpFin(models.Model):
    """Oracle FINANCE.FI_XX_MH_EMP_FIN — employee finance / bank."""

    emp_cd = models.CharField(max_length=5, primary_key=True)
    bank_cd = models.CharField(max_length=6, blank=True, default="")
    paymode_cd = models.CharField(max_length=2, blank=True, default="")
    bank_ac_no = models.CharField(max_length=20, blank=True, default="")
    last_gi_dt = models.DateField(null=True, blank=True)
    next_gi_dt = models.DateField(null=True, blank=True)
    suspend_flg = models.CharField(max_length=1, blank=True, default="")
    suspend_wef_dt = models.DateField(null=True, blank=True)
    qtr_flg = models.IntegerField(null=True, blank=True)
    transport_flg = models.IntegerField(null=True, blank=True)
    tel_flg = models.IntegerField(null=True, blank=True)
    past_serv_days = models.IntegerField(null=True, blank=True)
    dues_clr_flg = models.IntegerField(null=True, blank=True)
    remarks = models.CharField(max_length=150, blank=True, default="")
    date_created = models.DateField(null=True, blank=True)
    date_modified = models.DateField(null=True, blank=True)
    modified_by = models.CharField(max_length=5, blank=True, default="")
    created_by = models.CharField(max_length=5, blank=True, default="")
    pay_pct = models.DecimalField(max_digits=14, decimal_places=4, null=True, blank=True)
    final_stlmt_status = models.CharField(max_length=1, blank=True, default="")
    fa_no = models.CharField(max_length=5, blank=True, default="")
    scale_sl = models.CharField(max_length=14, blank=True, default="")
    scale_wef_dt = models.DateField(null=True, blank=True)
    scale_optfor = models.CharField(max_length=1, blank=True, default="")
    inland_cert_class = models.CharField(max_length=1, blank=True, default="")
    emp_class = models.IntegerField(null=True, blank=True)

    class Meta:
        db_table = "fi_xx_mh_emp_fin"
        verbose_name = "Employee FIN (Oracle mirror)"
        ordering = ["emp_cd"]

    def __str__(self):
        return self.emp_cd


class FiXxMdFinscale(models.Model):
    """Oracle FINANCE.FI_XX_MD_FINSCALE — employee scale history."""

    # Oracle PK: (EMP_CD, WEF_DT, SL_NO) — no surrogate id column.
    pk = models.CompositePrimaryKey("emp_cd", "wef_dt", "sl_no")
    emp_cd = models.CharField(max_length=5, db_index=True)
    scale_sl = models.CharField(max_length=14)
    wef_dt = models.DateField()
    sl_no = models.IntegerField()
    date_created = models.DateField(null=True, blank=True)
    date_modified = models.DateField(null=True, blank=True)
    modified_by = models.CharField(max_length=30, blank=True, default="")
    created_by = models.CharField(max_length=30, blank=True, default="")
    history_flg = models.IntegerField(null=True, blank=True)
    basic_amt = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    stag_pay_amt = models.DecimalField(
        max_digits=14, decimal_places=2, null=True, blank=True
    )
    ref_no = models.CharField(max_length=10, blank=True, default="")
    tran_flg = models.CharField(max_length=1, blank=True, default="")
    active_rec = models.CharField(max_length=1, blank=True, default="")
    remarks = models.CharField(max_length=500, blank=True, default="")

    class Meta:
        db_table = "fi_xx_md_finscale"
        verbose_name = "Employee finscale (Oracle mirror)"
        ordering = ["emp_cd", "-wef_dt", "sl_no"]
        indexes = [
            models.Index(fields=["emp_cd", "wef_dt"]),
        ]

    def __str__(self):
        return f"{self.emp_cd} {self.scale_sl} @ {self.wef_dt}"


class FiXxMhEmpData(models.Model):
    """Oracle FINANCE.FI_XX_MH_EMP_DATA — posting / department snapshot per employee."""

    emp_cd = models.CharField(max_length=5, primary_key=True)
    dept_cd = models.CharField(max_length=2, blank=True, default="")
    dept_desc = models.CharField(max_length=100, blank=True, default="")
    budcntr_cd = models.CharField(max_length=3, blank=True, default="")
    alloc_desc = models.CharField(max_length=100, blank=True, default="")
    fa_no = models.CharField(max_length=5, blank=True, default="")
    fa_desc = models.CharField(max_length=50, blank=True, default="")
    srf_no = models.CharField(max_length=7, blank=True, default="")
    emp_class = models.CharField(max_length=15, blank=True, default="", db_column="CLASS")
    name = models.CharField(max_length=62, blank=True, default="")
    desig = models.CharField(max_length=30, blank=True, default="")
    dob_text = models.CharField(max_length=10, blank=True, default="", db_column="DOB")
    age = models.FloatField(null=True, blank=True)
    join_dt_text = models.CharField(
        max_length=10, blank=True, default="", db_column="JOIN_DT"
    )
    ret_dt_text = models.CharField(
        max_length=10, blank=True, default="", db_column="RET_DT"
    )

    class Meta:
        db_table = "fi_xx_mh_emp_data"
        verbose_name = "Employee data (Oracle mirror)"
        ordering = ["emp_cd"]

    def __str__(self):
        return f"{self.emp_cd} {self.alloc_desc or self.desig}"


class FiXxDeptWiseEmpDtl(models.Model):
    """
    Oracle FINANCE.FI_XX_DEPT_WISE_EMP_DTL (MySQL VIEW).
    Department from FA / budget centre — used for First Pension Advice Through office.
    """

    emp_cd = models.CharField(max_length=5, primary_key=True)
    first_name = models.CharField(max_length=20, blank=True, default="")
    middle_name = models.CharField(max_length=20, blank=True, default="")
    last_name = models.CharField(max_length=20, blank=True, default="")
    fa_no = models.CharField(max_length=5, blank=True, default="")
    fa_desc = models.CharField(max_length=50, blank=True, default="")
    srf_no = models.CharField(max_length=7, blank=True, default="")
    pf_no = models.CharField(max_length=7, blank=True, default="")
    leave_ac_no = models.CharField(max_length=20, blank=True, default="")
    old_emp_no = models.CharField(max_length=6, blank=True, default="")
    budcntr_cd = models.CharField(max_length=3, blank=True, default="")
    alloc_desc = models.CharField(max_length=100, blank=True, default="")
    dept_cd = models.CharField(max_length=2, blank=True, default="")
    dept_desc = models.CharField(max_length=100, blank=True, default="")

    class Meta:
        managed = False
        db_table = "fi_xx_dept_wise_emp_dtl"
        verbose_name = "Dept-wise employee detail (Oracle view)"
        ordering = ["emp_cd"]

    def __str__(self):
        return f"{self.emp_cd} {self.dept_desc}"
