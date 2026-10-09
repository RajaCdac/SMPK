from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("methodology2", "0005_m2_consol_store"),
    ]

    operations = [
        migrations.AddField(
            model_name="methodology2consolidation",
            name="payment_done",
            field=models.BooleanField(db_index=True, default=False),
        ),
        migrations.AddField(
            model_name="methodology2consolidation",
            name="payment_done_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="methodology2consolidation",
            name="payment_done_by",
            field=models.CharField(blank=True, default="", max_length=80),
        ),
    ]
