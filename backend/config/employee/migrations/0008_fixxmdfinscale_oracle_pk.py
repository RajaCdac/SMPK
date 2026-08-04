from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("employee", "0007_oracle_offline_mirrors"),
    ]

    operations = [
        # Table already matches Oracle after finance→smpk sync (no surrogate id).
        migrations.SeparateDatabaseAndState(
            database_operations=[],
            state_operations=[
                migrations.RemoveConstraint(
                    model_name="fixxmdfinscale",
                    name="uniq_xx_md_finscale_key",
                ),
                migrations.RemoveField(
                    model_name="fixxmdfinscale",
                    name="id",
                ),
                migrations.AddField(
                    model_name="fixxmdfinscale",
                    name="pk",
                    field=models.CompositePrimaryKey(
                        "emp_cd",
                        "wef_dt",
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
