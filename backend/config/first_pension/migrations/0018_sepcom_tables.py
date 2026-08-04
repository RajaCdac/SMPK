from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("first_pension", "0017_pensionproposal_held_recovery"),
    ]

    operations = [
        migrations.CreateModel(
            name="FiPnThSepcom",
            fields=[
                (
                    "sepcom_id",
                    models.CharField(max_length=22, primary_key=True, serialize=False),
                ),
                ("sepcom_month", models.IntegerField()),
                ("sepcom_yr", models.IntegerField()),
                ("ca_no", models.CharField(blank=True, default="", max_length=22)),
                (
                    "original_com_amt",
                    models.DecimalField(
                        blank=True, decimal_places=2, max_digits=14, null=True
                    ),
                ),
                ("bill_no", models.CharField(blank=True, default="", max_length=22)),
                ("paid_month", models.IntegerField(blank=True, null=True)),
                ("paid_year", models.IntegerField(blank=True, null=True)),
                ("emp_cd", models.CharField(db_index=True, max_length=5)),
                ("nomin_type", models.CharField(blank=True, default="", max_length=2)),
                ("com_proc_tag", models.CharField(blank=True, default="C", max_length=1)),
                ("nomin_srl_no", models.IntegerField(default=0)),
                ("date_created", models.DateField(blank=True, null=True)),
                ("created_by", models.CharField(blank=True, default="", max_length=5)),
                ("date_modified", models.DateField(blank=True, null=True)),
                ("modified_by", models.CharField(blank=True, default="", max_length=5)),
                ("bank_cd", models.CharField(blank=True, default="", max_length=6)),
                (
                    "pen_dedn_amt",
                    models.DecimalField(
                        blank=True, decimal_places=2, max_digits=14, null=True
                    ),
                ),
                ("appcn_no", models.CharField(blank=True, default="", max_length=22)),
                ("appcn_dt", models.DateField(blank=True, null=True)),
            ],
            options={
                "verbose_name": "Separate commutation header",
                "db_table": "fi_pn_th_sepcom",
                "ordering": ["-sepcom_yr", "-sepcom_month", "sepcom_id"],
                "indexes": [
                    models.Index(
                        fields=["emp_cd", "sepcom_yr", "sepcom_month"],
                        name="fi_pn_th_se_emp_cd_8a1f2d_idx",
                    ),
                    models.Index(fields=["bill_no"], name="fi_pn_th_se_bill_no_idx"),
                ],
            },
        ),
        migrations.CreateModel(
            name="FiPnTdSepcom",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                ("earn_dedn_type", models.CharField(max_length=1)),
                ("earn_dedn_cd", models.CharField(max_length=3)),
                ("amount", models.DecimalField(decimal_places=2, default=0, max_digits=14)),
                ("date_created", models.DateField(blank=True, null=True)),
                ("created_by", models.CharField(blank=True, default="", max_length=5)),
                ("date_modified", models.DateField(blank=True, null=True)),
                ("modified_by", models.CharField(blank=True, default="", max_length=5)),
                ("sepcom_id", models.CharField(db_index=True, max_length=22)),
                ("emp_cd", models.CharField(db_index=True, max_length=5)),
                (
                    "original_amt",
                    models.DecimalField(
                        blank=True, decimal_places=2, max_digits=14, null=True
                    ),
                ),
                (
                    "arrear_amt",
                    models.DecimalField(
                        blank=True, decimal_places=2, default=0, max_digits=14, null=True
                    ),
                ),
            ],
            options={
                "verbose_name": "Separate commutation detail",
                "db_table": "fi_pn_td_sepcom",
                "ordering": ["sepcom_id", "earn_dedn_type", "earn_dedn_cd"],
            },
        ),
    ]
