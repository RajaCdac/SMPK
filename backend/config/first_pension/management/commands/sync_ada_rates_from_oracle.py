from django.core.management.base import BaseCommand

from first_pension.services.da_rate_service import sync_ada_rates_from_oracle


class Command(BaseCommand):
    help = "Sync FI_PR_MH_CALC_DA into MySQL (fi_pr_mh_calc_da)."

    def handle(self, *args, **options):
        count = sync_ada_rates_from_oracle()
        self.stdout.write(self.style.SUCCESS(f"Synced {count} ADA rate row(s)."))
