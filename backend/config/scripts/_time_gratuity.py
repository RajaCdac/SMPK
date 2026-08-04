import os, sys, time
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
import django; django.setup()

from first_pension.pension_calculation import (
    reload_pension_case_from_db,
    resolve_separation_date,
    get_gratuity_option_for_employee,
    get_separation_type_for_employee,
)
from first_pension.models import PensionSummary
from first_pension.services.gratuity_emoluments_service import (
    resolve_gratuity_emoluments,
    calculate_gratuity_payable,
)
from employee.services.oracle_service import oracle_reads_enabled

EMP = "40562"
print("oracle_reads_enabled", oracle_reads_enabled())
case = reload_pension_case_from_db(EMP)
summary = PensionSummary.objects.filter(pension_case_id=case.id).first()
sep = resolve_separation_date(case.emp_code, case) or case.retirement_date

def timed(label, fn):
    t0 = time.perf_counter()
    r = fn()
    print(f"{(time.perf_counter()-t0)*1000:8.1f} ms  {label}")
    return r

em = timed("resolve_gratuity_emoluments", lambda: resolve_gratuity_emoluments(
    case.emp_code, case.emp_class, case.last_basic, separation_dt=sep
))
print("emoluments result", em[0] if em else None, em[1] if em else None)
if em and em[0]:
    timed("calculate_gratuity_payable", lambda: calculate_gratuity_payable(
        emoluments=em[0],
        gratuity_option=get_gratuity_option_for_employee(case.emp_code),
        separation_dt=sep,
        tccs_years=summary.tccs_years,
        tccs_months=summary.tccs_months,
        tccs_days=summary.tccs_days,
        tqs_years=summary.tqs_years,
        tqs_months=summary.tqs_months,
        tqs_days=summary.tqs_days,
        emp_cd=case.emp_code,
        emp_class=case.emp_class,
        separation_type=get_separation_type_for_employee(case.emp_code),
        joining_date=case.joining_date,
        exp_retirement_date=case.retirement_date,
    ))
