import os
import sys
import traceback

import django

sys.path.insert(0, r"d:\SMPK\SMPK\backend\config")
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from family_pension.services.claim_service import prefill_from_emp, save_claim

pref = prefill_from_emp("27117", "CM")["prefill"]
payload = {
    "clmca_id": "",
    "clm_ca_type": "CM",
    "ca_no": "",
    "emp_cd": "",
    "disp_name": "",
    "appcn_no": "",
    "appcn_date": "",
    "appcn_status": "",
    "double_fpen_eligibility": 0,
    "double_fpen_upto": "",
    "applicant_type": "",
    "applicant_name": "",
    "applicant_address": "",
    "dod_emp_pensioner": "",
    "gurdian_relation_cd": "",
    "disp_relation": "",
    "dob_guardian": "",
    "service_pension_amt": "",
    "fpen_start_mnth": "",
    "fprn_start_yr": "",
    "retirement_cpi": "",
    "pension_opt": "",
    "last_fpen_mth": "",
    "last_fpen_yr": "",
    "scale_cd": "",
    "last_basic_at_ret": "",
    "incentive_holder_flg": "",
    "consolid_cpi_scl_stamt": "",
    "equiv_pay_at_base_cpi": "",
    "applicants": [
        {
            "sl_no": 1,
            "name": "WIDOW TEST",
            "dob": "",
            "relation_cd": "1",
            "relation_desc": "WIFE",
            "bank_cd": "",
            "account_no": "",
            "lic_bank_cd": "",
            "handicap_flg": "N",
            "fpen_active": 1,
            "status_flg": "S",
        }
    ],
}
payload.update(pref)
payload["clmca_id"] = ""  # new mode
print("PAYLOAD KEYS", {k: payload[k] for k in payload if k != "applicants"})
try:
    print(save_claim(payload, user_id="admin"))
except Exception:
    traceback.print_exc()
