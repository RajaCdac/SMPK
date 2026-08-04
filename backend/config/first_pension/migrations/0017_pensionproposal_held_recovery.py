from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("first_pension", "0016_pensioncase_boys_serv_days"),
    ]

    operations = [
        migrations.AddField(
            model_name="pensionproposal",
            name="held_recovery_amt",
            field=models.DecimalField(
                blank=True, decimal_places=2, max_digits=12, null=True
            ),
        ),
        migrations.AddField(
            model_name="pensionproposal",
            name="held_recovery_date",
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="pensionproposal",
            name="held_recovery_ref_no",
            field=models.CharField(blank=True, default="", max_length=30),
        ),
        migrations.AddField(
            model_name="pensionproposal",
            name="held_recovery_remarks",
            field=models.CharField(blank=True, default="", max_length=500),
        ),
    ]
