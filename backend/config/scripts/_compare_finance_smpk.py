"""Compare finance vs smpk_pension table presence."""
import MySQLdb

SOURCE = dict(host="127.0.0.1", port=3307, user="root", passwd="root123", db="finance")
TARGET = dict(host="127.0.0.1", port=3306, user="root", passwd="root123", db="smpk_pension")

PREFERRED = [
    "fi_xx_xx_m_h_fin_ctrl", "fi_xx_xx_m_d_fin_ctrl", "fi_xx_mh_dept", "fi_xx_mh_desig",
    "fi_xx_mh_emp_per", "fi_xx_mh_emp_adm", "fi_xx_mh_emp_fin", "fi_xx_mh_emp_data",
    "fi_xx_md_finscale", "fi_pm_mh_bankabbr", "fi_pm_mh_bank", "fi_pm_mh_payscale",
    "fi_pn_mh_earndedn", "fi_pn_mh_erndednmap", "fi_pn_mh_jrnltype", "fi_pn_md_jrnltype",
    "fi_pn_mh_ada_rate", "fi_pn_mh_base_cpi", "fi_pn_md_commrate_rupee",
    "fi_pn_mh_death_gratchart", "fi_pn_md_death_gratchart", "fi_pn_mh_service_gratchart",
    "fi_pn_md_maxadm_gratuity", "fi_pn_mh_billtype", "fi_pn_md_edbilltype_map",
    "fi_pn_mh_pmthsetup", "fi_pn_mh_oldbill_param", "fi_pn_mh_application",
    "fi_pn_mh_pension_proposal", "fi_pn_md_pension_proposal", "fi_pn_mh_pensioner",
    "fi_pn_th_salout", "fi_pn_td_salout", "fi_pr_th_salout", "fi_pr_td_salout",
    "fi_pr_mh_erndednmap", "fi_pn_th_first_month_pension", "fi_pn_td_first_month_pension",
    "fi_pn_th_pension_bill", "fi_pn_th_billpass", "fi_pn_td_billpass", "fi_pn_mh_bill_print",
    "fi_pn_th_jv", "fi_pn_td_jv", "fi_pn_th_sepcom", "fi_pn_td_sepcom",
]

RUNTIME_FINANCE = [
    "fi_pm_mh_relation", "fi_pn_md_fpen_appcn", "fi_pn_md_pension_proposal",
    "fi_pn_mh_application", "fi_pn_mh_erndednmap", "fi_pn_mh_fpen_caclaim",
    "fi_pn_mh_oldbill_param", "fi_pn_mh_pension_proposal", "fi_pn_mh_pensioner",
    "fi_pn_td_jv", "fi_pn_th_billpass", "fi_pn_th_first_month_pension",
    "fi_pn_th_jv", "fi_pn_th_pension_bill", "fi_xx_mh_emp_adm", "fi_xx_mh_emp_fin",
    "fi_xx_mh_emp_per",
]

FP_TABLES = [
    "fi_pn_mh_familypensioner", "fi_pn_mh_fpen_caclaim", "fi_pn_md_fpen_appcn",
    "fi_pm_mh_relation", "fi_xx_mh_emp_per", "fi_pn_mh_familypensioner_prev",
    "fi_pn_th_first_month_fpen", "fi_pn_td_first_month_fpen", "fi_pn_th_fpension_bill",
    "fi_pn_mh_consolidation", "fi_pn_wage_2022_hdr_third", "fi_pn_wage_2017_hdr_offi2",
]

src = MySQLdb.connect(**SOURCE)
tgt = MySQLdb.connect(**TARGET)
sc = src.cursor()
tc = tgt.cursor()
sc.execute(
    "SELECT table_name FROM information_schema.tables "
    "WHERE table_schema='finance' AND table_name LIKE 'fi_%'"
)
finance_all = {r[0].lower() for r in sc.fetchall()}
tc.execute(
    "SELECT table_name FROM information_schema.tables "
    "WHERE table_schema='smpk_pension' AND table_name LIKE 'fi_%'"
)
smpk_all = {r[0].lower() for r in tc.fetchall()}


def report(title, tables):
    print(f"\n=== {title} ===")
    for t in tables:
        fin = "yes" if t in finance_all else "no"
        smpk = "yes" if t in smpk_all else "MISSING"
        print(f"  {t:40} finance={fin:3}  smpk_pension={smpk}")


report("FAMILY PENSION — import priority", FP_TABLES)
report("RUNTIME connections['finance']", RUNTIME_FINANCE)
report("FIRST PENSION sync list — missing only", [t for t in PREFERRED if t not in smpk_all])
