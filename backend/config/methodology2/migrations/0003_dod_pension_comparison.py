# Generated manually for DOD-aware M2 consolidation print

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("methodology2", "0002_add_pensioner_fields"),
    ]

    operations = [
        migrations.AddField(
            model_name="methodology2consolidation",
            name="date_of_death",
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="methodology2consolidation",
            name="pension_comparison",
            field=models.JSONField(blank=True, default=dict),
        ),
    ]
