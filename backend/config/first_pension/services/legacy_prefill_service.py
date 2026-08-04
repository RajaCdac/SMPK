"""
Prefill First Pension forms for legacy employees from Oracle mirrors / finance archive.

Same idea as commutation_defaults (FI_PN_MH_APPLICATION): when SMPK has no saved
row yet, show Oracle historical values so users can review and Save.
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal


def _clip(emp_cd) -> str:
    return str(emp_cd or "").strip()[:5]


def _fmt_date(value):
    if not value:
        return None
    if isinstance(value, datetime):
        return value.strftime("%Y-%m-%d")
    if isinstance(value, date):
        return value.strftime("%Y-%m-%d")
    text = str(value).strip()
    if len(text) >= 10 and text[4] == "-":
        return text[:10]
    # dd-mm-yyyy
    parts = text.split("-")
    if len(parts) == 3 and len(parts[0]) <= 2:
        return f"{parts[2]}-{parts[1]}-{parts[0]}"
    return text


def _num(value):
    if value is None:
        return None
    if isinstance(value, Decimal):
        return float(value)
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _ymd(y, m, d):
    if y is None and m is None and d is None:
        return None
    return f"{int(y or 0)}Y {int(m or 0)}M {int(d or 0)}D"


def _yn_bool(value):
    return str(value or "").strip().upper() in ("Y", "1", "YES", "T", "TRUE")


def _yn_yes_no(value):
    code = str(value or "").strip().upper()
    if code in ("Y", "YES", "1"):
        return "YES"
    if code in ("N", "NO", "0"):
        return "NO"
    return ""


def _bank_name(bank_cd):
    code = str(bank_cd or "").strip()
    if not code:
        return ""
    try:
        from master_data.models import FiPmMhBank

        branch = FiPmMhBank.objects.filter(bank_cd=code).first()
        if branch and branch.bank_desc:
            return branch.bank_desc.strip()
    except Exception:
        pass
    return ""


def _earndedn_desc(code):
    try:
        from master_data.services.earndedn_service import lookup_earndedn_by_code

        row = lookup_earndedn_by_code(code)
        if isinstance(row, dict):
            return row.get("earndedn_desc") or row.get("desc") or ""
        if row is not None:
            return getattr(row, "earndedn_desc", "") or ""
    except Exception:
        pass
    return ""


def load_no_pay_defaults(emp_cd):
    """Prefill No-Pay tab from FI_PN_MH_OLDBILL_PARAM (mirror, then finance archive)."""
    emp = _clip(emp_cd)
    row = None
    source = None

    try:
        from ..oracle_mirror import FiPnMhOldbillParam

        mirror = FiPnMhOldbillParam.objects.filter(emp_cd=emp).first()
        if mirror:
            row = {
                "no_pay_days": int(mirror.npay_prior_10mth or 0),
                "dies_non_days": int(mirror.dnon_days or 0),
                "no_pay_more_than_240_days": int(mirror.npay_morethan_240_dys or 0),
                "suspension_days": int(mirror.susp_days or 0),
                "boys_serv_days": int(mirror.boy_serv_days or 0),
            }
            source = "mirror"
    except Exception:
        pass

    if row is None:
        try:
            from .archive_service import get_no_pay

            archived = get_no_pay(emp)
            if archived:
                row = {
                    "no_pay_days": int(archived.get("no_pay_days") or 0),
                    "dies_non_days": int(archived.get("dies_non_days") or 0),
                    "no_pay_more_than_240_days": int(
                        archived.get("no_pay_more_than_240_days") or 0
                    ),
                    "suspension_days": int(archived.get("suspension_days") or 0),
                    "boys_serv_days": int(archived.get("boys_serv_days") or 0),
                }
                source = "finance_archive"
        except Exception:
            pass

    if not row:
        return None

    row["source"] = source
    row["legacy"] = True
    return row


def load_amount_defaults(emp_cd):
    """Prefill Amount tab from FI_PN_MH_PENSIONER (mirror, then finance archive)."""
    emp = _clip(emp_cd)

    try:
        from ..oracle_mirror import FiPnMhPensioner

        pen = (
            FiPnMhPensioner.objects.filter(emp_cd=emp)
            .order_by("-date_created")
            .first()
        )
        if pen:
            return {
                "legacy": True,
                "source": "mirror",
                "calculated": True,
                "inputs_ready": True,
                "ca_number": pen.ca_number,
                "original_pension_amount": _num(pen.original_pension_amt),
                "pension_amount": _num(pen.original_pension_amt),
                "payable_pension": _num(pen.payable_pension),
                "commutation_percent": _num(pen.commutation_per),
                "commuted_portion": _num(pen.commuted_portion),
                "commutation_amount": _num(pen.commuted_portion),
                "gratuity_amount": _num(pen.gratuity),
                "gratuity_emoluments": _num(pen.gratuity_emoluments),
                "pension_emoluments": _num(pen.pension_emoluments),
                "pension_basic": _num(pen.pension_emoluments),
                "emoluments_basic": _num(pen.pension_emoluments),
                "last_basic": _num(pen.pension_emoluments),
                "tccs": _ymd(pen.tccs_yr, pen.tccs_month, pen.tccs_days),
                "tqs": _ymd(pen.tqs_yr, pen.tqs_month, pen.tqs_days),
                "effective_stdt_pension": _fmt_date(pen.effective_stdt_pension),
                "date_commutation": _fmt_date(pen.date_commutation),
                "message": (
                    "Legacy amounts from Oracle pensioner master "
                    "(read-only until you recalculate in SMPK)."
                ),
            }
    except Exception:
        pass

    try:
        from .archive_service import get_amount

        archived = get_amount(emp)
        if archived:
            return {
                **archived,
                "legacy": True,
                "source": "finance_archive",
                "message": (
                    "Legacy amounts from finance archive "
                    "(read-only until you recalculate in SMPK)."
                ),
            }
    except Exception:
        pass

    return None


def _md_earning_rows(ca_number):
    """FI_PN_MD_PENSION_PROPOSAL lines → form earning_deductions."""
    ca = str(ca_number or "").strip()
    if not ca:
        return []

    rows = []
    try:
        from ..models import PensionProposalEarndedn

        qs = PensionProposalEarndedn.objects.filter(ca_number=ca).order_by(
            "earndedn_cd", "earn_dedn_type"
        )
        for line in qs:
            code = str(line.earndedn_cd or "").strip()
            rows.append(
                {
                    "type": str(line.earn_dedn_type or "E").strip().upper() or "E",
                    "code": code,
                    "desc": _earndedn_desc(code),
                    "amount": (
                        ""
                        if line.amount is None
                        else str(_num(line.amount) or 0)
                    ),
                    "deduction_priority": (
                        ""
                        if line.e_d_priority is None
                        else str(line.e_d_priority)
                    ),
                }
            )
    except Exception:
        rows = []

    if rows:
        return rows

    # Fallback: finance archive DB
    try:
        from django.db import connections

        with connections["default"].cursor() as cur:
            cur.execute(
                """
                SELECT EARNDEDN_CD, EARN_DEDN_TYPE, AMOUNT, E_D_PRIORITY
                FROM FI_PN_MD_PENSION_PROPOSAL
                WHERE CA_NUMBER = %s
                ORDER BY EARNDEDN_CD
                """,
                [ca],
            )
            for code, ed_type, amount, priority in cur.fetchall():
                code = str(code or "").strip()
                rows.append(
                    {
                        "type": str(ed_type or "E").strip().upper() or "E",
                        "code": code,
                        "desc": _earndedn_desc(code),
                        "amount": "" if amount is None else str(_num(amount) or 0),
                        "deduction_priority": (
                            "" if priority is None else str(priority)
                        ),
                    }
                )
    except Exception:
        pass

    return rows


def _map_mh_proposal_to_form(mirror, *, source="mirror"):
    """Map FiPnMhPensionProposal (+ MD lines) to proposal form payload."""
    bank_cd = str(mirror.bank_cd or "").strip()
    lic_bank_cd = str(mirror.lic_bank_cd or "").strip()
    ca = str(mirror.ca_number or "").strip()

    extra_flg = str(getattr(mirror, "extra_grat_tccs_flg", "") or "").strip().upper()
    held_flg = str(getattr(mirror, "held_grat_flg", "") or "").strip().upper()
    status = str(getattr(mirror, "employee_status", "") or "").strip().upper() or "P"

    compassionate_tag = getattr(mirror, "comp_allowance_check_tag", None)
    compassionate = (
        str(compassionate_tag)
        if compassionate_tag not in (None, "")
        else ""
    )

    data = {
        "legacy": True,
        "source": source,
        "id": None,
        "emp_cd": str(mirror.emp_cd or "").strip(),
        "employee_status": status if status in ("P", "F") else "P",
        "ca_number": ca,
        "pension_type": str(mirror.pension_type or "").strip().upper(),
        "pension_proposal_no": str(mirror.pension_proposal_no or "").strip(),
        "pension_proposal_date": _fmt_date(mirror.pension_proposal_dt),
        "eligible_double_family_pension": bool(
            getattr(mirror, "double_fpen_eligibility", 0) or 0
        ),
        "separation_type": str(mirror.separation_type or "").strip().upper(),
        "separation_date": _fmt_date(mirror.separation_dt),
        "implemented_month": getattr(mirror, "impl_month", None),
        "implemented_year": getattr(mirror, "impl_yr", None),
        "start_month": getattr(mirror, "start_month", None),
        "start_year": getattr(mirror, "start_yr", None),
        "pension_option": str(mirror.pension_option or "").strip().upper(),
        "option_given_by": str(getattr(mirror, "opt_given_by", "") or "").strip().upper(),
        "regn_no": str(getattr(mirror, "regn_no", "") or "").strip(),
        "regn_date": _fmt_date(getattr(mirror, "regn_date", None)),
        "pension_roll_no": str(getattr(mirror, "pension_roll_no", "") or "").strip(),
        "double_family_pension_upto_date": _fmt_date(
            getattr(mirror, "double_fpen_upto", None)
        ),
        "provisional_pension_pct": _num(getattr(mirror, "prov_pen_percentage", None)),
        "bank_cd": bank_cd,
        "bank_name": _bank_name(bank_cd),
        "account_no": str(getattr(mirror, "account_no", "") or "").strip(),
        "vigilance_clearance_ref_no": str(
            getattr(mirror, "vigilance_clearance_ref_no", "") or ""
        ).strip(),
        "vigilance_clearance_ref_dt": _fmt_date(
            getattr(mirror, "vigilance_clearance_ref_dt", None)
        ),
        "vigilance_cleared": _yn_bool(
            getattr(mirror, "vigilance_clearance_tag", None)
        ),
        "lic_bank_cd": lic_bank_cd,
        "lic_bank_name": _bank_name(lic_bank_cd),
        "vr_ref_no": str(getattr(mirror, "vr_ref_no", "") or "").strip(),
        "vr_ref_dt": _fmt_date(getattr(mirror, "vr_ref_dt", None)),
        "compassionate_allowance": compassionate,
        "compassionate_allowance_amt": _num(getattr(mirror, "comp_allowance", None)),
        "quarter_status": str(getattr(mirror, "quarter_status", "") or "").strip().upper(),
        "nominee_eform": str(
            getattr(mirror, "nomin_eform_grat_flg", "") or ""
        ).strip().upper(),
        "port_city_resident": _yn_yes_no(getattr(mirror, "port_city_resident", None)),
        "gratuity_option": (
            ""
            if getattr(mirror, "gratuity_option", None) is None
            else str(mirror.gratuity_option)
        ),
        "retirement_cpi": _num(getattr(mirror, "base_cpi", None)),
        "id_card_submitted": _yn_bool(getattr(mirror, "id_card_submitted", None)),
        "incentive_holder": _yn_yes_no(getattr(mirror, "incentive_holder_flg", None)),
        "held_up_flag": held_flg,
        "held_gratuity_amt": _num(getattr(mirror, "held_grat_amt", None)),
        "held_recovery_amt": _num(getattr(mirror, "held_commu_amt", None)),
        "held_recovery_date": None,
        "held_recovery_ref_no": "",
        "held_recovery_remarks": "",
        "extra_tccs_enabled": extra_flg == "Y",
        "extra_tccs_years": int(getattr(mirror, "extra_grat_tccs_yr", 0) or 0),
        "extra_tccs_months": int(getattr(mirror, "extra_grat_tccs_mon", 0) or 0),
        "extra_tccs_days": int(getattr(mirror, "extra_grat_tccs_days", 0) or 0),
        "earning_deductions": _md_earning_rows(ca),
    }
    return data


def enrich_proposal_defaults_from_legacy(emp_cd, defaults=None):
    """
    Full proposal form prefill from FI_PN_MH_PENSION_PROPOSAL + FI_PN_MD_PENSION_PROPOSAL.
    Merges on top of existing proposal_defaults (bank from fin, service tenure, etc.).
    """
    out = dict(defaults or {})
    emp = _clip(emp_cd)

    mirror = None
    try:
        from ..oracle_mirror import FiPnMhPensionProposal

        mirror = (
            FiPnMhPensionProposal.objects.filter(emp_cd=emp)
            .order_by("-pension_proposal_dt")
            .first()
        )
    except Exception:
        mirror = None

    if mirror:
        legacy = _map_mh_proposal_to_form(mirror, source="mirror")
        # Existing defaults win only when legacy field is empty.
        for key, value in legacy.items():
            if key in ("legacy", "source", "earning_deductions"):
                out[key] = value
                continue
            if value in (None, "", []) and out.get(key) not in (None, "", []):
                continue
            out[key] = value
        if not out.get("bank_name") and out.get("bank_cd"):
            out["bank_name"] = _bank_name(out["bank_cd"])
        if not out.get("lic_bank_name") and out.get("lic_bank_cd"):
            out["lic_bank_name"] = _bank_name(out["lic_bank_cd"])
        out["legacy"] = True
        out["source"] = "mirror"
        return out

    # Finance archive fallback (header only + MD via finance)
    try:
        from django.db import connections

        with connections["default"].cursor() as cur:
            cur.execute(
                "SELECT * FROM FI_PN_MH_PENSION_PROPOSAL WHERE EMP_CD = %s",
                [emp],
            )
            row = cur.fetchone()
            if not row:
                return out
            cols = [c[0] for c in cur.description]
            data = dict(zip(cols, row))

        class _Obj:
            pass

        obj = _Obj()
        mapping = {
            "ca_number": "CA_NUMBER",
            "emp_cd": "EMP_CD",
            "pension_type": "PENSION_TYPE",
            "pension_proposal_no": "PENSION_PROPOSAL_NO",
            "pension_proposal_dt": "PENSION_PROPOSAL_DT",
            "impl_month": "IMPL_MONTH",
            "impl_yr": "IMPL_YR",
            "start_month": "START_MONTH",
            "start_yr": "START_YR",
            "employee_status": "EMPLOYEE_STATUS",
            "vigilance_clearance_tag": "VIGILANCE_CLEARANCE_TAG",
            "vigilance_clearance_ref_no": "VIGILANCE_CLEARANCE_REF_NO",
            "vigilance_clearance_ref_dt": "VIGILANCE_CLEARANCE_REF_DT",
            "prov_pen_percentage": "PROV_PEN_PERCENTAGE",
            "quarter_status": "QUARTER_STATUS",
            "pension_option": "PENSION_OPTION",
            "pension_roll_no": "PENSION_ROLL_NO",
            "id_card_submitted": "ID_CARD_SUBMITTED",
            "port_city_resident": "PORT_CITY_RESIDENT",
            "separation_type": "SEPARATION_TYPE",
            "separation_dt": "SEPARATION_DT",
            "comp_allowance_check_tag": "COMP_ALLOWANCE_CHECK_TAG",
            "comp_allowance": "COMP_ALLOWANCE",
            "gratuity_option": "GRATUITY_OPTION",
            "bank_cd": "BANK_CD",
            "double_fpen_eligibility": "DOUBLE_FPEN_ELIGIBILITY",
            "double_fpen_upto": "DOUBLE_FPEN_UPTO",
            "base_cpi": "BASE_CPI",
            "extra_grat_tccs_flg": "EXTRA_GRAT_TCCS_FLG",
            "extra_grat_tccs_days": "EXTRA_GRAT_TCCS_DAYS",
            "extra_grat_tccs_mon": "EXTRA_GRAT_TCCS_MON",
            "extra_grat_tccs_yr": "EXTRA_GRAT_TCCS_YR",
            "incentive_holder_flg": "INCENTIVE_HOLDER_FLG",
            "held_grat_flg": "HELD_GRAT_FLG",
            "held_grat_amt": "HELD_GRAT_AMT",
            "lic_bank_cd": "LIC_BANK_CD",
            "regn_no": "REGN_NO",
            "regn_date": "REGN_DATE",
            "account_no": "ACCOUNT_NO",
            "opt_given_by": "OPT_GIVEN_BY",
            "nomin_eform_grat_flg": "NOMIN_EFORM_GRAT_FLG",
            "vr_ref_no": "VR_REF_NO",
            "vr_ref_dt": "VR_REF_DT",
            "held_commu_amt": "HELD_COMMU_AMT",
        }
        for attr, col in mapping.items():
            setattr(obj, attr, data.get(col))

        legacy = _map_mh_proposal_to_form(obj, source="finance_archive")
        for key, value in legacy.items():
            if key in ("legacy", "source", "earning_deductions"):
                out[key] = value
                continue
            if value in (None, "", []) and out.get(key) not in (None, "", []):
                continue
            out[key] = value
        out["legacy"] = True
        out["source"] = "finance_archive"
    except Exception:
        pass

    return out
