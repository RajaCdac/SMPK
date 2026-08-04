from datetime import date
from decimal import Decimal

from django.db import migrations, models


def seed_ada_rates(apps, schema_editor):
    FiPrMhAdaRateVw = apps.get_model("first_pension", "FiPrMhAdaRateVw")
    # Q4 2023 ADA (used for VR separation 01-01-2024 / Dec 2023 increment month).
    FiPrMhAdaRateVw.objects.update_or_create(
        wef_dt=date(2023, 10, 1),
        emp_type="RE",
        emp_class_grp=1,
        defaults={"da_pct": Decimal("43.9148")},
    )


class Migration(migrations.Migration):

    dependencies = [
        ("first_pension", "0020_fipnmdcommraterupee_and_more"),
    ]

    operations = [
        migrations.CreateModel(
            name="FiPrMhAdaRateVw",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("wef_dt", models.DateField()),
                ("emp_type", models.CharField(default="RE", max_length=2)),
                ("emp_class_grp", models.IntegerField(default=1)),
                ("da_pct", models.DecimalField(decimal_places=4, max_digits=10)),
            ],
            options={
                "verbose_name": "ADA rate (quarterly DA %)",
                "db_table": "fi_pr_mh_ada_rate_vw",
                "ordering": ["-wef_dt"],
            },
        ),
        migrations.AddConstraint(
            model_name="fiprmhadaratevw",
            constraint=models.UniqueConstraint(
                fields=("wef_dt", "emp_type", "emp_class_grp"),
                name="uniq_ada_rate_wef_type_grp",
            ),
        ),
        migrations.RunPython(seed_ada_rates, migrations.RunPython.noop),
    ]
