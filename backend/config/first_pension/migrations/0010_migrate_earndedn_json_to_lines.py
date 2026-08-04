from decimal import Decimal, InvalidOperation

from django.db import migrations


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


def migrate_json_to_lines(apps, schema_editor):
    PensionProposal = apps.get_model("first_pension", "PensionProposal")
    PensionProposalEarndedn = apps.get_model(
        "first_pension", "PensionProposalEarndedn"
    )

    for proposal in PensionProposal.objects.all().iterator():
        if PensionProposalEarndedn.objects.filter(proposal_id=proposal.id).exists():
            continue
        rows = proposal.earning_deductions or []
        if not rows:
            continue
        for index, row in enumerate(rows):
            if not isinstance(row, dict):
                continue
            code = str(row.get("code") or "").strip()[:3]
            if not code:
                continue
            row_type = str(row.get("type") or "E").strip().upper()
            earn_dedn_type = "D" if row_type.startswith("D") else "E"
            PensionProposalEarndedn.objects.create(
                proposal_id=proposal.id,
                ca_number=str(proposal.ca_number or "").strip()[:22],
                earndedn_cd=code,
                earn_dedn_type=earn_dedn_type,
                amount=_parse_decimal(row.get("amount")),
                e_d_priority=_parse_priority(row.get("deduction_priority")),
                deducted_amt=None,
                line_order=index,
                created_by="MIG",
                modified_by="MIG",
            )


class Migration(migrations.Migration):

    dependencies = [
        ("first_pension", "0009_earndedn_tables"),
    ]

    operations = [
        migrations.RunPython(migrate_json_to_lines, migrations.RunPython.noop),
    ]
