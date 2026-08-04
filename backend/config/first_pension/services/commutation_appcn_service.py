"""Commutation application number: Oracle when available, else local MySQL max+1."""

from django.db.models import Max

from employee.services.oracle_commutation_service import get_next_appcn_no
from first_pension.models import CommutationApplication


def get_next_appcn_no_local():
    """Next APPCN_NO from highest saved commutation in SMPK MySQL."""
    agg = CommutationApplication.objects.aggregate(max_no=Max("appcn_no"))
    max_no = agg.get("max_no") or 0
    try:
        return int(max_no) + 1
    except (TypeError, ValueError):
        return 1


def get_next_appcn_no_with_fallback():
    """
    Prefer Oracle FINANCE.FI_PN_MH_APPLICATION; on failure use local max+1.
    Returns (appcn_no: int, source: 'oracle' | 'local').
    """
    try:
        return int(get_next_appcn_no()), "oracle"
    except Exception:
        return get_next_appcn_no_local(), "local"


def resolve_appcn_no_for_create(data):
    """Use submitted number if present, otherwise allocate with fallback."""
    raw = data.get("appcn_no")
    if raw is not None and str(raw).strip() != "":
        return int(raw), "provided"
    return get_next_appcn_no_with_fallback()
