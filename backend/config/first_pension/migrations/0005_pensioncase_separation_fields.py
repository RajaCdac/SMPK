from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("first_pension", "0004_pensioncase_no_pay_more_than_240_days_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="pensioncase",
            name="separation_type",
            field=models.CharField(blank=True, default="", max_length=50),
        ),
        migrations.AddField(
            model_name="pensioncase",
            name="separation_date",
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="pensioncase",
            name="process_remarks",
            field=models.TextField(blank=True, default=""),
        ),
    ]
