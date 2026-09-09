"""
Docker UAT DB bootstrap.

Finance dumps often include fi_* mirror tables but may lack Django auth tables
(accounts_user). Plain migrate hits MySQL 1050 on existing mirrors; skipping
migrate hits 1146 on login. This command reconciles both cases.
"""

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.db import connection

DJANGO_CORE_APPS = (
    "contenttypes",
    "auth",
    "accounts",
    "admin",
    "sessions",
)

MIRROR_APPS = ("master_data",)


class Command(BaseCommand):
    help = "Bootstrap Docker UAT DB: fake mirror tables, create missing Django tables."

    def add_arguments(self, parser):
        parser.add_argument(
            "--seed-admin",
            action="store_true",
            help="Create default admin user when no users exist",
        )

    def _table_exists(self, name: str) -> bool:
        with connection.cursor() as cursor:
            cursor.execute("SHOW TABLES LIKE %s", [name])
            return cursor.fetchone() is not None

    def _django_migrations_exists(self) -> bool:
        return self._table_exists("django_migrations")

    def _clear_core_migration_rows(self) -> None:
        if not self._django_migrations_exists():
            return
        placeholders = ", ".join(["%s"] * len(DJANGO_CORE_APPS))
        with connection.cursor() as cursor:
            cursor.execute(
                f"DELETE FROM django_migrations WHERE app IN ({placeholders})",
                list(DJANGO_CORE_APPS),
            )

    def handle(self, *args, **options):
        for app in MIRROR_APPS:
            self.stdout.write(f"Fake-initial mirror app: {app}")
            call_command("migrate", app, "--fake-initial", "--noinput")

        if not self._table_exists("accounts_user"):
            self.stdout.write(
                self.style.WARNING("accounts_user missing — creating Django core tables")
            )
            if self._django_migrations_exists():
                self._clear_core_migration_rows()
            for app in DJANGO_CORE_APPS:
                call_command("migrate", app, "--noinput")

        self.stdout.write("Applying remaining migrations...")
        call_command("migrate", "--fake-initial", "--noinput")
        call_command("migrate", "--noinput")

        if options["seed_admin"] and get_user_model().objects.count() == 0:
            self.stdout.write("No users found — seeding default admin...")
            call_command("seed_smpk_bootstrap")

        self.stdout.write(self.style.SUCCESS("UAT database bootstrap complete."))
