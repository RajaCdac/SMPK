from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("first_pension", "0007_commutationapplication_bank_fields"),
    ]

    operations = [
        migrations.AddField(
            model_name="commutationapplication",
            name="ca_no",
            field=models.CharField(blank=True, default="", max_length=50),
        ),
        migrations.AddField(
            model_name="commutationapplication",
            name="ref_no",
            field=models.CharField(blank=True, default="", max_length=100),
        ),
        migrations.AddField(
            model_name="commutationapplication",
            name="bill_no",
            field=models.CharField(blank=True, default="", max_length=50),
        ),
        migrations.AddField(
            model_name="commutationapplication",
            name="sanction_parameter",
            field=models.CharField(blank=True, default="", max_length=200),
        ),
    ]
