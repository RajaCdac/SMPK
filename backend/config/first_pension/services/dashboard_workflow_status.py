"""Batch workflow progress for dashboard retirement list (MySQL)."""

from first_pension.models import (
    CommutationApplication,
    PensionCase,
    PensionProposal,
    PensionSummary,
)

WORKFLOW_LABELS = {
    "not_started": "Not started",
    "in_progress": "In progress",
    "amount_done": "Amount calculated",
}


def _code_variants(emp_code):
    key = str(emp_code).strip()
    if not key:
        return []
    variants = [key]
    if key.isdigit():
        variants.append(str(int(key)))
    return variants


def _intake_complete(case):
    return bool(
        case
        and (case.separation_type or "").strip()
        and case.separation_date
    )


def _amount_complete(summary):
    if not summary:
        return False
    try:
        return summary.pension_amount is not None and summary.pension_amount > 0
    except TypeError:
        return False


def batch_workflow_status(emp_codes):
    """
    Returns dict emp_code -> workflow fields for dashboard rows.
    Steps mirror First Pension tabs: intake, commutation, no-pay, proposal, amount.
    """
    codes = set()
    for raw in emp_codes:
        codes.update(_code_variants(raw))

    if not codes:
        return {}

    cases = list(PensionCase.objects.filter(emp_code__in=codes))
    case_by_code = {}
    case_ids = []
    for case in cases:
        case_by_code[case.emp_code] = case
        case_ids.append(case.id)

    proposal_codes = set(
        PensionProposal.objects.filter(emp_cd__in=codes).values_list("emp_cd", flat=True)
    )
    commutation_codes = set(
        CommutationApplication.objects.filter(emp_cd__in=codes).values_list(
            "emp_cd", flat=True
        )
    )

    summary_by_case_id = {
        s.pension_case_id: s
        for s in PensionSummary.objects.filter(pension_case_id__in=case_ids)
    }

    result = {}
    for raw in emp_codes:
        key = str(raw).strip()
        if not key:
            continue

        case = None
        for variant in _code_variants(key):
            case = case_by_code.get(variant)
            if case:
                break

        summary = summary_by_case_id.get(case.id) if case else None

        steps = {
            "intake": _intake_complete(case),
            "commutation": any(v in commutation_codes for v in _code_variants(key)),
            "no_pay": case is not None,
            "proposal": any(v in proposal_codes for v in _code_variants(key)),
            "amount": _amount_complete(summary),
        }

        if steps["amount"]:
            status = "amount_done"
        elif any(steps.values()):
            status = "in_progress"
        else:
            status = "not_started"

        completed_count = sum(1 for v in steps.values() if v)

        result[key] = {
            "workflow_status": status,
            "workflow_label": WORKFLOW_LABELS[status],
            "workflow_steps": steps,
            "workflow_step_count": completed_count,
            "workflow_step_total": len(steps),
        }

    return result


def enrich_retirement_list(retirement_list):
    """Attach workflow fields to each retirement row; return list + summary counts."""
    if not retirement_list:
        return [], _empty_workflow_summary()

    codes = [r.get("emp_code") for r in retirement_list]
    status_map = batch_workflow_status(codes)

    enriched = []
    summary = _empty_workflow_summary()

    for row in retirement_list:
        code = str(row.get("emp_code", "")).strip()
        wf = status_map.get(code)
        if not wf and code.isdigit():
            wf = status_map.get(str(int(code)))
        if not wf:
            wf = {
                "workflow_status": "not_started",
                "workflow_label": WORKFLOW_LABELS["not_started"],
                "workflow_steps": {
                    "intake": False,
                    "commutation": False,
                    "no_pay": False,
                    "proposal": False,
                    "amount": False,
                },
                "workflow_step_count": 0,
                "workflow_step_total": 5,
            }

        merged = {**row, **wf}
        enriched.append(merged)

        status = wf["workflow_status"]
        if status == "amount_done":
            summary["calculated"] += 1
        elif status == "in_progress":
            summary["in_progress"] += 1
        else:
            summary["not_started"] += 1

        steps = wf["workflow_steps"]
        if steps.get("intake"):
            summary["intake_done"] += 1
        if steps.get("commutation"):
            summary["commutation_done"] += 1
        if steps.get("no_pay"):
            summary["no_pay_done"] += 1
        if steps.get("proposal"):
            summary["proposal_done"] += 1
        if steps.get("amount"):
            summary["amount_step_done"] += 1

    summary["total"] = len(enriched)
    return enriched, summary


def _empty_workflow_summary():
    return {
        "total": 0,
        "not_started": 0,
        "in_progress": 0,
        "calculated": 0,
        "intake_done": 0,
        "commutation_done": 0,
        "no_pay_done": 0,
        "proposal_done": 0,
        "amount_step_done": 0,
    }
