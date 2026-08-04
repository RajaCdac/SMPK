from datetime import date, datetime

from .models import PensionProposal

HELD_FLAGS_REQUIRING_AMT = frozenset({"P", "C", "R", "S"})


def _normalize_withhold_reason(value):
    code = str(value or "").strip().upper()
    if code == "1":
        return "O"
    if code == "2":
        return "Q"
    return code


def _normalize_held_up_flag(value):
    code = str(value or "").strip().upper()
    if code == "GP":
        return "H"
    return code


def _parse_date(value):
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


def _yyyy_mm(d):
    if not d:
        return None
    return d.year * 100 + d.month


def _is_blank(value):
    return value is None or str(value).strip() == ""


def _is_positive_number(value):
    if _is_blank(value):
        return False
    try:
        return float(value) > 0
    except (TypeError, ValueError):
        return False


def validate_pension_proposal_data(data, *, instance=None):
    """
    Validate pension proposal payload (Oracle FI_PN_MH_PENSION_PROPOSAL_E rules).
    Returns list of error strings; empty list means valid.
    """
    errors = []

    separation_date = _parse_date(data.get("separation_date"))
    if instance and not separation_date:
        separation_date = instance.separation_date

    separation_type = data.get("separation_type")
    if instance and _is_blank(separation_type):
        separation_type = instance.separation_type

    if not separation_date:
        errors.append(
            "Separation date is not available. Update employee master first."
        )
    if _is_blank(separation_type):
        errors.append(
            "Separation type is not available. Update employee master first."
        )

    ca_number = str(data.get("ca_number") or "").strip()
    if not ca_number:
        errors.append(
            "CA No. is required (links earning/deduction grid to "
            "fi_pn_md_pension_proposal)."
        )
    else:
        dup_qs = PensionProposal.objects.filter(ca_number=ca_number)
        if instance:
            dup_qs = dup_qs.exclude(pk=instance.pk)
        if dup_qs.exists():
            errors.append("CA No. already exists for another employee.")

    pension_type = str(data.get("pension_type") or "").strip().upper()
    if not pension_type:
        errors.append("Pension Type is required.")

    start_month = data.get("start_month")
    start_year = data.get("start_year")
    if instance:
        if start_month in (None, ""):
            start_month = instance.start_month
        if start_year in (None, ""):
            start_year = instance.start_year
    try:
        start_month = int(start_month) if start_month not in (None, "") else None
        start_year = int(start_year) if start_year not in (None, "") else None
    except (TypeError, ValueError):
        start_month = start_year = None

    sep_ym = _yyyy_mm(separation_date)
    if sep_ym and start_month and start_year:
        start_ym = start_year * 100 + start_month
        if start_ym < sep_ym:
            errors.append(
                "Start month and year cannot be less than Separation Date."
            )

    vigilance_dt = _parse_date(data.get("vigilance_clearance_ref_dt"))
    double_upto = _parse_date(data.get("double_family_pension_upto_date"))

    if pension_type == "N" and vigilance_dt and separation_date:
        if vigilance_dt > separation_date:
            errors.append(
                "Vigilance clearance date cannot be after Separation Date "
                "for Normal Pension."
            )

    if double_upto and separation_date and double_upto < separation_date:
        errors.append(
            "Double Family Pension upto date must not be before Separation Date."
        )

    if pension_type == "P":
        prov = data.get("provisional_pension_pct")
        if instance and prov in (None, ""):
            prov = instance.provisional_pension_pct
        if _is_blank(prov):
            errors.append("Please enter Provisional Pension percentage.")
        else:
            try:
                pct = float(prov)
                if pct < 0 or pct > 100:
                    errors.append(
                        "Provisional Pension % must be between 0 and 100."
                    )
            except (TypeError, ValueError):
                errors.append("Provisional Pension % must be a number.")

    # Compassionate fields are readonly on first entry; validate only on update.
    if pension_type == "C" and instance is not None:
        comp_tag = data.get("compassionate_allowance")
        comp_amt = data.get("compassionate_allowance_amt")
        if _is_blank(comp_tag):
            comp_tag = instance.compassionate_allowance
        if comp_amt in (None, ""):
            comp_amt = instance.compassionate_allowance_amt
        if _is_blank(comp_tag):
            errors.append(
                "Compassionate Allowance option is required for this pension type."
            )
        if not _is_positive_number(comp_amt):
            errors.append(
                "Compassionate Allowance amount is required for this pension type."
            )

    held_flag = _normalize_held_up_flag(data.get("held_up_flag"))
    held_amt = data.get("held_gratuity_amt")
    if instance and not held_flag:
        held_flag = _normalize_held_up_flag(instance.held_up_flag)
    if instance and held_amt in (None, ""):
        held_amt = instance.held_gratuity_amt
    if held_flag in HELD_FLAGS_REQUIRING_AMT and not _is_positive_number(held_amt):
        errors.append("Held amount is required for the selected Held Up flag.")

    recovery_amt = data.get("held_recovery_amt")
    recovery_date = data.get("held_recovery_date")
    recovery_ref = data.get("held_recovery_ref_no")
    recovery_remarks = data.get("held_recovery_remarks")
    if instance:
        if recovery_amt in (None, ""):
            recovery_amt = instance.held_recovery_amt
        if not recovery_date:
            recovery_date = instance.held_recovery_date
        if _is_blank(recovery_ref):
            recovery_ref = instance.held_recovery_ref_no
        if _is_blank(recovery_remarks):
            recovery_remarks = instance.held_recovery_remarks

    has_recovery = any(
        not _is_blank(v) for v in (recovery_amt, recovery_date, recovery_ref, recovery_remarks)
    )
    if has_recovery:
        if not _is_positive_number(recovery_amt):
            errors.append("Amount recovered is required when recording a recovery.")
        if not _parse_date(recovery_date):
            errors.append("Recovery date is required when recording a recovery.")

    impl_month = data.get("implemented_month")
    if not _is_blank(impl_month):
        try:
            m = int(impl_month)
            if m < 1 or m > 12:
                errors.append("Implementation month must be between 1 and 12.")
        except (TypeError, ValueError):
            errors.append("Implementation month must be between 1 and 12.")

    rows = data.get("earning_deductions")
    if rows is None and instance:
        rows = instance.earning_deductions or []
    rows = rows or []
    codes_seen = set()
    for index, row in enumerate(rows):
        if not isinstance(row, dict):
            continue
        code = str(row.get("code") or "").strip()
        if not code:
            continue
        if code in codes_seen:
            errors.append(
                f"Duplicate earning/deduction code {code} in row {index + 1}."
            )
        codes_seen.add(code)

        ed_type = str(row.get("type") or "E").strip().upper()
        if ed_type.startswith("D") and not _is_positive_number(row.get("amount")):
            errors.append(
                f"Amount is required for deduction code {code} (row {index + 1})."
            )

    return errors


def normalize_pension_proposal_payload(data):
    """Normalize earning/deduction rows before save."""
    payload = dict(data)

    if "held_up_flag" in payload:
        payload["held_up_flag"] = _normalize_held_up_flag(payload.get("held_up_flag"))
    if "quarter_status" in payload:
        payload["quarter_status"] = _normalize_withhold_reason(
            payload.get("quarter_status")
        )

    rows = payload.get("earning_deductions")
    if rows is not None:
        normalized = []
        for row in rows:
            if not isinstance(row, dict):
                continue
            item = dict(row)
            ed_type = str(item.get("type") or "E").strip().upper()
            if not ed_type.startswith("D"):
                item["deduction_priority"] = ""
            normalized.append(item)
        payload["earning_deductions"] = normalized

    return payload
