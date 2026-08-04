from django.core.management.base import BaseCommand
from django.db import transaction

from master_data.models import FiPmMhBank, FiPmMhBankAbbr
from master_data.services.oracle_bank_service import (
    fetch_oracle_bank_abbr_rows_for_sync,
    fetch_oracle_bank_rows_for_sync,
)


class Command(BaseCommand):
    help = "Import FINANCE.FI_PM_MH_BANK and FI_PM_MH_BANKABBR from Oracle into MySQL."

    def handle(self, *args, **options):
        bank_rows = fetch_oracle_bank_rows_for_sync()
        abbr_rows = fetch_oracle_bank_abbr_rows_for_sync()

        bank_created = bank_updated = 0
        abbr_created = abbr_updated = 0

        with transaction.atomic():
            for row in bank_rows:
                code = row.pop("bank_cd")
                obj, was_created = FiPmMhBank.objects.update_or_create(
                    bank_cd=code,
                    defaults=row,
                )
                if was_created:
                    bank_created += 1
                else:
                    bank_updated += 1

            for row in abbr_rows:
                code = row.pop("bank_type")
                obj, was_created = FiPmMhBankAbbr.objects.update_or_create(
                    bank_type=code,
                    defaults=row,
                )
                if was_created:
                    abbr_created += 1
                else:
                    abbr_updated += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"FI_PM_MH_BANK: {len(bank_rows)} rows "
                f"(created {bank_created}, updated {bank_updated})"
            )
        )
        self.stdout.write(
            self.style.SUCCESS(
                f"FI_PM_MH_BANKABBR: {len(abbr_rows)} rows "
                f"(created {abbr_created}, updated {abbr_updated})"
            )
        )
