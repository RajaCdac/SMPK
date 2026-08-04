"""Time First Pension employee search components."""
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

import django

django.setup()

EMP = "40562"


def timed(label, fn):
    t0 = time.perf_counter()
    try:
        result = fn()
        ms = (time.perf_counter() - t0) * 1000
        print(f"{ms:8.1f} ms  {label}")
        return result
    except Exception as exc:
        ms = (time.perf_counter() - t0) * 1000
        print(f"{ms:8.1f} ms  {label} ERROR: {exc}")
        return None


from first_pension.views import (
    _build_employee_db_context,
    _employee_search_from_mirror,
)
from employee.services.employee_mirror_service import load_employee_from_mirror
from first_pension.services.legacy_prefill_service import (
    load_no_pay_defaults,
    load_amount_defaults,
    enrich_proposal_defaults_from_legacy,
)
from first_pension.services.commutation_defaults_service import load_commutation_defaults
from first_pension.pension_calculation import build_amount_lookup_payload

print("=== component timings ===")
timed("load_employee_from_mirror", lambda: load_employee_from_mirror(EMP))
timed("load_commutation_defaults", lambda: load_commutation_defaults(EMP))
timed("load_no_pay_defaults", lambda: load_no_pay_defaults(EMP))
timed("load_amount_defaults", lambda: load_amount_defaults(EMP))
timed(
    "enrich_proposal_defaults_from_legacy",
    lambda: enrich_proposal_defaults_from_legacy(EMP, None),
)
timed("build_amount_lookup_payload", lambda: build_amount_lookup_payload(EMP))
ctx = timed(
    "_build_employee_db_context",
    lambda: _build_employee_db_context(EMP, include_oracle_intake=True),
)
if ctx:
    existing = ctx.get("_existing_no_pay")
    timed(
        "_employee_search_from_mirror (full)",
        lambda: _employee_search_from_mirror(EMP, {k: v for k, v in ctx.items() if not k.startswith("_")}, existing),
    )

from django.test import RequestFactory
from first_pension.views import EmployeeSearchAPIView

rf = RequestFactory()
req = rf.get(f"/api/first-pension/employees/{EMP}/")
view = EmployeeSearchAPIView.as_view()
timed("FULL EmployeeSearchAPIView GET", lambda: view(req, emp_id=EMP))
