from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("first_pension", "0026_pmthsetup_composite_pk"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[],
            state_operations=[
                migrations.RemoveConstraint(
                    model_name="fiprthsalout",
                    name="uniq_pr_th_salout_key",
                ),
                migrations.RemoveField(model_name="fiprthsalout", name="id"),
                migrations.AddField(
                    model_name="fiprthsalout",
                    name="pk",
                    field=models.CompositePrimaryKey(
                        "emp_cd",
                        "sal_mth",
                        "sal_yr",
                        blank=True,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                migrations.RemoveConstraint(
                    model_name="fiprtdsalout",
                    name="uniq_pr_td_salout_key",
                ),
                migrations.RemoveField(model_name="fiprtdsalout", name="id"),
                migrations.AddField(
                    model_name="fiprtdsalout",
                    name="pk",
                    field=models.CompositePrimaryKey(
                        "emp_cd",
                        "sal_mth",
                        "sal_yr",
                        "earndedn_cd",
                        blank=True,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                migrations.RemoveField(model_name="fipntdsepcom", name="id"),
                migrations.AddField(
                    model_name="fipntdsepcom",
                    name="pk",
                    field=models.CompositePrimaryKey(
                        "sepcom_id",
                        "earn_dedn_cd",
                        "earn_dedn_type",
                        blank=True,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                migrations.AlterField(
                    model_name="fipntdsepcom",
                    name="arrear_amt",
                    field=models.DecimalField(
                        blank=True,
                        db_column="AREAR_AMT",
                        decimal_places=2,
                        default=0,
                        max_digits=14,
                        null=True,
                    ),
                ),
            ],
        ),
    ]
