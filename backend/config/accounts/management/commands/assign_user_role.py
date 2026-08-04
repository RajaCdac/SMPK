from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from accounts.models import Role, UserProfile, UserRole

User = get_user_model()


class Command(BaseCommand):
    help = (
        "Assign an application role to a login user (accounts_userrole table). "
        "Example: python manage.py assign_user_role admin_smpk --role-code ADMIN"
    )

    def add_arguments(self, parser):
        parser.add_argument("username", help="Login username (accounts_user.username)")
        parser.add_argument(
            "--role-id",
            type=int,
            help="Role primary key from accounts_role",
        )
        parser.add_argument(
            "--role-code",
            help="Role code e.g. ADMIN, PENSION_ADMIN, FIRST_PENSION_USER",
        )
        parser.add_argument(
            "--role-name",
            help="Role display name (partial match, case-insensitive)",
        )

    def handle(self, *args, **options):
        username = options["username"]
        user = User.objects.filter(username__iexact=username).first()
        if not user:
            self.stderr.write(self.style.ERROR(f"User '{username}' not found."))
            return

        role = self._resolve_role(options)
        if not role:
            self.stderr.write(self.style.ERROR("Role not found. List roles:"))
            for r in Role.objects.all().order_by("id"):
                self.stderr.write(f"  {r.id}: {r.name} ({r.code}) active={r.is_active}")
            return

        UserRole.objects.filter(user=user).update(is_active=False)
        assignment, created = UserRole.objects.update_or_create(
            user=user,
            role=role,
            defaults={"is_active": True},
        )
        UserProfile.objects.get_or_create(user=user)

        verb = "Created" if created else "Updated"
        self.stdout.write(
            self.style.SUCCESS(
                f"{verb} role for '{user.username}' -> {role.name} ({role.code})"
            )
        )

    def _resolve_role(self, options):
        if options.get("role_id"):
            return Role.objects.filter(pk=options["role_id"]).first()
        if options.get("role_code"):
            code = options["role_code"].strip().upper()
            return Role.objects.filter(code__iexact=code).first()
        if options.get("role_name"):
            name = options["role_name"].strip()
            return Role.objects.filter(name__icontains=name).first()
        return Role.objects.filter(code__in=["ADMIN", "PENSION_ADMIN"]).first()
