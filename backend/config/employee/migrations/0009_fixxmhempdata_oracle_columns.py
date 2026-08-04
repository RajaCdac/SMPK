from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("employee", "0008_fixxmdfinscale_oracle_pk"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[],
            state_operations=[
                migrations.AlterField(
                    model_name="fixxmhempdata",
                    name="emp_class",
                    field=models.CharField(
                        blank=True,
                        db_column="CLASS",
                        default="",
                        max_length=15,
                    ),
                ),
                migrations.AlterField(
                    model_name="fixxmhempdata",
                    name="dob_text",
                    field=models.CharField(
                        blank=True,
                        db_column="DOB",
                        default="",
                        max_length=10,
                    ),
                ),
                migrations.AlterField(
                    model_name="fixxmhempdata",
                    name="age",
                    field=models.FloatField(blank=True, null=True),
                ),
                migrations.AlterField(
                    model_name="fixxmhempdata",
                    name="join_dt_text",
                    field=models.CharField(
                        blank=True,
                        db_column="JOIN_DT",
                        default="",
                        max_length=10,
                    ),
                ),
                migrations.AlterField(
                    model_name="fixxmhempdata",
                    name="ret_dt_text",
                    field=models.CharField(
                        blank=True,
                        db_column="RET_DT",
                        default="",
                        max_length=10,
                    ),
                ),
            ],
        ),
    ]
