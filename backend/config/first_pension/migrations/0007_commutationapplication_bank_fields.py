from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("first_pension", "0006_oracle_local_cache"),
    ]

    operations = [
        migrations.AddField(
            model_name="commutationapplication",
            name="bank_cd",
            field=models.CharField(blank=True, default="", max_length=6),
        ),
        migrations.AddField(
            model_name="commutationapplication",
            name="bank_desc",
            field=models.CharField(blank=True, default="", max_length=50),
        ),
    ]
