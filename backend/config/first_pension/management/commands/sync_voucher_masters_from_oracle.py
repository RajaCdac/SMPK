from django.core.management.base import BaseCommand

from first_pension.services.voucher_master_sync import sync_jrnl_types_from_oracle


class Command(BaseCommand):
    help = (
        "Import journal voucher master data from Oracle into MySQL "
        "(FI_PN_MH/M D_JRNLTYPE and earn zonal/allocation). Read-only on Oracle."
    )

    def handle(self, *args, **options):
        result = sync_jrnl_types_from_oracle()
        self.stdout.write(
            self.style.SUCCESS(
                f"Journal masters synced: "
                f"MH_JRNLTYPE={result['mh_jrnltype']}, "
                f"MD_JRNLTYPE={result['md_jrnltype']}, "
                f"earndedn zonal updated={result['earndedn_zonal']}"
            )
        )
