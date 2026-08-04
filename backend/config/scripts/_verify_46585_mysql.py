import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from first_pension.oracle_mirror import (
    FiPnMhPensioner,
    FiPnThFirstMonthPension,
    FiPnThPensionBill,
    FiPnTdFirstMonthPension,
)
from first_pension.models import PensionCase
from first_pension.services.bill_abstract_report_service import build_bill_abstract_report

EMP = "46585"
PPN = "PPN/09/2025/79"

print("=== MySQL pensioner ===")
p = FiPnMhPensioner.objects.filter(emp_cd=EMP).first()
print(p.__dict__ if p else None)

print("\n=== MySQL first month ===")
for h in FiPnThFirstMonthPension.objects.filter(emp_cd=EMP):
    print(h.fmpen_id, h.bill_no, h.bank_cd, h.lic_bank_cd)

print("\n=== MySQL bill ===")
b = FiPnThPensionBill.objects.filter(bill_no=PPN).first()
print(b.__dict__ if b else None)

print("\n=== MySQL case ===")
c = PensionCase.objects.filter(emp_code=EMP).first()
if c:
    print(c.emp_code, c.retirement_date, c.name)

print("\n=== SMPK abstract report ===")
try:
    r = build_bill_abstract_report(PPN, emp_codes=[EMP])
    import json
    print(json.dumps(r, indent=2, default=str))
except Exception as e:
    print("ERROR:", e)
