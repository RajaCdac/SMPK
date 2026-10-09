from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("m2_oldage_arrear", "0003_oa_benefit_mth_pensions"),
    ]

    operations = [
        migrations.AddField(
            model_name="m2oldagearrearconsolidation",
            name="payment_done",
            field=models.BooleanField(db_index=True, default=False),
        ),
        migrations.AddField(
            model_name="m2oldagearrearconsolidation",
            name="payment_done_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="m2oldagearrearconsolidation",
            name="payment_done_by",
            field=models.CharField(blank=True, default="", max_length=80),
        ),
    ]
