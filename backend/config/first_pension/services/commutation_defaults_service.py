"""Defaults for commutation entry from pension case / Oracle mirror."""

from ..oracle_mirror import FiPnMhApplication
from ..pension_calculation import get_separation_type_for_employee, is_voluntary_retirement


def _format_date(value):
    if not value:
        return ""
    if hasattr(value, "strftime"):
        return value.strftime("%Y-%m-%d")
    return str(value)


def load_commutation_defaults(emp_cd):
    """
    Prefill commutation form when no SMPK CommutationApplication exists yet.
    Oracle FI_PN_MH_APPLICATION (wave-2 mirror) is the reference for legacy cases.
    """
    emp_key = str(emp_cd).strip()[:5]
    is_vr = is_voluntary_retirement(emp_key)
    separation_type = get_separation_type_for_employee(emp_key)

    defaults = {
        "is_voluntary_retirement": is_vr,
        "separation_type": separation_type,
        "impl_fpen_combill": "COM" if is_vr else "",
    }

    app = (
        FiPnMhApplication.objects.filter(emp_cd=emp_key)
        .order_by("-appcn_dt", "-appcn_no")
        .first()
    )
    if not app:
        return defaults

    impl = (app.impl_fpen_combill or "").strip().upper()
    defaults.update(
        {
            "appcn_no": app.appcn_no or "",
            "application_time": app.application_time,
            "comm_start_mnth": app.comm_start_mnth,
            "appcn_dt": _format_date(app.appcn_dt),
            "application_rcvd_dt": _format_date(app.application_rcvd_dt),
            "impl_fpen_combill": impl or defaults["impl_fpen_combill"],
            "bill_no": (app.impl_bill_no or "").strip(),
            "ref_no": (app.ref_no or "").strip(),
            "commutation_dt": _format_date(app.commutation_date),
            "commutation_per": (
                float(app.commutation_per)
                if app.commutation_per is not None
                else None
            ),
            "mo_certificate_ref": (app.mo_certificate_ref or "").strip(),
            "mo_certificate_dt": _format_date(app.mo_certification_dt),
            "commutation_reasons": (app.commutation_reasons or "").strip(),
            "sanction_parameter": (app.sanction_particulars or "").strip(),
            "bank_cd": (app.bank_cd or "").strip(),
            "ca_no": (app.ca_no or "").strip(),
        }
    )
    return defaults
