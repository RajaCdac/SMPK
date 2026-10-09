from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("m2_oldage_arrear", "0005_bunch_basic"),
    ]

    operations = [
        migrations.AddField(
            model_name="m2oldagearrearconsolidation",
            name="consolidated_by",
            field=models.CharField(blank=True, default="", max_length=80),
        ),
    ]
