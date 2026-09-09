from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("methodology2", "0003_dod_pension_comparison"),
    ]

    operations = [
        migrations.AddField(
            model_name="methodology2consolidation",
            name="retirement_type",
            field=models.CharField(blank=True, default="", max_length=80),
        ),
    ]
