from django.db import migrations


def copy_full_name_to_user(apps, schema_editor):
    User = apps.get_model("accounts", "User")
    UserProfile = apps.get_model("accounts", "UserProfile")
    for profile in UserProfile.objects.exclude(full_name="").select_related("user"):
        user = profile.user
        if user.first_name or user.last_name:
            continue
        parts = (profile.full_name or "").strip().split(None, 1)
        user.first_name = parts[0] if parts else ""
        user.last_name = parts[1] if len(parts) > 1 else ""
        user.save(update_fields=["first_name", "last_name"])


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0004_userprofile_role_code"),
    ]

    operations = [
        migrations.RunPython(copy_full_name_to_user, migrations.RunPython.noop),
        migrations.RemoveField(
            model_name="userprofile",
            name="full_name",
        ),
    ]
