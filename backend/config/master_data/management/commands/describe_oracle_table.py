from django.core.management.base import BaseCommand

from employee.services.oracle_service import get_oracle_connection


class Command(BaseCommand):
    help = "List Oracle table columns (e.g. FI_PM_MH_BANK, FI_PM_MH_BANKABBR)."

    def add_arguments(self, parser):
        parser.add_argument(
            "table_name",
            nargs="?",
            default="FI_PM_MH_BANK",
            help="Table name without schema",
        )
        parser.add_argument("--owner", default="FINANCE")

    def handle(self, *args, **options):
        owner = options["owner"].strip().upper()
        table = options["table_name"].strip().upper()

        with get_oracle_connection().cursor() as cursor:
            cursor.execute(
                """
                SELECT column_name, data_type, data_length, nullable
                FROM all_tab_columns
                WHERE owner = :owner AND table_name = :table_name
                ORDER BY column_id
                """,
                {"owner": owner, "table_name": table},
            )
            rows = cursor.fetchall()

        if not rows:
            self.stderr.write(self.style.ERROR(f"No columns for {owner}.{table}"))
            return

        self.stdout.write(f"{owner}.{table} ({len(rows)} columns):\n")
        for name, dtype, length, nullable in rows:
            null_txt = "NULL" if nullable == "Y" else "NOT NULL"
            self.stdout.write(f"  {name:<20} {dtype}({length}) {null_txt}")
