from django.core.management.base import BaseCommand

from master_data.services.oracle_pension_master_sync import (
    PENSION_MASTER_SYNC_SPECS,
    sync_all_pension_masters,
    sync_pension_master_table,
)


class Command(BaseCommand):
    help = (
        "Import pension calculation master tables from Oracle FINANCE into MySQL "
        "(Wave 1: earn maps, gratuity charts, ADA/CPI, designations, FIN_CTRL)."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--table",
            dest="table",
            help="Sync one Oracle table only (e.g. FI_PN_MH_ERNDEDNMAP)",
        )

    def handle(self, *args, **options):
        table_filter = (options.get("table") or "").strip().upper()
        if table_filter:
            spec = next(
                (s for s in PENSION_MASTER_SYNC_SPECS if s["oracle_table"] == table_filter),
                None,
            )
            if not spec:
                known = ", ".join(s["oracle_table"] for s in PENSION_MASTER_SYNC_SPECS)
                self.stderr.write(
                    self.style.ERROR(f"Unknown table {table_filter}. Known: {known}")
                )
                return
            results = [sync_pension_master_table(spec)]
        else:
            results = sync_all_pension_masters()

        for row in results:
            self.stdout.write(
                self.style.SUCCESS(
                    f"{row['oracle_table']}: {row['total']} rows "
                    f"(created {row['created']}, updated {row['updated']}, "
                    f"skipped {row['skipped']})"
                )
            )
