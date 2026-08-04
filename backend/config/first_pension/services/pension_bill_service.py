"""
Pension bill generation — port of FI_PN_First_Pension_Bill.fmb (FPROC_BILL_GENERATE).
"""

from collections import defaultdict
from datetime import date
from decimal import Decimal

from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from employee.oracle_mirror import FiXxMhEmpAdm, FiXxMhEmpPer
from master_data.models import FiPnMhEarndedn, FiXxMhDesig, FiXxXxMDFinCtrl
from master_data.services.fin_year_service import fin_year_for_month
from master_data.services.erndedn_map_service import MAP_PENSION, resolve_earndedn_cd

from ..models import PensionCase, PensionProposal, PensionSummary
from ..oracle_mirror import (
    FiPnMhPensionProposal,
    FiPnMhPensioner,
    FiPnMhPmthsetup,
    FiPnTdFirstMonthPension,
    FiPnThFirstMonthPension,
    FiPnThPensionBill,
)
from ..utils.amount_words import rupees_amount_in_words


class PensionBillError(Exception):
    pass


DOC_ABV_PPN = "PPN"

_MONTH_NAMES = (
    "",
    "JANUARY",
    "FEBRUARY",
    "MARCH",
    "APRIL",
    "MAY",
    "JUNE",
    "JULY",
    "AUGUST",
    "SEPTEMBER",
    "OCTOBER",
    "NOVEMBER",
    "DECEMBER",
)
_MONTH_SHORT = (
    "",
    "JAN",
    "FEB",
    "MAR",
    "APR",
    "MAY",
    "JUN",
    "JUL",
    "AUG",
    "SEP",
    "OCT",
    "NOV",
    "DEC",
)


def _user_code(user):
    if not user or not getattr(user, "is_authenticated", False):
        return "A0001"
    return str(getattr(user, "username", None) or "A0001").strip()[:5].upper() or "A0001"


def _clip(value, max_len, default=""):
    if value is None:
        return default
    text = str(value).strip()
    if not text:
        return default
    return text[:max_len]


def _dec(value):
    if value is None:
        return Decimal("0")
    return Decimal(str(value))


def _resolve_fin_year_for_month(bill_month, bill_year):
    fin_yr = fin_year_for_month(bill_month, bill_year)
    if fin_yr is not None:
        return fin_yr
    raise PensionBillError(
        f"No active financial year for bill month {int(bill_month):02d}/{int(bill_year)}."
    )


def _allocate_ppn_serial(fin_yr):
    try:
        ctrl = FiXxXxMDFinCtrl.objects.select_for_update().get(
            fin_yr=fin_yr,
            doc_abv=DOC_ABV_PPN,
        )
    except FiXxXxMDFinCtrl.DoesNotExist as exc:
        raise PensionBillError(
            f"FIN_CTRL row missing for DOC_ABV={DOC_ABV_PPN}, FIN_YR={fin_yr}."
        ) from exc
    serial = int(ctrl.l_trn_no or 0) + 1
    ctrl.l_trn_no = serial
    ctrl.save(update_fields=["l_trn_no"])
    return serial


def _has_bill_no(value):
    return bool(str(value or "").strip())


def _filter_unbilled(qs):
    """Oracle mirror rows often have NULL BILL_NO instead of empty string."""
    return qs.filter(Q(bill_no="") | Q(bill_no__isnull=True))


def _filter_billed(qs):
    return qs.exclude(Q(bill_no="") | Q(bill_no__isnull=True))


def _format_ppn_bill_no(bill_month, bill_year, serial):
    return f"PPN/{int(bill_month):02d}/{int(bill_year)}/{int(serial)}"


def please_sum_pension(
    *,
    emp_cd,
    bill_type,
    month,
    year,
    excluded_earn_codes=None,
    fmpen_id=None,
):
    """
    Port of FINANCE.PLEASE_SUM_PENSION — sum earn/dedn TD lines for employee FMPEN.
    """
    emp_key = _clip(emp_cd, 5)
    bill_type_key = _clip(bill_type, 3, "N")[:1]

    header_fmpen_id = _clip(fmpen_id, 22) if fmpen_id else ""
    if not header_fmpen_id:
        header = FiPnThFirstMonthPension.objects.filter(
            emp_cd=emp_key,
            pension_type__startswith=bill_type_key,
            pension_month=int(month),
            pension_yr=int(year),
        ).first()
        if not header:
            return Decimal("0"), Decimal("0")
        header_fmpen_id = header.fmpen_id

    earn_codes = set(
        FiPnMhEarndedn.objects.filter(earndedn_type="E").values_list(
            "earndedn_cd", flat=True
        )
    )
    dedn_codes = set(
        FiPnMhEarndedn.objects.filter(earndedn_type="D").values_list(
            "earndedn_cd", flat=True
        )
    )
    skip_codes = set(excluded_earn_codes or ())

    lines = FiPnTdFirstMonthPension.objects.filter(fmpen_id=header_fmpen_id)
    earn_sum = Decimal("0")
    dedn_sum = Decimal("0")
    for line in lines:
        if line.earn_dedn_cd in skip_codes:
            continue
        amt = _dec(line.amount)
        if line.earn_dedn_cd in earn_codes or line.earn_dedn_type == "E":
            earn_sum += amt
        elif line.earn_dedn_cd in dedn_codes or line.earn_dedn_type == "D":
            dedn_sum += amt
    return earn_sum, dedn_sum


def _lic_report_excluded_earn_codes():
    """PEN_FIRST_BILL_REPORT_LIC — gratuity + commutation only, not monthly pension."""
    try:
        return {resolve_earndedn_cd(MAP_PENSION, "E")}
    except Exception:
        return {"200"}


def _bill_sum_excluded_earn_codes(header):
    """LIC first bills pay commutation + gratuity only (not monthly pension)."""
    if str(header.lic_bank_cd or "").strip():
        return _lic_report_excluded_earn_codes()
    return frozenset()


def please_sum_pension_for_header(header):
    """Bill totals / abstract — match Oracle LIC bill when lic_bank_cd is set."""
    return please_sum_pension(
        emp_cd=header.emp_cd,
        bill_type=header.pension_type,
        month=header.pension_month,
        year=header.pension_yr,
        fmpen_id=header.fmpen_id,
        excluded_earn_codes=_bill_sum_excluded_earn_codes(header),
    )


def _ensure_month_setup(bill_type, bill_month, bill_year, user_code, today):
    setup, _ = FiPnMhPmthsetup.objects.get_or_create(
        bill_type=_clip(bill_type, 3, "N")[:1],
        bill_mth=int(bill_month),
        bill_yr=int(bill_year),
        defaults={
            "bill_process_flg": 0,
            "bill_close_flg": 0,
            "date_created": today,
            "created_by": user_code,
        },
    )
    return setup


def assert_month_not_closed(bill_type, bill_month, bill_year):
    setup = FiPnMhPmthsetup.objects.filter(
        bill_type=_clip(bill_type, 3, "N")[:1],
        bill_mth=int(bill_month),
        bill_yr=int(bill_year),
    ).first()
    if setup and int(setup.bill_close_flg or 0) == 1:
        raise PensionBillError(
            "Bill has been closed for this month. No further generation allowed."
        )


def _employee_name(emp_cd):
    per = FiXxMhEmpPer.objects.filter(emp_cd=emp_cd).first()
    if not per:
        return ""
    parts = [per.first_name, per.middle_name, per.last_name]
    return " ".join(p for p in parts if p).strip()


def _format_dd_mm_yyyy(value):
    if not value:
        return ""
    if hasattr(value, "strftime"):
        return value.strftime("%d/%m/%Y")
    return str(value)


def _month_title(month, year):
    m = int(month)
    y = int(year)
    name = _MONTH_NAMES[m] if 1 <= m <= 12 else str(m)
    return f"{name} {y}"


def _month_short_label(month, year):
    m = int(month)
    y = int(year) % 100
    short = _MONTH_SHORT[m] if 1 <= m <= 12 else str(m)
    return f"{short} - {y:02d}"


def _month_mm_yyyy(month, year):
    return f"{int(month):02d}/{int(year)}"


def _month_name_comma_year(month, year):
    m = int(month)
    y = int(year)
    name = _MONTH_NAMES[m] if 1 <= m <= 12 else str(m)
    return f"{name} ,{y}"


def _earndedn_descriptions():
    return {
        row["earndedn_cd"]: row["earndedn_desc"]
        for row in FiPnMhEarndedn.objects.values("earndedn_cd", "earndedn_desc")
    }


def _designation_name(desig_cd):
    if not desig_cd:
        return ""
    row = FiXxMhDesig.objects.filter(desig_cd=desig_cd).first()
    return (row.desig_desc if row else "").strip().upper()


def _format_case_no(ca_no):
    text = _clip(ca_no, 22)
    if not text:
        return ""
    upper = text.upper()
    if "C/A" in upper:
        return upper
    return f"{text} C/A"


def _format_roll_no(pensioner, proposal):
    roll = ""
    if pensioner and str(pensioner.pension_roll_no or "").strip():
        roll = str(pensioner.pension_roll_no).strip()
    elif proposal and str(proposal.pension_roll_no or "").strip():
        roll = str(proposal.pension_roll_no).strip()
    if not roll:
        return ""
    upper = roll.upper()
    if not upper.startswith("LIC"):
        roll = f"LIC-{roll}"
    return f"**{roll}"


ID_CARD_HOLDUP_LINE = (
    "Rs 0 is to be held up for non submission of ID Card"
)


def _is_id_card_submitted(proposal_mirror, emp_cd, ca_no=None):
    """ID card submitted flag from Oracle mirror or SMPK PensionProposal."""
    if proposal_mirror is not None:
        tag = (proposal_mirror.id_card_submitted or "").strip().upper()
        if tag in ("Y", "1"):
            return True
        if tag in ("N", "0"):
            return False

    emp_key = _clip(emp_cd, 5)
    qs = PensionProposal.objects.filter(emp_cd=emp_key)
    ca_key = _clip(ca_no, 50) if ca_no else ""
    proposal = qs.filter(ca_number=ca_key).first() if ca_key else None
    if not proposal:
        proposal = qs.first()
    if proposal is not None:
        return bool(proposal.id_card_submitted)
    return False


def _lic_treasurer_holdup_line(proposal_mirror, emp_cd, ca_no):
    if _is_id_card_submitted(proposal_mirror, emp_cd, ca_no):
        return ""
    return ID_CARD_HOLDUP_LINE


def _format_report_amount(value, decimals=2):
    n = float(value or 0)
    if decimals == 0:
        return str(int(round(n)))
    return f"{n:.{decimals}f}"


def _build_bill_report_page(
    header,
    bill,
    desc_map,
    *,
    excluded_earn_codes=None,
    gross_pension_earn_line=False,
):
    """Shared first-bill page builder (Oracle PEN_FIRST_BILL_REPORT layout)."""
    pensioner = FiPnMhPensioner.objects.filter(
        ca_number=header.ca_no
    ).first() or FiPnMhPensioner.objects.filter(emp_cd=header.emp_cd).first()
    proposal = FiPnMhPensionProposal.objects.filter(
        ca_number=header.ca_no
    ).first() or FiPnMhPensionProposal.objects.filter(emp_cd=header.emp_cd).first()

    name = ""
    if pensioner and pensioner.name:
        name = pensioner.name.strip().upper()
    if not name:
        name = _employee_name(header.emp_cd).upper()

    desig_cd = pensioner.desig_cd if pensioner else None
    if not desig_cd:
        adm = FiXxMhEmpAdm.objects.filter(emp_cd=header.emp_cd).first()
        desig_cd = adm.desig_cd if adm else None

    base_cpi = header.base_cpi or (pensioner.base_cpi if pensioner else None)
    if base_cpi is None and proposal:
        base_cpi = proposal.base_cpi

    sepn_dt = None
    if proposal:
        sepn_dt = proposal.separation_dt
    if not sepn_dt and pensioner:
        sepn_dt = pensioner.emp_ret_dt

    account_no = ""
    if pensioner and pensioner.account_no:
        account_no = pensioner.account_no
    elif proposal and proposal.account_no:
        account_no = proposal.account_no

    td_lines = list(
        FiPnTdFirstMonthPension.objects.filter(fmpen_id=header.fmpen_id).order_by(
            "earn_dedn_type", "earn_dedn_cd"
        )
    )
    skip_codes = set(excluded_earn_codes or ())
    earn_lines = []
    dedn_lines = []
    gross_earn = Decimal("0")
    gross_dedn = Decimal("0")
    for line in td_lines:
        if line.earn_dedn_cd in skip_codes:
            continue
        amt = _dec(line.amount)
        desc = desc_map.get(line.earn_dedn_cd) or line.earn_dedn_cd
        entry = {
            "earn_dedn_cd": line.earn_dedn_cd,
            "earn_dedn_type": line.earn_dedn_type,
            "description": desc.strip().upper(),
            "amount": float(amt),
            "amount_display": _format_report_amount(amt, decimals=0),
        }
        if line.earn_dedn_type == "E":
            earn_lines.append(entry)
            gross_earn += amt
        else:
            dedn_lines.append(entry)
            gross_dedn += amt

    line_items = earn_lines + dedn_lines
    net_earn = gross_earn - gross_dedn

    if gross_pension_earn_line:
        pension_cd = None
        try:
            pension_cd = resolve_earndedn_cd(MAP_PENSION, "E")
        except Exception:
            pension_cd = "200"
        summary = None
        case = PensionCase.objects.filter(emp_code=header.emp_cd).first()
        if case:
            summary = PensionSummary.objects.filter(pension_case_id=case.id).first()
        if summary and summary.pension_amount is not None:
            gross_pension = _dec(summary.pension_amount)
            for entry in earn_lines:
                if entry["earn_dedn_cd"] == pension_cd:
                    entry["amount"] = float(gross_pension)
                    entry["amount_display"] = _format_report_amount(
                        gross_pension,
                        decimals=0,
                    )
                    break
            gross_earn = sum(_dec(e["amount"]) for e in earn_lines)
            gross_dedn = sum(_dec(d["amount"]) for d in dedn_lines)
            line_items = earn_lines + dedn_lines
            net_earn = gross_earn - gross_dedn

    return {
        "emp_cd": header.emp_cd,
        "fmpen_id": header.fmpen_id,
        "roll_no": _format_roll_no(pensioner, proposal),
        "case_no": _format_case_no(header.ca_no),
        "base_cpi": str(int(base_cpi)) if base_cpi is not None else "",
        "sepn_date": _format_dd_mm_yyyy(sepn_dt),
        "name": name,
        "account_no": account_no,
        "designation": _designation_name(desig_cd),
        "month_label": _month_short_label(header.pension_month, header.pension_yr),
        "line_items": line_items,
        "gross_earn": float(gross_earn),
        "gross_dedn": float(gross_dedn),
        "net_earn": float(net_earn),
        "gross_earn_display": _format_report_amount(gross_earn),
        "gross_dedn_display": _format_report_amount(gross_dedn),
        "net_earn_display": _format_report_amount(net_earn),
        "gross_earn_words": rupees_amount_in_words(gross_earn),
        "gross_dedn_words": rupees_amount_in_words(gross_dedn),
        "net_earn_words": rupees_amount_in_words(net_earn),
        "no_of_cases": 1,
        "lic_bank_cd": header.lic_bank_cd or "",
        "pension_proposal_no": (
            proposal.pension_proposal_no.strip() if proposal else ""
        ),
        "pension_proposal_date": (
            _format_dd_mm_yyyy(proposal.pension_proposal_dt) if proposal else ""
        ),
    }


def _build_lic_page(header, bill, desc_map):
    page = _build_bill_report_page(
        header,
        bill,
        desc_map,
        excluded_earn_codes=_lic_report_excluded_earn_codes(),
    )
    proposal = FiPnMhPensionProposal.objects.filter(
        ca_number=header.ca_no
    ).first() or FiPnMhPensionProposal.objects.filter(emp_cd=header.emp_cd).first()
    page["treasurer_holdup_line"] = _lic_treasurer_holdup_line(
        proposal,
        header.emp_cd,
        header.ca_no,
    )
    return page


def serialize_bill_candidate(header):
    earn, dedn = please_sum_pension_for_header(header)
    return {
        "fmpen_id": header.fmpen_id,
        "emp_cd": header.emp_cd,
        "emp_name": _employee_name(header.emp_cd),
        "ca_no": header.ca_no,
        "bank_cd": header.bank_cd or "",
        "lic_bank_cd": header.lic_bank_cd or "",
        "pension_type": header.pension_type,
        "pension_month": header.pension_month,
        "pension_yr": header.pension_yr,
        "original_fpension_amt": float(header.original_fpension_amt or 0),
        "payable_pension": float(header.payable_pension or 0),
        "bill_no": header.bill_no or "",
        "ready_for_bill": not _has_bill_no(header.bill_no),
        "earn_sum": float(earn),
        "dedn_sum": float(dedn),
    }


def list_bill_candidates(*, bill_month, bill_year, bill_type, emp_cd=None):
    """Rows ready for bill (BILL_NO empty), matching FI_PN_First_Pension_Bill retrieve."""
    bill_type_key = _clip(bill_type, 3, "N")[:1]
    qs = _filter_unbilled(
        FiPnThFirstMonthPension.objects.filter(
            pension_month=int(bill_month),
            pension_yr=int(bill_year),
            pension_type__startswith=bill_type_key,
        )
    )
    if emp_cd:
        qs = qs.filter(emp_cd=_clip(emp_cd, 5))
    return [serialize_bill_candidate(h) for h in qs.order_by("bank_cd", "emp_cd")]


def list_ppn_bills(*, bill_month, bill_year):
    """PPN bills for month/year (LIC report LOV)."""
    rows = FiPnThPensionBill.objects.filter(
        bill_month=int(bill_month),
        bill_yr=int(bill_year),
        bill_no__startswith="PPN",
    ).order_by("bill_no")
    return [
        {
            "bill_no": b.bill_no,
            "bill_type": b.bill_type,
            "bill_month": b.bill_month,
            "bill_yr": b.bill_yr,
            "bank_cd": b.bank_cd,
            "total_amt_earned": float(b.total_amt_earned or 0),
            "total_amt_deducted": float(b.total_amt_deducted or 0),
            "gen_lic_tag": b.gen_lic_tag or "",
        }
        for b in rows
    ]


def get_employee_bill_status(emp_cd):
    header = (
        FiPnThFirstMonthPension.objects.filter(emp_cd=_clip(emp_cd, 5))
        .order_by("-pension_yr", "-pension_month")
        .first()
    )
    if not header:
        return {"has_first_month": False}

    bill = None
    if header.bill_no:
        bill = FiPnThPensionBill.objects.filter(bill_no=header.bill_no).first()

    return {
        "has_first_month": True,
        "fmpen_id": header.fmpen_id,
        "pension_month": header.pension_month,
        "pension_yr": header.pension_yr,
        "pension_type": header.pension_type,
        "bill_no": header.bill_no or "",
        "bank_cd": header.bank_cd or "",
        "lic_bank_cd": header.lic_bank_cd or "",
        "has_pension_bill": bool(bill),
        "pension_bill": (
            {
                "bill_no": bill.bill_no,
                "total_amt_earned": float(bill.total_amt_earned or 0),
                "total_amt_deducted": float(bill.total_amt_deducted or 0),
                "gen_lic_tag": bill.gen_lic_tag or "",
            }
            if bill
            else None
        ),
    }


@transaction.atomic
def generate_pension_bills(
    *,
    bill_month,
    bill_year,
    bill_type,
    fmpen_ids,
    user=None,
    include_same_bank_unselected=False,
):
    """
    Generate PPN bills grouped by bank_cd for selected first-month headers.
    """
    if not fmpen_ids:
        raise PensionBillError("Select at least one pensioner for bill generation.")

    bill_type_key = _clip(bill_type, 3, "N")[:1]
    assert_month_not_closed(bill_type_key, bill_month, bill_year)

    user_code = _user_code(user)
    today = timezone.localdate()
    fin_yr = _resolve_fin_year_for_month(bill_month, bill_year)

    selected = list(
        FiPnThFirstMonthPension.objects.filter(
            fmpen_id__in=[_clip(x, 22) for x in fmpen_ids],
            pension_month=int(bill_month),
            pension_yr=int(bill_year),
            pension_type__startswith=bill_type_key,
        )
    )
    if not selected:
        raise PensionBillError("No matching first-month pension records found.")

    if include_same_bank_unselected:
        bank_codes = {h.bank_cd or "" for h in selected}
        extra = _filter_unbilled(
            FiPnThFirstMonthPension.objects.filter(
                pension_month=int(bill_month),
                pension_yr=int(bill_year),
                pension_type__startswith=bill_type_key,
                bank_cd__in=bank_codes,
            )
        ).exclude(fmpen_id__in=[h.fmpen_id for h in selected])
        selected.extend(list(extra))

    unbilled = [h for h in selected if not _has_bill_no(h.bill_no)]
    if not unbilled:
        raise PensionBillError("Selected pensioners already have a bill number.")

    by_bank = defaultdict(list)
    for header in unbilled:
        by_bank[header.bank_cd or ""].append(header)

    created_bills = []
    for bank_cd, headers in by_bank.items():
        total_earn = Decimal("0")
        total_dedn = Decimal("0")
        gen_lic = "F"
        for header in headers:
            earn, dedn = please_sum_pension_for_header(header)
            total_earn += earn
            total_dedn += dedn
            if str(header.lic_bank_cd or "").strip():
                gen_lic = "G"

        serial = _allocate_ppn_serial(fin_yr)
        bill_no = _format_ppn_bill_no(bill_month, bill_year, serial)

        FiPnThPensionBill.objects.create(
            bill_no=bill_no,
            bill_type=bill_type_key,
            bill_month=int(bill_month),
            bill_yr=int(bill_year),
            bank_cd=_clip(bank_cd, 6),
            total_amt_earned=total_earn,
            total_amt_deducted=total_dedn,
            date_created=today,
            created_by=user_code,
            gen_lic_tag=gen_lic,
        )

        FiPnThFirstMonthPension.objects.filter(
            fmpen_id__in=[h.fmpen_id for h in headers]
        ).update(bill_no=bill_no, date_modified=today, modified_by=user_code)

        created_bills.append(
            {
                "bill_no": bill_no,
                "bank_cd": bank_cd,
                "total_amt_earned": float(total_earn),
                "total_amt_deducted": float(total_dedn),
                "gen_lic_tag": gen_lic,
                "pensioner_count": len(headers),
                "fmpen_ids": [h.fmpen_id for h in headers],
            }
        )

    setup = _ensure_month_setup(bill_type_key, bill_month, bill_year, user_code, today)
    setup.bill_process_flg = 1
    setup.date_modified = today
    setup.modified_by = user_code
    setup.save(update_fields=["bill_process_flg", "date_modified", "modified_by"])

    return {
        "bills": created_bills,
        "fin_year": fin_yr,
        "bill_month": int(bill_month),
        "bill_year": int(bill_year),
        "bill_type": bill_type_key,
    }


def _build_first_bill_report_payload(
    bill,
    pages,
    *,
    report_kind,
    show_abstract_meta,
):
    bill_month = bill.bill_month
    bill_year = bill.bill_yr

    total_pages = len(pages) or 1
    for index, page in enumerate(pages, start=1):
        page["page_no"] = index
        page["total_pages"] = total_pages

    bill_meta = {
        "bill_no": bill.bill_no,
        "bill_type": bill.bill_type,
        "bill_month": bill.bill_month,
        "bill_yr": bill.bill_yr,
        "mm_yyyy": _month_mm_yyyy(bill.bill_month, bill.bill_yr),
        "bank_cd": bill.bank_cd,
        "gen_lic_tag": bill.gen_lic_tag or "",
        "total_amt_earned": float(bill.total_amt_earned or 0),
        "total_amt_deducted": float(bill.total_amt_deducted or 0),
    }
    if show_abstract_meta:
        bill_meta["bill_abstract_no"] = bill.bill_abstract_no or ""
        bill_meta["abstract_date"] = _format_dd_mm_yyyy(bill.abstract_date)

    return {
        "report_kind": report_kind,
        "org_name": "SYAMA PRASAD MOOKERJEE PORT, KOLKATA",
        "report_title": f"First Pension Bill For {_month_title(bill_month, bill_year)}",
        "bank_wise_heading": _month_name_comma_year(bill_month, bill_year),
        "bill": bill_meta,
        "pages": pages,
        "row_count": len(pages),
    }


def build_lic_report(bill_no, *, emp_codes=None):
    """LIC first-bill print payload (Oracle PEN_FIRST_BILL_REPORT_LIC layout)."""
    bill = FiPnThPensionBill.objects.filter(bill_no=_clip(bill_no, 22)).first()
    if not bill:
        raise PensionBillError(f"Bill {bill_no} not found.")

    headers = FiPnThFirstMonthPension.objects.filter(bill_no=bill.bill_no)
    if emp_codes:
        codes = {_clip(c, 5) for c in emp_codes}
        headers = headers.filter(emp_cd__in=codes)

    desc_map = _earndedn_descriptions()
    pages = []
    for header in headers.order_by("emp_cd"):
        if not str(header.lic_bank_cd or "").strip():
            continue
        pages.append(_build_lic_page(header, bill, desc_map))

    return _build_first_bill_report_payload(
        bill,
        pages,
        report_kind="lic",
        show_abstract_meta=True,
    )


def get_month_setup_status(bill_type, bill_month, bill_year):
    setup = FiPnMhPmthsetup.objects.filter(
        bill_type=_clip(bill_type, 3, "N")[:1],
        bill_mth=int(bill_month),
        bill_yr=int(bill_year),
    ).first()
    if not setup:
        return {
            "bill_type": _clip(bill_type, 3, "N")[:1],
            "bill_mth": int(bill_month),
            "bill_yr": int(bill_year),
            "bill_process_flg": 0,
            "bill_close_flg": 0,
            "exists": False,
        }
    return {
        "bill_type": setup.bill_type,
        "bill_mth": setup.bill_mth,
        "bill_yr": setup.bill_yr,
        "bill_process_flg": int(setup.bill_process_flg or 0),
        "bill_close_flg": int(setup.bill_close_flg or 0),
        "exists": True,
    }


def serialize_reprocess_candidate(header):
    earn, dedn = please_sum_pension_for_header(header)
    bill = FiPnThPensionBill.objects.filter(bill_no=header.bill_no).first()
    return {
        **serialize_bill_candidate(header),
        "ready_for_bill": False,
        "ready_for_reprocess": _has_bill_no(header.bill_no),
        "stored_earn_sum": float(bill.total_amt_earned or 0) if bill else None,
        "stored_dedn_sum": float(bill.total_amt_deducted or 0) if bill else None,
        "earn_changed": (
            bill is not None
            and (
                float(earn) != float(bill.total_amt_earned or 0)
                or float(dedn) != float(bill.total_amt_deducted or 0)
            )
        ),
    }


def list_reprocess_candidates(*, bill_month, bill_year, bill_type, emp_cd=None):
    """Rows on an existing PPN bill — port of FI_PENSION_BILL_REPROCESS retrieve."""
    bill_type_key = _clip(bill_type, 3, "N")[:1]
    qs = _filter_billed(
        FiPnThFirstMonthPension.objects.filter(
            pension_month=int(bill_month),
            pension_yr=int(bill_year),
            pension_type__startswith=bill_type_key,
        )
    ).filter(bill_no__startswith="PPN")
    if emp_cd:
        qs = qs.filter(emp_cd=_clip(emp_cd, 5))
    return [
        serialize_reprocess_candidate(h)
        for h in qs.order_by("bill_no", "bank_cd", "emp_cd")
    ]


def _recompute_bill_totals(bill_no):
    headers = FiPnThFirstMonthPension.objects.filter(bill_no=bill_no)
    total_earn = Decimal("0")
    total_dedn = Decimal("0")
    gen_lic = "F"
    for header in headers:
        earn, dedn = please_sum_pension_for_header(header)
        total_earn += earn
        total_dedn += dedn
        if str(header.lic_bank_cd or "").strip():
            gen_lic = "G"
    return total_earn, total_dedn, gen_lic, headers.count()


@transaction.atomic
def reprocess_pension_bills(
    *,
    bill_month,
    bill_year,
    bill_type,
    fmpen_ids,
    user=None,
):
    """
    Re-sum earn/dedn and UPDATE existing PPN bill headers (no new serial).
    Port of FI_PENSION_BILL_REPROCESS.FPROC_BILL_GENERATE.
    """
    if not fmpen_ids:
        raise PensionBillError("Select at least one pensioner to reprocess.")

    bill_type_key = _clip(bill_type, 3, "N")[:1]
    assert_month_not_closed(bill_type_key, bill_month, bill_year)

    user_code = _user_code(user)
    today = timezone.localdate()

    selected = list(
        FiPnThFirstMonthPension.objects.filter(
            fmpen_id__in=[_clip(x, 22) for x in fmpen_ids],
            pension_month=int(bill_month),
            pension_yr=int(bill_year),
            pension_type__startswith=bill_type_key,
        ).exclude(Q(bill_no="") | Q(bill_no__isnull=True))
    )
    if not selected:
        raise PensionBillError("No billed first-month pension records found.")

    bill_nos = sorted({h.bill_no for h in selected if str(h.bill_no or "").strip()})
    updated_bills = []

    for bill_no in bill_nos:
        bill = FiPnThPensionBill.objects.filter(bill_no=bill_no).first()
        if not bill:
            raise PensionBillError(f"Bill header {bill_no} not found.")

        total_earn, total_dedn, gen_lic, pensioner_count = _recompute_bill_totals(
            bill_no
        )
        bill.total_amt_earned = total_earn
        bill.total_amt_deducted = total_dedn
        bill.gen_lic_tag = gen_lic
        bill.date_modified = today
        bill.modified_by = user_code
        bill.save(
            update_fields=[
                "total_amt_earned",
                "total_amt_deducted",
                "gen_lic_tag",
                "date_modified",
                "modified_by",
            ]
        )
        updated_bills.append(
            {
                "bill_no": bill_no,
                "bank_cd": bill.bank_cd,
                "total_amt_earned": float(total_earn),
                "total_amt_deducted": float(total_dedn),
                "gen_lic_tag": gen_lic,
                "pensioner_count": pensioner_count,
            }
        )

    setup = _ensure_month_setup(bill_type_key, bill_month, bill_year, user_code, today)
    setup.bill_process_flg = 1
    setup.date_modified = today
    setup.modified_by = user_code
    setup.save(update_fields=["bill_process_flg", "date_modified", "modified_by"])

    return {
        "bills": updated_bills,
        "bill_month": int(bill_month),
        "bill_year": int(bill_year),
        "bill_type": bill_type_key,
    }


@transaction.atomic
def repair_orphan_pension_bill(*, bill_no=None, emp_cd=None, user=None):
    """
    Recreate a missing FI_PN_TH_PENSION_BILL row when first-month headers still
    reference a bill_no (e.g. after Oracle wave3 sync removed local bill rows).
    MySQL only — does not write to Oracle.
    """
    bill_no = _clip(bill_no, 22)
    emp_key = _clip(emp_cd, 5)

    if not bill_no and not emp_key:
        raise PensionBillError("bill_no or emp_cd is required.")

    headers_qs = _filter_billed(FiPnThFirstMonthPension.objects.all())
    if bill_no:
        headers_qs = headers_qs.filter(bill_no=bill_no)
    if emp_key:
        headers_qs = headers_qs.filter(emp_cd=emp_key)

    headers = list(headers_qs.order_by("emp_cd"))
    if not headers:
        raise PensionBillError("No billed first-month pension records found.")

    bill_no = bill_no or _clip(headers[0].bill_no, 22)
    if FiPnThPensionBill.objects.filter(bill_no=bill_no).exists():
        raise PensionBillError(f"Bill header {bill_no} already exists.")

    orphan_headers = [h for h in headers if h.bill_no == bill_no]
    if not orphan_headers:
        raise PensionBillError(f"No first-month rows reference bill {bill_no}.")

    bank_codes = {h.bank_cd or "" for h in orphan_headers}
    if len(bank_codes) > 1:
        raise PensionBillError(
            f"Bill {bill_no} spans multiple banks {sorted(bank_codes)}; repair manually."
        )

    sample = orphan_headers[0]
    bill_month = int(sample.pension_month)
    bill_year = int(sample.pension_yr)
    bill_type_key = _clip(sample.pension_type, 3, "N")[:1]
    assert_month_not_closed(bill_type_key, bill_month, bill_year)

    total_earn, total_dedn, gen_lic, pensioner_count = _recompute_bill_totals(bill_no)
    user_code = _user_code(user)
    today = timezone.localdate()

    bill = FiPnThPensionBill.objects.create(
        bill_no=bill_no,
        bill_type=bill_type_key,
        bill_month=bill_month,
        bill_yr=bill_year,
        bank_cd=_clip(orphan_headers[0].bank_cd, 6),
        total_amt_earned=total_earn,
        total_amt_deducted=total_dedn,
        date_created=today,
        created_by=user_code,
        gen_lic_tag=gen_lic,
    )

    setup = _ensure_month_setup(bill_type_key, bill_month, bill_year, user_code, today)
    setup.bill_process_flg = 1
    setup.date_modified = today
    setup.modified_by = user_code
    setup.save(update_fields=["bill_process_flg", "date_modified", "modified_by"])

    return {
        "bill_no": bill.bill_no,
        "bank_cd": bill.bank_cd,
        "bill_month": bill.bill_month,
        "bill_yr": bill.bill_yr,
        "bill_type": bill.bill_type,
        "total_amt_earned": float(total_earn),
        "total_amt_deducted": float(total_dedn),
        "gen_lic_tag": gen_lic,
        "pensioner_count": pensioner_count,
        "emp_codes": [h.emp_cd for h in orphan_headers],
        "repaired": True,
    }


@transaction.atomic
def close_pension_bill_month(*, bill_type, bill_month, bill_year, user=None):
    """Port of FPROC_PENBILL_CLOSE — lock month after bill work is complete."""
    bill_type_key = _clip(bill_type, 3, "N")[:1]
    setup = FiPnMhPmthsetup.objects.filter(
        bill_type=bill_type_key,
        bill_mth=int(bill_month),
        bill_yr=int(bill_year),
    ).first()
    if setup and int(setup.bill_close_flg or 0) == 1:
        raise PensionBillError(
            "Bill has been closed for this month. No further changes allowed."
        )

    user_code = _user_code(user)
    today = timezone.localdate()
    setup = _ensure_month_setup(
        bill_type_key, bill_month, bill_year, user_code, today
    )
    setup.bill_close_flg = 1
    setup.bill_process_flg = 1
    setup.date_modified = today
    setup.modified_by = user_code
    setup.save(
        update_fields=[
            "bill_close_flg",
            "bill_process_flg",
            "date_modified",
            "modified_by",
        ]
    )
    return get_month_setup_status(bill_type_key, bill_month, bill_year)
