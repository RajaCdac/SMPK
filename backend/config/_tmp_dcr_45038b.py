import os, sys
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import django
django.setup()
from django.db import connection

def q(sql, p=None):
    with connection.cursor() as cur:
        cur.execute(sql, p or [])
        if not cur.description:
            return []
        cols = [d[0].lower() for d in cur.description]
        return [dict(zip(cols, r)) for r in cur.fetchall()]

emp='45038'
print('adm', q("SELECT EMP_CD, JOIN_DT, SEPARATION_DT, SEPARATION_TYPE, EXP_RET_DT FROM fi_xx_mh_emp_adm WHERE EMP_CD=%s",[emp]))
print('pensioner cols try')
print(q("SHOW COLUMNS FROM fi_pn_mh_pensioner LIKE '%RET%'"))
print(q("SHOW COLUMNS FROM fi_pn_mh_pensioner LIKE '%DOD%'"))
print(q("SHOW COLUMNS FROM fi_pn_mh_pensioner LIKE '%GRAT%'"))
print(q("SHOW COLUMNS FROM fi_pn_th_first_month_fpension LIKE '%GRAT%'"))
print('th', q("SELECT FAM_FMPEN_ID, EMP_CD, FPENSION_TYPE, FPENSION_AMT, RELIEF, GRATUITY_AMT FROM fi_pn_th_first_month_fpension WHERE EMP_CD=%s",[emp]))
print('td grat', q("""
SELECT FAM_FMPEN_ID, EARN_DEDN_CD, EARN_DEDN_TYPE, AMOUNT, ORIGINAL_AMT
FROM fi_pn_td_first_month_fpension
WHERE FAM_FMPEN_ID IN (SELECT FAM_FMPEN_ID FROM fi_pn_th_first_month_fpension WHERE EMP_CD=%s)
ORDER BY 1,2
""",[emp]))
