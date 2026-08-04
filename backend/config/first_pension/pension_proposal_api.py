from decimal import Decimal

from datetime import date, datetime

from django.conf import settings
from django.shortcuts import get_object_or_404
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from audit.services import log_audit
from master_data.services.bank_service import (
    fetch_bank_abbr_by_type,
    fetch_bank_abbr_list,
    fetch_bank_by_code,
    fetch_bank_master_list,
)
from master_data.services.earndedn_service import (
    list_earndedn_from_mysql,
    lookup_earndedn_by_code,
    serialize_earndedn_master,
)
from master_data.services.oracle_bank_service import fetch_employee_bank_details
from employee.services.oracle_service import (
    get_oracle_connection,
    oracle_reads_enabled,
    try_oracle_connection,
)
from .services.proposal_earndedn_service import (
    proposal_earndedn_to_api_rows,
    save_proposal_earndedn_rows,
)
from employee.services.oracle_pension_proposal_service import (
    upsert_fi_pn_mh_pension_proposal,
)
from .models import CommutationApplication, PensionCase, PensionProposal
from .pension_calculation import (
    get_commutation_application_for_employee,
    get_service_tenure_for_employee,
)
from .pension_proposal_validation import (
    _normalize_held_up_flag,
    _normalize_withhold_reason,
    normalize_pension_proposal_payload,
    validate_pension_proposal_data,
)


def sync_commutation_ca_no_from_proposal(emp_cd, ca_number):
    """Keep commutation ca_no in sync with pension proposal CA number."""
    ca = str(ca_number or "").strip()
    if not ca:
        return
    app = get_commutation_application_for_employee(emp_cd)
    if not app:
        return
    CommutationApplication.objects.filter(pk=app.pk).update(ca_no=ca[:50])


def _format_date_for_api(value):
    if not value:
        return ""
    if hasattr(value, "strftime"):
        return value.strftime("%Y-%m-%d")
    return str(value)


def _parse_optional_date(value):
    if value is None or value == "":
        return None
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if hasattr(value, "date"):
        return value.date()
    text = str(value).strip()[:10]
    for fmt in ("%Y-%m-%d", "%d-%m-%Y"):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    return None


def _coerce_date_value(value):
    """Return a date object from date/datetime/str, or None."""
    return _parse_optional_date(value)


def _parse_optional_date_value(value):
    return _coerce_date_value(value)


def _parse_bool(value):
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    text = str(value).strip().upper()
    if text in ("Y", "YES", "TRUE", "1", "ON"):
        return True
    if text in ("N", "NO", "FALSE", "0", "OFF", ""):
        return False
    return False


def _parse_int(value, default=None):
    if value is None or value == "":
        return default
    return int(value)


def _parse_decimal(value):
    if value is None or value == "":
        return None
    return value


def _decimal_for_json(value):
    if value is None:
        return None
    if isinstance(value, Decimal):
        return float(value)
    return value


def _earning_deductions_for_json(rows):
    serialized = []
    for row in rows or []:
        if not isinstance(row, dict):
            continue
        item = dict(row)
        if item.get("amount") not in (None, ""):
            try:
                item["amount"] = float(item["amount"])
            except (TypeError, ValueError):
                pass
        serialized.append(item)
    return serialized


def serialize_pension_proposal(obj):
    ctx = _resolve_separation_context(obj.emp_cd, None)
    sep_type = (obj.separation_type or ctx["separation_type"] or "").strip().upper()
    ref = _resolve_proposal_start_reference(
        obj.emp_cd,
        None,
        separation_type=sep_type,
        separation_dt=obj.separation_date or ctx["separation_date"],
    )
    start_month = obj.start_month
    start_year = obj.start_year
    if sep_type == "VR" and ref:
        ref = _coerce_date_value(ref)
        if ref:
            start_month = ref.month
            start_year = ref.year

    ca_number = str(obj.ca_number or "").strip() or resolve_proposal_ca_number(obj)

    return {
        "id": obj.id,
        "emp_cd": obj.emp_cd,
        "emp_name": obj.emp_name,
        "employee_status": obj.employee_status,
        "ca_number": ca_number,
        "pension_type": obj.pension_type,
        "pension_proposal_no": obj.pension_proposal_no,
        "eligible_double_family_pension": obj.eligible_double_family_pension,
        "separation_type": obj.separation_type,
        "separation_date": _format_date_for_api(obj.separation_date),
        "implemented_year": obj.implemented_year,
        "implemented_month": obj.implemented_month,
        "service_tenure": obj.service_tenure,
        "pension_option": obj.pension_option,
        "option_given_by": obj.option_given_by,
        "regn_no": obj.regn_no,
        "regn_date": _format_date_for_api(obj.regn_date),
        "start_month": start_month,
        "start_year": start_year,
        "pension_roll_no": obj.pension_roll_no,
        "pension_proposal_date": _format_date_for_api(obj.pension_proposal_date),
        "double_family_pension_upto_date": _format_date_for_api(
            obj.double_family_pension_upto_date
        ),
        "provisional_pension_pct": _decimal_for_json(obj.provisional_pension_pct),
        "bank_cd": obj.bank_cd,
        "bank_name": obj.bank_name,
        "account_no": obj.account_no,
        "vigilance_clearance_ref_no": obj.vigilance_clearance_ref_no,
        "vigilance_clearance_ref_dt": _format_date_for_api(
            obj.vigilance_clearance_ref_dt
        ),
        "lic_bank_cd": obj.lic_bank_cd,
        "lic_bank_name": obj.lic_bank_name,
        "vr_ref_no": obj.vr_ref_no,
        "vr_ref_dt": _format_date_for_api(obj.vr_ref_dt),
        "compassionate_allowance": obj.compassionate_allowance,
        "quarter_status": obj.quarter_status,
        "nominee_eform": obj.nominee_eform,
        "compassionate_allowance_amt": _decimal_for_json(
            obj.compassionate_allowance_amt
        ),
        "port_city_resident": obj.port_city_resident,
        "gratuity_option": obj.gratuity_option,
        "retirement_cpi": _decimal_for_json(obj.retirement_cpi),
        "id_card_submitted": obj.id_card_submitted,
        "vigilance_cleared": obj.vigilance_cleared,
        "incentive_holder": obj.incentive_holder,
        "held_up_flag": obj.held_up_flag,
        "held_gratuity_amt": _decimal_for_json(obj.held_gratuity_amt),
        "held_recovery_amt": _decimal_for_json(obj.held_recovery_amt),
        "held_recovery_date": _format_date_for_api(obj.held_recovery_date),
        "held_recovery_ref_no": obj.held_recovery_ref_no,
        "held_recovery_remarks": obj.held_recovery_remarks,
        "extra_tccs_enabled": obj.extra_tccs_enabled,
        "extra_tccs_years": obj.extra_tccs_years,
        "extra_tccs_months": obj.extra_tccs_months,
        "extra_tccs_days": obj.extra_tccs_days,
        "earning_deductions": _earning_deductions_for_json(
            proposal_earndedn_to_api_rows(obj)
        ),
    }


def _apply_date_defaults(defaults, ref_date):
    """Set separation / start / impl fields from a reference date."""
    ref = _coerce_date_value(ref_date)
    if not ref:
        return
    defaults["separation_date"] = ref.strftime("%Y-%m-%d")
    defaults["start_month"] = ref.month
    defaults["start_year"] = ref.year


def _resolve_separation_context(emp_id, pension_case=None):
    """Separation type/date from case, intake, or MySQL ADM mirror."""
    emp_key = str(emp_id).strip()[:5]
    sep_type = ""
    sep_dt = None
    exp_ret_dt = None

    if pension_case:
        sep_type = (pension_case.separation_type or "").strip().upper()
        sep_dt = pension_case.separation_date

    if not sep_type or not sep_dt:
        from .process_intake_api import serialize_process_intake

        intake = serialize_process_intake(case=pension_case, emp_code=emp_key)
        if intake:
            sep_type = sep_type or (intake.get("separation_type") or "").strip().upper()
            if not sep_dt:
                sep_dt = _parse_optional_date_value(intake.get("separation_date"))

    from employee.oracle_mirror import FiXxMhEmpAdm

    adm = FiXxMhEmpAdm.objects.filter(emp_cd=emp_key).first()
    if adm:
        sep_type = sep_type or (adm.separation_type or "").strip().upper()
        if not sep_dt:
            sep_dt = adm.separation_dt
        exp_ret_dt = adm.exp_ret_dt

    proposal = get_pension_proposal_for_employee(emp_key)
    if proposal:
        sep_type = sep_type or (proposal.separation_type or "").strip().upper()
        if not sep_dt:
            sep_dt = proposal.separation_date

    return {
        "separation_type": sep_type,
        "separation_date": sep_dt,
        "exp_ret_date": exp_ret_dt,
    }


def _resolve_proposal_start_reference(emp_id, pension_case=None, *, separation_type=None, separation_dt=None, exp_ret_dt=None):
    """
    Pension start month/year reference date.
    VR (and any saved separation) uses separation date, not retirement / EXP_RET_DT.
    """
    ctx = _resolve_separation_context(emp_id, pension_case)
    sep_type = (separation_type or ctx["separation_type"] or "").strip().upper()
    sep = separation_dt or ctx["separation_date"]
    exp_ret = exp_ret_dt or ctx["exp_ret_date"]

    if sep_type == "VR" and sep:
        return sep
    if sep:
        return sep
    if exp_ret:
        return exp_ret
    if pension_case and pension_case.retirement_date:
        return pension_case.retirement_date
    return None


def _sync_vr_start_period(obj):
    """Keep start month/year aligned with separation date for VR proposals."""
    if (obj.separation_type or "").strip().upper() != "VR":
        return
    sep = _coerce_date_value(obj.separation_date)
    if not sep:
        return
    obj.separation_date = sep
    obj.start_month = int(sep.month)
    obj.start_year = int(sep.year)


def fetch_bank_details_from_oracle(cursor, emp_id):
    return fetch_employee_bank_details(cursor, emp_id)


def merge_oracle_bank_into_proposal_data(proposal_data, proposal_defaults):
    """Fill empty bank fields and VR start period on saved proposal from defaults."""
    if not proposal_data or not proposal_defaults:
        return proposal_data
    for key in ("bank_cd", "bank_name", "account_no"):
        if not proposal_data.get(key) and proposal_defaults.get(key):
            proposal_data[key] = proposal_defaults[key]
    if proposal_defaults.get("service_tenure"):
        proposal_data["service_tenure"] = proposal_defaults["service_tenure"]

    sep_type = (
        proposal_data.get("separation_type")
        or proposal_defaults.get("separation_type")
        or ""
    ).strip().upper()
    if not proposal_data.get("separation_date") and proposal_defaults.get("separation_date"):
        proposal_data["separation_date"] = proposal_defaults["separation_date"]
    if sep_type == "VR":
        if proposal_defaults.get("start_month") is not None:
            proposal_data["start_month"] = proposal_defaults["start_month"]
        if proposal_defaults.get("start_year") is not None:
            proposal_data["start_year"] = proposal_defaults["start_year"]
    if not proposal_data.get("ca_number") and proposal_defaults.get("ca_number"):
        proposal_data["ca_number"] = proposal_defaults["ca_number"]
    return proposal_data


def fetch_proposal_defaults_from_oracle(cursor, emp_id, pension_case=None):
    """
    Load separation date, start month/year, and bank details from Oracle.
    """
    defaults = {
        "separation_type": "",
        "separation_date": "",
        "implemented_month": None,
        "implemented_year": None,
        "start_month": None,
        "start_year": None,
        "bank_cd": "",
        "bank_name": "",
        "account_no": "",
        "ca_number": "",
    }

    queries = [
        """
        SELECT t2.SEPARATION_TYPE, t2.SEPARATION_DT, t2.EXP_RET_DT
        FROM FINANCE.FI_XX_MH_EMP_PER t1
        LEFT JOIN FINANCE.FI_XX_MH_EMP_ADM t2 ON t1.EMP_CD = t2.EMP_CD
        WHERE t1.EMP_CD = :emp_id
        """,
        """
        SELECT t2.SEPARATION_TYPE, t2.EXP_RET_DT
        FROM FINANCE.FI_XX_MH_EMP_PER t1
        LEFT JOIN FINANCE.FI_XX_MH_EMP_ADM t2 ON t1.EMP_CD = t2.EMP_CD
        WHERE t1.EMP_CD = :emp_id
        """,
    ]

    for query in queries:
        try:
            cursor.execute(query, {"emp_id": emp_id})
            row = cursor.fetchone()
            if not row:
                continue

            if row[0]:
                defaults["separation_type"] = str(row[0]).strip()

            sep_dt = row[1] if len(row) > 2 else None
            exp_ret = row[2] if len(row) > 2 else row[1]
            sep_type = (defaults.get("separation_type") or "").strip().upper()
            if sep_type == "VR" and sep_dt:
                ref_date = sep_dt
            else:
                ref_date = sep_dt or exp_ret
            _apply_date_defaults(defaults, ref_date)
            break
        except Exception:
            continue

    ctx = _resolve_separation_context(emp_id, pension_case)
    if ctx["separation_type"] and not defaults["separation_type"]:
        defaults["separation_type"] = ctx["separation_type"]
    ref_date = _resolve_proposal_start_reference(
        emp_id,
        pension_case,
        separation_type=defaults.get("separation_type") or ctx["separation_type"],
        separation_dt=_parse_optional_date_value(defaults.get("separation_date"))
        or ctx["separation_date"],
        exp_ret_dt=ctx["exp_ret_date"],
    )
    if ref_date:
        _apply_date_defaults(defaults, ref_date)
    elif pension_case and pension_case.retirement_date and not defaults["separation_date"]:
        _apply_date_defaults(defaults, pension_case.retirement_date)

    defaults.update(fetch_bank_details_from_oracle(cursor, emp_id))
    defaults["ca_number"] = _load_ca_number_for_employee(emp_id, cursor=cursor)
    defaults["service_tenure"] = get_service_tenure_for_employee(emp_id)

    return defaults


def load_proposal_defaults_from_oracle(emp_id, pension_case=None):
    """
    Open Oracle via employee.services.oracle_service.get_oracle_connection
    and load all proposal default fields (dates, bank, etc.).
    """
    with get_oracle_connection().cursor() as cursor:
        return fetch_proposal_defaults_from_oracle(
            cursor, emp_id, pension_case
        )


def load_proposal_defaults_from_mirror(emp_id, pension_case=None):
    """Proposal defaults from MySQL mirror + SMPK case/intake when Oracle is down."""
    defaults = {
        "separation_type": "",
        "separation_date": "",
        "implemented_month": None,
        "implemented_year": None,
        "start_month": None,
        "start_year": None,
        "bank_cd": "",
        "bank_name": "",
        "account_no": "",
        "ca_number": "",
    }
    ctx = _resolve_separation_context(emp_id, pension_case)
    if ctx["separation_type"]:
        defaults["separation_type"] = ctx["separation_type"]
    ref_date = _resolve_proposal_start_reference(emp_id, pension_case)
    if ref_date:
        _apply_date_defaults(defaults, ref_date)

    emp_key = str(emp_id).strip()[:5]
    from employee.oracle_mirror import FiXxMhEmpFin

    fin = FiXxMhEmpFin.objects.filter(emp_cd=emp_key).first()
    if fin:
        defaults["bank_cd"] = (fin.bank_cd or "").strip()
        defaults["account_no"] = (fin.bank_ac_no or "").strip()
        if defaults["bank_cd"]:
            try:
                from master_data.models import FiPmMhBank

                branch = FiPmMhBank.objects.filter(bank_cd=defaults["bank_cd"]).first()
                if branch and branch.bank_desc:
                    defaults["bank_name"] = branch.bank_desc.strip()
            except Exception:
                pass

    defaults["ca_number"] = _load_ca_number_for_employee(emp_key)
    defaults["service_tenure"] = get_service_tenure_for_employee(emp_id)
    return defaults


def load_proposal_defaults(emp_id, pension_case=None):
    """MySQL mirror + SMPK first; live Oracle only when ORACLE_READ_ENABLED."""
    if not oracle_reads_enabled():
        return load_proposal_defaults_from_mirror(emp_id, pension_case)
    try:
        return load_proposal_defaults_from_oracle(emp_id, pension_case)
    except Exception:
        return load_proposal_defaults_from_mirror(emp_id, pension_case)


def _load_ca_number_for_employee(emp_id, cursor=None):
    """CA number from saved proposal, Oracle header, or MySQL mirror."""
    emp_key = str(emp_id).strip()[:5]
    proposal = get_pension_proposal_for_employee(emp_key)
    if proposal:
        ca = str(proposal.ca_number or "").strip()
        if ca:
            return ca[:50]

    if cursor is not None:
        try:
            cursor.execute(
                """
                SELECT CA_NUMBER
                FROM FINANCE.FI_PN_MH_PENSION_PROPOSAL
                WHERE EMP_CD = :emp_id
                """,
                {"emp_id": emp_key},
            )
            row = cursor.fetchone()
            if row and row[0]:
                return str(row[0]).strip()[:50]
        except Exception:
            pass

    from .oracle_mirror import FiPnMhPensionProposal

    mirror = FiPnMhPensionProposal.objects.filter(emp_cd=emp_key).first()
    if mirror and mirror.ca_number:
        return str(mirror.ca_number).strip()[:50]

    comm = CommutationApplication.objects.filter(emp_cd=emp_key).first()
    if comm and comm.ca_no:
        return str(comm.ca_no).strip()[:50]
    return ""


def resolve_proposal_ca_number(proposal, emp_code=None):
    """Best available CA number for proposal / first-pension generation."""
    if proposal:
        ca = str(proposal.ca_number or "").strip()
        if ca:
            return ca[:50]
    return _load_ca_number_for_employee(emp_code or getattr(proposal, "emp_cd", ""))


def backfill_proposal_ca_number(proposal, ca_number=None):
    """Persist resolved CA number on the local proposal when missing."""
    if not proposal:
        return ""
    ca = str(ca_number or resolve_proposal_ca_number(proposal) or "").strip()[:50]
    if ca and not str(proposal.ca_number or "").strip():
        proposal.ca_number = ca
        proposal.save(update_fields=["ca_number"])
    return ca


def get_pension_proposal_for_employee(emp_id):
    emp_key = str(emp_id).strip()
    proposal = PensionProposal.objects.filter(emp_cd=emp_key).first()
    if proposal:
        return proposal
    if emp_key.isdigit():
        proposal = PensionProposal.objects.filter(
            emp_cd=str(int(emp_key))
        ).first()
        if proposal:
            return proposal
    return PensionProposal.objects.filter(emp_cd__iexact=emp_key).first()


def apply_pension_proposal_fields(obj, data, user, *, is_create=False):
    obj.emp_name = data.get("emp_name", obj.emp_name)
    obj.employee_status = data.get("employee_status", obj.employee_status)
    obj.ca_number = str(
        data.get("ca_number") if "ca_number" in data else obj.ca_number or ""
    ).strip()[:50]
    obj.pension_type = data.get("pension_type", obj.pension_type)
    obj.pension_proposal_no = data.get(
        "pension_proposal_no", obj.pension_proposal_no
    )
    obj.eligible_double_family_pension = _parse_bool(
        data.get("eligible_double_family_pension", obj.eligible_double_family_pension)
    )

    obj.separation_type = data.get("separation_type", obj.separation_type)
    obj.separation_date = _parse_optional_date(data.get("separation_date"))
    _sync_vr_start_period(obj)
    # User requirement: Impl month/year should remain NULL unless explicitly entered.
    # Blank payload values must clear the field instead of keeping the old value.
    obj.implemented_year = _parse_int(data.get("implemented_year"), None)
    obj.implemented_month = _parse_int(data.get("implemented_month"), None)
    computed_tenure = get_service_tenure_for_employee(obj.emp_cd)
    obj.service_tenure = computed_tenure or data.get("service_tenure") or ""

    obj.pension_option = data.get("pension_option", obj.pension_option)
    obj.option_given_by = data.get("option_given_by", obj.option_given_by)
    obj.regn_no = data.get("regn_no", obj.regn_no)
    obj.regn_date = _parse_optional_date(data.get("regn_date"))
    obj.start_month = _parse_int(data.get("start_month"), obj.start_month)
    obj.start_year = _parse_int(data.get("start_year"), obj.start_year)
    _sync_vr_start_period(obj)
    obj.pension_roll_no = data.get("pension_roll_no", obj.pension_roll_no)
    obj.pension_proposal_date = _parse_optional_date(
        data.get("pension_proposal_date")
    )
    obj.double_family_pension_upto_date = _parse_optional_date(
        data.get("double_family_pension_upto_date")
    )

    obj.provisional_pension_pct = _parse_decimal(
        data.get("provisional_pension_pct")
    )
    obj.bank_cd = data.get("bank_cd", obj.bank_cd)
    obj.bank_name = data.get("bank_name", obj.bank_name)
    obj.account_no = data.get("account_no", obj.account_no)

    obj.vigilance_clearance_ref_no = data.get(
        "vigilance_clearance_ref_no", obj.vigilance_clearance_ref_no
    )
    obj.vigilance_clearance_ref_dt = _parse_optional_date(
        data.get("vigilance_clearance_ref_dt")
    )
    obj.lic_bank_cd = data.get("lic_bank_cd", obj.lic_bank_cd)
    obj.lic_bank_name = data.get("lic_bank_name", obj.lic_bank_name)

    obj.vr_ref_no = data.get("vr_ref_no", obj.vr_ref_no)
    obj.vr_ref_dt = _parse_optional_date(data.get("vr_ref_dt"))
    obj.compassionate_allowance = data.get(
        "compassionate_allowance", obj.compassionate_allowance
    )
    obj.quarter_status = _normalize_withhold_reason(
        data.get("quarter_status", obj.quarter_status)
    )
    obj.nominee_eform = data.get("nominee_eform", obj.nominee_eform)
    obj.compassionate_allowance_amt = _parse_decimal(
        data.get("compassionate_allowance_amt")
    )

    obj.port_city_resident = data.get("port_city_resident", obj.port_city_resident)
    obj.gratuity_option = data.get("gratuity_option", obj.gratuity_option)
    obj.retirement_cpi = _parse_decimal(data.get("retirement_cpi"))
    obj.id_card_submitted = _parse_bool(
        data.get("id_card_submitted", obj.id_card_submitted)
    )
    obj.vigilance_cleared = _parse_bool(
        data.get("vigilance_cleared", obj.vigilance_cleared)
    )
    obj.incentive_holder = data.get("incentive_holder", obj.incentive_holder)
    obj.held_up_flag = _normalize_held_up_flag(
        data.get("held_up_flag", obj.held_up_flag)
    )
    obj.held_gratuity_amt = _parse_decimal(data.get("held_gratuity_amt"))
    obj.held_recovery_amt = _parse_decimal(data.get("held_recovery_amt"))
    obj.held_recovery_date = _parse_optional_date(data.get("held_recovery_date"))
    obj.held_recovery_ref_no = data.get("held_recovery_ref_no", obj.held_recovery_ref_no)
    obj.held_recovery_remarks = data.get(
        "held_recovery_remarks", obj.held_recovery_remarks
    )

    obj.extra_tccs_enabled = _parse_bool(
        data.get("extra_tccs_enabled", obj.extra_tccs_enabled)
    )
    obj.extra_tccs_years = _parse_int(data.get("extra_tccs_years"), 0)
    obj.extra_tccs_months = _parse_int(data.get("extra_tccs_months"), 0)
    obj.extra_tccs_days = _parse_int(data.get("extra_tccs_days"), 0)

    earning_rows = None
    if "earning_deductions" in data:
        earning_rows = data.get("earning_deductions") or []

    if is_create:
        obj.created_by = user
    elif user and user.is_authenticated:
        obj.updated_by = user

    obj.save()

    if earning_rows is not None:
        save_proposal_earndedn_rows(obj, earning_rows, user)


def _oracle_sync_required():
    return getattr(settings, "ORACLE_SYNC_REQUIRED", False)


def _user_code_from_request(request):
    return (getattr(request.user, "username", None) or "SYS")[:5]


def sync_pension_proposal_to_oracle(obj, user_code):
    """
    Push proposal to FI_PN_MH_PENSION_PROPOSAL.
    Returns (synced, error_message).
    """
    try:
        oracle_result = upsert_fi_pn_mh_pension_proposal(obj, user_code=user_code)
    except Exception as e:
        return False, str(e)

    update_fields = []
    if oracle_result.get("pension_proposal_no") and not obj.pension_proposal_no:
        obj.pension_proposal_no = oracle_result["pension_proposal_no"]
        update_fields.append("pension_proposal_no")
    if oracle_result.get("ca_number") and not obj.ca_number:
        obj.ca_number = oracle_result["ca_number"]
        update_fields.append("ca_number")
    if update_fields:
        obj.save(update_fields=update_fields)
    return True, None


def _build_proposal_save_response(request, obj, *, is_create, old_data=None):
    # ORACLE WRITE DISABLED — MySQL-only mode. Uncomment to sync proposal to Oracle.
    # synced, oracle_error = sync_pension_proposal_to_oracle(
    #     obj, _user_code_from_request(request)
    # )
    # if not synced and _oracle_sync_required():
    #     return Response(
    #         {
    #             "error": (
    #                 "Could not update Oracle (FI_PN_MH_PENSION_PROPOSAL): "
    #                 f"{oracle_error}"
    #             ),
    #             "oracle_synced": False,
    #             "id": obj.id,
    #             "proposal_data": serialize_pension_proposal(obj),
    #         },
    #         status=status.HTTP_502_BAD_GATEWAY,
    #     )

    new_data = serialize_pension_proposal(obj)
    sync_commutation_ca_no_from_proposal(obj.emp_cd, obj.ca_number)
    log_audit(
        request,
        table_name="PensionProposal",
        record_id=obj.id,
        action="CREATE" if is_create else "UPDATE",
        old_data=old_data,
        new_data=new_data,
        module="FIRST_PENSION",
    )

    if is_create:
        message = "Pension Proposal Saved Successfully"
    else:
        message = "Pension Proposal Updated Successfully"

    return Response({
        "message": message,
        "id": obj.id,
        "proposal_data": new_data,
    })


class PensionProposalLookupAPIView(APIView):
    def get(self, request, emp_code):
        proposal = get_pension_proposal_for_employee(emp_code)
        if proposal:
            proposal_data = serialize_pension_proposal(proposal)
            try:
                pension_case = PensionCase.objects.filter(
                    emp_code=str(emp_code).strip()
                ).first()
                defaults = load_proposal_defaults(
                    emp_code, pension_case
                )
                proposal_data = merge_oracle_bank_into_proposal_data(
                    proposal_data, defaults
                )
            except Exception:
                pass
            return Response({
                "exists": True,
                "proposal_data": proposal_data,
            })

        proposal_defaults = {}
        try:
            emp_key = str(emp_code).strip()
            pension_case = PensionCase.objects.filter(emp_code=emp_key).first()
            proposal_defaults = load_proposal_defaults(
                emp_code, pension_case
            )
            from .services.legacy_prefill_service import (
                enrich_proposal_defaults_from_legacy,
            )

            proposal_defaults = enrich_proposal_defaults_from_legacy(
                emp_code, proposal_defaults
            )
        except Exception:
            pass

        return Response({
            "exists": False,
            "proposal_data": None,
            "proposal_defaults": proposal_defaults,
        })


class PensionProposalAPIView(APIView):
    def post(self, request):
        try:
            emp_cd = request.data.get("emp_cd")
            if PensionProposal.objects.filter(emp_cd=emp_cd).exists():
                return Response(
                    {
                        "error": (
                            "Pension proposal already exists for this employee. "
                            "Use Edit to update."
                        )
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            payload = normalize_pension_proposal_payload(request.data)
            errors = validate_pension_proposal_data(payload)
            if errors:
                return Response(
                    {"error": errors[0], "errors": errors},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            obj = PensionProposal(emp_cd=emp_cd)
            apply_pension_proposal_fields(
                obj, payload, request.user, is_create=True
            )
            return _build_proposal_save_response(
                request, obj, is_create=True, old_data=None
            )
        except Exception as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    def put(self, request, pk):
        try:
            obj = get_object_or_404(PensionProposal, pk=pk)
            old_data = serialize_pension_proposal(obj)
            payload = normalize_pension_proposal_payload(request.data)
            errors = validate_pension_proposal_data(payload, instance=obj)
            if errors:
                return Response(
                    {"error": errors[0], "errors": errors},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            apply_pension_proposal_fields(
                obj, payload, request.user, is_create=False
            )
            return _build_proposal_save_response(
                request, obj, is_create=False, old_data=old_data
            )
        except Exception as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


def fetch_earndedn_by_code(earndedn_cd):
    """Lookup earn/dedn from MySQL master, then Oracle."""
    code = str(earndedn_cd).strip()
    if not code:
        return None

    master = lookup_earndedn_by_code(code)
    if master:
        return serialize_earndedn_master(master)
    if not oracle_reads_enabled():
        return None
    return fetch_earndedn_from_oracle(code)


def fetch_earndedn_from_oracle(earndedn_cd):
    """Lookup earning/deduction description from FINANCE.FI_PN_MH_EARNDEDN."""
    code = str(earndedn_cd).strip()
    if not code:
        return None

    type_map = {"E": "EARN", "D": "DEDN"}

    conn = try_oracle_connection()
    if conn is None:
        return None
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT EARNDEDN_CD, EARNDEDN_TYPE, EARNDEDN_DESC
                FROM FINANCE.FI_PN_MH_EARNDEDN
                WHERE TRIM(EARNDEDN_CD) = TRIM(:code)
                """,
                {"code": code},
            )
            row = cursor.fetchone()
            if not row:
                return None

            ed_type = str(row[1]).strip().upper() if row[1] else ""
            return {
                "code": str(row[0]).strip(),
                "type": type_map.get(ed_type, "EARN"),
                "desc": str(row[2]).strip() if row[2] else "",
                "earndedn_type": ed_type,
            }
    except Exception:
        return None
    finally:
        conn.close()


def fetch_earndedn_list(*, ed_type=None):
    """List earn/dedn codes from MySQL master, falling back to Oracle."""
    items = list_earndedn_from_mysql(ed_type=ed_type)
    if items:
        return items
    if not oracle_reads_enabled():
        return []

    type_filter = str(ed_type or "").strip().upper()[:1]
    type_map = {"E": "EARN", "D": "DEDN"}

    sql = """
        SELECT EARNDEDN_CD, EARNDEDN_TYPE, EARNDEDN_DESC
        FROM FINANCE.FI_PN_MH_EARNDEDN
    """
    params = {}
    if type_filter:
        sql += " WHERE EARNDEDN_TYPE = :ed_type"
        params["ed_type"] = type_filter
    sql += " ORDER BY EARNDEDN_CD"

    conn = try_oracle_connection()
    if conn is None:
        return []
    try:
        with conn.cursor() as cursor:
            cursor.execute(sql, params or None)
            rows = cursor.fetchall()
    except Exception:
        return []
    finally:
        conn.close()

    result = []
    for row in rows:
        code = str(row[0]).strip() if row[0] else ""
        if not code:
            continue
        ora_type = str(row[1]).strip().upper() if row[1] else "E"
        result.append(
            {
                "code": code,
                "type": type_map.get(ora_type, "EARN"),
                "desc": str(row[2]).strip() if row[2] else "",
                "earndedn_type": ora_type,
            }
        )
    return result


class EarnDednListAPIView(APIView):
    """LOV for earn/dedn codes (Oracle F9 list). ?type=D deductions, ?type=E earnings."""

    def get(self, request):
        try:
            ed_type = request.GET.get("type")
            if ed_type:
                ed_type = str(ed_type).strip().upper()
                if ed_type in ("DEDN", "DEDUCTION"):
                    ed_type = "D"
                elif ed_type in ("EARN", "EARNING"):
                    ed_type = "E"
                else:
                    ed_type = ed_type[:1]
            items = fetch_earndedn_list(ed_type=ed_type or None)
            return Response({"count": len(items), "items": items})
        except Exception as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class EarnDednLookupAPIView(APIView):
    def get(self, request, code):
        try:
            data = fetch_earndedn_by_code(code)
            if not data:
                return Response(
                    {"error": "Earning/Deduction code not found"},
                    status=status.HTTP_404_NOT_FOUND,
                )
            return Response(data)
        except Exception as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class BankMasterAPIView(APIView):
    """List banks from local MySQL fi_pm_mh_bank (FI_PM_MH_BANK mirror)."""

    def get(self, request):
        search = request.GET.get("q") or request.GET.get("search")
        try:
            limit = int(request.GET.get("limit", 500))
        except (TypeError, ValueError):
            limit = 500
        limit = max(1, min(limit, 2000))

        try:
            banks = fetch_bank_master_list(search=search, limit=limit)
            return Response({"count": len(banks), "banks": banks})
        except Exception as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class BankLookupAPIView(APIView):
    """Single bank by BANK_CD."""

    def get(self, request, bank_cd):
        try:
            data = fetch_bank_by_code(bank_cd)
            if not data:
                return Response(
                    {"error": "Bank code not found"},
                    status=status.HTTP_404_NOT_FOUND,
                )
            return Response(data)
        except Exception as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class BankAbbrAPIView(APIView):
    """List bank abbreviations from local FI_PM_MH_BANKABBR."""

    def get(self, request):
        search = request.GET.get("q") or request.GET.get("search")
        try:
            limit = int(request.GET.get("limit", 500))
        except (TypeError, ValueError):
            limit = 500
        limit = max(1, min(limit, 2000))

        try:
            rows = fetch_bank_abbr_list(search=search, limit=limit)
            return Response({"count": len(rows), "banks": rows})
        except Exception as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class BankAbbrLookupAPIView(APIView):
    """Single bank abbreviation by BANK_TYPE."""

    def get(self, request, bank_type):
        try:
            data = fetch_bank_abbr_by_type(bank_type)
            if not data:
                return Response(
                    {"error": "Bank type not found"},
                    status=status.HTTP_404_NOT_FOUND,
                )
            return Response(data)
        except Exception as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
