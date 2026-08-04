from django.core.management.base import BaseCommand

from first_pension.services.pension_bill_service import (
    PensionBillError,
    repair_orphan_pension_bill,
)


class Command(BaseCommand):
    help = (
        "Recreate a missing fi_pn_th_pension_bill row in MySQL when first-month "
        "headers still reference the bill number (no Oracle writes)."
    )

    def add_arguments(self, parser):
        parser.add_argument("--bill-no", dest="bill_no", help="PPN bill number")
        parser.add_argument("--emp", dest="emp_cd", help="Employee code")

    def handle(self, *args, **options):
        bill_no = (options.get("bill_no") or "").strip()
        emp_cd = (options.get("emp_cd") or "").strip()
        try:
            result = repair_orphan_pension_bill(bill_no=bill_no or None, emp_cd=emp_cd or None)
        except PensionBillError as exc:
            self.stderr.write(self.style.ERROR(str(exc)))
            return

        self.stdout.write(
            self.style.SUCCESS(
                f"Repaired bill {result['bill_no']} — "
                f"earn {result['total_amt_earned']}, ded {result['total_amt_deducted']}, "
                f"LIC tag {result['gen_lic_tag']}, "
                f"pensioners {result['pensioner_count']} ({', '.join(result['emp_codes'])})"
            )
        )
