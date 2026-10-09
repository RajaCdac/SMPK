from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("m2_oldage_arrear", "0004_payment_done"),
    ]

    operations = [
        migrations.AddField(
            model_name="m2oldagearrearconsolidation",
            name="bunch_basic",
            field=models.DecimalField(
                blank=True, decimal_places=2, max_digits=14, null=True
            ),
        ),
    ]
