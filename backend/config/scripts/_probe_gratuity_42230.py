import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from employee.services.oracle_service import get_oracle_connection
from first_pension.oracle_mirror import FiPnMhPensioner
from first_pension.pension_calculation import (
    fetch_calculation_inputs_from_db,
    get_separation_type_for_employee,
    resolve_separation_date,
)
from first_pension.services.gratuity_emoluments_service import (
    calculate_gratuity_payable,
    gratuity_qualifying_years,
    qualifying_tqs_for_gratuity_opt_ii,
    resolve_gratuity_emoluments,
)

EMP = "42230"
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
    "EMP ADM",
    "SELECT EMP_CD, JOIN_DT, SEPARATION_DT, SEPARATION_TYPE, EXP_RET_DT "
    "FROM FINANCE.FI_XX_MH_EMP_ADM WHERE EMP_CD = :e",
    {"e": EMP},
)
show(
    "PENSIONER",
    "SELECT GRATUITY, GRATUITY_EMOLUMENTS, TCCS_YR, TCCS_MONTH, TCCS_DAYS, "
    "TQS_YR, TQS_MONTH, TQS_DAYS, PENSION_EMOLUMENTS "
    "FROM FINANCE.FI_PN_MH_PENSIONER WHERE EMP_CD = :e",
    {"e": EMP},
)
show(
    "PROPOSAL",
    "SELECT GRATUITY_OPTION, SEPARATION_DT FROM FINANCE.FI_PN_MH_PENSION_PROPOSAL "
    "WHERE EMP_CD = :e",
    {"e": EMP},
)
show(
    "PN SALOUT latest",
    "SELECT SAL_YR, SAL_MTH, EARNDEDN_CD, ACT_EARNDEDN_AMT, ADJ_EARNDEDN_AMT "
    "FROM FINANCE.FI_PN_TD_SALOUT WHERE EMP_CD = :e AND EARNDEDN_CD IN ('001','007','111') "
    "ORDER BY SAL_YR DESC, SAL_MTH DESC, EARNDEDN_CD",
    {"e": EMP},
)
show(
    "PR SALOUT latest",
    "SELECT * FROM ("
    "  SELECT SAL_YR, SAL_MTH, EARNDEDN_CD, ACT_EARNDEDN_AMT, ADJ_EARNDEDN_AMT "
    "  FROM FINANCE.FI_PR_TD_SALOUT WHERE EMP_CD = :e AND EARNDEDN_CD IN ('001','007','111') "
    "  ORDER BY SAL_YR DESC, SAL_MTH DESC, EARNDEDN_CD"
    ") WHERE ROWNUM <= 12",
    {"e": EMP},
)

inputs = fetch_calculation_inputs_from_db(EMP)
sep = resolve_separation_date(EMP)
st = get_separation_type_for_employee(EMP)
print("\n=== SMPK inputs ===")
print(
    "emp_class",
    inputs.get("emp_class"),
    "last_basic",
    inputs.get("last_basic"),
    "sep",
    sep,
    "sep_type",
    st,
)

em, src, detail = resolve_gratuity_emoluments(
    EMP, inputs["emp_class"], inputs["last_basic"], separation_dt=sep
)
print("emoluments", em, "source", src)
print("detail", detail)

pen = FiPnMhPensioner.objects.filter(emp_cd=EMP).first()
if pen:
    print(
        "mysql pensioner gratuity",
        pen.gratuity,
        "grat_emol",
        pen.gratuity_emoluments,
    )

cur.execute(
    "SELECT TCCS_YR, TCCS_MONTH, TCCS_DAYS, TQS_YR, TQS_MONTH, TQS_DAYS, "
    "GRATUITY_EMOLUMENTS, GRATUITY FROM FINANCE.FI_PN_MH_PENSIONER WHERE EMP_CD = :e",
    {"e": EMP},
)
ty, tm, td, qy, qm, qd, ge, g = cur.fetchone()
print(f"\nOracle TCCS {ty}/{tm}/{td} TQS {qy}/{qm}/{qd}")
tccs = gratuity_qualifying_years(ty, tm, td)
tqs = qualifying_tqs_for_gratuity_opt_ii(qy, qm, qd, separation_type=st)
print("qual TCCS", tccs, "qual TQS", tqs)
print("formula opt-I with oracle emol", float(ge) * 15 * tccs / 26)
print("formula opt-II with oracle emol", float(ge) * tqs / 2)
print("Oracle stored gratuity", g)

r = calculate_gratuity_payable(
    emoluments=em,
    separation_dt=sep,
    tccs_years=ty,
    tccs_months=tm,
    tccs_days=td,
    tqs_years=qy,
    tqs_months=qm,
    tqs_days=qd,
    emp_cd=EMP,
    emp_class=inputs["emp_class"],
    separation_type=st,
)
print("\n=== SMPK gratuity result ===")
for k, v in sorted(r.items()):
    if any(x in k for x in ("gratuity", "cap", "emol", "opt")):
        print(k, v)

cur.close()
conn.close()
