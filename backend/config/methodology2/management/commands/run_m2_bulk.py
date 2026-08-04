from django.core.management.base import BaseCommand

from methodology2.services.bulk_run_service import (
    default_run_output_dir,
    run_bulk_from_excel,
)


class Command(BaseCommand):
    help = (
        "Bulk Methodology-2 (class 1/2 + 3/4): Excel EMP_CD → calc/save → "
        "Desktop/M2_YYYY-MM-DD/{case_no}.pdf"
    )

    def add_arguments(self, parser):
        parser.add_argument("excel", help="Path to Excel with EMP_CD column")
        parser.add_argument(
            "--output-dir",
            default="",
            help="Override output folder (default Desktop/M2_YYYY-MM-DD)",
        )

    def handle(self, *args, **options):
        out = options["output_dir"] or None
        summary = run_bulk_from_excel(
            options["excel"],
            output_dir=out or default_run_output_dir(),
        )
        self.stdout.write(
            self.style.SUCCESS(
                f"Done: total={summary['total']} ok={summary['ok']} "
                f"skipped={summary['skipped']} failed={summary['failed']}"
            )
        )
        self.stdout.write(f"Folder: {summary['output_dir']}")
        self.stdout.write(f"Log: {summary['log_path']}")
