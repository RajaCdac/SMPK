"""
Create first_pension_pensionproposal if missing (e.g. migration recorded but table not created).
Run: python manage.py ensure_pension_proposal_table
"""
from django.core.management.base import BaseCommand
from django.core.management import call_command
from django.db import connection


class Command(BaseCommand):
    help = "Ensure first_pension_pensionproposal table exists in MySQL"

    def handle(self, *args, **options):
        with connection.cursor() as cursor:
            cursor.execute(
                "SHOW TABLES LIKE %s",
                ["first_pension_pensionproposal"],
            )
            exists = cursor.fetchone()

        if exists:
            self.stdout.write(
                self.style.SUCCESS(
                    "Table first_pension_pensionproposal already exists."
                )
            )
            return

        self.stdout.write(
            "Table missing. Re-applying migration 0003_pensionproposal..."
        )

        # Unmark migration if it was recorded without creating the table
        with connection.cursor() as cursor:
            cursor.execute(
                "DELETE FROM django_migrations "
                "WHERE app = 'first_pension' AND name = '0003_pensionproposal'"
            )

        call_command("migrate", "first_pension", "0003", verbosity=1)

        with connection.cursor() as cursor:
            cursor.execute(
                "SHOW TABLES LIKE %s",
                ["first_pension_pensionproposal"],
            )
            if cursor.fetchone():
                self.stdout.write(
                    self.style.SUCCESS("Table created successfully.")
                )
            else:
                self.stdout.write(
                    self.style.ERROR(
                        "Table still missing. Run: python manage.py migrate first_pension"
                    )
                )
