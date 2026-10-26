import os
from collections import Counter

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from django.db import connection
from M2_oldage_arrear.models import M2OldageArrearConsolidation as OA
from methodology2.models import Methodology2Consolidation as M2

m2_fields = {f.name for f in M2._meta.concrete_fields}
oa_fields = {f.name for f in OA._meta.concrete_fields}
print("DB:", connection.settings_dict.get("NAME"), connection.settings_dict.get("HOST"), connection.settings_dict.get("PORT"))
print("Only in methodology2_consolidation:", sorted(m2_fields - oa_fields))
print("Only in m2_oldage_arrear_consolidation:", sorted(oa_fields - m2_fields))

m2_emps = set(M2.objects.values_list("emp_cd", flat=True))
oa_emps = set(OA.objects.values_list("emp_cd", flat=True))
both = m2_emps & oa_emps
only_m2 = m2_emps - oa_emps
print(f"methodology2_consolidation rows: {len(m2_emps)}")
print(f"m2_oldage_arrear_consolidation rows: {len(oa_emps)}")
print(f"in both (keep old-age row): {len(both)}")
print(f"only in methodology2 (would be imported): {len(only_m2)}")
print(f"only in old-age: {len(oa_emps - m2_emps)}")

q = M2.objects.filter(emp_cd__in=only_m2)
print("to-import: payment_done =", q.filter(payment_done=True).count())
print("to-import: employee pension =", q.filter(is_employee_pension=True).count(),
      "family =", q.filter(is_employee_pension=False).count())
print("to-import by category:", Counter(q.values_list("category", flat=True)))
dates = list(q.exclude(updated_at=None).values_list("updated_at", flat=True))
if dates:
    print("to-import updated_at range:", min(dates), "->", max(dates))
print("to-import consolidated_by:", Counter(q.values_list("consolidated_by", flat=True)).most_common(8))

# Same emp in both: how different are they?
diff = 0
for emp in list(both)[:2000]:
    a = M2.objects.filter(emp_cd=emp).values("m2_pension_277", "m2_family_pension_277", "m1_family_pension_277").first()
    b = OA.objects.filter(emp_cd=emp).values("m2_pension_277", "m2_family_pension_277", "m1_family_pension_277").first()
    if a != b:
        diff += 1
print(f"in both with different 277 amounts: {diff} of {min(len(both), 2000)} checked")

try:
    from methodology2.models import M2ConsolCase
    print("M2ConsolCase by source:", Counter(M2ConsolCase.objects.values_list("source_app", flat=True)))
except Exception as exc:
    print("M2ConsolCase:", exc)
