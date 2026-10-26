from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("m2_oldage_arrear", "0006_consolidated_by"),
    ]

    operations = [
        migrations.AddField(
            model_name="m2oldagearrearconsolidation",
            name="payment_phase",
            field=models.CharField(blank=True, default="", max_length=40),
        ),
        migrations.AddField(
            model_name="m2oldagearrearconsolidation",
            name="payment_abstract_no",
            field=models.CharField(blank=True, default="", max_length=40),
        ),
        migrations.AddField(
            model_name="m2oldagearrearconsolidation",
            name="payment_ref_date",
            field=models.DateField(blank=True, null=True),
        ),
    ]
