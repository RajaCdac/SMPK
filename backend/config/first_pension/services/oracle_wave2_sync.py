"""
Import Wave 2 Oracle FINANCE tables into MySQL (workflow + employee reference).
"""

from django.apps import apps
from django.db import transaction

from master_data.services.oracle_pension_master_sync import (
    _clip_str,
    _date_val,
    _dec_val,
    _int_val,
    _oracle_rows,
    _row_dict,
)


def _map_pension_proposal_header(data):
    ca = _clip_str(data.get("CA_NUMBER"), 22)
    if not ca:
        return None
    sep_dt = _date_val(data.get("SEPARATION_DT"))
    prop_dt = _date_val(data.get("PENSION_PROPOSAL_DT"))
    if not sep_dt or not prop_dt:
        return None
    return {
        "ca_number": ca,
        "emp_cd": _clip_str(data.get("EMP_CD"), 5),
        "pension_type": _clip_str(data.get("PENSION_TYPE"), 1, "N"),
        "pension_proposal_no": _clip_str(data.get("PENSION_PROPOSAL_NO"), 30, "1"),
        "pension_proposal_dt": prop_dt,
        "impl_month": _int_val(data.get("IMPL_MONTH")),
        "impl_yr": _int_val(data.get("IMPL_YR")),
        "start_month": _int_val(data.get("START_MONTH")),
        "start_yr": _int_val(data.get("START_YR")),
        "employee_status": _clip_str(data.get("EMPLOYEE_STATUS"), 1, "E"),
        "vigilance_clearance_tag": _clip_str(data.get("VIGILANCE_CLEARANCE_TAG"), 1, "N"),
        "vigilance_clearance_ref_no": _clip_str(data.get("VIGILANCE_CLEARANCE_REF_NO"), 22),
        "vigilance_clearance_ref_dt": _date_val(data.get("VIGILANCE_CLEARANCE_REF_DT")),
        "prov_pen_percentage": _dec_val(data.get("PROV_PEN_PERCENTAGE")),
        "quarter_status": _clip_str(data.get("QUARTER_STATUS"), 1),
        "pension_option": _clip_str(data.get("PENSION_OPTION"), 1, " "),
        "pension_roll_no": _clip_str(data.get("PENSION_ROLL_NO"), 22),
        "id_card_submitted": _clip_str(data.get("ID_CARD_SUBMITTED"), 1, "N"),
        "port_city_resident": _clip_str(data.get("PORT_CITY_RESIDENT"), 1, "N"),
        "separation_type": _clip_str(data.get("SEPARATION_TYPE"), 3),
        "separation_dt": sep_dt,
        "date_created": _date_val(data.get("DATE_CREATED")),
        "created_by": _clip_str(data.get("CREATED_BY"), 5),
        "date_modified": _date_val(data.get("DATE_MODIFIED")),
        "modified_by": _clip_str(data.get("MODIFIED_BY"), 5),
        "comp_allowance_check_tag": _int_val(data.get("COMP_ALLOWANCE_CHECK_TAG")),
        "comp_allowance": _dec_val(data.get("COMP_ALLOWANCE")),
        "gratuity_option": _int_val(data.get("GRATUITY_OPTION")),
        "bank_cd": _clip_str(data.get("BANK_CD"), 6),
        "double_fpen_eligibility": _int_val(data.get("DOUBLE_FPEN_ELIGIBILITY")),
        "double_fpen_upto": _date_val(data.get("DOUBLE_FPEN_UPTO")),
        "base_cpi": _dec_val(data.get("BASE_CPI")),
        "extra_grat_tccs_flg": _clip_str(data.get("EXTRA_GRAT_TCCS_FLG"), 1),
        "extra_grat_tccs_days": _int_val(data.get("EXTRA_GRAT_TCCS_DAYS")),
        "extra_grat_tccs_mon": _int_val(data.get("EXTRA_GRAT_TCCS_MON")),
        "extra_grat_tccs_yr": _int_val(data.get("EXTRA_GRAT_TCCS_YR")),
        "incentive_holder_flg": _clip_str(data.get("INCENTIVE_HOLDER_FLG"), 1),
        "held_grat_flg": _clip_str(data.get("HELD_GRAT_FLG"), 1),
        "held_grat_amt": _dec_val(data.get("HELD_GRAT_AMT")),
        "lic_bank_cd": _clip_str(data.get("LIC_BANK_CD"), 6),
        "regn_no": _clip_str(data.get("REGN_NO"), 22),
        "regn_date": _date_val(data.get("REGN_DATE")),
        "account_no": _clip_str(data.get("ACCOUNT_NO"), 20),
        "opt_given_by": _clip_str(data.get("OPT_GIVEN_BY"), 1),
        "nomin_eform_grat_flg": _clip_str(data.get("NOMIN_EFORM_GRAT_FLG"), 1),
        "vr_ref_no": _clip_str(data.get("VR_REF_NO"), 30),
        "vr_ref_dt": _date_val(data.get("VR_REF_DT")),
        "letter_no": _clip_str(data.get("LETTER_NO"), 15),
        "acepted_dt": _date_val(data.get("ACEPTED_DT")),
        "dcr_type": _clip_str(data.get("DCR_TYPE"), 10),
        "held_commu_amt": _dec_val(data.get("HELD_COMMU_AMT")),
    }


def _map_proposal_earndedn_line(data, line_order=0):
    ca = _clip_str(data.get("CA_NUMBER"), 22)
    code = _clip_str(data.get("EARNDEDN_CD"), 3)
    ed_type = _clip_str(data.get("EARN_DEDN_TYPE"), 1, "E")
    if not ca or not code:
        return None
    return {
        "ca_number": ca,
        "earndedn_cd": code,
        "earn_dedn_type": ed_type,
        "amount": _dec_val(data.get("AMOUNT")),
        "e_d_priority": _int_val(data.get("E_D_PRIORITY")),
        "deducted_amt": _dec_val(data.get("DEDUCTED_AMT")),
        "line_order": line_order,
        "date_created": _date_val(data.get("DATE_CREATED")),
        "created_by": _clip_str(data.get("CREATED_BY"), 5),
        "date_modified": _date_val(data.get("DATE_MODIFIED")),
        "modified_by": _clip_str(data.get("MODIFIED_BY"), 5),
    }


def _map_application(data):
    emp = _clip_str(data.get("EMP_CD"), 5)
    appcn_no = _clip_str(data.get("APPCN_NO"), 22)
    appcn_dt = _date_val(data.get("APPCN_DT"))
    if not emp or not appcn_no or not appcn_dt:
        return None
    return {
        "emp_cd": emp,
        "appcn_no": appcn_no,
        "appcn_dt": appcn_dt,
        "ref_no": _clip_str(data.get("REF_NO"), 22),
        "pen_amt": _dec_val(data.get("PEN_AMT")),
        "commutation_per": _dec_val(data.get("COMMUTATION_PER")),
        "sanction_particulars": _clip_str(data.get("SANCTION_PARTICULARS"), 500),
        "commutation_reasons": _clip_str(data.get("COMMUTATION_REASONS"), 500),
        "prev_comm_particulars": _clip_str(data.get("PREV_COMM_PARTICULARS"), 500),
        "avg_expected_life": _clip_str(data.get("AVG_EXPECTED_LIFE"), 240),
        "date_created": _date_val(data.get("DATE_CREATED")),
        "created_by": _clip_str(data.get("CREATED_BY"), 5),
        "date_modified": _date_val(data.get("DATE_MODIFIED")),
        "modified_by": _clip_str(data.get("MODIFIED_BY"), 5),
        "comm_start_mnth": _int_val(data.get("COMM_START_MNTH")),
        "comm_start_yr": _int_val(data.get("COMM_START_YR")),
        "impl_bill_no": _clip_str(data.get("IMPL_BILL_NO"), 22),
        "mo_certificate_ref": _clip_str(data.get("MO_CERTIFICATE_REF"), 20),
        "mo_certification_dt": _date_val(data.get("MO_CERTIFICATION_DT")),
        "application_rcvd_dt": _date_val(data.get("APPLICATION_RCVD_DT")),
        "commutation_date": _date_val(data.get("COMMUTATION_DATE")),
        "commutation_amt": _dec_val(data.get("COMMUTATION_AMT")),
        "impl_fpen_combill": _clip_str(data.get("IMPL_FPEN_COMBILL"), 3),
        "bank_cd": _clip_str(data.get("BANK_CD"), 6),
        "ca_no": _clip_str(data.get("CA_NO"), 22),
        "restoration_dt": _date_val(data.get("RESTORATION_DT")),
        "restoration_flg": _int_val(data.get("RESTORATION_FLG")),
        "application_time": _int_val(data.get("APPLICATION_TIME")),
    }


def _map_oldbill_param(data):
    emp = _clip_str(data.get("EMP_CD"), 5)
    if not emp:
        return None
    return {
        "emp_cd": emp,
        "appointment_dt": _date_val(data.get("APPOINTMENT_DT")),
        "retirement_dt": _date_val(data.get("RETIREMENT_DT")),
        "boy_serv_days": _int_val(data.get("BOY_SERV_DAYS")),
        "birth_dt": _date_val(data.get("BIRTH_DT")),
        "dnon_days": _int_val(data.get("DNON_DAYS")),
        "edn_lv_days": _int_val(data.get("EDN_LV_DAYS")),
        "npay_prior_10mth": _int_val(data.get("NPAY_PRIOR_10MTH")),
        "susp_days": _int_val(data.get("SUSP_DAYS")),
        "npay_morethan_240_dys": _int_val(data.get("NPAY_MORETHAN_240_DYS")),
    }


def _map_th_salout(data):
    emp = _clip_str(data.get("EMP_CD"), 5)
    sal_mth = _int_val(data.get("SAL_MTH"))
    sal_yr = _int_val(data.get("SAL_YR"))
    if not emp or sal_mth is None or sal_yr is None:
        return None
    return {
        "emp_cd": emp,
        "sal_mth": sal_mth,
        "sal_yr": sal_yr,
        "fa_no": _clip_str(data.get("FA_NO"), 10),
        "sal_bill_no": _clip_str(data.get("SAL_BILL_NO"), 22),
        "gross_earn_amt": _dec_val(data.get("GROSS_EARN_AMT")),
        "gross_dedn_amt": _dec_val(data.get("GROSS_DEDN_AMT")),
        "net_earn_amt": _dec_val(data.get("NET_EARN_AMT")),
        "scale_desc": _clip_str(data.get("SCALE_DESC"), 100),
        "basic_rate": _dec_val(data.get("BASIC_RATE")),
        "wg_st_dt": _date_val(data.get("WG_ST_DT")),
        "wg_end_dt": _date_val(data.get("WG_END_DT")),
        "date_created": _date_val(data.get("DATE_CREATED")),
        "date_modified": _date_val(data.get("DATE_MODIFIED")),
        "modified_by": _clip_str(data.get("MODIFIED_BY"), 5),
        "created_by": _clip_str(data.get("CREATED_BY"), 5),
    }


def _map_salout(data):
    emp = _clip_str(data.get("EMP_CD"), 5)
    sal_mth = _int_val(data.get("SAL_MTH"))
    sal_yr = _int_val(data.get("SAL_YR"))
    code = _clip_str(data.get("EARNDEDN_CD"), 3)
    if not emp or sal_mth is None or sal_yr is None or not code:
        return None
    return {
        "emp_cd": emp,
        "sal_mth": sal_mth,
        "sal_yr": sal_yr,
        "earndedn_cd": code,
        "earndedn_type": _clip_str(data.get("EARNDEDN_TYPE"), 1),
        "no_of_units": _dec_val(data.get("NO_OF_UNITS")),
        "rate": _dec_val(data.get("RATE")),
        "rate_pct_flg": _int_val(data.get("RATE_PCT_FLG")),
        "act_earndedn_amt": _dec_val(data.get("ACT_EARNDEDN_AMT")),
        "adj_earndedn_amt": _dec_val(data.get("ADJ_EARNDEDN_AMT")),
        "arr_earn_amt": _dec_val(data.get("ARR_EARN_AMT")),
        "date_created": _date_val(data.get("DATE_CREATED")),
        "date_modified": _date_val(data.get("DATE_MODIFIED")),
        "modified_by": _clip_str(data.get("MODIFIED_BY"), 5),
        "created_by": _clip_str(data.get("CREATED_BY"), 5),
        "spl_pay": _dec_val(data.get("SPL_PAY")),
    }


def _map_emp_adm(data):
    emp = _clip_str(data.get("EMP_CD"), 5)
    if not emp:
        return None
    return {
        "emp_cd": emp,
        "mo_cert_ref": _clip_str(data.get("MO_CERT_REF"), 30),
        "join_dt": _date_val(data.get("JOIN_DT")),
        "emp_origin_tag": _clip_str(data.get("EMP_ORIGIN_TAG"), 1),
        "confirm_dt": _date_val(data.get("CONFIRM_DT")),
        "app_quota": _clip_str(data.get("APP_QUOTA"), 3),
        "separation_type": _clip_str(data.get("SEPARATION_TYPE"), 3),
        "separation_dt": _date_val(data.get("SEPARATION_DT")),
        "termin_remark": _clip_str(data.get("TERMIN_REMARK"), 800),
        "exp_ret_dt": _date_val(data.get("EXP_RET_DT")),
        "pf_type": _clip_str(data.get("PF_TYPE"), 1),
        "hindi_flg": _int_val(data.get("HINDI_FLG")),
        "dlypaid_years": _int_val(data.get("DLYPAID_YEARS")),
        "date_created": _date_val(data.get("DATE_CREATED")),
        "date_modified": _date_val(data.get("DATE_MODIFIED")),
        "modified_by": _clip_str(data.get("MODIFIED_BY"), 5),
        "created_by": _clip_str(data.get("CREATED_BY"), 5),
        "vig_cert_no": _clip_str(data.get("VIG_CERT_NO"), 20),
        "vig_cert_dt": _date_val(data.get("VIG_CERT_DT")),
        "order_no": _clip_str(data.get("ORDER_NO"), 20),
        "order_dt": _date_val(data.get("ORDER_DT")),
        "order_issued_by": _clip_str(data.get("ORDER_ISSUED_BY"), 20),
        "desig_cd": _int_val(data.get("DESIG_CD")),
        "union_cd": _int_val(data.get("UNION_CD")),
        "mc_reg_no": _clip_str(data.get("MC_REG_NO"), 5),
        "mc_reg_dt": _date_val(data.get("MC_REG_DT")),
        "known_flg": _int_val(data.get("KNOWN_FLG")),
        "known_details": _clip_str(data.get("KNOWN_DETAILS"), 100),
        "pan_no": _clip_str(data.get("PAN_NO"), 10),
    }


def _map_emp_per(data):
    emp = _clip_str(data.get("EMP_CD"), 5)
    if not emp:
        return None
    return {
        "emp_cd": emp,
        "title": _clip_str(data.get("TITLE"), 8),
        "first_name": _clip_str(data.get("FIRST_NAME"), 20),
        "middle_name": _clip_str(data.get("MIDDLE_NAME"), 20),
        "last_name": _clip_str(data.get("LAST_NAME"), 20),
        "perm_addr1": _clip_str(data.get("PERM_ADDR1"), 25),
        "perm_addr2": _clip_str(data.get("PERM_ADDR2"), 25),
        "perm_ps": _clip_str(data.get("PERM_PS"), 30),
        "perm_city": _clip_str(data.get("PERM_CITY"), 20),
        "perm_dist": _clip_str(data.get("PERM_DIST"), 20),
        "perm_state": _clip_str(data.get("PERM_STATE"), 20),
        "perm_pin": _int_val(data.get("PERM_PIN")),
        "perm_country": _clip_str(data.get("PERM_COUNTRY"), 20),
        "perm_contact1": _clip_str(data.get("PERM_CONTACT1"), 15),
        "perm_contact2": _clip_str(data.get("PERM_CONTACT2"), 15),
        "perm_fax_no": _clip_str(data.get("PERM_FAX_NO"), 15),
        "perm_email_id": _clip_str(data.get("PERM_EMAIL_ID"), 30),
        "pres_addr1": _clip_str(data.get("PRES_ADDR1"), 25),
        "pres_addr2": _clip_str(data.get("PRES_ADDR2"), 25),
        "pres_ps": _clip_str(data.get("PRES_PS"), 30),
        "pres_city": _clip_str(data.get("PRES_CITY"), 20),
        "pres_dist": _clip_str(data.get("PRES_DIST"), 20),
        "pres_state": _clip_str(data.get("PRES_STATE"), 20),
        "pres_pin": _int_val(data.get("PRES_PIN")),
        "pres_country": _clip_str(data.get("PRES_COUNTRY"), 20),
        "pres_contact1": _clip_str(data.get("PRES_CONTACT1"), 15),
        "pres_contact2": _clip_str(data.get("PRES_CONTACT2"), 15),
        "pres_fax_no": _clip_str(data.get("PRES_FAX_NO"), 15),
        "pres_email_id": _clip_str(data.get("PRES_EMAIL_ID"), 30),
        "f_h_flg": _clip_str(data.get("F_H_FLG"), 1),
        "f_h_name": _clip_str(data.get("F_H_NAME"), 50),
        "birth_dt": _date_val(data.get("BIRTH_DT")),
        "dob_evidence": _clip_str(data.get("DOB_EVIDENCE"), 100),
        "sex": _clip_str(data.get("SEX"), 1),
        "edu_qual": _clip_str(data.get("EDU_QUAL"), 80),
        "prof_qual": _clip_str(data.get("PROF_QUAL"), 80),
        "other_qual": _clip_str(data.get("OTHER_QUAL"), 80),
        "awards": _clip_str(data.get("AWARDS"), 80),
        "religion": _clip_str(data.get("RELIGION"), 15),
        "nationality": _clip_str(data.get("NATIONALITY"), 15),
        "height_cm": _int_val(data.get("HEIGHT_CM")),
        "id_marks": _clip_str(data.get("ID_MARKS"), 100),
        "category": _clip_str(data.get("CATEGORY"), 3),
        "handicap_flg": _int_val(data.get("HANDICAP_FLG")),
        "marital_status": _clip_str(data.get("MARITAL_STATUS"), 1),
        "date_created": _date_val(data.get("DATE_CREATED")),
        "date_modified": _date_val(data.get("DATE_MODIFIED")),
        "modified_by": _clip_str(data.get("MODIFIED_BY"), 5),
        "created_by": _clip_str(data.get("CREATED_BY"), 5),
        "status": _clip_str(data.get("STATUS"), 2),
        "f_h_addr": _clip_str(data.get("F_H_ADDR"), 140),
        "doctor_flg": _int_val(data.get("DOCTOR_FLG")),
        "remarks": _clip_str(data.get("REMARKS"), 300),
    }


def _map_emp_fin(data):
    emp = _clip_str(data.get("EMP_CD"), 5)
    if not emp:
        return None
    return {
        "emp_cd": emp,
        "bank_cd": _clip_str(data.get("BANK_CD"), 6),
        "paymode_cd": _clip_str(data.get("PAYMODE_CD"), 2),
        "bank_ac_no": _clip_str(data.get("BANK_AC_NO"), 20),
        "last_gi_dt": _date_val(data.get("LAST_GI_DT")),
        "next_gi_dt": _date_val(data.get("NEXT_GI_DT")),
        "suspend_flg": _clip_str(data.get("SUSPEND_FLG"), 1),
        "suspend_wef_dt": _date_val(data.get("SUSPEND_WEF_DT")),
        "qtr_flg": _int_val(data.get("QTR_FLG")),
        "transport_flg": _int_val(data.get("TRANSPORT_FLG")),
        "tel_flg": _int_val(data.get("TEL_FLG")),
        "past_serv_days": _int_val(data.get("PAST_SERV_DAYS")),
        "dues_clr_flg": _int_val(data.get("DUES_CLR_FLG")),
        "remarks": _clip_str(data.get("REMARKS"), 150),
        "date_created": _date_val(data.get("DATE_CREATED")),
        "date_modified": _date_val(data.get("DATE_MODIFIED")),
        "modified_by": _clip_str(data.get("MODIFIED_BY"), 5),
        "created_by": _clip_str(data.get("CREATED_BY"), 5),
        "pay_pct": _dec_val(data.get("PAY_PCT")),
        "final_stlmt_status": _clip_str(data.get("FINAL_STLMT_STATUS"), 1),
        "fa_no": _clip_str(data.get("FA_NO"), 5),
        "scale_sl": _clip_str(data.get("SCALE_SL"), 14),
        "scale_wef_dt": _date_val(data.get("SCALE_WEF_DT")),
        "scale_optfor": _clip_str(data.get("SCALE_OPTFOR"), 1),
        "inland_cert_class": _clip_str(data.get("INLAND_CERT_CLASS"), 1),
        "emp_class": _int_val(data.get("EMP_CLASS")),
    }


def _map_finscale(data):
    emp = _clip_str(data.get("EMP_CD"), 5)
    wef_dt = _date_val(data.get("WEF_DT"))
    sl_no = _int_val(data.get("SL_NO"))
    if not emp or not wef_dt or sl_no is None:
        return None
    return {
        "emp_cd": emp,
        "scale_sl": _clip_str(data.get("SCALE_SL"), 14),
        "wef_dt": wef_dt,
        "sl_no": sl_no,
        "date_created": _date_val(data.get("DATE_CREATED")),
        "date_modified": _date_val(data.get("DATE_MODIFIED")),
        "modified_by": _clip_str(data.get("MODIFIED_BY"), 30),
        "created_by": _clip_str(data.get("CREATED_BY"), 30),
        "history_flg": _int_val(data.get("HISTORY_FLG")),
        "basic_amt": _dec_val(data.get("BASIC_AMT")),
        "stag_pay_amt": _dec_val(data.get("STAG_PAY_AMT")),
        "ref_no": _clip_str(data.get("REF_NO"), 10),
        "tran_flg": _clip_str(data.get("TRAN_FLG"), 1),
        "active_rec": _clip_str(data.get("ACTIVE_REC"), 1),
        "remarks": _clip_str(data.get("REMARKS"), 500),
    }


def _map_emp_data(data):
    emp = _clip_str(data.get("EMP_CD"), 5)
    if not emp:
        return None
    return {
        "emp_cd": emp,
        "dept_cd": _clip_str(data.get("DEPT_CD"), 2),
        "dept_desc": _clip_str(data.get("DEPT_DESC"), 100),
        "budcntr_cd": _clip_str(data.get("BUDCNTR_CD"), 3),
        "alloc_desc": _clip_str(data.get("ALLOC_DESC"), 100),
        "fa_no": _clip_str(data.get("FA_NO"), 5),
        "fa_desc": _clip_str(data.get("FA_DESC"), 50),
        "srf_no": _clip_str(data.get("SRF_NO"), 7),
        "emp_class": _clip_str(data.get("CLASS"), 15),
        "name": _clip_str(data.get("NAME"), 62),
        "desig": _clip_str(data.get("DESIG"), 30),
        "dob_text": _clip_str(data.get("DOB"), 10),
        "age": _int_val(data.get("AGE")),
        "join_dt_text": _clip_str(data.get("JOIN_DT"), 10),
        "ret_dt_text": _clip_str(data.get("RET_DT"), 10),
    }


def _map_pr_th_salout(data):
    emp = _clip_str(data.get("EMP_CD"), 5)
    sal_mth = _int_val(data.get("SAL_MTH"))
    sal_yr = _int_val(data.get("SAL_YR"))
    if not emp or sal_mth is None or sal_yr is None:
        return None
    return {
        "emp_cd": emp,
        "sal_mth": sal_mth,
        "sal_yr": sal_yr,
        "fa_no": _clip_str(data.get("FA_NO"), 5),
        "sal_bill_no": _clip_str(data.get("SAL_BILL_NO"), 20),
        "gross_earn_amt": _dec_val(data.get("GROSS_EARN_AMT")),
        "gross_dedn_amt": _dec_val(data.get("GROSS_DEDN_AMT")),
        "net_earn_amt": _dec_val(data.get("NET_EARN_AMT")),
        "scale_desc": _clip_str(data.get("SCALE_DESC"), 40),
        "basic_rate": _dec_val(data.get("BASIC_RATE")),
        "wg_st_dt": _date_val(data.get("WG_ST_DT")),
        "wg_end_dt": _date_val(data.get("WG_END_DT")),
        "date_created": _date_val(data.get("DATE_CREATED")),
        "date_modified": _date_val(data.get("DATE_MODIFIED")),
        "modified_by": _clip_str(data.get("MODIFIED_BY"), 5),
        "created_by": _clip_str(data.get("CREATED_BY"), 5),
    }


def _map_pr_td_salout(data):
    emp = _clip_str(data.get("EMP_CD"), 5)
    sal_mth = _int_val(data.get("SAL_MTH"))
    sal_yr = _int_val(data.get("SAL_YR"))
    code = _clip_str(data.get("EARNDEDN_CD"), 3)
    if not emp or sal_mth is None or sal_yr is None or not code:
        return None
    return {
        "emp_cd": emp,
        "sal_mth": sal_mth,
        "sal_yr": sal_yr,
        "earndedn_cd": code,
        "earndedn_type": _clip_str(data.get("EARNDEDN_TYPE"), 1),
        "no_of_units": _dec_val(data.get("NO_OF_UNITS")),
        "rate": _dec_val(data.get("RATE")),
        "rate_pct_flg": _int_val(data.get("RATE_PCT_FLG")),
        "act_earndedn_amt": _dec_val(data.get("ACT_EARNDEDN_AMT")),
        "adj_earndedn_amt": _dec_val(data.get("ADJ_EARNDEDN_AMT")),
        "arr_earn_amt": _dec_val(data.get("ARR_EARN_AMT")),
        "notional_amount": _dec_val(data.get("NOTIONAL_AMOUNT")),
        "date_created": _date_val(data.get("DATE_CREATED")),
        "date_modified": _date_val(data.get("DATE_MODIFIED")),
        "modified_by": _clip_str(data.get("MODIFIED_BY"), 5),
        "created_by": _clip_str(data.get("CREATED_BY"), 5),
    }


WAVE2_SYNC_SPECS = [
    {
        "oracle_table": "FI_PN_MH_PENSION_PROPOSAL",
        "app": "first_pension",
        "model": "FiPnMhPensionProposal",
        "mapper": _map_pension_proposal_header,
        "order_by": "CA_NUMBER",
        "pk_field": "ca_number",
        "emp_filter_column": "EMP_CD",
    },
    {
        "oracle_table": "FI_PN_MD_PENSION_PROPOSAL",
        "app": "first_pension",
        "model": "PensionProposalEarndedn",
        "mapper": _map_proposal_earndedn_line,
        "order_by": "CA_NUMBER, EARNDEDN_CD, EARN_DEDN_TYPE",
        "emp_filter_column": None,
        "sequential_line_order": True,
    },
    {
        "oracle_table": "FI_PN_MH_APPLICATION",
        "app": "first_pension",
        "model": "FiPnMhApplication",
        "mapper": _map_application,
        "order_by": "EMP_CD, APPCN_NO, APPCN_DT",
        "emp_filter_column": "EMP_CD",
    },
    {
        "oracle_table": "FI_PN_MH_OLDBILL_PARAM",
        "app": "first_pension",
        "model": "FiPnMhOldbillParam",
        "mapper": _map_oldbill_param,
        "order_by": "EMP_CD",
        "pk_field": "emp_cd",
        "emp_filter_column": "EMP_CD",
    },
    {
        "oracle_table": "FI_PN_TD_SALOUT",
        "app": "first_pension",
        "model": "FiPnTdSalout",
        "mapper": _map_salout,
        "order_by": "EMP_CD, SAL_YR, SAL_MTH, EARNDEDN_CD",
        "emp_filter_column": "EMP_CD",
    },
    {
        "oracle_table": "FI_PN_TH_SALOUT",
        "app": "first_pension",
        "model": "FiPnThSalout",
        "mapper": _map_th_salout,
        "order_by": "EMP_CD, SAL_YR, SAL_MTH",
        "emp_filter_column": "EMP_CD",
    },
    {
        "oracle_table": "FI_XX_MH_EMP_ADM",
        "app": "employee",
        "model": "FiXxMhEmpAdm",
        "mapper": _map_emp_adm,
        "order_by": "EMP_CD",
        "pk_field": "emp_cd",
        "emp_filter_column": "EMP_CD",
    },
    {
        "oracle_table": "FI_XX_MH_EMP_PER",
        "app": "employee",
        "model": "FiXxMhEmpPer",
        "mapper": _map_emp_per,
        "order_by": "EMP_CD",
        "pk_field": "emp_cd",
        "emp_filter_column": "EMP_CD",
    },
    {
        "oracle_table": "FI_XX_MH_EMP_FIN",
        "app": "employee",
        "model": "FiXxMhEmpFin",
        "mapper": _map_emp_fin,
        "order_by": "EMP_CD",
        "pk_field": "emp_cd",
        "emp_filter_column": "EMP_CD",
    },
    {
        "oracle_table": "FI_XX_MD_FINSCALE",
        "app": "employee",
        "model": "FiXxMdFinscale",
        "mapper": _map_finscale,
        "order_by": "EMP_CD, WEF_DT, SL_NO",
        "emp_filter_column": "EMP_CD",
    },
    {
        "oracle_table": "FI_XX_MH_EMP_DATA",
        "app": "employee",
        "model": "FiXxMhEmpData",
        "mapper": _map_emp_data,
        "order_by": "EMP_CD",
        "pk_field": "emp_cd",
        "emp_filter_column": "EMP_CD",
    },
    {
        "oracle_table": "FI_PR_TD_SALOUT",
        "app": "first_pension",
        "model": "FiPrTdSalout",
        "mapper": _map_pr_td_salout,
        "order_by": "EMP_CD, SAL_YR, SAL_MTH, EARNDEDN_CD",
        "emp_filter_column": "EMP_CD",
    },
    {
        "oracle_table": "FI_PR_TH_SALOUT",
        "app": "first_pension",
        "model": "FiPrThSalout",
        "mapper": _map_pr_th_salout,
        "order_by": "EMP_CD, SAL_YR, SAL_MTH",
        "emp_filter_column": "EMP_CD",
    },
]


def _fetch_oracle_rows_filtered(spec, emp_cd=None):
    sql = f"SELECT * FROM FINANCE.{spec['oracle_table']}"
    binds = {}
    if emp_cd and spec.get("emp_filter_column"):
        sql += f" WHERE {spec['emp_filter_column']} = :emp_cd"
        binds["emp_cd"] = str(emp_cd).strip()[:5]
    if spec.get("order_by"):
        sql += f" ORDER BY {spec['order_by']}"

    from employee.services.oracle_service import get_oracle_connection

    with get_oracle_connection().cursor() as cursor:
        if binds:
            cursor.execute(sql, binds)
        else:
            cursor.execute(sql)
        column_names = [d[0] for d in cursor.description]
        rows = cursor.fetchall()
    return column_names, rows


def _flush_batch(model, batch, batch_size):
    if not batch:
        return 0
    model.objects.bulk_create(batch, batch_size=batch_size)
    count = len(batch)
    batch.clear()
    return count


def sync_wave2_table(spec, *, full_refresh=True, batch_size=2000, emp_cd=None):
    model = apps.get_model(spec["app"], spec["model"])
    column_names, rows = _fetch_oracle_rows_filtered(spec, emp_cd=emp_cd)

    if full_refresh and not emp_cd:
        model.objects.all().delete()
    elif full_refresh and emp_cd and spec.get("emp_filter_column"):
        model.objects.filter(**{spec["emp_filter_column"].lower(): str(emp_cd).strip()[:5]}).delete()

    inserted = skipped = 0
    batch = []
    line_order = 0

    for row in rows:
        data = _row_dict(column_names, row)
        if spec.get("sequential_line_order"):
            mapped = spec["mapper"](data, line_order=line_order)
            line_order += 1
        else:
            mapped = spec["mapper"](data)
        if not mapped:
            skipped += 1
            continue
        batch.append(model(**mapped))
        if len(batch) >= batch_size:
            inserted += _flush_batch(model, batch, batch_size)

    inserted += _flush_batch(model, batch, batch_size)

    return {
        "oracle_table": spec["oracle_table"],
        "model": spec["model"],
        "total": len(rows),
        "inserted": inserted,
        "skipped": skipped,
    }


def sync_all_wave2(*, full_refresh=True, batch_size=2000, emp_cd=None, tables=None):
    selected = tables or [s["oracle_table"] for s in WAVE2_SYNC_SPECS]
    results = []
    with transaction.atomic():
        for spec in WAVE2_SYNC_SPECS:
            if spec["oracle_table"] not in selected:
                continue
            results.append(
                sync_wave2_table(
                    spec,
                    full_refresh=full_refresh,
                    batch_size=batch_size,
                    emp_cd=emp_cd,
                )
            )
    return results
