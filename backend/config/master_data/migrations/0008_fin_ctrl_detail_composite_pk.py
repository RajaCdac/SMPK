from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("master_data", "0007_commrate_rupee_composite_pk"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[],
            state_operations=[
                migrations.RemoveConstraint(
                    model_name="fixxxxmdfinctrl",
                    name="uniq_fin_ctrl_detail_key",
                ),
                migrations.RemoveField(model_name="fixxxxmdfinctrl", name="id"),
                migrations.AddField(
                    model_name="fixxxxmdfinctrl",
                    name="pk",
                    field=models.CompositePrimaryKey(
                        "fin_yr",
                        "doc_abv",
                        blank=True,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
            ],
        ),
    ]
