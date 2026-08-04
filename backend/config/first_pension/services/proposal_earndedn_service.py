from decimal import Decimal, InvalidOperation

from django.utils import timezone

from master_data.services.earndedn_service import lookup_earndedn_by_code

from ..models import PensionProposalEarndedn


def _user_code(user):
    if not user or not getattr(user, "is_authenticated", False):
        return "SYS"
    return str(getattr(user, "username", None) or "SYS").strip()[:5].upper() or "SYS"


def _ca_number(proposal):
    return str(proposal.ca_number or "").strip()[:22]


def _normalize_row_type(value):
    text = str(value or "").strip().upper()
    if text.startswith("D"):
        return PensionProposalEarndedn.DEDN
    return PensionProposalEarndedn.EARN


def _parse_decimal(value):
    if value in (None, ""):
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return None


def _parse_priority(value):
    if value in (None, ""):
        return None
    try:
        parsed = int(value)
        return parsed if parsed > 0 else None
    except (TypeError, ValueError):
        return None


def _lines_for_ca(ca_number):
    return PensionProposalEarndedn.objects.filter(ca_number=ca_number).order_by(
        "earndedn_cd", "earn_dedn_type"
    )


def _rows_from_lines(lines):
    rows = []
    for line in lines:
        master = lookup_earndedn_by_code(line.earndedn_cd)
        ui_type = "D" if line.earn_dedn_type == PensionProposalEarndedn.DEDN else "E"
        rows.append(
            {
                "type": ui_type,
                "code": line.earndedn_cd,
                "desc": master.earndedn_desc if master else "",
                "amount": float(line.amount) if line.amount is not None else "",
                "deduction_priority": (
                    str(line.e_d_priority) if line.e_d_priority is not None else ""
                ),
            }
        )
    return rows


def proposal_earndedn_to_api_rows(proposal):
    ca_number = _ca_number(proposal)
    if ca_number:
        lines = _lines_for_ca(ca_number)
        if lines.exists():
            return _rows_from_lines(lines)
    return _legacy_json_rows(proposal)


def _legacy_json_rows(proposal):
    rows = []
    for row in proposal.earning_deductions or []:
        if not isinstance(row, dict):
            continue
        code = str(row.get("code") or "").strip()
        if not code:
            continue
        rows.append(dict(row))
    return rows


def save_proposal_earndedn_rows(proposal, rows, user):
    """Replace earn/dedn lines for proposal CA number (FI_PN_MD_PENSION_PROPOSAL key)."""
    today = timezone.localdate()
    user_code = _user_code(user)
    ca_number = _ca_number(proposal)

    if not ca_number:
        proposal.earning_deductions = _legacy_json_rows(proposal) or list(rows or [])
        proposal.save(update_fields=["earning_deductions"])
        return []

    PensionProposalEarndedn.objects.filter(ca_number=ca_number).delete()

    saved = []
    for index, row in enumerate(rows or []):
        if not isinstance(row, dict):
            continue
        code = str(row.get("code") or "").strip()
        if not code:
            continue

        master = lookup_earndedn_by_code(code)
        earn_dedn_type = _normalize_row_type(
            row.get("type") or (master.earndedn_type if master else "E")
        )

        line = PensionProposalEarndedn.objects.create(
            ca_number=ca_number,
            earndedn_cd=code[:3],
            earn_dedn_type=earn_dedn_type,
            amount=_parse_decimal(row.get("amount")),
            e_d_priority=_parse_priority(row.get("deduction_priority")),
            deducted_amt=None,
            date_created=today,
            created_by=user_code,
            date_modified=today,
            modified_by=user_code,
        )
        saved.append(line)

    proposal.earning_deductions = proposal_earndedn_to_api_rows(proposal)
    proposal.save(update_fields=["earning_deductions"])
    return saved
