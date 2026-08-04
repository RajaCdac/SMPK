from django.core.management.base import BaseCommand
from django.db import transaction

from master_data.models import FiPnMhEarndedn
from master_data.services.oracle_earndedn_service import (
    fetch_oracle_earndedn_rows_for_sync,
)


class Command(BaseCommand):
    help = "Import FINANCE.FI_PN_MH_EARNDEDN from Oracle into MySQL."

    def handle(self, *args, **options):
        rows = fetch_oracle_earndedn_rows_for_sync()
        created = updated = 0

        with transaction.atomic():
            for row in rows:
                code = row.pop("earndedn_cd")
                _, was_created = FiPnMhEarndedn.objects.update_or_create(
                    earndedn_cd=code,
                    defaults=row,
                )
                if was_created:
                    created += 1
                else:
                    updated += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"FI_PN_MH_EARNDEDN: {len(rows)} rows "
                f"(created {created}, updated {updated})"
            )
        )
