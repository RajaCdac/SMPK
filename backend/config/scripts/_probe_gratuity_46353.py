import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from employee.services.oracle_service import try_oracle_connection, oracle_reads_enabled
from first_pension.pension_calculation import (
    fetch_calculation_inputs_from_db,
    highest_side_round,
    resolve_service_tenure,
)
from first_pension.services.gratuity_emoluments_service import (
    gratuity_qualifying_years,
    qualifying_tqs_for_gratuity_opt_ii,
    resolve_gratuity_emoluments,
    round_tqs_years_oracle,
)

EMP = "46353"

print("oracle_reads_enabled", oracle_reads_enabled())
conn = try_oracle_connection()
if conn:
    cur = conn.cursor()

    def show(title, sql, binds=None):
        print(f"\n=== {title} ===")
        cur.execute(sql, binds or {})
        cols = [d[0] for d in cur.description]
        print(" | ".join(cols))
        for row in cur.fetchall():
            print(" | ".join(str(v) for v in row))

    for fn, args in [
        ("FFUNC_TQS_ROUND_2(N)", ("46353", "N")),
        ("FFUNC_TQS_ROUND_2(Y)", ("46353", "Y")),
        ("FFUNC_DCR_GRATUITY opt0", ("46353", "G", 0)),
        ("FFUNC_DCR_GRATUITY opt1", ("46353", "G", 1)),
    ]:
        try:
            if "DCR" in fn:
                cur.execute(
                    "SELECT FINANCE.FFUNC_DCR_GRATUITY(:e,:p,:o) FROM DUAL",
                    {"e": args[0], "p": args[1], "o": args[2]},
                )
            else:
                cur.execute(
                    "SELECT FINANCE.FFUNC_TQS_ROUND_2(:e,:d) FROM DUAL",
                    {"e": args[0], "d": args[1]},
                )
            print(fn, cur.fetchone()[0])
        except Exception as exc:
            print(fn, "ERR", exc)

    show(
        "PENSIONER globals",
        """
        SELECT GRATUITY, GRATUITY_EMOLUMENTS,
               TCCS_YR, TCCS_MONTH, TCCS_DAYS,
               TQS_YR, TQS_MONTH, TQS_DAYS,
               NO_PAY_PERIOD, DIES_NON_PERIOD
        FROM FINANCE.FI_PN_MH_PENSIONER WHERE EMP_CD = :e
        """,
        {"e": EMP},
    )
    show(
        "OLDBILL",
        """
        SELECT NPAY_PRIOR_10MTH, NPAY_MORETHAN_240_DYS, DNON_DAYS, SUSP_DAYS, BOY_SERV_DAYS
        FROM FINANCE.FI_PN_MH_OLDBILL_PARAM WHERE EMP_CD = :e
        """,
        {"e": EMP},
    )
    cur.close()
    conn.close()
else:
    print("Oracle not available")

inputs = fetch_calculation_inputs_from_db(EMP)
t = resolve_service_tenure(
    joining_date=inputs["joining_date"],
    service_end=inputs["separation_date"],
    no_pay_days=inputs["no_pay_days"],
    dies_non_days=inputs["dies_non_days"],
    no_pay_more_than_240_days=inputs["no_pay_more_than_240_days"],
    suspension_days=inputs["suspension_days"],
    boys_serv_days=inputs["boys_serv_days"],
)
emol, _, _ = resolve_gratuity_emoluments(
    EMP, inputs["case"].emp_class, inputs["case"].last_basic,
    separation_dt=inputs["separation_date"],
)
print("\n=== SMPK ===")
print("TQS y/m/d", t["tqs_years"], t["tqs_months"], t["tqs_days"])
print("round_tqs_oracle", round_tqs_years_oracle(t["tqs_years"], t["tqs_months"], t["tqs_days"]))
print("optII qual", qualifying_tqs_for_gratuity_opt_ii(
    t["tqs_years"], t["tqs_months"], t["tqs_days"],
    separation_type=inputs["case"].separation_type,
    joining_date=inputs["joining_date"],
    exp_retirement_date=inputs["retirement_date"],
))
print("emoluments", emol)
for q in [32, 32.5]:
    amt = highest_side_round(emol * q / 2)
    print(f"formula tqs={q}", amt)
