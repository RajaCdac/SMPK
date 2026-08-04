import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from first_pension.oracle_mirror import (
    FiPnThPensionBill,
    FiPnThFirstMonthPension,
    FiPnTdFirstMonthPension,
    FiPnMhPensioner,
)

bill_no = "PPN/07/2026/207"
bill = FiPnThPensionBill.objects.get(bill_no=bill_no)
print("bill", bill.bill_no, bill.bank_cd, bill.gen_lic_tag, bill.bill_abstract_no, bill.voucher_no)
headers = FiPnThFirstMonthPension.objects.filter(bill_no=bill_no)
print("headers", headers.count())
for h in headers[:5]:
    print(
        h.emp_cd,
        h.ca_no,
        h.lic_bank_cd,
        h.bank_cd,
        h.sys_man_tag,
        list(
            FiPnTdFirstMonthPension.objects.filter(fmpen_id=h.fmpen_id).values_list(
                "earn_dedn_cd", "amount"
            )[:6]
        ),
    )
    p = FiPnMhPensioner.objects.filter(emp_cd=h.emp_cd).first()
    if p:
        print("  pensioner", p.name, p.ca_number, p.account_no)
