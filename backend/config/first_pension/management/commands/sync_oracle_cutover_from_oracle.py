"""
One-shot Oracle → MySQL bootstrap before discontinuing live Oracle reads.

Run while Oracle is still reachable. Then set ORACLE_READ_ENABLED=False in settings.
"""

from django.core.management import call_command
from django.core.management.base import BaseCommand


CUTOVER_STEPS = [
    ("sync_pension_masters_from_oracle", "Pension calculation masters + dept + desig"),
    ("sync_banks_from_oracle", "Bank master"),
    ("sync_earndedn_from_oracle", "Earn/dedn master"),
    ("sync_voucher_masters_from_oracle", "Journal voucher masters"),
    ("sync_ada_rates_from_oracle", "Payroll ADA rates"),
    ("sync_oracle_wave2_from_oracle", "Workflow, employee ref, salout (PR+PN)"),
    ("sync_oracle_wave3_from_oracle", "Pensioner, bills, first-month pension"),
]


class Command(BaseCommand):
    help = (
        "Bootstrap MySQL mirrors from Oracle for offline operation "
        "(masters, employee data, payroll/pension salout, pension output)."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--emp",
            dest="emp_cd",
            help="Limit employee-scoped wave2 tables to one EMP_CD (faster trial sync)",
        )
        parser.add_argument(
            "--skip-wave3",
            action="store_true",
            help="Skip wave 3 (pension bills / pensioner) if not needed yet",
        )

    def handle(self, *args, **options):
        emp_cd = (options.get("emp_cd") or "").strip() or None
        skip_wave3 = bool(options.get("skip_wave3"))

        for command_name, label in CUTOVER_STEPS:
            if skip_wave3 and command_name == "sync_oracle_wave3_from_oracle":
                self.stdout.write(self.style.WARNING(f"Skipping: {label}"))
                continue

            self.stdout.write(self.style.MIGRATE_HEADING(f"→ {label} ({command_name})"))
            kwargs = {}
            if emp_cd and command_name == "sync_oracle_wave2_from_oracle":
                kwargs["emp_cd"] = emp_cd
            call_command(command_name, **kwargs)

        self.stdout.write(
            self.style.SUCCESS(
                "Cutover sync complete. Set ORACLE_READ_ENABLED=False and restart Django."
            )
        )
