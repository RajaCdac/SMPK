from django.shortcuts import get_object_or_404
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from audit.services import log_audit
from employee.services.oracle_service import get_oracle_connection
from .models import PensionCase, PensionProposal


def _format_date_for_api(value):
    if not value:
        return ""
    if hasattr(value, "strftime"):
        return value.strftime("%Y-%m-%d")
    return str(value)


def _parse_optional_date(value):
    if value is None or value == "":
        return None
    return value


def _parse_bool(value):
    if isinstance(value, bool):
        return value
    return str(value).lower() in ("true", "1", "yes", "on")


def _parse_int(value, default=None):
    if value is None or value == "":
        return default
    return int(value)


def _parse_decimal(value):
    if value is None or value == "":
        return None
    return value


def serialize_pension_proposal(obj):
    return {
        "id": obj.id,
        "emp_cd": obj.emp_cd,
        "emp_name": obj.emp_name,
        "employee_status": obj.employee_status,
        "ca_number": obj.ca_number,
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
        "start_month": obj.start_month,
        "start_year": obj.start_year,
        "pension_roll_no": obj.pension_roll_no,
        "pension_proposal_date": _format_date_for_api(obj.pension_proposal_date),
        "double_family_pension_upto_date": _format_date_for_api(
            obj.double_family_pension_upto_date
        ),
        "provisional_pension_pct": obj.provisional_pension_pct,
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
        "compassionate_allowance_amt": obj.compassionate_allowance_amt,
        "port_city_resident": obj.port_city_resident,
        "gratuity_option": obj.gratuity_option,
        "retirement_cpi": obj.retirement_cpi,
        "id_card_submitted": obj.id_card_submitted,
        "vigilance_cleared": obj.vigilance_cleared,
        "incentive_holder": obj.incentive_holder,
        "held_up_flag": obj.held_up_flag,
        "held_gratuity_amt": obj.held_gratuity_amt,
        "extra_tccs_enabled": obj.extra_tccs_enabled,
        "extra_tccs_years": obj.extra_tccs_years,
        "extra_tccs_months": obj.extra_tccs_months,
        "extra_tccs_days": obj.extra_tccs_days,
        "earning_deductions": obj.earning_deductions or [],
    }


def _apply_date_defaults(defaults, ref_date):
    """Set separation / start / impl fields from a reference date."""
    if not ref_date:
        return
    if hasattr(ref_date, "strftime"):
        defaults["separation_date"] = ref_date.strftime("%Y-%m-%d")
        defaults["implemented_month"] = ref_date.month
        defaults["implemented_year"] = ref_date.year
        defaults["start_month"] = ref_date.month
        defaults["start_year"] = ref_date.year


def fetch_bank_details_from_oracle(cursor, emp_id):
    """
    Bank code, name, and account from Oracle.
    FI_XX_MH_EMP_FIN: BANK_CD, BANK_AC_NO
    FI_PM_MH_BANK: BANK_DESC (bank name)
    """
    bank = {
        "bank_cd": "",
        "bank_name": "",
        "account_no": "",
    }
    queries = [
        """
        SELECT e.EMP_CD, e.BANK_CD, b.BANK_DESC, e.BANK_AC_NO
        FROM FINANCE.FI_XX_MH_EMP_FIN e
        LEFT JOIN FINANCE.FI_PM_MH_BANK b ON e.BANK_CD = b.BANK_CD
        WHERE e.EMP_CD = :emp_id
        """,
        """
        SELECT e.EMP_CD, e.BANK_CD, b.BANK_DESC, e.BANK_AC_NO
        FROM FINANCE.FI_XX_MH_EMP_FIN e
        LEFT JOIN FINANCE.FI_PM_MH_BANK b ON e.BANK_CD = b.BANK_CD
        WHERE TRIM(e.EMP_CD) = TRIM(:emp_id)
        """,
    ]
    for query in queries:
        try:
            cursor.execute(query, {"emp_id": str(emp_id).strip()})
            row = cursor.fetchone()
            if row:
                bank["bank_cd"] = str(row[1]).strip() if row[1] is not None else ""
                bank["bank_name"] = str(row[2]).strip() if row[2] is not None else ""
                bank["account_no"] = str(row[3]).strip() if row[3] is not None else ""
                break
        except Exception:
            continue
    return bank


def merge_oracle_bank_into_proposal_data(proposal_data, proposal_defaults):
    """Fill empty bank fields on saved proposal from Oracle defaults."""
    if not proposal_data or not proposal_defaults:
        return proposal_data
    for key in ("bank_cd", "bank_name", "account_no"):
        if not proposal_data.get(key) and proposal_defaults.get(key):
            proposal_data[key] = proposal_defaults[key]
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
            ref_date = sep_dt or exp_ret
            _apply_date_defaults(defaults, ref_date)
            break
        except Exception:
            continue

    if pension_case and pension_case.retirement_date:
        if not defaults["separation_date"]:
            _apply_date_defaults(defaults, pension_case.retirement_date)

    defaults.update(fetch_bank_details_from_oracle(cursor, emp_id))

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
    obj.ca_number = data.get("ca_number", obj.ca_number)
    obj.pension_type = data.get("pension_type", obj.pension_type)
    obj.pension_proposal_no = data.get(
        "pension_proposal_no", obj.pension_proposal_no
    )
    obj.eligible_double_family_pension = _parse_bool(
        data.get("eligible_double_family_pension", obj.eligible_double_family_pension)
    )

    obj.separation_type = data.get("separation_type", obj.separation_type)
    obj.separation_date = _parse_optional_date(data.get("separation_date"))
    obj.implemented_year = _parse_int(data.get("implemented_year"), obj.implemented_year)
    obj.implemented_month = _parse_int(
        data.get("implemented_month"), obj.implemented_month
    )
    obj.service_tenure = data.get("service_tenure", obj.service_tenure)

    obj.pension_option = data.get("pension_option", obj.pension_option)
    obj.option_given_by = data.get("option_given_by", obj.option_given_by)
    obj.regn_no = data.get("regn_no", obj.regn_no)
    obj.regn_date = _parse_optional_date(data.get("regn_date"))
    obj.start_month = _parse_int(data.get("start_month"), obj.start_month)
    obj.start_year = _parse_int(data.get("start_year"), obj.start_year)
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
    obj.quarter_status = data.get("quarter_status", obj.quarter_status)
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
    obj.held_up_flag = data.get("held_up_flag", obj.held_up_flag)
    obj.held_gratuity_amt = _parse_decimal(data.get("held_gratuity_amt"))

    obj.extra_tccs_enabled = _parse_bool(
        data.get("extra_tccs_enabled", obj.extra_tccs_enabled)
    )
    obj.extra_tccs_years = _parse_int(data.get("extra_tccs_years"), 0)
    obj.extra_tccs_months = _parse_int(data.get("extra_tccs_months"), 0)
    obj.extra_tccs_days = _parse_int(data.get("extra_tccs_days"), 0)

    if "earning_deductions" in data:
        obj.earning_deductions = data.get("earning_deductions") or []

    if is_create:
        obj.created_by = user
    elif user and user.is_authenticated:
        obj.updated_by = user

    obj.save()


class PensionProposalLookupAPIView(APIView):
    def get(self, request, emp_code):
        proposal = get_pension_proposal_for_employee(emp_code)
        if proposal:
            proposal_data = serialize_pension_proposal(proposal)
            try:
                pension_case = PensionCase.objects.filter(
                    emp_code=str(emp_code).strip()
                ).first()
                defaults = load_proposal_defaults_from_oracle(
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
            proposal_defaults = load_proposal_defaults_from_oracle(
                emp_code, pension_case
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

            obj = PensionProposal(emp_cd=emp_cd)
            apply_pension_proposal_fields(
                obj, request.data, request.user, is_create=True
            )

            log_audit(
                request,
                table_name="PensionProposal",
                record_id=obj.id,
                action="CREATE",
                old_data=None,
                new_data=serialize_pension_proposal(obj),
                module="FIRST_PENSION",
            )

            return Response({
                "message": "Pension Proposal Saved Successfully",
                "id": obj.id,
                "proposal_data": serialize_pension_proposal(obj),
            })
        except Exception as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    def put(self, request, pk):
        try:
            obj = get_object_or_404(PensionProposal, pk=pk)
            old_data = serialize_pension_proposal(obj)
            apply_pension_proposal_fields(
                obj, request.data, request.user, is_create=False
            )
            new_data = serialize_pension_proposal(obj)

            log_audit(
                request,
                table_name="PensionProposal",
                record_id=obj.id,
                action="UPDATE",
                old_data=old_data,
                new_data=new_data,
                module="FIRST_PENSION",
            )

            return Response({
                "message": "Pension Proposal Updated Successfully",
                "id": obj.id,
                "proposal_data": new_data,
            })
        except Exception as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


def fetch_earndedn_from_oracle(earndedn_cd):
    """Lookup earning/deduction description from FINANCE.FI_PN_MH_EARNDEDN."""
    code = str(earndedn_cd).strip()
    if not code:
        return None

    type_map = {"E": "EARN", "D": "DEDN"}

    with get_oracle_connection().cursor() as cursor:
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


class EarnDednLookupAPIView(APIView):
    def get(self, request, code):
        try:
            data = fetch_earndedn_from_oracle(code)
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
