from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("m2_oldage_arrear", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="M2OaThOldageBenefit",
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
                ("name", models.CharField(blank=True, default="", max_length=200)),
                ("roll_no", models.CharField(blank=True, default="", max_length=30)),
                ("case_no", models.CharField(blank=True, default="", max_length=20)),
                ("category", models.CharField(blank=True, default="", max_length=20)),
                ("is_employee_pension", models.BooleanField(default=True)),
                ("from_year", models.PositiveIntegerField()),
                ("from_month", models.PositiveSmallIntegerField()),
                ("to_year", models.PositiveIntegerField()),
                ("to_month", models.PositiveSmallIntegerField()),
                ("dob", models.DateField(blank=True, null=True)),
                ("as_on_date", models.DateField(blank=True, null=True)),
                (
                    "m1_pension_277",
                    models.DecimalField(
                        blank=True, decimal_places=2, max_digits=14, null=True
                    ),
                ),
                (
                    "m2_pension_277",
                    models.DecimalField(
                        blank=True, decimal_places=2, max_digits=14, null=True
                    ),
                ),
                (
                    "m1_pension_359",
                    models.DecimalField(
                        blank=True, decimal_places=2, max_digits=14, null=True
                    ),
                ),
                (
                    "m2_pension_359",
                    models.DecimalField(
                        blank=True, decimal_places=2, max_digits=14, null=True
                    ),
                ),
                (
                    "benefit_277",
                    models.DecimalField(
                        blank=True, decimal_places=2, max_digits=14, null=True
                    ),
                ),
                (
                    "benefit_359",
                    models.DecimalField(
                        blank=True, decimal_places=2, max_digits=14, null=True
                    ),
                ),
                ("age_completed", models.PositiveSmallIntegerField(blank=True, null=True)),
                (
                    "applicable_percent",
                    models.DecimalField(
                        blank=True, decimal_places=2, max_digits=5, null=True
                    ),
                ),
                (
                    "additional_pension",
                    models.DecimalField(
                        blank=True, decimal_places=2, max_digits=14, null=True
                    ),
                ),
                (
                    "monthly_da",
                    models.DecimalField(
                        blank=True, decimal_places=2, max_digits=14, null=True
                    ),
                ),
                (
                    "monthly_total",
                    models.DecimalField(
                        blank=True, decimal_places=2, max_digits=14, null=True
                    ),
                ),
                (
                    "da_pct",
                    models.DecimalField(
                        blank=True, decimal_places=2, max_digits=7, null=True
                    ),
                ),
                (
                    "total_arrear",
                    models.DecimalField(
                        blank=True, decimal_places=2, max_digits=14, null=True
                    ),
                ),
                (
                    "total_arrear_basic",
                    models.DecimalField(
                        blank=True, decimal_places=2, max_digits=14, null=True
                    ),
                ),
                (
                    "total_arrear_da",
                    models.DecimalField(
                        blank=True, decimal_places=2, max_digits=14, null=True
                    ),
                ),
                ("version_no", models.PositiveIntegerField(default=1)),
                ("calculated_at", models.DateTimeField(blank=True, null=True)),
                (
                    "calculated_by",
                    models.CharField(blank=True, default="", max_length=80),
                ),
                ("payload_json", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "verbose_name": "M2 OA old-age benefit header",
                "db_table": "m2_oa_th_oldage_benefit",
                "ordering": ["-updated_at"],
            },
        ),
        migrations.CreateModel(
            name="M2OaTdOldageBenefitMth",
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
                ("bill_year", models.PositiveIntegerField(db_index=True)),
                ("bill_month", models.PositiveSmallIntegerField()),
                ("bill_mth", models.CharField(blank=True, default="", max_length=3)),
                ("month_start", models.DateField()),
                ("month_end", models.DateField()),
                ("cpi_point", models.PositiveIntegerField(blank=True, null=True)),
                (
                    "oa_percent",
                    models.DecimalField(
                        blank=True, decimal_places=2, max_digits=5, null=True
                    ),
                ),
                ("age_slab", models.PositiveSmallIntegerField(blank=True, null=True)),
                (
                    "benefit_base",
                    models.DecimalField(
                        blank=True, decimal_places=2, max_digits=14, null=True
                    ),
                ),
                (
                    "oa_basic",
                    models.DecimalField(
                        blank=True, decimal_places=2, max_digits=14, null=True
                    ),
                ),
                (
                    "da_pct",
                    models.DecimalField(
                        blank=True, decimal_places=2, max_digits=7, null=True
                    ),
                ),
                (
                    "oa_da",
                    models.DecimalField(
                        blank=True, decimal_places=2, max_digits=14, null=True
                    ),
                ),
                (
                    "month_total",
                    models.DecimalField(
                        blank=True, decimal_places=2, max_digits=14, null=True
                    ),
                ),
                (
                    "hdr",
                    models.ForeignKey(
                        db_column="hdr_id",
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="months",
                        to="m2_oldage_arrear.m2oatholdagebenefit",
                    ),
                ),
            ],
            options={
                "verbose_name": "M2 OA old-age benefit month",
                "db_table": "m2_oa_td_oldage_benefit_mth",
                "ordering": ["bill_year", "bill_month", "id"],
            },
        ),
        migrations.AddConstraint(
            model_name="m2oatholdagebenefit",
            constraint=models.UniqueConstraint(
                fields=(
                    "emp_cd",
                    "from_year",
                    "from_month",
                    "to_year",
                    "to_month",
                ),
                name="uniq_m2_oa_th_oldage_benefit_range",
            ),
        ),
        migrations.AddConstraint(
            model_name="m2oatdoldagebenefitmth",
            constraint=models.UniqueConstraint(
                fields=("hdr", "bill_year", "bill_month"),
                name="uniq_m2_oa_td_oldage_benefit_mth",
            ),
        ),
        migrations.AddIndex(
            model_name="m2oatdoldagebenefitmth",
            index=models.Index(
                fields=["emp_cd", "bill_year", "bill_month"],
                name="m2_oa_td_ben_mth_emp_idx",
            ),
        ),
    ]
