from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("methodology2", "0006_payment_done"),
    ]

    operations = [
        migrations.AddField(
            model_name="methodology2consolidation",
            name="bunch_basic",
            field=models.DecimalField(
                blank=True, decimal_places=2, max_digits=14, null=True
            ),
        ),
    ]
