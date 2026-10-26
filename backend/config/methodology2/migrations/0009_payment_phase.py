from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("methodology2", "0008_consolidated_by"),
    ]

    operations = [
        migrations.AddField(
            model_name="methodology2consolidation",
            name="payment_phase",
            field=models.CharField(blank=True, default="", max_length=40),
        ),
        migrations.AddField(
            model_name="methodology2consolidation",
            name="payment_abstract_no",
            field=models.CharField(blank=True, default="", max_length=40),
        ),
        migrations.AddField(
            model_name="methodology2consolidation",
            name="payment_ref_date",
            field=models.DateField(blank=True, null=True),
        ),
    ]
