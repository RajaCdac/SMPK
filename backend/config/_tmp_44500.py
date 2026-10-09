import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from django.db import connection

emp = "44500"
tables = [
    "fi_pn_wage_2017_hdr_offi2",
    "fi_pn_wage_2017_hdr_third",
    "fi_pn_wage_2022_hdr_third",
]
with connection.cursor() as cursor:
    for table in tables:
        cursor.execute(
            f"""
            SELECT EMP_CD, EMP_NAME, PEN_NAME, PENSIONER_TYPE, CASE_NO, ROLL_NO,
                   OLD_BASIC_PENSION, REV_BASIC_PENSION,
                   OLD_SINGLE_BASIC_PENSION, REV_SINGLE_BASIC_PENSION
            FROM {table}
            WHERE EMP_CD = %s
            """,
            [emp],
        )
        rows = cursor.fetchall()
        print("TABLE", table, "count", len(rows))
        for row in rows:
            print(" ", row)

    cursor.execute(
        """
        SELECT EMP_CD, ORIGINAL_PENSION_AMT, APP_CLASS
        FROM fi_pn_mh_pensioner
        WHERE EMP_CD = %s
        LIMIT 5
        """,
        [emp],
    )
    print("PENSIONER", cursor.fetchall())
    cursor.execute(
        """
        SELECT p.EMP_CD, p.EMP_NAME, p.PEN_NAME, p.PENSIONER_TYPE, p.ROLL_NO,
               p.OLD_BASIC_PENSION, p.REV_BASIC_PENSION,
               p.OLD_SINGLE_BASIC_PENSION, p.REV_SINGLE_BASIC_PENSION
        FROM fi_pn_wage_2017_hdr_offi2 f
        INNER JOIN fi_pn_wage_2017_hdr_offi2 p
          ON p.CASE_NO = f.CASE_NO
        WHERE f.EMP_CD = %s
        """,
        [emp],
    )
    print("CASE ROWS")
    for row in cursor.fetchall():
        print(" ", row)

from methodology2.services.consolidation_service import (
    fetch_methodology1_pension_from_wage,
    build_pension_comparison,
)

for cat in ("1",):
    wage = fetch_methodology1_pension_from_wage(emp, category=cat)
    if wage.get("wage_by_type") or wage.get("date_of_death"):
        print("--- category", cat)
        print("dod", wage.get("date_of_death"), "upto", wage.get("double_fpension_upto"))
        print("cutover", wage.get("rate_cutover"), "enhanced", wage.get("enhanced_family_pension"))
        print("dih", wage.get("die_in_harness"), "case", wage.get("case_type"))
        print("m1_277", wage.get("m1_family_pension_277"), "m1_359", wage.get("m1_family_pension_359"))
        for k, v in (wage.get("wage_by_type") or {}).items():
            print(" ", k, {kk: v.get(kk) for kk in (
                "m1_277", "m1_359", "m1_single_277", "m1_single_359",
                "m1_enhanced_277", "m1_old_basic_pension", "m1_rev_basic_pension",
                "m1_old_single_basic_pension", "m1_rev_single_basic_pension",
                "pensioner_type",
            )})
        cmp = build_pension_comparison(
            date_of_death=wage.get("date_of_death"),
            wage_by_type=wage.get("wage_by_type") or {},
            m2_emp_277=54765,
            m2_emp_359=None,
            m2_fam_277=None,
            m2_fam_359=None,
            double_fpension_upto=wage.get("double_fpension_upto"),
            enhanced_family_pension=wage.get("enhanced_family_pension"),
            rate_cutover=wage.get("rate_cutover"),
            die_in_harness=wage.get("die_in_harness"),
            case_type=wage.get("case_type"),
            category=cat,
        )
        for col in cmp.get("columns") or []:
            print(
                "COL",
                col.get("kind"),
                col.get("period_note"),
                "m2",
                col.get("m2"),
                "m1",
                col.get("m1"),
            )
        break

wage63 = fetch_methodology1_pension_from_wage("44563", category="1")
cmp63 = build_pension_comparison(
    date_of_death=wage63.get("date_of_death"),
    wage_by_type=wage63.get("wage_by_type") or {},
    m2_emp_277=51705,
    m2_emp_359=None,
    m2_fam_277=31023,
    m2_fam_359=None,
    double_fpension_upto=wage63.get("double_fpension_upto"),
    enhanced_family_pension=wage63.get("enhanced_family_pension"),
    rate_cutover=wage63.get("rate_cutover"),
    die_in_harness=wage63.get("die_in_harness"),
    case_type=wage63.get("case_type"),
    category="1",
)
print("--- 44563")
for col in cmp63.get("columns") or []:
    print(col.get("kind"), col.get("period_note"), "m1", col.get("m1"), "m2", col.get("m2"))
