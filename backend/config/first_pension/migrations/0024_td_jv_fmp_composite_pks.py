from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("first_pension", "0023_oracle_composite_pks"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[],
            state_operations=[
                migrations.RemoveConstraint(
                    model_name="fipntdfirstmonthpension",
                    name="uniq_fmpen_earndedn_type",
                ),
                migrations.RemoveField(
                    model_name="fipntdfirstmonthpension", name="id"
                ),
                migrations.AddField(
                    model_name="fipntdfirstmonthpension",
                    name="pk",
                    field=models.CompositePrimaryKey(
                        "fmpen_id",
                        "earn_dedn_cd",
                        "earn_dedn_type",
                        blank=True,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                migrations.AlterField(
                    model_name="fipntdfirstmonthpension",
                    name="arrear_amt",
                    field=models.DecimalField(
                        blank=True,
                        db_column="AREAR_AMT",
                        decimal_places=2,
                        max_digits=14,
                        null=True,
                    ),
                ),
                migrations.RemoveConstraint(
                    model_name="fipntdjv",
                    name="uniq_pn_td_jv_line",
                ),
                migrations.RemoveField(model_name="fipntdjv", name="id"),
                migrations.AddField(
                    model_name="fipntdjv",
                    name="pk",
                    field=models.CompositePrimaryKey(
                        "voucher_no",
                        "sl_no",
                        blank=True,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
            ],
        ),
    ]
