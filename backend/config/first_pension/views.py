from django.shortcuts import render
from datetime import date, datetime, timedelta

from dateutil.relativedelta import relativedelta
from employee.utils.age import calculate_age
from django.shortcuts import get_object_or_404
from rest_framework.views import APIView
from rest_framework.response import Response
from employee.services.oracle_service import (
    get_oracle_connection,
    oracle_reads_enabled,
)
from rest_framework import status
from employee.services.oracle_commutation_service import (
    upsert_fi_pn_mh_application_from_commutation,
)
from .services.commutation_appcn_service import (
    get_next_appcn_no_with_fallback,
    resolve_appcn_no_for_create,
)
from employee.services.oracle_no_pay_service import (
    upsert_fi_pn_mh_oldbill_param_from_pension_case,
)

from .models import PensionCase, PensionSummary, CommutationApplication
from .pension_calculation import resolve_service_tenure

from audit.services import log_audit
from .pension_proposal_api import (
    get_pension_proposal_for_employee,
    load_proposal_defaults,
    merge_oracle_bank_into_proposal_data,
    serialize_pension_proposal,
)
from .pension_calculation import (
    build_amount_lookup_payload,
    get_commutation_application_for_employee,
    round_gratuity_up_to_rupee,
    round_up_to_rupee,
)
from .services.commutation_defaults_service import load_commutation_defaults
from .process_intake_api import (
    process_intake_is_complete,
    serialize_process_intake,
)
from methodology2.services.oracle_employee_service import resolve_scale_display
from employee.services.emp_data_service import resolve_posting_designation_display
from employee.utils.display_format import normalize_department_name


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


def _apply_commutation_fields(obj, data, user, *, is_create=False):
    obj.application_time = data.get("application_time", obj.application_time)
    obj.comm_start_mnth = data.get("comm_start_mnth", obj.comm_start_mnth)
    obj.appcn_dt = _parse_optional_date(data.get("appcn_dt")) or obj.appcn_dt
    obj.application_rcvd_dt = _parse_optional_date(
        data.get("application_rcvd_dt") or data.get("appcn_dt")
    ) or obj.application_rcvd_dt
    obj.impl_fpen_combill = data.get("impl_fpen_combill", obj.impl_fpen_combill)
    obj.commutation_dt = _parse_optional_date(
        data.get("commutation_dt") or data.get("appcn_dt")
    ) or obj.commutation_dt
    if obj.commutation_dt:
        obj.restoration_dt = obj.commutation_dt + relativedelta(years=15)
    else:
        obj.restoration_dt = None
    obj.commutation_per = data.get("commutation_per", obj.commutation_per)
    obj.mo_certificate_dt = _parse_optional_date(data.get("mo_certificate_dt"))
    obj.mo_certificate_ref = data.get("mo_certificate_ref", obj.mo_certificate_ref)
    obj.commutation_reasons = data.get(
        "commutation_reasons", obj.commutation_reasons
    )
    if "bank_cd" in data:
        obj.bank_cd = str(data.get("bank_cd") or "").strip()[:6]
    if "bank_desc" in data:
        obj.bank_desc = str(data.get("bank_desc") or "").strip()[:50]
    elif "bank_description" in data:
        obj.bank_desc = str(data.get("bank_description") or "").strip()[:50]
    if "ref_no" in data:
        obj.ref_no = str(data.get("ref_no") or "").strip()[:100]
    if "bill_no" in data:
        obj.bill_no = str(data.get("bill_no") or "").strip()[:50]
    if is_create and not (obj.impl_fpen_combill or "").strip():
        from .pension_calculation import is_voluntary_retirement

        if is_voluntary_retirement(obj.emp_cd):
            obj.impl_fpen_combill = "COM"
    if "sanction_parameter" in data:
        obj.sanction_parameter = str(
            data.get("sanction_parameter") or ""
        ).strip()[:200]

    if obj.emp_cd:
        proposal = get_pension_proposal_for_employee(obj.emp_cd)
        if proposal and proposal.ca_number:
            obj.ca_no = str(proposal.ca_number).strip()[:50]

    if is_create:
        obj.created_by = user
    elif user and user.is_authenticated:
        obj.updated_by = user

    obj.save()


def serialize_no_pay_data(case):
    return {
        "id": case.id,
        "emp_code": case.emp_code,
        "no_pay_days": case.no_pay_days,
        "dies_non_days": case.dies_non_days,
        "no_pay_more_than_240_days": case.no_pay_more_than_240_days,
        "suspension_days": case.suspension_days,
        "boys_serv_days": case.boys_serv_days,
    }


def _get_pension_case_for_employee(emp_id):
    """Find row in first_pension_pensioncase by employee code."""
    emp_key = str(emp_id).strip()
    case = PensionCase.objects.filter(emp_code=emp_key).first()
    if case:
        return case
    if emp_key.isdigit():
        normalized = str(int(emp_key))
        case = PensionCase.objects.filter(emp_code=normalized).first()
        if case:
            return case
    return PensionCase.objects.filter(emp_code__iexact=emp_key).first()


def _parse_dd_mm_yyyy(value):
    if not value:
        return None
    return datetime.strptime(value, "%d-%m-%Y").date()


def serialize_commutation_application(app):
    """Return all commutation fields from DB for the frontend form."""
    return {
        "id": app.id,
        "emp_cd": app.emp_cd,
        "appcn_no": app.appcn_no,
        "application_time": app.application_time,
        "comm_start_mnth": app.comm_start_mnth,
        "appcn_dt": _format_date_for_api(app.appcn_dt),
        "application_rcvd_dt": _format_date_for_api(app.application_rcvd_dt),
        "impl_fpen_combill": app.impl_fpen_combill or "",
        "commutation_dt": _format_date_for_api(app.commutation_dt),
        "restoration_dt": _format_date_for_api(app.restoration_dt),
        "commutation_per": (
            float(app.commutation_per)
            if app.commutation_per is not None
            else None
        ),
        "mo_certificate_dt": _format_date_for_api(app.mo_certificate_dt),
        "mo_certificate_ref": app.mo_certificate_ref or "",
        "commutation_reasons": app.commutation_reasons or "",
        "bank_cd": app.bank_cd or "",
        "bank_desc": app.bank_desc or "",
        "bank_description": app.bank_desc or "",
        "ca_no": app.ca_no or "",
        "ca_number": app.ca_no or "",
        "ref_no": app.ref_no or "",
        "bill_no": app.bill_no or "",
        "sanction_parameter": app.sanction_parameter or "",
        "status": app.status,
    }


def _enrich_commutation_data_from_proposal(commutation_data, proposal):
    """Fill CA no. from pension proposal when commutation row has none yet."""
    if not commutation_data or not proposal:
        return commutation_data
    if not commutation_data.get("ca_no") and proposal.ca_number:
        commutation_data = {**commutation_data}
        commutation_data["ca_no"] = proposal.ca_number
        commutation_data["ca_number"] = proposal.ca_number
    return commutation_data


class PensionProcessView(APIView):

    def post(self, request):

        data = request.data

        # =========================
        # CREATE PENSION CASE
        # =========================

        obj = PensionCase.objects.create(

            emp_code=data.get("emp_code"),

            name=data.get("name"),

            emp_class=data.get("class"),

            #birth_date=data.get("birth_date"),
            birth_date=datetime.strptime(data.get("birth_date"),"%d-%m-%Y"),

            #joining_date=data.get("joining_date"),
            joining_date=datetime.strptime(data.get("joining_date"),"%d-%m-%Y"),

            #retirement_date=data.get("retirement_date"),
            retirement_date=datetime.strptime(data.get("retirement_date"),"%d-%m-%Y"),

            designation=data.get("designation"),

            scale=data.get("scale"),

            last_basic=data.get("last_basic"),

            no_pay_days=data.get("no_pay_days"),

            dies_non_days=data.get("dies_non_days"),

            commutation_percent=data.get(
                "commutation_percent"
            ),

            commutation_reason=data.get(
                "commutation_reason"
            ),

            created_by=request.user
        )

        # =========================
        # DATE CALCULATION
        # =========================

        join_date = datetime.strptime(
            data.get("joining_date"),
            "%d-%m-%Y"
        )
        
        ret_date = datetime.strptime(
            data.get("retirement_date"),
            "%d-%m-%Y"
        )
        
        effective_ret_date = ret_date - timedelta(days=1)
        service_life = calculate_age(join_date,ret_date)       
        print("Service Life: ", service_life)
        # =========================
        # TCCS / TQS (Oracle FFUNC_TQS_ROUND_2_Org)
        # =========================

        tenure = resolve_service_tenure(
            joining_date=join_date,
            service_end=ret_date,
            dies_non_days=int(data.get("dies_non_days", 0) or 0),
            suspension_days=int(data.get("suspension_days", 0) or 0),
            boys_serv_days=int(data.get("boys_serv_days", 0) or 0),
            no_pay_days=int(data.get("no_pay_days", 0) or 0),
            no_pay_more_than_240_days=int(
                data.get("no_pay_more_than_240_days", 0) or 0
            ),
        )

        years = tenure["total_service_years"]
        months = tenure["total_service_months"]
        days = tenure["total_service_days"]
        tccs_years = tenure["tccs_years"]
        tccs_months = tenure["tccs_months"]
        tccs_days = tenure["tccs_days"]
        tqs_years = tenure["tqs_years"]
        tqs_months = tenure["tqs_months"]
        tqs_days = tenure["tqs_days"]

        # =========================
        # FINANCIAL CALCULATION
        # =========================

        basic = float(
            data.get("last_basic")
        )

        # Pension
        pension_amount = (
            basic * 0.5
        )

        # Commutation (age-based rate from fi_pn_md_commrate_rupee)
        from .services.commutation_rate_service import (
            CommutationRateError,
            compute_commutation_amounts,
        )

        birth_date = None
        if data.get("birth_date"):
            birth_date = datetime.strptime(
                data.get("birth_date"),
                "%d-%m-%Y",
            ).date()
        comm_pct = float(data.get("commutation_percent", 40) or 40)
        try:
            comm_result = compute_commutation_amounts(
                pension_amount=pension_amount,
                commutation_percent=comm_pct,
                birth_date=birth_date,
                separation_dt=ret_date.date() if hasattr(ret_date, "date") else ret_date,
                use_highest_side_round=True,
            )
            commutation_amount = comm_result["lump_sum"]
        except CommutationRateError:
            commutation_amount = 0

        # DA
        # da = (
        #     basic * 0.1851
        # )
        emp_class = data.get("class")
        if emp_class in ["I", "II"]:
            da_percent = 54.32
        else:
            da_percent = 19.07
        da = ( basic * da_percent / 100)

        # Rounded TCCS
        qualifying_years = tccs_years

        if tccs_months >= 6 or (tccs_months == 6 and tccs_days > 0):
            qualifying_years += 1
        

        gratuity_amount = (
            ((basic + da)*15* qualifying_years)/ 26
        )
        # gratuity_amount_tqs = (
        #     ((basic + da)*15* qualifying_years)/ 26
        # )
        print("Gratuity Amount: ", gratuity_amount)

        if gratuity_amount > 2000000:
            gratuity_amount = 2000000
        gratuity_amount = round_gratuity_up_to_rupee(gratuity_amount)

        # =========================
        # SAVE SUMMARY
        # =========================

        PensionSummary.objects.create(

            pension_case=obj,

            total_service_years=years,
            total_service_months=months,
            total_service_days=days,

            tccs_years=tccs_years,
            tccs_months=tccs_months,
            tccs_days=tccs_days,

            tqs_years=tqs_years,
            tqs_months=tqs_months,
            tqs_days=tqs_days,

            pension_amount=pension_amount,

            commutation_amount=commutation_amount,

            gratuity_amount=gratuity_amount,

            pension_start_date=ret_date
        )

        log_audit(
            request,
            table_name="PensionCase",
            record_id=obj.id,
            action="CREATE",
            old_data=None,
            new_data={
                "emp_code": obj.emp_code,
                "name": obj.name,
                "status": obj.status,
            },
            module="FIRST_PENSION",
        )

        return Response({

            "message": "Saved Successfully",
            "case_id": obj.id,

            "pension_amount": float(pension_amount),

            "commutation_amount": float(commutation_amount),

            "gratuity_amount": float(gratuity_amount),
        })
# Create your views here.

class PensionReportView(APIView):

    def get(self, request, id):

        case = get_object_or_404(
            PensionCase,
            id=id
        )
        summary = case.summary
        join_date = case.joining_date

        ret_date = case.retirement_date

        birth_date = case.birth_date

        effective_ret_date = (
            ret_date - timedelta(days=1)
        )

        # Age on Appointment
        app_age = relativedelta(
            join_date,
            birth_date
        )

        age_on_appointment = (
            f"{app_age.years}Y "
            f"{app_age.months}M "
            f"{app_age.days}D"
        )

        # Age on Retirement
        ret_age = relativedelta(
            effective_ret_date,
            birth_date
        )

        age_on_retirement = (
            f"{ret_age.years}Y "
            f"{ret_age.months}M "
            f"{ret_age.days}D"
        )

        # =========================
        # DA CALCULATION
        # =========================

        if case.emp_class in ["I", "II"]:

            da_percent = 54.32

        else:

            da_percent = 19.07

        da_amount = round(
            float(case.last_basic)
            * da_percent / 100,
            2
        )

        data = {

            "case_no": case.id,

            "name": case.name,

            "joining_date": case.joining_date,

            "retirement_date": case.retirement_date,

            "birth_date": case.birth_date,

            "last_basic": float(case.last_basic),

            "no_pay_days": case.no_pay_days,

            "dies_non_days": case.dies_non_days,

            "pension_amount": float(summary.pension_amount),

            "commutation_amount": float(summary.commutation_amount),

            "gratuity_amount": float(summary.gratuity_amount),

            "total_service":
                f"{summary.total_service_years}Y "
                f"{summary.total_service_months}M "
                f"{summary.total_service_days}D",

            "tccs":
                f"{summary.tccs_years}Y "
                f"{summary.tccs_months}M "
                f"{summary.tccs_days}D",

            "tqs":
                f"{summary.tqs_years}Y "
                f"{summary.tqs_months}M "
                f"{summary.tqs_days}D",

            "da_amount": da_amount,

            "da_percent": da_percent,

            "age_on_appointment":
                age_on_appointment,

            "age_on_retirement":
                age_on_retirement,
        }

        return Response(data)
    
class PensionCaseListView(APIView):

    def get(self, request):

        cases = PensionCase.objects.all().order_by("emp_code")

        data = []

        for case in cases:

            data.append({

                "id": case.id,
                "emp_code": case.emp_code,
                "name": case.name,
                "designation": case.designation,
                "retirement_date": case.retirement_date,
                "status": case.status,
                "last_basic": float(case.last_basic),
            })

        return Response(data)
    
def _build_employee_db_context(emp_id, *, include_oracle_intake=False):
    from .services.legacy_prefill_service import (
        enrich_proposal_defaults_from_legacy,
        load_amount_defaults,
    )

    existing_commutation = get_commutation_application_for_employee(emp_id)
    existing_no_pay = _get_pension_case_for_employee(emp_id)
    process_intake_completed = process_intake_is_complete(emp_id)
    existing_proposal = get_pension_proposal_for_employee(emp_id)
    existing_amount_summary = None
    if existing_no_pay:
        existing_amount_summary = PensionSummary.objects.filter(
            pension_case_id=existing_no_pay.id
        ).first()

    proposal_data = (
        serialize_pension_proposal(existing_proposal)
        if existing_proposal
        else None
    )

    commutation_data = (
        serialize_commutation_application(existing_commutation)
        if existing_commutation
        else None
    )
    commutation_data = _enrich_commutation_data_from_proposal(
        commutation_data, existing_proposal
    )

    commutation_defaults = (
        None
        if existing_commutation
        else load_commutation_defaults(emp_id)
    )

    no_pay_data = (
        serialize_no_pay_data(existing_no_pay) if existing_no_pay else None
    )
    # Do not prefill no-pay from Oracle oldbill / mirror — user enters blank
    # fields in SMPK when no local values exist (or uses stored SMPK values as-is).

    amount_data = None
    if existing_no_pay:
        try:
            amount_data = build_amount_lookup_payload(emp_id).get("amount_data")
        except Exception:
            amount_data = None

    amount_defaults = None
    if not existing_amount_summary or not (amount_data and amount_data.get("calculated")):
        try:
            amount_defaults = load_amount_defaults(emp_id)
        except Exception:
            amount_defaults = None

    return {
        "commutation_exists": bool(existing_commutation),
        "commutation_data": commutation_data,
        "commutation_defaults": commutation_defaults,
        "no_pay_exists": bool(existing_no_pay),
        "no_pay_data": no_pay_data,
        # Never auto-fill no-pay form from legacy/Oracle.
        "no_pay_defaults": None,
        "process_intake_completed": process_intake_completed,
        "process_intake_data": (
            serialize_process_intake(case=existing_no_pay, emp_code=emp_id)
            if include_oracle_intake
            else serialize_process_intake(case=existing_no_pay)
        ),
        "proposal_exists": bool(existing_proposal),
        "proposal_data": proposal_data,
        "proposal_defaults": enrich_proposal_defaults_from_legacy(emp_id, None),
        "amount_exists": bool(existing_amount_summary),
        "amount_data": amount_data,
        "amount_defaults": amount_defaults,
        "_existing_no_pay": existing_no_pay,
        "_existing_proposal": existing_proposal,
    }


def _employee_search_from_mirror(emp_key, db_context, existing_no_pay):
    from employee.services.employee_mirror_service import load_employee_from_mirror

    mirrored = load_employee_from_mirror(emp_key)
    if not mirrored:
        return None

    merged = {**mirrored, **db_context}
    proposal_data = db_context.get("proposal_data")
    if proposal_data:
        merged["proposal_data"] = proposal_data
    try:
        proposal_defaults = load_proposal_defaults(emp_key, existing_no_pay)
        from .services.legacy_prefill_service import (
            enrich_proposal_defaults_from_legacy,
        )

        proposal_defaults = enrich_proposal_defaults_from_legacy(
            emp_key, proposal_defaults
        )
        merged["proposal_defaults"] = proposal_defaults
        if proposal_data:
            merged["proposal_data"] = merge_oracle_bank_into_proposal_data(
                proposal_data, proposal_defaults
            )
    except Exception:
        merged["proposal_defaults"] = db_context.get("proposal_defaults") or {}
    merged["data_source"] = "mirror"
    merged["cache_message"] = (
        "Showing employee data from MySQL mirror (Oracle reads disabled)."
    )
    return merged


class EmployeeSearchAPIView(APIView):

    def get(self, request, emp_id):
        emp_key = str(emp_id).strip()
        db_context = _build_employee_db_context(
            emp_key, include_oracle_intake=True
        )
        existing_no_pay = db_context.pop("_existing_no_pay")
        existing_proposal = db_context.pop("_existing_proposal")

        if not oracle_reads_enabled():
            mirrored = _employee_search_from_mirror(
                emp_key, db_context, existing_no_pay
            )
            if mirrored:
                return Response(mirrored)
            return Response(
                {
                    "error": "Employee not found in MySQL mirror",
                    "partial": True,
                    "emp_id": emp_key,
                    **db_context,
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        try:
            with get_oracle_connection().cursor() as cursor:
                query = """
                    SELECT t1.EMP_CD,TRIM( t1.TITLE || ' ' || t1.FIRST_NAME || ' ' || NVL(t1.MIDDLE_NAME, '') || ' ' || t1.LAST_NAME ) AS full_name,
                    t2.JOIN_DT,t2.EXP_RET_DT,t1.BIRTH_DT,t7.DEPT_DESC,t3.DESIG_DESC,t6.ALLOC_DESC,
                    t4.SCALE_SL,t5.BASIC_AMT,t5.CLASS
                    FROM FINANCE.FI_XX_MH_EMP_PER t1
                    LEFT JOIN FINANCE.FI_XX_MH_EMP_ADM t2 ON t1.EMP_CD = t2.EMP_CD
                    LEFT JOIN FINANCE.FI_XX_MH_DESIG t3 ON t2.DESIG_CD = t3.DESIG_CD
                    LEFT JOIN FINANCE.FI_XX_MH_EMP_DATA t6 ON t1.EMP_CD = t6.EMP_CD
                    LEFT JOIN FINANCE.FI_XX_MH_DEPT t7 ON t6.DEPT_CD = t7.DEPT_CD
                    LEFT JOIN FINANCE.FI_XX_MH_EMP_FIN t4 ON t1.EMP_CD = t4.EMP_CD
                    LEFT JOIN FINANCE.FI_XX_MH_EMP_FIN_vw t5 ON t4.EMP_CD = t5.EMP_CD
                    WHERE TO_CHAR(t1.EMP_CD) = :emp_id
                """
                cursor.execute(query, {"emp_id": emp_key})
                row = cursor.fetchone()

                if not row:
                    return Response(
                        {
                            "error": "Employee not found in Oracle",
                            "partial": True,
                            "emp_id": emp_key,
                            **db_context,
                        },
                        status=status.HTTP_404_NOT_FOUND,
                    )

                proposal_defaults = {}
                try:
                    proposal_defaults = load_proposal_defaults(
                        emp_key, existing_no_pay
                    )
                except Exception:
                    proposal_defaults = {}
                try:
                    from .services.legacy_prefill_service import (
                        enrich_proposal_defaults_from_legacy,
                    )

                    proposal_defaults = enrich_proposal_defaults_from_legacy(
                        emp_key, proposal_defaults
                    )
                except Exception:
                    pass

                proposal_data = db_context.get("proposal_data")
                if proposal_data:
                    proposal_data = merge_oracle_bank_into_proposal_data(
                        proposal_data, proposal_defaults
                    )

                employee_data = {
                    "emp_id": row[0],
                    "name": row[1],
                    "join_date": row[2].strftime("%d-%m-%Y") if row[2] else None,
                    "expected_retirement_date": row[3].strftime("%d-%m-%Y") if row[3] else None,
                    "birth_date": row[4].strftime("%d-%m-%Y") if row[4] else None,
                    "department": normalize_department_name(row[5]),
                    "designation": resolve_posting_designation_display(
                        dept_desc=row[5],
                        desig_desc=row[6],
                        alloc_desc=row[7],
                    ),
                    "posting_alloc_desc": str(row[7]).strip() if row[7] else "",
                    "posting_dept_desc": str(row[5]).strip() if row[5] else "",
                    "posting_desig_desc": str(row[6]).strip() if row[6] else "",
                    "scale": resolve_scale_display(row[8], row[3], cursor=cursor),
                    "scale_code": str(row[8]).strip() if row[8] else "",
                    "basic_amount": float(row[9]) if row[9] is not None else None,
                    "class": row[10],
                    "age_on_appointment": calculate_age(row[4], row[2]) if row[4] and row[2] else None,
                    "age_on_retirement": calculate_age(row[4], row[3]) if row[4] and row[3] else None,
                    "partial": False,
                    **db_context,
                    "proposal_data": proposal_data,
                    "proposal_defaults": proposal_defaults,
                }
                from first_pension.services.oracle_cache_service import (
                    sync_employee_search_to_cache,
                )

                sync_employee_search_to_cache(emp_key, employee_data)
                employee_data["data_source"] = "oracle"
                return Response(employee_data)

        except Exception as e:
            from employee.services.employee_mirror_service import (
                load_employee_from_mirror,
            )
            from first_pension.services.oracle_cache_service import (
                load_employee_from_cache,
                merge_cached_employee_with_db,
            )

            cached = load_employee_from_cache(emp_key)
            if cached:
                merged = merge_cached_employee_with_db(
                    cached,
                    db_context,
                    merge_proposal_bank=merge_oracle_bank_into_proposal_data,
                )
                merged["cache_message"] = (
                    "Oracle is unavailable; showing employee data last synced from Oracle."
                )
                return Response(merged)

            mirrored = load_employee_from_mirror(emp_key)
            if mirrored:
                merged = {**mirrored, **db_context}
                proposal_data = db_context.get("proposal_data")
                if proposal_data:
                    merged["proposal_data"] = proposal_data
                try:
                    merged["proposal_defaults"] = load_proposal_defaults(
                        emp_key, existing_no_pay
                    )
                except Exception:
                    merged["proposal_defaults"] = {}
                merged["cache_message"] = (
                    "Oracle is unavailable; showing employee data from MySQL mirror."
                )
                return Response(merged)

            return Response(
                {
                    "error": str(e),
                    "partial": True,
                    "emp_id": emp_key,
                    **db_context,
                },
                status=status.HTTP_200_OK,
            )

class NoPayLookupAPIView(APIView):
    """Load no-pay / dies-non from first_pension_pensioncase for one employee."""

    def get(self, request, emp_code):
        case = _get_pension_case_for_employee(emp_code)
        if not case:
            return Response({"exists": False, "no_pay_data": None})

        return Response({
            "exists": True,
            "no_pay_data": serialize_no_pay_data(case),
        })


class NoPayLeaveDetailsAPIView(APIView):
    """No-pay (NPL) leave details for one employee from smpk_pension MySQL."""

    def get(self, request, emp_code):
        from employee.services.oracle_leave_service import (
            get_no_pay_leave_details,
        )

        try:
            data = get_no_pay_leave_details(emp_code)
        except Exception as exc:
            return Response(
                {"error": f"Could not read leave details from smpk_pension: {exc}"},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        return Response(data)


class NoPayEntryAPIView(APIView):

    def post(self, request):
        try:
            emp_code = request.data.get("emp_code")
            if PensionCase.objects.filter(emp_code=emp_code).exists():
                return Response(
                    {
                        "error": (
                            "No-pay entry already exists for this employee. "
                            "Use Edit to update."
                        )
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            data = request.data
            obj = PensionCase.objects.create(
                emp_code=emp_code,
                name=data.get("name"),
                emp_class=data.get("class"),
                birth_date=_parse_dd_mm_yyyy(data.get("birth_date")),
                joining_date=_parse_dd_mm_yyyy(data.get("joining_date")),
                retirement_date=_parse_dd_mm_yyyy(data.get("retirement_date")),
                designation=data.get("designation"),
                scale=data.get("scale"),
                last_basic=data.get("last_basic"),
                no_pay_days=int(data.get("no_pay_days") or 0),
                dies_non_days=int(data.get("dies_non_days") or 0),
                no_pay_more_than_240_days=int(
                    data.get("no_pay_more_than_240_days") or 0
                ),
                suspension_days=int(data.get("suspension_days") or 0),
                boys_serv_days=int(data.get("boys_serv_days") or 0),
                created_by=request.user,
            )

            # ORACLE WRITE DISABLED — MySQL-only mode. Uncomment to sync no-pay to Oracle.
            # try:
            #     upsert_fi_pn_mh_oldbill_param_from_pension_case(obj)
            # except Exception as oracle_err:
            #     return Response(
            #         {
            #             "error": (
            #                 "Could not update Oracle (FI_PN_MH_OLDBILL_PARAM): "
            #                 f"{oracle_err}"
            #             )
            #         },
            #         status=status.HTTP_502_BAD_GATEWAY,
            #     )

            log_audit(
                request,
                table_name="PensionCase",
                record_id=obj.id,
                action="CREATE",
                old_data=None,
                new_data=serialize_no_pay_data(obj),
                module="FIRST_PENSION",
            )

            return Response({
                "message": "No-Pay Entry Saved Successfully",
                "id": obj.id,
                "no_pay_data": serialize_no_pay_data(obj),
            })

        except Exception as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    def put(self, request, pk):
        try:
            obj = get_object_or_404(PensionCase, pk=pk)
            old_data = serialize_no_pay_data(obj)

            obj.no_pay_days = int(request.data.get("no_pay_days") or 0)
            obj.dies_non_days = int(request.data.get("dies_non_days") or 0)
            obj.no_pay_more_than_240_days = int(
                request.data.get("no_pay_more_than_240_days") or 0
            )
            obj.suspension_days = int(request.data.get("suspension_days") or 0)
            obj.boys_serv_days = int(request.data.get("boys_serv_days") or 0)
            if request.user.is_authenticated:
                obj.updated_by = request.user
            obj.save()

            # ORACLE WRITE DISABLED — MySQL-only mode. Uncomment to sync no-pay to Oracle.
            # try:
            #     upsert_fi_pn_mh_oldbill_param_from_pension_case(obj)
            # except Exception as oracle_err:
            #     return Response(
            #         {
            #             "error": (
            #                 "Could not update Oracle (FI_PN_MH_OLDBILL_PARAM): "
            #                 f"{oracle_err}"
            #             )
            #         },
            #         status=status.HTTP_502_BAD_GATEWAY,
            #     )

            new_data = serialize_no_pay_data(obj)

            log_audit(
                request,
                table_name="PensionCase",
                record_id=obj.id,
                action="UPDATE",
                old_data=old_data,
                new_data=new_data,
                module="FIRST_PENSION",
            )

            return Response({
                "message": "No-Pay Entry Updated Successfully",
                "id": obj.id,
                "no_pay_data": new_data,
            })

        except Exception as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


def _sync_commutation_to_oracle(obj, user):
    user_code = (getattr(user, "username", None) or "SYS")[:5]
    upsert_fi_pn_mh_application_from_commutation(
        emp_cd=obj.emp_cd,
        appcn_no=obj.appcn_no,
        appcn_dt=obj.appcn_dt,
        application_time=obj.application_time,
        comm_start_mnth=obj.comm_start_mnth,
        commutation_per=obj.commutation_per,
        commutation_reasons=obj.commutation_reasons,
        impl_fpen_combill=obj.impl_fpen_combill,
        impl_bill_no=obj.bill_no,
        ref_no=obj.ref_no,
        application_rcvd_dt=obj.application_rcvd_dt,
        commutation_dt=obj.commutation_dt,
        restoration_dt=obj.restoration_dt,
        mo_certificate_dt=obj.mo_certificate_dt,
        mo_certificate_ref=obj.mo_certificate_ref,
        user_code=user_code,
    )


class CommutationCreateAPIView(APIView):
    def get(self, request):
        next_appcn_no, source = get_next_appcn_no_with_fallback()
        return Response({
            "appcn_no": str(next_appcn_no),
            "appcn_source": source,
        })

    def post(self, request):
        try:
            emp_cd = request.data.get("emp_cd")
            if CommutationApplication.objects.filter(emp_cd=emp_cd).exists():
                return Response(
                    {
                        "error": (
                            "Commutation application already exists for this "
                            "employee. Use Edit to update."
                        )
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            appcn_no, _source = resolve_appcn_no_for_create(request.data)

            obj = CommutationApplication(
                emp_cd=emp_cd,
                appcn_no=appcn_no,
            )
            _apply_commutation_fields(
                obj, request.data, request.user, is_create=True
            )

            # ORACLE WRITE DISABLED — MySQL-only mode. Uncomment to sync commutation to Oracle.
            # oracle_synced = True
            # oracle_error = None
            # try:
            #     _sync_commutation_to_oracle(obj, request.user)
            # except Exception as e:
            #     oracle_synced = False
            #     oracle_error = str(e)
            #     if getattr(settings, "ORACLE_SYNC_REQUIRED", False):
            #         return Response(
            #             {
            #                 "error": (
            #                     "Could not update Oracle (FI_PN_MH_APPLICATION): "
            #                     f"{oracle_error}"
            #                 ),
            #                 "id": obj.id,
            #                 "application_no": obj.appcn_no,
            #             },
            #             status=status.HTTP_502_BAD_GATEWAY,
            #         )

            log_audit(
                request,
                table_name="CommutationApplication",
                record_id=obj.id,
                action="CREATE",
                old_data=None,
                new_data=serialize_commutation_application(obj),
                module="FIRST_PENSION",
            )

            return Response({
                "message": "Commutation Application Saved Successfully",
                "application_no": obj.appcn_no,
                "id": obj.id,
                "commutation_data": serialize_commutation_application(obj),
            })

        except Exception as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    def put(self, request, pk):
        try:
            obj = get_object_or_404(CommutationApplication, pk=pk)
            old_data = serialize_commutation_application(obj)
            _apply_commutation_fields(
                obj, request.data, request.user, is_create=False
            )
            new_data = serialize_commutation_application(obj)

            # ORACLE WRITE DISABLED — MySQL-only mode. Uncomment to sync commutation to Oracle.
            # oracle_synced = True
            # oracle_error = None
            # try:
            #     _sync_commutation_to_oracle(obj, request.user)
            # except Exception as e:
            #     oracle_synced = False
            #     oracle_error = str(e)
            #     if getattr(settings, "ORACLE_SYNC_REQUIRED", False):
            #         return Response(
            #             {
            #                 "error": (
            #                     "Could not update Oracle (FI_PN_MH_APPLICATION): "
            #                     f"{oracle_error}"
            #                 ),
            #                 "commutation_data": new_data,
            #             },
            #             status=status.HTTP_502_BAD_GATEWAY,
            #         )

            log_audit(
                request,
                table_name="CommutationApplication",
                record_id=obj.id,
                action="UPDATE",
                old_data=old_data,
                new_data=new_data,
                module="FIRST_PENSION",
            )

            return Response({
                "message": "Commutation Application Updated Successfully",
                "application_no": obj.appcn_no,
                "id": obj.id,
                "commutation_data": new_data,
            })

        except Exception as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    

