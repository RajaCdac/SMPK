import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from employee.services.oracle_service import get_oracle_connection
from first_pension.services.gratuity_emoluments_service import (
    calculate_gratuity_payable,
    calculate_ffunc_dcr_gratuity,
    gratuity_qualifying_years,
    resolve_gratuity_emoluments,
)
from first_pension.pension_calculation import (
    fetch_calculation_inputs_from_db,
    resolve_separation_date,
)

EMP = "43917"
conn = get_oracle_connection()
cur = conn.cursor()


def show(title, sql, binds=None):
    print(f"\n=== {title} ===")
    cur.execute(sql, binds or {})
    cols = [d[0] for d in cur.description]
    print(" | ".join(cols))
    rows = cur.fetchall()
    if not rows:
        print("(no rows)")
    for row in rows:
        print(" | ".join(str(v) for v in row))


show(
    "PENSIONER",
    "SELECT GRATUITY, GRATUITY_EMOLUMENTS, TCCS_YR, TCCS_MONTH, TCCS_DAYS, "
    "TQS_YR, TQS_MONTH, TQS_DAYS "
    "FROM FINANCE.FI_PN_MH_PENSIONER WHERE EMP_CD = :e",
    {"e": EMP},
)

show(
    "PROPOSAL EXTRA TCCS",
    """
    SELECT EXTRA_GRAT_TCCS_FLG, EXTRA_GRAT_TCCS_YR, EXTRA_GRAT_TCCS_MON, EXTRA_GRAT_TCCS_DAYS,
           GRATUITY_OPTION, SEPARATION_DT
    FROM FINANCE.FI_PN_MH_PENSION_PROPOSAL WHERE EMP_CD = :e
    """,
    {"e": EMP},
)

show(
    "MAXADM all matching rows (latest first)",
    """
    SELECT RET_DT_FROM, RET_DT_TO, MAX_EMOLUMENT, MAX_ADM_GRATUITY
    FROM FINANCE.FI_PN_MD_MAXADM_GRATUITY
    WHERE GRATUITY_TYPE = 1
      AND TO_DATE('2024-01-01','YYYY-MM-DD') BETWEEN RET_DT_FROM
          AND NVL(RET_DT_TO, TO_DATE('2024-01-01','YYYY-MM-DD'))
    ORDER BY RET_DT_FROM DESC
    """,
)

show(
    "PENSIONER service extras",
    """
    SELECT TCCS_YR, TCCS_MONTH, TCCS_DAYS, TQS_YR, TQS_MONTH, TQS_DAYS,
           BOY_S_YR, BOY_S_MONTH, BOY_S_DAYS, DIES_NON_PERIOD, NO_PAY_PERIOD
    FROM FINANCE.FI_PN_MH_PENSIONER WHERE EMP_CD = :e
    """,
    {"e": EMP},
)

# Try GRAT_CAL if callable
try:
    cur2 = get_oracle_connection().cursor()
    cur2.execute(
        """
        SELECT object_name, argument_name, data_type, position
        FROM all_arguments
        WHERE owner = 'FINANCE' AND object_name = 'GRAT_CAL'
        ORDER BY position
        """
    )
    print("\n=== GRAT_CAL args ===")
    for row in cur2.fetchall():
        print(row)
    cur2.close()
except Exception as exc:
    print("GRAT_CAL args error", exc)

    """
    SELECT object_name, object_type FROM all_objects
    WHERE owner = 'FINANCE' AND object_name LIKE '%GRAT%'
    ORDER BY object_name
    """
)
print("\n=== FINANCE GRAT objects ===")
for row in cur.fetchall():
    print(row)

cur.close()
conn.close()

inputs = fetch_calculation_inputs_from_db(EMP)
sep = resolve_separation_date(EMP)
em, src, _ = resolve_gratuity_emoluments(
    EMP, inputs["emp_class"], inputs["last_basic"], separation_dt=sep
)

# Oracle pensioner service values
tccs = (28, 7, 25)
tqs = (28, 7, 14)

from first_pension.models import PensionCase

case = PensionCase.objects.filter(emp_code=EMP).first()
if case:
    try:
        s = case.summary
        tccs = (s.tccs_years, s.tccs_months, s.tccs_days)
        tqs = (s.tqs_years, s.tqs_months, s.tqs_days)
    except Exception:
        pass

print("\n=== SERVICE INPUTS ===")
print("emoluments", em, src)
print("TCCS", tccs, "TQS", tqs)
print("TCCS yrs rounded", gratuity_qualifying_years(*tccs))
print("TQS yrs rounded", gratuity_qualifying_years(*tqs))

opt_i = calculate_ffunc_dcr_gratuity(
    emoluments=em,
    gratuity_option=0,
    separation_dt=sep,
    tccs_years=tccs[0],
    tccs_months=tccs[1],
    tccs_days=tccs[2],
    tqs_years=tqs[0],
    tqs_months=tqs[1],
    tqs_days=tqs[2],
    emp_cd=EMP,
    emp_class=inputs["emp_class"],
)
opt_ii = calculate_ffunc_dcr_gratuity(
    emoluments=em,
    gratuity_option=1,
    separation_dt=sep,
    tccs_years=tccs[0],
    tccs_months=tccs[1],
    tccs_days=tccs[2],
    tqs_years=tqs[0],
    tqs_months=tqs[1],
    tqs_days=tqs[2],
    emp_cd=EMP,
    emp_class=inputs["emp_class"],
)
pay = calculate_gratuity_payable(
    emoluments=em,
    separation_dt=sep,
    tccs_years=tccs[0],
    tccs_months=tccs[1],
    tccs_days=tccs[2],
    tqs_years=tqs[0],
    tqs_months=tqs[1],
    tqs_days=tqs[2],
    emp_cd=EMP,
    emp_class=inputs["emp_class"],
)

print("\n=== SMPK BREAKDOWN ===")
print("Opt-I formula", opt_i["formula_amount"], "capped", opt_i["gratuity_amount"])
print("Opt-II formula", opt_ii["formula_amount"], "capped", opt_ii["gratuity_amount"])
print("emoluments used opt-ii", opt_ii.get("gratuity_emoluments_used"))
print("qual yrs opt-ii", opt_ii.get("gratuity_qualifying_years"))
print("payable", pay["gratuity_amount"])

print("\n=== REVERSE 1565973 ===")
target = 1565973
emol_oracle = 94907.44
for tqs_y in range(27, 34):
    v = emol_oracle * tqs_y / 2
    print(f"  emol {emol_oracle} x tqs {tqs_y} / 2 = {v:.2f}", "MATCH" if abs(v - target) < 5000 else "")

# max emolument cap effect
cur = get_oracle_connection().cursor()
cur.execute(
    """
    SELECT MAX_EMOLUMENT, MAX_ADM_GRATUITY
    FROM FINANCE.FI_PN_MD_MAXADM_GRATUITY
    WHERE GRATUITY_TYPE = 1
      AND TO_DATE('2024-01-01','YYYY-MM-DD') BETWEEN RET_DT_FROM
          AND NVL(RET_DT_TO, TO_DATE('2024-01-01','YYYY-MM-DD'))
    """
)
row = cur.fetchone()
if row:
    max_emol, max_adm = float(row[0] or 0), float(row[1] or 0)
    em_used = min(emol_oracle, max_emol) if max_emol > 0 else emol_oracle
    tqs_r = gratuity_qualifying_years(*tqs)
    if tqs_r > 33:
        tqs_r = 33
    raw = em_used * tqs_r / 2
    print(f"\nmax_emol={max_emol} max_adm={max_adm}")
    print(f"em_used={em_used} tqs={tqs_r} raw={raw}")
cur.close()
