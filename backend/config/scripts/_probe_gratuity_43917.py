import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from employee.services.oracle_service import get_oracle_connection
from first_pension.oracle_mirror import FiPnMhPensioner, FiPnTdSalout

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
    "EMP ADM",
    "SELECT EMP_CD, JOIN_DT, SEPARATION_DT, SEPARATION_TYPE, EXP_RET_DT "
    "FROM FINANCE.FI_XX_MH_EMP_ADM WHERE EMP_CD = :e",
    {"e": EMP},
)

show(
    "OLDBILL PARAM cols",
    "SELECT * FROM FINANCE.FI_PN_MH_OLDBILL_PARAM WHERE EMP_CD = :e",
    {"e": EMP},
)

show(
    "PENSION PROPOSAL",
    "SELECT EMP_CD, CA_NUMBER, GRATUITY_OPTION, SEPARATION_DT, PENSION_OPTION "
    "FROM FINANCE.FI_PN_MH_PENSION_PROPOSAL WHERE EMP_CD = :e",
    {"e": EMP},
)

show(
    "PENSIONER",
    "SELECT GRATUITY, GRATUITY_EMOLUMENTS, TCCS_YR, TCCS_MONTH, TCCS_DAYS, "
    "TQS_YR, TQS_MONTH, TQS_DAYS, PENSION_EMOLUMENTS, ORIGINAL_PENSION_AMT "
    "FROM FINANCE.FI_PN_MH_PENSIONER WHERE EMP_CD = :e",
    {"e": EMP},
)

show(
    "SALOUT last 2 months basic+DA",
    "SELECT SAL_YR, SAL_MTH, EARNDEDN_CD, ACT_EARNDEDN_AMT, ADJ_EARNDEDN_AMT "
    "FROM FINANCE.FI_PN_TD_SALOUT WHERE EMP_CD = :e AND EARNDEDN_CD IN ('001','007') "
    "ORDER BY SAL_YR DESC, SAL_MTH DESC, EARNDEDN_CD",
    {"e": EMP},
)

cur.close()
conn.close()

print("\n=== MYSQL MIRROR PENSIONER ===")
pen = FiPnMhPensioner.objects.filter(emp_cd=EMP).first()
if pen:
    print(
        "gratuity", pen.gratuity,
        "grat_emol", pen.gratuity_emoluments,
        "tccs", pen.tccs_yr, pen.tccs_month, pen.tccs_days,
    )
else:
    print("(none)")

print("\n=== MYSQL PN TD SALOUT (latest) ===")
rows = list(
    FiPnTdSalout.objects.filter(emp_cd=EMP, earndedn_cd__in=["001", "007"])
    .order_by("-sal_yr", "-sal_mth")[:8]
)
for r in rows:
    print(r.sal_yr, r.sal_mth, r.earndedn_cd, r.act_earndedn_amt, r.adj_earndedn_amt)

# Manual formula check with Oracle values
if pen and pen.gratuity_emoluments:
    from first_pension.services.gratuity_emoluments_service import gratuity_qualifying_years
    tccs = gratuity_qualifying_years(pen.tccs_yr, pen.tccs_month, pen.tccs_days)
    emol = float(pen.gratuity_emoluments)
    raw = emol * 15 * tccs / 26
    print(f"\nFormula with mirror emol {emol}, TCCS yrs {tccs}: {raw:.2f}")

print("\n=== ADA RATES 2023 ===")
cur = get_oracle_connection().cursor()
cur.execute(
    """
    SELECT WEF_DT, DA_PCT FROM FINANCE.FI_PR_MH_ADA_RATE_VW
    WHERE WEF_DT >= TO_DATE('2023-01-01', 'YYYY-MM-DD')
      AND EMP_TYPE = 'RE' AND EMP_CLASS_GRP = 1
    ORDER BY WEF_DT
    """
)
for row in cur.fetchall():
    print(row)
cur.close()
