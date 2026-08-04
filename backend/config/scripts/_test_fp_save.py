import MySQLdb
import os
import sys
import traceback

import django

sys.path.insert(0, r"d:\SMPK\SMPK\backend\config")
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

conn = MySQLdb.connect(
    host="127.0.0.1", port=3306, user="root", passwd="root123", db="smpk_pension"
)
cur = conn.cursor()
print("=== master columns of interest ===")
cur.execute(
    "SHOW COLUMNS FROM fi_pn_mh_fpen_caclaim WHERE Field IN "
    "('PENSION_OPT','EMP_CD','CLM_CA_TYPE','SCALE_CD','CREATED_BY',"
    "'MODIFIED_BY','INCENTIVE_HOLDER_FLG','CLASS','APPLICANT_TYPE')"
)
for r in cur.fetchall():
    print(r)

print("=== detail columns ===")
cur.execute("SHOW COLUMNS FROM fi_pn_md_fpen_appcn")
for r in cur.fetchall():
    print(r[0], r[1], r[2], r[3])

print("=== check test claim ===")
cur.execute(
    "SELECT CLMCA_ID, EMP_CD FROM fi_pn_mh_fpen_caclaim WHERE CLMCA_ID=%s",
    ("CM/18905",),
)
print(cur.fetchone())

from family_pension.services.claim_service import save_claim

# Simulate form payload closer to frontend (long pension_opt, empty applicants names)
payload = {
    "emp_cd": "27117",
    "clm_ca_type": "CM",
    "clmca_id": "",
    "ca_no": "8914",
    "service_pension_amt": "1850",
    "dod_emp_pensioner": "1982-03-01",
    "incentive_holder_flg": "Y",
    "double_fpen_eligibility": 0,
    "appcn_status": "1",
    "applicant_type": "1",
    "applicant_name": "TEST",
    "pension_opt": "Government",
    "scale_cd": "123456789012345",
    "applicants": [
        {
            "sl_no": 1,
            "name": "",
            "relation_cd": "",
            "dob": "",
            "handicap_flg": "N",
            "bank_cd": "",
            "lic_bank_cd": "",
            "account_no": "",
            "fpen_active": 1,
            "status_flg": "S",
        }
    ],
}
try:
    print("SAVE1", save_claim(payload, user_id="SMPK"))
except Exception:
    traceback.print_exc()

payload2 = dict(payload)
payload2["clmca_id"] = "CM/18905"
payload2["applicants"] = [
    {
        "sl_no": 1,
        "name": "TEST WIDOW UPD",
        "relation_cd": "1",
        "dob": "1950-01-01",
        "handicap_flg": "N",
        "bank_cd": "SBI001",
        "lic_bank_cd": "LIC01",
        "account_no": "1234567890",
        "fpen_active": 1,
        "status_flg": "S",
    }
]
try:
    print("SAVE2", save_claim(payload2, user_id="longusername"))
except Exception:
    traceback.print_exc()
