from django.core.management.base import BaseCommand

from first_pension.services.oracle_wave3_sync import (
    WAVE3_SYNC_SPECS,
    sync_all_wave3,
    sync_wave3_table,
)


class Command(BaseCommand):
    help = (
        "Import Wave 3 Oracle tables into MySQL: first-month pension output, "
        "pensioner master, pension bills, and month setup."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--table",
            dest="table",
            help="Sync one Oracle table only (e.g. FI_PN_TH_PENSION_BILL)",
        )
        parser.add_argument(
            "--emp",
            dest="emp_cd",
            help="Sync rows for one employee only (EMP_CD)",
        )
        parser.add_argument(
            "--no-full-refresh",
            action="store_true",
            help="Append without deleting existing MySQL rows first",
        )
        parser.add_argument(
            "--batch-size",
            type=int,
            default=2000,
            help="bulk_create batch size (default 2000)",
        )

    def handle(self, *args, **options):
        table_filter = (options.get("table") or "").strip().upper()
        emp_cd = (options.get("emp_cd") or "").strip() or None
        full_refresh = not options.get("no_full_refresh")
        batch_size = max(100, int(options.get("batch_size") or 2000))

        if table_filter:
            spec = next(
                (s for s in WAVE3_SYNC_SPECS if s["oracle_table"] == table_filter),
                None,
            )
            if not spec:
                known = ", ".join(s["oracle_table"] for s in WAVE3_SYNC_SPECS)
                self.stderr.write(
                    self.style.ERROR(f"Unknown table {table_filter}. Known: {known}")
                )
                return
            results = [
                sync_wave3_table(
                    spec,
                    full_refresh=full_refresh,
                    batch_size=batch_size,
                    emp_cd=emp_cd,
                )
            ]
        else:
            results = sync_all_wave3(
                full_refresh=full_refresh,
                batch_size=batch_size,
                emp_cd=emp_cd,
            )

        for row in results:
            self.stdout.write(
                self.style.SUCCESS(
                    f"{row['oracle_table']}: {row['total']} Oracle rows, "
                    f"{row['inserted']} inserted, {row['skipped']} skipped"
                )
            )
