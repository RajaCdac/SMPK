from django.db import migrations, models


def backfill_ca_from_proposal(apps, schema_editor):
    PensionProposal = apps.get_model("first_pension", "PensionProposal")
    PensionProposalEarndedn = apps.get_model(
        "first_pension", "PensionProposalEarndedn"
    )

    for line in PensionProposalEarndedn.objects.select_related("proposal").iterator():
        if str(line.ca_number or "").strip():
            continue
        proposal = getattr(line, "proposal", None)
        if not proposal:
            continue
        ca = str(proposal.ca_number or "").strip()[:22]
        if ca:
            line.ca_number = ca
            line.save(update_fields=["ca_number"])


def remove_lines_without_ca(apps, schema_editor):
    PensionProposalEarndedn = apps.get_model(
        "first_pension", "PensionProposalEarndedn"
    )
    PensionProposalEarndedn.objects.filter(ca_number="").delete()


class Migration(migrations.Migration):

    dependencies = [
        ("first_pension", "0010_migrate_earndedn_json_to_lines"),
    ]

    operations = [
        migrations.RunPython(backfill_ca_from_proposal, migrations.RunPython.noop),
        migrations.RemoveConstraint(
            model_name="pensionproposalearndedn",
            name="uniq_proposal_earndedn_cd",
        ),
        migrations.RemoveField(
            model_name="pensionproposalearndedn",
            name="proposal",
        ),
        migrations.RunPython(remove_lines_without_ca, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="pensionproposalearndedn",
            name="ca_number",
            field=models.CharField(db_index=True, max_length=22),
        ),
        migrations.AddConstraint(
            model_name="pensionproposalearndedn",
            constraint=models.UniqueConstraint(
                fields=("ca_number", "earndedn_cd"),
                name="uniq_ca_earndedn_cd",
            ),
        ),
    ]
