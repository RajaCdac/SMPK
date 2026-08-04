# Generated manually for fi_pn_th_salout mirror

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("first_pension", "0018_sepcom_tables"),
    ]

    operations = [
        migrations.CreateModel(
            name="FiPnThSalout",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("emp_cd", models.CharField(db_index=True, max_length=5)),
                ("sal_mth", models.IntegerField()),
                ("sal_yr", models.IntegerField()),
                ("fa_no", models.CharField(blank=True, default="", max_length=10)),
                (
                    "sal_bill_no",
                    models.CharField(blank=True, default="", max_length=22),
                ),
                (
                    "gross_earn_amt",
                    models.DecimalField(
                        blank=True, decimal_places=2, max_digits=14, null=True
                    ),
                ),
                (
                    "gross_dedn_amt",
                    models.DecimalField(
                        blank=True, decimal_places=2, max_digits=14, null=True
                    ),
                ),
                (
                    "net_earn_amt",
                    models.DecimalField(
                        blank=True, decimal_places=2, max_digits=14, null=True
                    ),
                ),
                (
                    "scale_desc",
                    models.CharField(blank=True, default="", max_length=100),
                ),
                (
                    "basic_rate",
                    models.DecimalField(
                        blank=True, decimal_places=2, max_digits=14, null=True
                    ),
                ),
                ("wg_st_dt", models.DateField(blank=True, null=True)),
                ("wg_end_dt", models.DateField(blank=True, null=True)),
                ("date_created", models.DateField(blank=True, null=True)),
                ("date_modified", models.DateField(blank=True, null=True)),
                (
                    "modified_by",
                    models.CharField(blank=True, default="", max_length=5),
                ),
                (
                    "created_by",
                    models.CharField(blank=True, default="", max_length=5),
                ),
            ],
            options={
                "verbose_name": "Pension salout header (Oracle mirror)",
                "db_table": "fi_pn_th_salout",
                "ordering": ["emp_cd", "-sal_yr", "-sal_mth"],
                "indexes": [
                    models.Index(
                        fields=["emp_cd", "sal_yr", "sal_mth"],
                        name="fi_pn_th_salout_emp_yr_mth_idx",
                    )
                ],
            },
        ),
        migrations.AddConstraint(
            model_name="fipnthsalout",
            constraint=models.UniqueConstraint(
                fields=("emp_cd", "sal_mth", "sal_yr"),
                name="uniq_pn_th_salout_key",
            ),
        ),
    ]
