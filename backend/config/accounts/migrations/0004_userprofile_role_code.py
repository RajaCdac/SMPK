from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


def populate_role_codes(apps, schema_editor):
    Role = apps.get_model("accounts", "Role")
    used = set()
    for role in Role.objects.all():
        name = (role.name or "").strip().lower()
        if name in {"admin", "administrator"}:
            base = "ADMIN"
        elif name in {"pension user", "pension", "user", "clerk"}:
            base = "PENSION_USER"
        else:
            base = "".join(ch if ch.isalnum() else "_" for ch in name).strip("_").upper()
            base = base or f"ROLE_{role.id}"
        code = base
        suffix = 1
        while code in used:
            code = f"{base}_{suffix}"
            suffix += 1
        used.add(code)
        role.code = code
        role.save(update_fields=["code"])


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0003_diesnon_end_date"),
    ]

    operations = [
        migrations.AddField(
            model_name="role",
            name="code",
            field=models.CharField(blank=True, max_length=30, null=True),
        ),
        migrations.CreateModel(
            name="UserProfile",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("emp_code", models.CharField(blank=True, max_length=50)),
                ("full_name", models.CharField(blank=True, max_length=150)),
                ("designation", models.CharField(blank=True, max_length=100)),
                ("department", models.CharField(blank=True, max_length=100)),
                ("mobile_no", models.CharField(blank=True, max_length=20)),
                (
                    "user",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="profile",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
        ),
        migrations.RunPython(populate_role_codes, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="role",
            name="code",
            field=models.CharField(blank=True, max_length=30, unique=True),
        ),
    ]
