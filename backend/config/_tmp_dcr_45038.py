"""Debug death DCR gratuity for emp 45038."""
import os
import sys

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import django

django.setup()

from django.db import connection
from family_pension.services.dcr_gratuity_service import (
    compute_gratuity_emoluments,
    compute_tqs,
    ffunc_dcr_gratuity,
    _chart_multi_factor,
    _death_mh_limits,
    _last_sal_ym,
    _map_earn_cd,
    _salout_rate,
)


def q(sql, params=None):
    with connection.cursor() as cur:
        cur.execute(sql, params or [])
        cols = [d[0].lower() for d in cur.description]
        return [dict(zip(cols, r)) for r in cur.fetchall()]


emp = "45038"
print("=== ADM / PER / PENSIONER / CLAIM ===")
for sql in (
    "SELECT EMP_CD, JOIN_DT, SEPARATION_DT, SEPARATION_TYPE, EXP_RET_DT, DESIG_CD, CLASS FROM fi_xx_mh_emp_adm WHERE EMP_CD=%s",
    "SELECT EMP_CD, BIRTH_DT FROM fi_xx_mh_emp_per WHERE EMP_CD=%s",
    "SELECT EMP_CD, DOD, RETIREMENT_DT, PENSION_OPTION, BASE_CPI, LAST_PAY, PENSION_ROLL_NO FROM fi_pn_mh_pensioner WHERE EMP_CD=%s",
    "SELECT EMP_CD, DOD, RETIREMENT_DT, PENSION_OPT, INCENTIVE_HOLDER_FLG, LAST_PAY, CATEGORY FROM fi_pn_th_fpension_claim WHERE EMP_CD=%s ORDER BY 1",
    "SELECT FAM_FMPEN_ID, EMP_CD, FPENSION_TYPE, FPENSION_AMT, RELIEF, GRATUITY_AMT, TQS, TCCS FROM fi_pn_th_first_month_fpension WHERE EMP_CD=%s",
):
    try:
        rows = q(sql, [emp])
        print(sql.split(" FROM ")[1][:40], rows)
    except Exception as e:
        print("ERR", sql[:50], e)

print("\n=== TQS ===")
tqs = compute_tqs(emp)
print(tqs)

print("\n=== LAST SAL ===")
print(_last_sal_ym(emp))
for map_cd in (101, 103, 107):
    cd = _map_earn_cd(map_cd)
    yr, mth = _last_sal_ym(emp)
    print("map", map_cd, "cd", cd, "rate", _salout_rate(emp, cd, yr, mth) if yr else None)

print("\n=== EMOL ===")
print(compute_gratuity_emoluments(emp, last_basic_fallback=None, emp_class="3", as_of=tqs.separation_dt))

print("\n=== DCR ===")
print(ffunc_dcr_gratuity(emp, gratuity_option=2, emp_class="3", retirement_dt=tqs.separation_dt))

print("\n=== MH CHART ===")
print(_death_mh_limits(tqs.separation_dt))
print("factor for tqs", tqs.tqs, _chart_multi_factor(tqs.tqs, tqs.separation_dt))
print("factor 33", _chart_multi_factor(33, tqs.separation_dt))
print("factor 20", _chart_multi_factor(20, tqs.separation_dt))
print("factor 12", _chart_multi_factor(12, tqs.separation_dt))

print("\n=== MD CHART ROWS ===")
try:
    print(q("SELECT * FROM fi_pn_md_death_gratchart ORDER BY wef_dt DESC, tqs_start_yrs"))
except Exception as e:
    print(e)
print("\n=== MH CHART ROWS ===")
try:
    print(q("SELECT * FROM fi_pn_mh_death_gratchart ORDER BY wef_dt DESC"))
except Exception as e:
    print(e)

print("\n=== SALOUT LAST 3 ===")
try:
    print(q(
        """
        SELECT SAL_YR, SAL_MTH, EARNDEDN_CD, RATE, ACT_EARNDEDN_AMT
        FROM fi_pn_td_salout WHERE EMP_CD=%s
        ORDER BY SAL_YR DESC, SAL_MTH DESC, EARNDEDN_CD
        LIMIT 30
        """,
        [emp],
    ))
except Exception as e:
    print("pn salout", e)
try:
    print(q(
        """
        SELECT SAL_YR, SAL_MTH, EARNDEDN_CD, RATE, ACT_EARNDEDN_AMT
        FROM fi_pr_td_salout WHERE EMP_CD=%s
        ORDER BY SAL_YR DESC, SAL_MTH DESC, EARNDEDN_CD
        LIMIT 30
        """,
        [emp],
    ))
except Exception as e:
    print("pr salout", e)
