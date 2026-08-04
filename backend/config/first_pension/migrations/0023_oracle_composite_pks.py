from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("first_pension", "0022_oracle_offline_mirrors"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[],
            state_operations=[
                migrations.RemoveConstraint(
                    model_name="fipnmhapplication",
                    name="uniq_pn_application_key",
                ),
                migrations.RemoveField(model_name="fipnmhapplication", name="id"),
                migrations.AddField(
                    model_name="fipnmhapplication",
                    name="pk",
                    field=models.CompositePrimaryKey(
                        "emp_cd",
                        "appcn_no",
                        "appcn_dt",
                        blank=True,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                migrations.RemoveConstraint(
                    model_name="fipnthsalout",
                    name="uniq_pn_th_salout_key",
                ),
                migrations.RemoveField(model_name="fipnthsalout", name="id"),
                migrations.AddField(
                    model_name="fipnthsalout",
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
                    model_name="fipntdsalout",
                    name="uniq_pn_td_salout_key",
                ),
                migrations.RemoveField(model_name="fipntdsalout", name="id"),
                migrations.AddField(
                    model_name="fipntdsalout",
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
                migrations.RemoveConstraint(
                    model_name="pensionproposalearndedn",
                    name="uniq_ca_earndedn_cd_type",
                ),
                migrations.RemoveField(
                    model_name="pensionproposalearndedn", name="line_order"
                ),
                migrations.RemoveField(model_name="pensionproposalearndedn", name="id"),
                migrations.AddField(
                    model_name="pensionproposalearndedn",
                    name="pk",
                    field=models.CompositePrimaryKey(
                        "ca_number",
                        "earndedn_cd",
                        "earn_dedn_type",
                        blank=True,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                migrations.AlterModelOptions(
                    name="pensionproposalearndedn",
                    options={
                        "ordering": ["ca_number", "earndedn_cd", "earn_dedn_type"],
                        "verbose_name": "Pension proposal earn/dedn line",
                        "verbose_name_plural": "Pension proposal earn/dedn lines",
                    },
                ),
            ],
        ),
    ]
