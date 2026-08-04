"""
Import Wave 3 Oracle FINANCE tables: first-month output + pension bills.
"""

from django.apps import apps
from django.db import transaction

from master_data.services.oracle_pension_master_sync import (
    _clip_str,
    _date_val,
    _dec_val,
    _int_val,
    _row_dict,
)


def _map_th_first_month(data):
    fmpen_id = _clip_str(data.get("FMPEN_ID"), 22)
    if not fmpen_id:
        return None
    return {
        "fmpen_id": fmpen_id,
        "pension_type": _clip_str(data.get("PENSION_TYPE"), 3),
        "pension_month": _int_val(data.get("PENSION_MONTH")),
        "pension_yr": _int_val(data.get("PENSION_YR")),
        "ca_no": _clip_str(data.get("CA_NO"), 22),
        "ca_date": _date_val(data.get("CA_DATE")),
        "original_fpension_amt": _dec_val(data.get("ORIGINAL_FPENSION_AMT")),
        "payable_pension": _dec_val(data.get("PAYABLE_PENSION")),
        "date_of_execution": _date_val(data.get("DATE_OF_EXECUTION")),
        "bill_no": _clip_str(data.get("BILL_NO"), 22),
        "paid_month": _int_val(data.get("PAID_MONTH")),
        "paid_year": _int_val(data.get("PAID_YEAR")),
        "date_created": _date_val(data.get("DATE_CREATED")),
        "created_by": _clip_str(data.get("CREATED_BY"), 5),
        "date_modified": _date_val(data.get("DATE_MODIFIED")),
        "modified_by": _clip_str(data.get("MODIFIED_BY"), 5),
        "emp_cd": _clip_str(data.get("EMP_CD"), 5),
        "bank_cd": _clip_str(data.get("BANK_CD"), 6),
        "sys_man_tag": _clip_str(data.get("SYS_MAN_TAG"), 1),
        "cpi_no": _dec_val(data.get("CPI_NO")),
        "nomin_type": _clip_str(data.get("NOMIN_TYPE"), 2),
        "pen_proc_tag": _clip_str(data.get("PEN_PROC_TAG"), 1),
        "nomin_srl_no": _int_val(data.get("NOMIN_SRL_NO")),
        "base_cpi": _dec_val(data.get("BASE_CPI")),
        "payment_tag": _clip_str(data.get("PAYMENT_TAG"), 2),
        "lic_bank_cd": _clip_str(data.get("LIC_BANK_CD"), 6),
    }


def _map_td_first_month(data):
    fmpen_id = _clip_str(data.get("FMPEN_ID"), 22)
    code = _clip_str(data.get("EARN_DEDN_CD"), 3)
    ed_type = _clip_str(data.get("EARN_DEDN_TYPE"), 1)
    if not fmpen_id or not code or not ed_type:
        return None
    return {
        "fmpen_id": fmpen_id,
        "earn_dedn_type": ed_type,
        "earn_dedn_cd": code,
        "amount": _dec_val(data.get("AMOUNT")),
        "emp_cd": _clip_str(data.get("EMP_CD"), 5),
        "original_amt": _dec_val(data.get("ORIGINAL_AMT")),
        "arrear_amt": _dec_val(data.get("ARREAR_AMT")),
        "date_created": _date_val(data.get("DATE_CREATED")),
        "created_by": _clip_str(data.get("CREATED_BY"), 5),
        "date_modified": _date_val(data.get("DATE_MODIFIED")),
        "modified_by": _clip_str(data.get("MODIFIED_BY"), 5),
    }


def _map_pensioner(data):
    ca = _clip_str(data.get("CA_NUMBER"), 22)
    emp = _clip_str(data.get("EMP_CD"), 5)
    if not ca or not emp:
        return None
    return {
        "ca_number": ca,
        "emp_cd": emp,
        "original_pension_amt": _dec_val(data.get("ORIGINAL_PENSION_AMT")),
        "effective_stdt_pension": _date_val(data.get("EFFECTIVE_STDT_PENSION")),
        "commuted_portion": _dec_val(data.get("COMMUTED_PORTION")),
        "payable_pension": _dec_val(data.get("PAYABLE_PENSION")),
        "gratuity": _dec_val(data.get("GRATUITY")),
        "commutation_per": _dec_val(data.get("COMMUTATION_PER")),
        "relief": _dec_val(data.get("RELIEF")),
        "pension_emoluments": _dec_val(data.get("PENSION_EMOLUMENTS")),
        "gratuity_emoluments": _dec_val(data.get("GRATUITY_EMOLUMENTS")),
        "tccs_yr": _int_val(data.get("TCCS_YR")),
        "tccs_month": _int_val(data.get("TCCS_MONTH")),
        "tccs_days": _int_val(data.get("TCCS_DAYS")),
        "tqs_yr": _int_val(data.get("TQS_YR")),
        "tqs_month": _int_val(data.get("TQS_MONTH")),
        "tqs_days": _int_val(data.get("TQS_DAYS")),
        "name": _clip_str(data.get("NAME"), 62),
        "pension_option": _clip_str(data.get("PENSION_OPTION"), 1),
        "base_cpi": _dec_val(data.get("BASE_CPI")),
        "bank_cd": _clip_str(data.get("BANK_CD"), 6),
        "lic_bank_cd": _clip_str(data.get("LIC_BANK_CD"), 6),
        "account_no": _clip_str(data.get("ACCOUNT_NO"), 20),
        "pension_roll_no": _clip_str(data.get("PENSION_ROLL_NO"), 22),
        "sex": _clip_str(data.get("SEX"), 1),
        "dob": _date_val(data.get("DOB")),
        "desig_cd": _int_val(data.get("DESIG_CD")),
        "emp_ret_dt": _date_val(data.get("EMP_RET_DT")),
        "app_class": _int_val(data.get("APP_CLASS")),
        "date_commutation": _date_val(data.get("DATE_COMMUTATION")),
        "date_created": _date_val(data.get("DATE_CREATED")),
        "created_by": _clip_str(data.get("CREATED_BY"), 5),
        "date_modified": _date_val(data.get("DATE_MODIFIED")),
        "modified_by": _clip_str(data.get("MODIFIED_BY"), 5),
    }


def _map_pension_bill(data):
    bill_no = _clip_str(data.get("BILL_NO"), 22)
    if not bill_no:
        return None
    return {
        "bill_no": bill_no,
        "bill_type": _clip_str(data.get("BILL_TYPE"), 3),
        "bill_month": _int_val(data.get("BILL_MONTH")),
        "bill_yr": _int_val(data.get("BILL_YR")),
        "bank_cd": _clip_str(data.get("BANK_CD"), 6),
        "total_amt_earned": _dec_val(data.get("TOTAL_AMT_EARNED")),
        "total_amt_deducted": _dec_val(data.get("TOTAL_AMT_DEDUCTED")),
        "bill_abstract_no": _clip_str(data.get("BILL_ABSTRACT_NO"), 22),
        "abstract_type": _clip_str(data.get("ABSTRACT_TYPE"), 2),
        "cheque_no": _int_val(data.get("CHEQUE_NO")),
        "cheque_dt": _date_val(data.get("CHEQUE_DT")),
        "cheque_amt": _dec_val(data.get("CHEQUE_AMT")),
        "date_created": _date_val(data.get("DATE_CREATED")),
        "created_by": _clip_str(data.get("CREATED_BY"), 5),
        "date_modified": _date_val(data.get("DATE_MODIFIED")),
        "modified_by": _clip_str(data.get("MODIFIED_BY"), 5),
        "remarks": _clip_str(data.get("REMARKS"), 100),
        "voucher_no": _clip_str(data.get("VOUCHER_NO"), 25),
        "abstract_date": _date_val(data.get("ABSTRACT_DATE")),
        "gen_lic_tag": _clip_str(data.get("GEN_LIC_TAG"), 1),
        "posted": _clip_str(data.get("POSTED"), 1),
        "posted_on": _date_val(data.get("POSTED_ON")),
        "posted_by": _clip_str(data.get("POSTED_BY"), 5),
    }


def _map_pmthsetup(data):
    bill_type = _clip_str(data.get("BILL_TYPE"), 3)
    bill_mth = _int_val(data.get("BILL_MTH"))
    bill_yr = _int_val(data.get("BILL_YR"))
    if not bill_type or bill_mth is None or bill_yr is None:
        return None
    return {
        "bill_type": bill_type,
        "bill_mth": bill_mth,
        "bill_yr": bill_yr,
        "bill_process_flg": _int_val(data.get("BILL_PROCESS_FLG"), 0),
        "bill_close_flg": _int_val(data.get("BILL_CLOSE_FLG"), 0),
        "date_created": _date_val(data.get("DATE_CREATED")),
        "created_by": _clip_str(data.get("CREATED_BY"), 5),
        "date_modified": _date_val(data.get("DATE_MODIFIED")),
        "modified_by": _clip_str(data.get("MODIFIED_BY"), 5),
    }


WAVE3_SYNC_SPECS = [
    {
        "oracle_table": "FI_PN_TH_FIRST_MONTH_PENSION",
        "app": "first_pension",
        "model": "FiPnThFirstMonthPension",
        "mapper": _map_th_first_month,
        "order_by": "FMPEN_ID",
        "pk_field": "fmpen_id",
        "emp_filter_column": "EMP_CD",
    },
    {
        "oracle_table": "FI_PN_TD_FIRST_MONTH_PENSION",
        "app": "first_pension",
        "model": "FiPnTdFirstMonthPension",
        "mapper": _map_td_first_month,
        "order_by": "FMPEN_ID, EARN_DEDN_TYPE, EARN_DEDN_CD",
        "emp_filter_column": "EMP_CD",
        "composite_unique": ("fmpen_id", "earn_dedn_cd", "earn_dedn_type"),
    },
    {
        "oracle_table": "FI_PN_MH_PENSIONER",
        "app": "first_pension",
        "model": "FiPnMhPensioner",
        "mapper": _map_pensioner,
        "order_by": "CA_NUMBER",
        "pk_field": "ca_number",
        "emp_filter_column": "EMP_CD",
    },
    {
        "oracle_table": "FI_PN_TH_PENSION_BILL",
        "app": "first_pension",
        "model": "FiPnThPensionBill",
        "mapper": _map_pension_bill,
        "order_by": "BILL_NO",
        "pk_field": "bill_no",
    },
    {
        "oracle_table": "FI_PN_MH_PMTHSETUP",
        "app": "first_pension",
        "model": "FiPnMhPmthsetup",
        "mapper": _map_pmthsetup,
        "order_by": "BILL_TYPE, BILL_MTH, BILL_YR",
        "composite_unique": ("bill_type", "bill_mth", "bill_yr"),
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


def _delete_existing(model, spec, emp_cd=None):
    if emp_cd and spec.get("emp_filter_column"):
        col = spec["emp_filter_column"].lower()
        if spec["oracle_table"] == "FI_PN_TD_FIRST_MONTH_PENSION":
            from first_pension.oracle_mirror import FiPnThFirstMonthPension

            fmpen_ids = FiPnThFirstMonthPension.objects.filter(
                emp_cd=str(emp_cd).strip()[:5]
            ).values_list("fmpen_id", flat=True)
            model.objects.filter(fmpen_id__in=list(fmpen_ids)).delete()
            return
        model.objects.filter(**{col: str(emp_cd).strip()[:5]}).delete()
        return
    model.objects.all().delete()


def _flush_batch(model, batch, batch_size):
    if not batch:
        return 0
    model.objects.bulk_create(batch, batch_size=batch_size)
    count = len(batch)
    batch.clear()
    return count


def sync_wave3_table(spec, *, full_refresh=True, batch_size=2000, emp_cd=None):
    model = apps.get_model(spec["app"], spec["model"])
    column_names, rows = _fetch_oracle_rows_filtered(spec, emp_cd=emp_cd)

    if full_refresh:
        _delete_existing(model, spec, emp_cd=emp_cd)

    inserted = skipped = 0
    batch = []

    for row in rows:
        data = _row_dict(column_names, row)
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


def sync_all_wave3(*, full_refresh=True, batch_size=2000, emp_cd=None, tables=None):
    selected = tables or [s["oracle_table"] for s in WAVE3_SYNC_SPECS]
    results = []
    with transaction.atomic():
        for spec in WAVE3_SYNC_SPECS:
            if spec["oracle_table"] not in selected:
                continue
            results.append(
                sync_wave3_table(
                    spec,
                    full_refresh=full_refresh,
                    batch_size=batch_size,
                    emp_cd=emp_cd,
                )
            )
    return results
