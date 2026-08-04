"""
Create default roles and an optional admin login for a fresh SMPK install.

Usage:
  python manage.py seed_smpk_bootstrap
  python manage.py seed_smpk_bootstrap --admin-user admin --admin-password Admin@123
"""

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction

from accounts.models import Role, UserProfile, UserRole

User = get_user_model()

DEFAULT_ROLES = (
    ("Administrator", "ADMIN"),
    ("Pension Admin", "PENSION_ADMIN"),
    ("Pension User", "PENSION_USER"),
)


class Command(BaseCommand):
    help = "Seed default roles and optional admin user (for new machine / Docker install)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--admin-user",
            default="admin",
            help="Login username to create if missing (default: admin)",
        )
        parser.add_argument(
            "--admin-password",
            default="admin123",
            help="Password for new admin user (default: admin123 — change after login)",
        )
        parser.add_argument(
            "--skip-admin",
            action="store_true",
            help="Only create roles, do not create a user",
        )

    def handle(self, *args, **options):
        with transaction.atomic():
            roles = {}
            for name, code in DEFAULT_ROLES:
                role, created = Role.objects.update_or_create(
                    code=code,
                    defaults={"name": name, "is_active": True},
                )
                roles[code] = role
                verb = "Created" if created else "Updated"
                self.stdout.write(f"{verb} role: {role.name} ({role.code})")

            if options["skip_admin"]:
                self.stdout.write(self.style.SUCCESS("Roles ready."))
                return

            username = options["admin_user"].strip()
            password = options["admin_password"]
            admin_role = roles["ADMIN"]

            user, user_created = User.objects.get_or_create(
                username=username,
                defaults={
                    "is_staff": True,
                    "is_superuser": True,
                    "is_active": True,
                    "email": f"{username}@local",
                },
            )
            if user_created:
                user.set_password(password)
                user.save()
                self.stdout.write(
                    self.style.SUCCESS(f"Created user '{username}' (password from --admin-password)")
                )
            else:
                self.stdout.write(f"User '{username}' already exists — role assignment updated.")

            UserProfile.objects.get_or_create(user=user)
            UserRole.objects.filter(user=user).update(is_active=False)
            UserRole.objects.update_or_create(
                user=user,
                role=admin_role,
                defaults={"is_active": True},
            )
            self.stdout.write(
                self.style.SUCCESS(
                    f"Assigned {admin_role.name} to '{username}'. "
                    "Login at the app and change the password in production."
                )
            )
