from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("first_pension", "0015_voucher_jv"),
    ]

    operations = [
        migrations.AddField(
            model_name="pensioncase",
            name="boys_serv_days",
            field=models.IntegerField(default=0),
        ),
    ]
