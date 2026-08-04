from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("first_pension", "0024_td_jv_fmp_composite_pks"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[],
            state_operations=[
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
