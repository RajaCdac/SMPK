import os, sys, time
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
import django; django.setup()

EMP = "40562"

def timed(label, fn):
    t0 = time.perf_counter()
    try:
        r = fn()
        print(f"{(time.perf_counter()-t0)*1000:8.1f} ms  {label}")
        return r
    except Exception as e:
        print(f"{(time.perf_counter()-t0)*1000:8.1f} ms  {label} ERR {e}")
        return None

from first_pension.pension_calculation import (
    reload_pension_case_from_db,
    is_voluntary_retirement,
    get_commutation_percent_for_employee,
    serialize_amount_data,
    get_commutation_application_for_employee,
)
from first_pension.models import PensionSummary
from first_pension.services.first_month_pension_service import get_first_month_status
from first_pension.services.salout_transfer_service import (
    get_salout_status,
    resolve_emoluments_basic,
)
from first_pension.services.legacy_prefill_service import load_amount_defaults

case = timed("reload case", lambda: reload_pension_case_from_db(EMP))
timed("load_amount_defaults", lambda: load_amount_defaults(EMP))
timed("is_vr", lambda: is_voluntary_retirement(EMP))
timed("comm%", lambda: get_commutation_percent_for_employee(EMP, require_saved=False))
timed("comm app", lambda: get_commutation_application_for_employee(EMP))
summary = timed("summary", lambda: PensionSummary.objects.filter(pension_case_id=case.id).first())
timed("serialize_amount", lambda: serialize_amount_data(case, summary, None))
timed("first_month_status", lambda: get_first_month_status(EMP))
timed("resolve_emoluments", lambda: resolve_emoluments_basic(EMP, fallback_last_basic=float(case.last_basic)))
timed("get_salout_status", lambda: get_salout_status(EMP))
