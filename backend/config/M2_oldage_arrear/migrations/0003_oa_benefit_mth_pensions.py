from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("m2_oldage_arrear", "0002_m2_oa_oldage_benefit"),
    ]

    operations = [
        migrations.AddField(
            model_name="m2oatdoldagebenefitmth",
            name="m1_pension",
            field=models.DecimalField(
                blank=True, decimal_places=2, max_digits=14, null=True
            ),
        ),
        migrations.AddField(
            model_name="m2oatdoldagebenefitmth",
            name="m2_pension",
            field=models.DecimalField(
                blank=True, decimal_places=2, max_digits=14, null=True
            ),
        ),
    ]
