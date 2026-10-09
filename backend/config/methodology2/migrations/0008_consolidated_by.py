from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("methodology2", "0007_bunch_basic"),
    ]

    operations = [
        migrations.AddField(
            model_name="methodology2consolidation",
            name="consolidated_by",
            field=models.CharField(blank=True, default="", max_length=80),
        ),
    ]
