from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("first_pension", "0005_pensioncase_separation_fields"),
    ]

    operations = [
        migrations.CreateModel(
            name="DashboardMonthSnapshot",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("month", models.PositiveSmallIntegerField()),
                ("year", models.PositiveIntegerField()),
                ("total_employees", models.IntegerField(blank=True, null=True)),
                ("prev_month_count", models.IntegerField(default=0)),
                ("retirement_count", models.IntegerField(default=0)),
                ("next_month_count", models.IntegerField(default=0)),
                ("prev_month_label", models.CharField(blank=True, max_length=64)),
                ("this_month_label", models.CharField(blank=True, max_length=64)),
                ("next_month_label", models.CharField(blank=True, max_length=64)),
                ("synced_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "db_table": "first_pension_dashboard_snapshot",
                "indexes": [models.Index(fields=["year", "month"], name="first_pensi_year_8a0f0d_idx")],
                "unique_together": {("month", "year")},
            },
        ),
        migrations.CreateModel(
            name="CachedRetirementEmployee",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("emp_code", models.CharField(db_index=True, max_length=20)),
                ("retirement_month", models.PositiveSmallIntegerField()),
                ("retirement_year", models.PositiveIntegerField()),
                ("name", models.CharField(blank=True, max_length=300)),
                ("joining_date", models.CharField(blank=True, max_length=20)),
                ("retirement_date", models.CharField(blank=True, max_length=20)),
                ("birth_date", models.CharField(blank=True, max_length=20)),
                ("age_on_appointment", models.JSONField(blank=True, null=True)),
                ("age_on_retirement", models.JSONField(blank=True, null=True)),
                ("designation", models.CharField(blank=True, max_length=300)),
                ("scale", models.CharField(blank=True, max_length=100)),
                ("last_basic", models.DecimalField(blank=True, decimal_places=2, max_digits=12, null=True)),
                ("emp_class", models.CharField(blank=True, max_length=20)),
                ("row_payload", models.JSONField(default=dict)),
                ("synced_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "db_table": "first_pension_cached_retirement_emp",
                "indexes": [
                    models.Index(
                        fields=["retirement_year", "retirement_month"],
                        name="first_pensi_retire_6b2c8e_idx",
                    )
                ],
                "unique_together": {("emp_code", "retirement_month", "retirement_year")},
            },
        ),
        migrations.CreateModel(
            name="CachedEmployeeOracleDetail",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("emp_code", models.CharField(db_index=True, max_length=20, unique=True)),
                ("payload", models.JSONField(default=dict)),
                ("synced_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "db_table": "first_pension_cached_employee_oracle",
            },
        ),
    ]
