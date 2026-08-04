import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from django.db import connection
from first_pension.oracle_mirror import FiPnTdSalout

print("=== MySQL fi_pn_th_salout exists? ===")
with connection.cursor() as c:
    try:
        c.execute("DESCRIBE fi_pn_th_salout")
        print(c.fetchall())
    except Exception as e:
        print("NO:", e)

print("\n=== 43186 salout all rows ===")
for r in FiPnTdSalout.objects.filter(emp_cd="43186").order_by("sal_yr", "sal_mth", "earndedn_cd"):
    net = float(r.act_earndedn_amt or 0) + float(r.adj_earndedn_amt or 0)
    print(f"  {r.sal_mth:02d}/{r.sal_yr} cd={r.earndedn_cd} type={r.earndedn_type} act={r.act_earndedn_amt} adj={r.adj_earndedn_amt} net={net}")

print("\n=== 10-month basic average (code 001) for 43186 ===")
rows = list(
    FiPnTdSalout.objects.filter(emp_cd="43186", earndedn_cd="001")
    .order_by("-sal_yr", "-sal_mth")[:10]
)
basics = []
for r in rows:
    net = float(r.act_earndedn_amt or 0) + float(r.adj_earndedn_amt or 0)
    basics.append(net)
    print(f"  {r.sal_mth:02d}/{r.sal_yr} net basic={net}")
if basics:
    avg = sum(basics) / len(basics)
    print(f"  AVG={avg:.2f}  pension@50%={avg*0.5:.2f}")

print("\n=== Compare pension sources 43186 ===")
from first_pension.models import PensionCase, PensionSummary
from first_pension.oracle_mirror import FiPnMhApplication, FiPnMhPensioner

case = PensionCase.objects.filter(emp_code="43186").first()
summary = PensionSummary.objects.filter(pension_case=case).first() if case else None
app = FiPnMhApplication.objects.filter(emp_cd="43186").order_by("-appcn_dt").first()
pen = FiPnMhPensioner.objects.filter(emp_cd="43186").first()
print("  SMPK last_basic:", case.last_basic if case else None)
print("  SMPK summary pension:", summary.pension_amount if summary else None)
print("  Oracle app pen_amt:", app.pen_amt if app else None)
print("  Oracle pensioner orig:", pen.original_pension_amt if pen else None)

try:
    from employee.services.oracle_service import get_oracle_connection

    conn = get_oracle_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT table_name FROM all_tables WHERE owner='FINANCE' AND table_name LIKE '%SALOUT%'"
    )
    print("\n=== Oracle SALOUT tables (FI_PN only) ===")
    print([r[0] for r in cur.fetchall() if r[0].startswith("FI_PN_")])
    for t in ["FI_PN_TH_SALOUT", "FI_PN_TD_SALOUT"]:
        cur.execute(
            "SELECT column_name FROM all_tab_columns WHERE owner='FINANCE' AND table_name=:t ORDER BY column_id",
            {"t": t},
        )
        cols = [r[0] for r in cur.fetchall()]
        print(f"\n{t} columns ({len(cols)}):", cols)

    cur.execute(
        """
        SELECT SAL_MTH, SAL_YR, FA_NO, SAL_BILL_NO, GROSS_EARN_AMT, GROSS_DEDN_AMT,
               NET_EARN_AMT, SCALE_DESC, BASIC_RATE, WG_ST_DT, WG_END_DT
        FROM (
            SELECT * FROM FINANCE.FI_PN_TH_SALOUT
            WHERE EMP_CD = '43186'
            ORDER BY SAL_YR DESC, SAL_MTH DESC
        ) WHERE ROWNUM <= 12
        """
    )
    print("\n=== Oracle TH_SALOUT 43186 (last 12) ===")
    for row in cur.fetchall():
        print(row)

    cur.execute(
        """
        SELECT SAL_MTH, SAL_YR, EARNDEDN_CD, ACT_EARNDEDN_AMT, ADJ_EARNDEDN_AMT
        FROM (
            SELECT * FROM FINANCE.FI_PN_TD_SALOUT
            WHERE EMP_CD = '43186' AND EARNDEDN_CD = '001'
            ORDER BY SAL_YR DESC, SAL_MTH DESC
        ) WHERE ROWNUM <= 12
        """
    )
    print("\n=== Oracle TD_SALOUT 43186 basic 001 ===")
    for row in cur.fetchall():
        print(row)

    cur.close()
    conn.close()
except Exception as e:
    print("\nOracle probe:", e)
