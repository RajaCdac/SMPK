from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("first_pension", "0025_commrate_rupee_composite_pk"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[],
            state_operations=[
                migrations.RemoveConstraint(
                    model_name="fipnmhpmthsetup",
                    name="uniq_pmthsetup_key",
                ),
                migrations.RemoveField(model_name="fipnmhpmthsetup", name="id"),
                migrations.AddField(
                    model_name="fipnmhpmthsetup",
                    name="pk",
                    field=models.CompositePrimaryKey(
                        "bill_type",
                        "bill_mth",
                        "bill_yr",
                        blank=True,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
            ],
        ),
    ]
