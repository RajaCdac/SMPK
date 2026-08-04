from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("master_data", "0006_fi_pm_mh_payscale"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[],
            state_operations=[
                migrations.RemoveConstraint(
                    model_name="fipnmdcommraterupee",
                    name="uniq_commrate_rupee_key",
                ),
                migrations.RemoveField(
                    model_name="fipnmdcommraterupee", name="id"
                ),
                migrations.AddField(
                    model_name="fipnmdcommraterupee",
                    name="pk",
                    field=models.CompositePrimaryKey(
                        "age_yrs",
                        "wef_dt",
                        blank=True,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
            ],
        ),
    ]
