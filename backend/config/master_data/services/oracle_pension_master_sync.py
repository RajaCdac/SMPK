"""
Import pension calculation master tables from Oracle FINANCE schema into MySQL.
"""

from decimal import Decimal

from django.apps import apps
from django.db import transaction

from employee.services.oracle_service import get_oracle_connection


def _clip_str(value, max_len=None, default=""):
    if value is None:
        return default
    text = str(value).strip()
    if not text:
        return default
    return text[:max_len] if max_len else text


def _int_val(value, default=None):
    if value is None or value == "":
        return default
    return int(value)


def _dec_val(value):
    if value is None or value == "":
        return None
    return Decimal(str(value))


def _date_val(value):
    if value is None:
        return None
    if hasattr(value, "date"):
        return value.date()
    return value


def _oracle_rows(table_name, order_by=None):
    sql = f"SELECT * FROM FINANCE.{table_name}"
    if order_by:
        sql += f" ORDER BY {order_by}"
    with get_oracle_connection().cursor() as cursor:
        cursor.execute(sql)
        column_names = [d[0] for d in cursor.description]
        rows = cursor.fetchall()
    return column_names, rows


def _row_dict(column_names, row):
    return dict(zip(column_names, row))


def _audit_fields(data):
    return {
        "date_created": _date_val(data.get("DATE_CREATED")),
        "date_modified": _date_val(data.get("DATE_MODIFIED")),
        "created_by": _clip_str(data.get("CREATED_BY"), 5),
        "modified_by": _clip_str(data.get("MODIFIED_BY"), 5),
    }


def _fin_ctrl_audit_fields(data):
    return {
        "created_by": _clip_str(data.get("CREATED_BY"), 5),
        "created_on": _date_val(data.get("CREATED_ON")),
        "l_modified_by": _clip_str(data.get("L_MODIFIED_BY"), 5),
        "l_modified_on": _date_val(data.get("L_MODIFIED_ON")),
    }


def map_fi_pn_mh_erndednmap(data):
    return {
        "map_cd": _int_val(data.get("MAP_CD")),
        "e_d_type": _clip_str(data.get("E_D_TYPE"), 1),
        "map_desc": _clip_str(data.get("MAP_DESC"), 50),
        "earndedn_cd": _clip_str(data.get("EARNDEDN_CD"), 3),
        "dedn_priority": _int_val(data.get("DEDN_PRIORITY")),
        **_audit_fields(data),
    }


def map_fi_pr_mh_erndednmap(data):
    return {
        "map_cd": _int_val(data.get("MAP_CD")),
        "group_type": _clip_str(data.get("GROUP_TYPE"), 1),
        "map_desc": _clip_str(data.get("MAP_DESC"), 50),
        "earndedn_cd": _clip_str(data.get("EARNDEDN_CD"), 3),
        "dedn_priority": _int_val(data.get("DEDN_PRIORITY")),
        **_audit_fields(data),
    }


def map_fi_pn_mh_ada_rate(data):
    return {
        "emp_type": _clip_str(data.get("EMP_TYPE"), 3),
        "wef_dt": _date_val(data.get("WEF_DT")),
        "base_cpi_no": _int_val(data.get("BASE_CPI_NO")),
        "index_pts": _dec_val(data.get("INDEX_PTS")),
        "da_pct": _dec_val(data.get("DA_PCT")),
        "cpi_no": _dec_val(data.get("CPI_NO")),
        "wet_dt": _date_val(data.get("WET_DT")),
        **_audit_fields(data),
    }


def map_fi_pn_md_maxadm_gratuity(data):
    return {
        "wef_dt": _date_val(data.get("WEF_DT")),
        "gratuity_type": _int_val(data.get("GRATUITY_TYPE")),
        "ret_dt_from": _date_val(data.get("RET_DT_FROM")),
        "ret_dt_to": _date_val(data.get("RET_DT_TO")),
        "max_emolument": _dec_val(data.get("MAX_EMOLUMENT")),
        "max_adm_gratuity": _dec_val(data.get("MAX_ADM_GRATUITY")),
        **_audit_fields(data),
    }


def map_fi_pn_mh_death_gratchart(data):
    return {
        "wef_dt": _date_val(data.get("WEF_DT")),
        "gratuity_type": _int_val(data.get("GRATUITY_TYPE")),
        "inception_dt": _date_val(data.get("INCEPTION_DT")),
        "before_inception_max_lt": _int_val(data.get("BEFORE_INCEPTION_MAX_LT")),
        "after_inception_max_lt": _int_val(data.get("AFTER_INCEPTION_MAX_LT")),
        "circular_ref_no": _clip_str(data.get("CIRCULAR_REF_NO"), 22),
        **_audit_fields(data),
    }


def map_fi_pn_md_death_gratchart(data):
    return {
        "wef_dt": _date_val(data.get("WEF_DT")),
        "gratuity_type": _int_val(data.get("GRATUITY_TYPE")),
        "tqs_start_yrs": _int_val(data.get("TQS_START_YRS")),
        "tqs_end_yrs": _int_val(data.get("TQS_END_YRS")),
        "multiple_factor": _dec_val(data.get("MULTIPLE_FACTOR")),
        **_audit_fields(data),
    }


def map_fi_pn_mh_service_gratchart(data):
    return {
        "wef_dt": _date_val(data.get("WEF_DT")),
        "interval_srl": _int_val(data.get("INTERVAL_SRL")),
        "duration_month": _int_val(data.get("DURATION_MONTH")),
        "base_doc": _clip_str(data.get("BASE_DOC"), 15),
        "numerator_amt": _dec_val(data.get("NUMERATOR_AMT")),
        "denominator_amt": _dec_val(data.get("DENOMINATOR_AMT")),
        **_audit_fields(data),
    }


def map_fi_pn_md_commrate_rupee(data):
    return {
        "age_yrs": _int_val(data.get("AGE_YRS")),
        "wef_dt": _date_val(data.get("WEF_DT")),
        "amt_per_rupee": _dec_val(data.get("AMT_PER_RUPEE")),
        **_audit_fields(data),
    }


def map_fi_pn_mh_base_cpi(data):
    return {
        "emp_type": _clip_str(data.get("EMP_TYPE"), 2),
        "wef_dt": _date_val(data.get("WEF_DT")),
        "base_cpi": _dec_val(data.get("BASE_CPI")),
        **_audit_fields(data),
    }


def map_fi_xx_mh_desig(data):
    return {
        "desig_cd": _int_val(data.get("DESIG_CD")),
        "desig_desc": _clip_str(data.get("DESIG_DESC"), 60),
        "active_flg": _int_val(data.get("ACTIVE_FLG"), 0),
        **_audit_fields(data),
    }


def map_fi_xx_mh_dept(data):
    dept_cd = _clip_str(data.get("DEPT_CD"), 2)
    if not dept_cd:
        return None
    return {
        "dept_cd": dept_cd,
        "dept_desc": _clip_str(data.get("DEPT_DESC"), 100),
        "dept_short_desc": _clip_str(data.get("DEPT_SHORT_DESC"), 7),
        **_audit_fields(data),
    }


def map_fi_xx_xx_m_h_fin_ctrl(data):
    return {
        "fin_yr": _int_val(data.get("FIN_YR")),
        "yr_st_dt": _date_val(data.get("YR_ST_DT")),
        "yr_end_dt": _date_val(data.get("YR_END_DT")),
        "year_pd": _clip_str(data.get("YEAR_PD"), 9),
        "fin_stat": _int_val(data.get("FIN_STAT"), 0),
        "l_trn_no": _int_val(data.get("L_TRN_NO"), 0),
        **_fin_ctrl_audit_fields(data),
    }


def map_fi_xx_xx_m_d_fin_ctrl(data):
    return {
        "fin_yr": _int_val(data.get("FIN_YR")),
        "doc_abv": _clip_str(data.get("DOC_ABV"), 4),
        "doc_desc": _clip_str(data.get("DOC_DESC"), 60),
        "l_trn_no": _int_val(data.get("L_TRN_NO"), 0),
        "authority": _clip_str(data.get("AUTHORITY"), 300),
        **_fin_ctrl_audit_fields(data),
    }


def map_fi_pm_mh_payscale(data):
    desc = data.get("SCALE_DESC") or data.get("SCALE_DESCRIPTION")
    return {
        "scale_cd": _clip_str(data.get("SCALE_CD"), 20),
        "scale_desc": _clip_str(desc, 100),
        **_audit_fields(data),
    }


PENSION_MASTER_SYNC_SPECS = [
    {
        "oracle_table": "FI_PN_MH_ERNDEDNMAP",
        "model": "FiPnMhErndednmap",
        "keys": ["map_cd"],
        "order_by": "MAP_CD",
        "mapper": map_fi_pn_mh_erndednmap,
    },
    {
        "oracle_table": "FI_PR_MH_ERNDEDNMAP",
        "model": "FiPrMhErndednmap",
        "keys": ["map_cd"],
        "order_by": "MAP_CD",
        "mapper": map_fi_pr_mh_erndednmap,
    },
    {
        "oracle_table": "FI_PN_MH_ADA_RATE",
        "model": "FiPnMhAdaRate",
        "keys": ["wef_dt", "emp_type", "base_cpi_no"],
        "order_by": "WEF_DT, EMP_TYPE, BASE_CPI_NO",
        "mapper": map_fi_pn_mh_ada_rate,
    },
    {
        "oracle_table": "FI_PN_MD_MAXADM_GRATUITY",
        "model": "FiPnMdMaxadmGratuity",
        "keys": ["wef_dt", "gratuity_type", "ret_dt_from"],
        "order_by": "WEF_DT, GRATUITY_TYPE, RET_DT_FROM",
        "mapper": map_fi_pn_md_maxadm_gratuity,
    },
    {
        "oracle_table": "FI_PN_MH_DEATH_GRATCHART",
        "model": "FiPnMhDeathGratchart",
        "keys": ["wef_dt", "gratuity_type"],
        "order_by": "WEF_DT, GRATUITY_TYPE",
        "mapper": map_fi_pn_mh_death_gratchart,
    },
    {
        "oracle_table": "FI_PN_MD_DEATH_GRATCHART",
        "model": "FiPnMdDeathGratchart",
        "keys": ["tqs_start_yrs", "wef_dt", "gratuity_type"],
        "order_by": "WEF_DT, GRATUITY_TYPE, TQS_START_YRS",
        "mapper": map_fi_pn_md_death_gratchart,
    },
    {
        "oracle_table": "FI_PN_MH_SERVICE_GRATCHART",
        "model": "FiPnMhServiceGratchart",
        "keys": ["wef_dt", "interval_srl"],
        "order_by": "WEF_DT, INTERVAL_SRL",
        "mapper": map_fi_pn_mh_service_gratchart,
    },
    {
        "oracle_table": "FI_PN_MD_COMMRATE_RUPEE",
        "model": "FiPnMdCommrateRupee",
        "keys": ["age_yrs", "wef_dt"],
        "order_by": "WEF_DT, AGE_YRS",
        "mapper": map_fi_pn_md_commrate_rupee,
    },
    {
        "oracle_table": "FI_PN_MH_BASE_CPI",
        "model": "FiPnMhBaseCpi",
        "keys": ["emp_type", "wef_dt"],
        "order_by": "WEF_DT, EMP_TYPE",
        "mapper": map_fi_pn_mh_base_cpi,
    },
    {
        "oracle_table": "FI_XX_MH_DESIG",
        "model": "FiXxMhDesig",
        "keys": ["desig_cd"],
        "order_by": "DESIG_CD",
        "mapper": map_fi_xx_mh_desig,
    },
    {
        "oracle_table": "FI_XX_MH_DEPT",
        "model": "FiXxMhDept",
        "keys": ["dept_cd"],
        "order_by": "DEPT_CD",
        "mapper": map_fi_xx_mh_dept,
    },
    {
        "oracle_table": "FI_XX_XX_M_H_FIN_CTRL",
        "model": "FiXxXxMHFinCtrl",
        "keys": ["fin_yr"],
        "order_by": "FIN_YR",
        "mapper": map_fi_xx_xx_m_h_fin_ctrl,
    },
    {
        "oracle_table": "FI_XX_XX_M_D_FIN_CTRL",
        "model": "FiXxXxMDFinCtrl",
        "keys": ["fin_yr", "doc_abv"],
        "order_by": "FIN_YR, DOC_ABV",
        "mapper": map_fi_xx_xx_m_d_fin_ctrl,
    },
    {
        "oracle_table": "FI_PM_MH_PAYSCALE",
        "model": "FiPmMhPayscale",
        "keys": ["scale_cd"],
        "order_by": "SCALE_CD",
        "mapper": map_fi_pm_mh_payscale,
    },
]


def _lookup_kwargs(keys, defaults):
    missing = [k for k in keys if defaults.get(k) is None]
    if missing:
        raise ValueError(f"Missing key fields {missing} in row {defaults}")
    return {k: defaults[k] for k in keys}


def sync_pension_master_table(spec):
    model = apps.get_model("master_data", spec["model"])
    column_names, rows = _oracle_rows(spec["oracle_table"], spec.get("order_by"))
    created = updated = skipped = 0

    for row in rows:
        data = _row_dict(column_names, row)
        defaults = spec["mapper"](data)
        if defaults.get("map_cd") is None and "map_cd" in spec["keys"]:
            skipped += 1
            continue
        if defaults.get("desig_cd") is None and "desig_cd" in spec["keys"]:
            skipped += 1
            continue
        if defaults.get("fin_yr") is None and "fin_yr" in spec["keys"]:
            skipped += 1
            continue
        if defaults.get("wef_dt") is None and "wef_dt" in spec["keys"]:
            skipped += 1
            continue
        if defaults.get("scale_cd") is None and "scale_cd" in spec["keys"]:
            skipped += 1
            continue

        lookup = _lookup_kwargs(spec["keys"], defaults)
        payload = {k: v for k, v in defaults.items() if k not in lookup}
        _, was_created = model.objects.update_or_create(
            defaults=payload,
            **lookup,
        )
        if was_created:
            created += 1
        else:
            updated += 1

    return {
        "oracle_table": spec["oracle_table"],
        "model": spec["model"],
        "total": len(rows),
        "created": created,
        "updated": updated,
        "skipped": skipped,
    }


def sync_all_pension_masters():
    results = []
    with transaction.atomic():
        for spec in PENSION_MASTER_SYNC_SPECS:
            results.append(sync_pension_master_table(spec))
    return results
