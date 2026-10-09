"""
Recommendation & Sanction of Pension report (FI_PN_MH_PENSION_PROPOSAL_BMP).
"""

from django.utils import timezone

from employee.oracle_mirror import FiXxMhEmpPer
from employee.services.dept_wise_service import resolve_dept_wise_department
from employee.services.emp_data_service import resolve_employee_designation_name
from employee.services.oracle_service import get_oracle_connection
from employee.utils.age import calculate_age
from master_data.services.earndedn_service import lookup_earndedn_by_code

from ..models import PensionCase, PensionProposal, PensionProposalEarndedn, PensionSummary
from ..oracle_mirror import FiPnMhPensionProposal, FiPnMhPensioner
from ..pension_calculation import reload_pension_case_from_db
from .proposal_earndedn_service import proposal_earndedn_to_api_rows


class ProposalSanctionReportError(Exception):
    pass


# Oracle CF_GRAT_HELD_STRFORMULA reason suffixes (FI_PN_MH_PENSION_PROPOSAL).
_HELD_REASON_TEXT = {
    "QUARTER": "held up for Quater Clearence",
    "ID_CARD": "held up for non submission of ID-Card",
    "ELEC": "held up for Electricity Clearence",
    "QTR_ELEC": "held up for Quter  & Elec Clearence",
    "COURT": "held up for Court Attachement",
    "QTR_ELEC_CRT": "held up for Quter Elec Crt Charges",
    "QTR_CRT": "held up for Qtr clear & Crt Attachemnt",
    "ELEC_CRT": "held up for Elec  & Crt Attachement",
    "CREDIT_SOC": "held up for Co-Operative Credit Society",
}


def _clip(value, max_len, default=""):
    if value is None:
        return default
    text = str(value).strip()
    if not text:
        return default
    return text[:max_len]


def _money_float(value) -> float:
    if value is None or value == "":
        return 0.0
    try:
        return round(float(value), 2)
    except (TypeError, ValueError):
        return 0.0


def _normalize_held_grat_flg(raw) -> str:
    """
    Map proposal held_up_flag / HELD_GRAT_FLG to Oracle report codes.
    Entry form: G=full, H=partial; report formula: F=full, P=partial, N=none.
    """
    text = str(raw or "").strip().upper()
    if not text:
        return "N"
    if text == "GP":
        return "P"
    code = text[0]
    if code == "G":
        return "F"
    if code == "H":
        return "P"
    if code in ("F", "P", "N"):
        return code
    # C / R / P (pension) / S — amount comes from HELD_GRAT_AMT
    return code


def _proposal_held_fields(proposal, emp_cd, ca_number):
    """Read quarter / id-card / held flag+amt from SMPK proposal or Oracle mirror."""
    qtr = ""
    id_card = ""
    flg = "N"
    amt = 0.0

    if proposal is not None:
        qtr = str(
            _proposal_value(proposal, "quarter_status") or ""
        ).strip().upper()[:1]
        if isinstance(proposal, PensionProposal):
            id_card = "Y" if proposal.id_card_submitted else "N"
            flg = _normalize_held_grat_flg(proposal.held_up_flag)
            amt = _money_float(proposal.held_gratuity_amt)
        else:
            raw_id = str(
                getattr(proposal, "id_card_submitted", "") or ""
            ).strip().upper()
            if raw_id in ("Y", "1", "TRUE"):
                id_card = "Y"
            elif raw_id in ("N", "0", "FALSE"):
                id_card = "N"
            flg = _normalize_held_grat_flg(
                getattr(proposal, "held_grat_flg", None)
                or getattr(proposal, "held_up_flag", None)
            )
            amt = _money_float(
                getattr(proposal, "held_grat_amt", None)
                or getattr(proposal, "held_gratuity_amt", None)
            )

    # Fill gaps from mirror / SMPK row by CA / emp
    if not qtr or not id_card or flg == "N":
        emp_key = _clip(emp_cd, 5)
        ca_key = _clip(ca_number, 50) if ca_number else ""
        mirror = None
        if ca_key:
            mirror = FiPnMhPensionProposal.objects.filter(ca_number=ca_key).first()
        if not mirror and emp_key:
            mirror = (
                FiPnMhPensionProposal.objects.filter(emp_cd=emp_key)
                .order_by("-pension_proposal_dt")
                .first()
            )
        if mirror:
            if not qtr:
                qtr = str(mirror.quarter_status or "").strip().upper()[:1]
            if not id_card:
                tag = str(mirror.id_card_submitted or "").strip().upper()
                id_card = "Y" if tag in ("Y", "1", "TRUE") else "N"
            if flg == "N" and mirror.held_grat_flg:
                flg = _normalize_held_grat_flg(mirror.held_grat_flg)
            if amt <= 0 and mirror.held_grat_amt is not None:
                amt = _money_float(mirror.held_grat_amt)

        smpk = None
        if isinstance(proposal, PensionProposal):
            smpk = proposal
        else:
            qs = PensionProposal.objects.filter(emp_cd=emp_key)
            smpk = qs.filter(ca_number=ca_key).first() if ca_key else None
            if not smpk:
                smpk = qs.first()
        if smpk:
            if not qtr:
                qtr = str(smpk.quarter_status or "").strip().upper()[:1]
            if not id_card:
                id_card = "Y" if smpk.id_card_submitted else "N"
            if flg == "N" and smpk.held_up_flag:
                flg = _normalize_held_grat_flg(smpk.held_up_flag)
            if amt <= 0 and smpk.held_gratuity_amt is not None:
                amt = _money_float(smpk.held_gratuity_amt)

    if not id_card:
        id_card = "Y" if _is_id_card_submitted(proposal, emp_cd, ca_number) else "N"

    return qtr, id_card, flg, amt


def _held_gratuity_reason_code(qtr: str, id_card: str) -> str:
    """
    Hold reason for sanction note.

    Prefer form "Reasons to Withhold" (quarter_status).
    Use ID-Card text only when ID card is NOT submitted.
    (Legacy Oracle extract used id_card='Y' → ID-Card, which printed the
    wrong sentence when ID was already submitted.)
    """
    qtr = (qtr or "").strip().upper()[:1]
    id_card = (id_card or "").strip().upper()[:1]

    withhold_map = {
        "V": "QUARTER",
        "O": "ELEC",
        "Q": "QTR_ELEC",
        "C": "COURT",
        "A": "COURT",  # UI list uses A for Court Attachment
        "S": "QTR_ELEC_CRT",
        "T": "QTR_CRT",
        "U": "ELEC_CRT",
        "M": "CREDIT_SOC",
    }
    if qtr in withhold_map:
        return withhold_map[qtr]

    if id_card != "Y":
        return "ID_CARD"
    return ""


def _resolve_held_gratuity_amount(
    flg: str, held_amt: float, gratuity_amt: float, qtr: str, id_card: str
) -> float:
    """
    Amount resolution:
      F/G → full gratuity; H/P and other active flags → HELD_GRAT_AMT; N → 0
    """
    flg = (flg or "N").strip().upper()[:1] or "N"
    held = _money_float(held_amt)
    full = _money_float(gratuity_amt)

    if flg == "F":
        return full
    if flg == "N" or not flg:
        return 0.0
    # H/P (partial) and C/R/S → entered held amount
    return held


def _held_gratuity_sanction_note(
    proposal, *, emp_cd, ca_number, gratuity_amt=None
) -> str | None:
    """
    Sanction held-up line (Oracle CF_GRAT_HELD_STRFORMULA shape):
      *) Rs. {amt} as payment of gratuity amount is to be {reason}
    """
    qtr, id_card, flg, held_amt = _proposal_held_fields(
        proposal, emp_cd, ca_number
    )
    grat = _money_float(gratuity_amt)
    amt = _resolve_held_gratuity_amount(flg, held_amt, grat, qtr, id_card)
    reason = _held_gratuity_reason_code(qtr, id_card)

    active = flg not in ("N", "")
    if not active and amt <= 0:
        if id_card != "Y":
            reason = "ID_CARD"
            amt = 0.0
        else:
            return None

    amt_text = _format_amount_int(amt)

    if not reason:
        if id_card != "Y":
            reason = "ID_CARD"
        elif active and amt > 0:
            # Held flag + amount, but no withhold reason and ID is OK.
            return (
                f"*) Rs. {amt_text} as payment of gratuity amount is to be held up."
            )
        else:
            return None

    reason_text = _HELD_REASON_TEXT.get(
        reason, "held up for non submission of ID-Card"
    )
    return (
        f"*) Rs. {amt_text} as payment of gratuity amount is to be {reason_text}"
    )


def _format_dd_mm_yy(value):
    if not value:
        return ""
    if hasattr(value, "strftime"):
        return value.strftime("%d/%m/%y")
    return str(value)[:10]


def _format_run_date(value=None):
    dt = value or timezone.localdate()
    if hasattr(dt, "strftime"):
        return dt.strftime("%d/%m/%Y")
    return str(dt)


def _format_amount_int(value):
    if value is None:
        return ""
    return str(int(round(float(value))))


def _format_service_phrase(years, months, days, *, compact=False):
    y = int(years or 0)
    m = int(months or 0)
    d = int(days or 0)
    if compact:
        return f"{y}years {m}months {d}days"
    return f"{y} years {m} months {d} days"


def _format_age_compact(age):
    if not age:
        return ""
    y = int(age.get("years", 0))
    m = int(age.get("months", 0))
    d = int(age.get("days", 0))
    parts = [f"{y}years"]
    if m:
        parts.append(f"{m}months")
    if d:
        parts.append(f"{d}days")
    return "".join(parts)


def _pension_scheme_label(option):
    opt = (option or "G").strip().upper()
    if opt.startswith("P"):
        return "Port line"
    return "Government Line"


def _pension_scheme_phrase(option):
    opt = (option or "G").strip().upper()
    if opt.startswith("P"):
        return "Port line"
    return "Govt. line"


def _separation_reason_label(separation_type):
    code = (separation_type or "").strip().upper()
    mapping = {
        "RT": "Superannuation age",
        "SP": "Superannuation",
        "VR": "Voluntary retirement",
        "DE": "Death",
        "RE": "Resignation",
    }
    return mapping.get(code, "Superannuation age")


def _clean_report_name(name):
    text = " ".join(str(name or "").split()).upper()
    for prefix in ("MRS.", "MR.", "MS.", "MISS.", "SHRI.", "SMT."):
        if text.startswith(prefix + " "):
            return text[len(prefix) :].strip()
    return text


def _employee_pronoun(emp_cd):
    per = FiXxMhEmpPer.objects.filter(emp_cd=_clip(emp_cd, 5)).first()
    if per:
        title = (per.title or "").strip().upper().rstrip(".")
        if title in ("MRS", "MS", "MISS", "SMT", "KUMARI"):
            return "She"
        if title in ("MR", "SHRI", "SRI"):
            return "He"
    return "He"


def _employee_name(emp_cd, case=None, proposal=None, pensioner=None):
    if case and case.name:
        return _clean_report_name(case.name)
    if proposal and proposal.emp_name:
        return _clean_report_name(proposal.emp_name)
    if pensioner and pensioner.name:
        return _clean_report_name(pensioner.name)
    per = FiXxMhEmpPer.objects.filter(emp_cd=_clip(emp_cd, 5)).first()
    if per:
        parts = [per.first_name, per.middle_name, per.last_name]
        return _clean_report_name(
            " ".join(p for p in parts if p and str(p).strip())
        )
    return ""


def _department_name(emp_cd):
    emp_key = _clip(emp_cd, 5)
    from employee.oracle_mirror import FiXxMhEmpData
    from master_data.models import FiXxMhDept

    row = FiXxMhEmpData.objects.filter(emp_cd=emp_key).first()
    if row and row.dept_desc:
        text = str(row.dept_desc).strip().upper()
        if text.startswith("ADMIN/SECY"):
            return "SECRETARY"
        return text
    if row and row.dept_cd:
        dept = FiXxMhDept.objects.filter(dept_cd=row.dept_cd).first()
        if dept and dept.dept_desc:
            text = str(dept.dept_desc).strip().upper()
            if text.startswith("ADMIN/SECY"):
                return "SECRETARY"
            return text

    try:
        conn = get_oracle_connection()
        cur = conn.cursor()
        cur.execute(
            """
            SELECT d.DEPT_DESC
            FROM FINANCE.FI_XX_MH_EMP_DATA e
            LEFT JOIN FINANCE.FI_XX_MH_DEPT d ON e.DEPT_CD = d.DEPT_CD
            WHERE e.EMP_CD = :emp_cd
            """,
            {"emp_cd": _clip(emp_cd, 5)},
        )
        row = cur.fetchone()
        cur.close()
        conn.close()
        if row and row[0]:
            text = str(row[0]).strip().upper()
            if text.startswith("ADMIN/SECY"):
                return "SECRETARY"
            return text
    except Exception:
        pass
    return ""


def _format_case_no(ca_number):
    text = _clip(ca_number, 22)
    if not text:
        return ""
    upper = text.upper()
    if "C/A" in upper:
        return upper.replace(" C/A", "C/A").replace(" ", "")
    return f"{text}C/A"


def _format_roll_no(proposal, pensioner):
    roll = ""
    if proposal and proposal.pension_roll_no:
        roll = str(proposal.pension_roll_no).strip()
    elif pensioner and pensioner.pension_roll_no:
        roll = str(pensioner.pension_roll_no).strip()
    if not roll:
        return ""
    upper = roll.upper()
    if not upper.startswith("LIC"):
        roll = f"LIC-{roll}"
    return roll.upper()


def _is_id_card_submitted(active_proposal, emp_cd, ca_number=None):
    """ID card flag from SMPK proposal, Oracle mirror header, or default not submitted."""
    if isinstance(active_proposal, PensionProposal):
        return bool(active_proposal.id_card_submitted)

    if active_proposal is not None and hasattr(active_proposal, "id_card_submitted"):
        tag = str(active_proposal.id_card_submitted or "").strip().upper()
        if tag in ("Y", "1", "TRUE"):
            return True
        if tag in ("N", "0", "FALSE"):
            return False

    emp_key = _clip(emp_cd, 5)
    qs = PensionProposal.objects.filter(emp_cd=emp_key)
    ca_key = _clip(ca_number, 50) if ca_number else ""
    proposal = qs.filter(ca_number=ca_key).first() if ca_key else None
    if not proposal:
        proposal = qs.first()
    if proposal is not None:
        return bool(proposal.id_card_submitted)
    return False


def _proposal_earning_deduction_rows(active_proposal, ca_number):
    if isinstance(active_proposal, PensionProposal):
        return proposal_earndedn_to_api_rows(active_proposal)

    ca_key = _clip(ca_number, 22)
    if not ca_key:
        return []

    lines = PensionProposalEarndedn.objects.filter(ca_number=ca_key).order_by(
        "earndedn_cd", "earn_dedn_type"
    )
    if not lines.exists():
        return []

    rows = []
    for line in lines:
        master = lookup_earndedn_by_code(line.earndedn_cd)
        rows.append(
            {
                "type": "D" if line.earn_dedn_type == PensionProposalEarndedn.DEDN else "E",
                "code": line.earndedn_cd,
                "desc": (master.earndedn_desc if master else "").strip(),
                "amount": float(line.amount) if line.amount is not None else "",
            }
        )
    return rows


def _deduction_gl_as_of_date(active_proposal, emp_cd=None):
    """Prefer proposal pension start month for fin-year in GL (ALOC2)."""
    from datetime import date as date_cls

    if active_proposal is not None:
        sm = getattr(active_proposal, "start_month", None)
        sy = getattr(active_proposal, "start_year", None)
        if sm and sy:
            try:
                return date_cls(int(sy), int(sm), 1)
            except (TypeError, ValueError):
                pass
        sep = getattr(active_proposal, "separation_date", None)
        if sep:
            if hasattr(sep, "date") and callable(sep.date):
                try:
                    return sep.date()
                except Exception:
                    pass
            return sep
    if emp_cd:
        case = reload_pension_case_from_db(emp_cd)
        if case and case.retirement_date:
            return case.retirement_date
    return timezone.localdate()


def _deduction_credit_gl(earn_cd, *, as_of_date=None):
    """ALOC1/ALOC2/ALOC3 from journal masters (e.g. 596/2026/000)."""
    try:
        from .voucher_generation_service import credit_gl_triplet_for_earn

        return credit_gl_triplet_for_earn(earn_cd, as_of_date=as_of_date)
    except Exception:
        return None


def _deduction_note_text(row, *, as_of_date=None):
    desc = str(row.get("desc") or "").strip()
    if not desc:
        desc = str(row.get("code") or "").strip()
    amount = row.get("amount")
    if amount in (None, ""):
        base = f"Rs 0 is to be deducted towards {desc}." if desc else ""
    else:
        amt_text = _format_amount_int(amount)
        if desc:
            base = f"Rs.{amt_text}/- is to be deducted towards {desc}."
        else:
            base = f"Rs.{amt_text}/- is to be deducted."

    if not base:
        return ""

    code = str(row.get("code") or "").strip()
    gl = _deduction_credit_gl(code, as_of_date=as_of_date) if code else None
    if gl:
        # Drop trailing period before appending credit clause.
        base = base.rstrip().rstrip(".")
        return f"{base} and credited to {gl}."
    return base if base.endswith(".") else f"{base}."


def _proposal_deduction_notes(active_proposal, ca_number, *, emp_cd=None):
    notes = []
    seen = set()
    as_of = _deduction_gl_as_of_date(active_proposal, emp_cd)
    for row in _proposal_earning_deduction_rows(active_proposal, ca_number):
        row_type = str(row.get("type") or "").strip().upper()
        if row_type not in ("D", "DEDN", "DEDUCTION"):
            continue
        code = str(row.get("code") or "").strip()
        if not code or code in seen:
            continue
        seen.add(code)
        text = _deduction_note_text(row, as_of_date=as_of)
        if text:
            notes.append(text)
    return notes


def _build_notes(
    proposal, pronoun, base_cpi, *, emp_cd, ca_number, gratuity_amt=None
):
    notes = ["Submitted to the FA & CAO for sanction."]
    scheme = _pension_scheme_phrase(_proposal_value(proposal, "pension_option") or "G")
    regn_no = _proposal_value(proposal, "regn_no") or ""
    regn_dt = _format_dd_mm_yy(_proposal_value(proposal, "regn_date"))
    if regn_no:
        notes.append(
            f"{pronoun} was a permanent employee and opted for pension scheme "
            f"on {scheme} vide P.S. Reg. No. {regn_no} dated {regn_dt}"
        )
    else:
        notes.append(
            f"{pronoun} was a permanent employee and opted for pension scheme "
            f"on {scheme}."
        )
    if base_cpi:
        notes.append(f"Relief to be given over {int(float(base_cpi))} CPI.")

    # Oracle CF_GRAT_HELD_STRFORMULA (held-up flag + amount + reason).
    held_note = _held_gratuity_sanction_note(
        proposal,
        emp_cd=emp_cd,
        ca_number=ca_number,
        gratuity_amt=gratuity_amt,
    )
    if held_note:
        notes.append(held_note)

    # Oracle CF_DEDN_STMTFORMULA — proposal deduction lines.
    notes.extend(
        _proposal_deduction_notes(proposal, ca_number, emp_cd=emp_cd)
    )
    return notes


def _build_pension_admissible_text(summary, pronoun_lower="his"):
    pension_amt = _format_amount_int(summary.pension_amount)
    gratuity_amt = _format_amount_int(summary.gratuity_amount)
    tqs = _format_service_phrase(
        summary.tqs_years,
        summary.tqs_months,
        summary.tqs_days,
    )
    tccs = _format_service_phrase(
        summary.tccs_years,
        summary.tccs_months,
        summary.tccs_days,
        compact=True,
    )
    return (
        f"Superannuation Pension Rs.{pension_amt}/- p.m. for {pronoun_lower} "
        f"total qualifying service {tqs} and a Gratuity of Rs.{gratuity_amt} "
        f"for {pronoun_lower} total completed continuous service of {tccs}"
    )


def _proposal_value(proposal, *names):
    if not proposal:
        return None
    for name in names:
        if hasattr(proposal, name):
            value = getattr(proposal, name)
            if value not in (None, ""):
                return value
    return None


def _retirement_date(case, active_proposal, oracle_proposal=None):
    """
    Date for 'Retired From' and age on retirement (Oracle BMP / FI_PN_MH_PENSION_PROPOSAL).
    Prefer statutory retirement date over administrative separation date.
    """
    return (
        case.retirement_date
        or _proposal_value(oracle_proposal, "separation_dt")
        or _proposal_value(active_proposal, "separation_dt")
        or _proposal_value(active_proposal, "separation_date")
        or case.separation_date
    )


def _build_row(emp_cd):
    case = reload_pension_case_from_db(emp_cd)
    if not case:
        raise ProposalSanctionReportError(
            "Pension case not found. Complete no-pay and amount calculation first."
        )

    try:
        summary = case.summary
    except PensionSummary.DoesNotExist:
        raise ProposalSanctionReportError(
            "Pension amounts not calculated. Run amount calculation first."
        )

    proposal = PensionProposal.objects.filter(emp_cd=str(emp_cd).strip()).first()
    if not proposal and str(emp_cd).strip().isdigit():
        proposal = PensionProposal.objects.filter(
            emp_cd=str(int(emp_cd))
        ).first()

    oracle_proposal = (
        FiPnMhPensionProposal.objects.filter(emp_cd=_clip(emp_cd, 5)).first()
    )
    pensioner = FiPnMhPensioner.objects.filter(emp_cd=_clip(emp_cd, 5)).first()

    active_proposal = proposal or oracle_proposal
    ca_number = _proposal_value(active_proposal, "ca_number") or ""

    retirement_dt = _retirement_date(case, active_proposal, oracle_proposal)
    separation_type = (
        _proposal_value(active_proposal, "separation_type")
        or case.separation_type
        or "RT"
    )
    join_dt = case.joining_date
    birth_dt = case.birth_date

    base_cpi = (
        _proposal_value(active_proposal, "retirement_cpi", "base_cpi")
        or (pensioner.base_cpi if pensioner else None)
    )

    pronoun = _employee_pronoun(emp_cd)
    pronoun_lower = "her" if pronoun == "She" else "his"
    pension_option = _proposal_value(active_proposal, "pension_option") or "G"

    age = (
        calculate_age(birth_dt, retirement_dt)
        if birth_dt and retirement_dt
        else None
    )
    last_pay = _format_amount_int(case.last_basic)
    avg_emoluments = last_pay

    return {
        "emp_cd": _clip(emp_cd, 5),
        "case_no": _format_case_no(ca_number),
        "roll_no": _format_roll_no(active_proposal, pensioner),
        "name": _employee_name(emp_cd, case, active_proposal, pensioner),
        "scheme": _pension_scheme_label(pension_option),
        "last_pay": last_pay,
        "avg_emoluments": avg_emoluments,
        "nature_of_service": resolve_employee_designation_name(
            emp_cd, case=case, pensioner=pensioner
        ),
        "department": resolve_dept_wise_department(
            emp_cd,
            fallback=_department_name(emp_cd),
        ),
        "entered_service": _format_dd_mm_yy(join_dt),
        "retired_from": _format_dd_mm_yy(retirement_dt),
        "retirement_reason": _separation_reason_label(separation_type),
        "retirement_age": _format_age_compact(age),
        "notes": _build_notes(
            active_proposal,
            pronoun,
            base_cpi,
            emp_cd=emp_cd,
            ca_number=ca_number,
            gratuity_amt=summary.gratuity_amount,
        ),
        "pension_admissible_text": _build_pension_admissible_text(
            summary,
            pronoun_lower=pronoun_lower,
        ),
        "remarks": "Service verified from Office records.",
    }


def build_proposal_sanction_report(*, emp_codes=None):
    """Build FI_PN_MH_PENSION_PROPOSAL_BMP style report payload."""
    codes = [_clip(c, 5) for c in (emp_codes or []) if _clip(c, 5)]
    if not codes:
        raise ProposalSanctionReportError("emp_code is required.")

    rows = []
    for emp_cd in codes:
        rows.append(_build_row(emp_cd))

    total_pages = len(rows) or 1
    for index, row in enumerate(rows, start=1):
        row["page_no"] = index
        row["total_pages"] = total_pages

    return {
        "org_name": "SYAMA PRASAD MOOKERJEE PORT, KOLKATA",
        "report_title": "Recommendation and Sanction of Pension",
        "run_date": _format_run_date(),
        "pages": rows,
        "row_count": len(rows),
    }
