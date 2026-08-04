"""
MySQL-first first-month pension generation (FPROC_FIRST_PENSION_PROCESS subset).

Used by the Amount tab "First pension Generate" button — allocates FMPEN_ID /
PPN bill number locally and posts header, detail, and pensioner master rows.
"""

from datetime import date
from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from employee.oracle_mirror import FiXxMhEmpAdm, FiXxMhEmpFin, FiXxMhEmpPer
from master_data.models import FiXxXxMDFinCtrl
from master_data.services.fin_year_service import fin_year_for_month
from master_data.services.erndedn_map_service import (
    MAP_COMMUTATION,
    MAP_GRATUITY,
    MAP_PENSION,
    resolve_earndedn_cd,
)

from ..models import (
    CommutationApplication,
    PensionCase,
    PensionProposal,
    PensionProposalEarndedn,
    PensionSummary,
)
from ..pension_proposal_api import (
    backfill_proposal_ca_number,
    resolve_proposal_ca_number,
)
from ..oracle_mirror import (
    FiPnMhPensioner,
    FiPnTdFirstMonthPension,
    FiPnThFirstMonthPension,
)


class FirstMonthPensionError(Exception):
    pass


DOC_ABV_FIRST_PENSION = "NPEN"
DOC_ABV_FIRST_MONTH_BILL = "PPN"


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


def _resolve_fin_year_for_month(pension_month, pension_year):
    fin_yr = fin_year_for_month(pension_month, pension_year)
    if fin_yr is not None:
        return fin_yr
    raise FirstMonthPensionError(
        f"No active financial year found for pension month {pension_month:02d}/{pension_year}."
    )


def _allocate_serial(doc_abv, fin_yr):
    try:
        ctrl = FiXxXxMDFinCtrl.objects.select_for_update().get(
            fin_yr=fin_yr,
            doc_abv=doc_abv,
        )
    except FiXxXxMDFinCtrl.DoesNotExist as exc:
        raise FirstMonthPensionError(
            f"FIN_CTRL row missing for DOC_ABV={doc_abv}, FIN_YR={fin_yr}."
        ) from exc
    serial = int(ctrl.l_trn_no or 0) + 1
    ctrl.l_trn_no = serial
    ctrl.save(update_fields=["l_trn_no"])
    return serial


def _format_ppn_bill_no(pension_month, pension_year, serial):
    return f"PPN/{int(pension_month):02d}/{int(pension_year)}/{int(serial)}"


def _format_fmpen_id(pension_year, serial):
    return f"NPEN/F/{int(pension_year)}/{int(serial)}"


def _employee_name(emp_cd):
    per = FiXxMhEmpPer.objects.filter(emp_cd=emp_cd).first()
    if not per:
        return ""
    parts = [per.first_name, per.middle_name, per.last_name]
    return " ".join(p for p in parts if p).strip()[:62]


def _pension_period(proposal, summary):
    if proposal.start_month and proposal.start_year:
        return int(proposal.start_month), int(proposal.start_year)
    start = summary.pension_start_date
    return start.month, start.year


def get_first_month_status(emp_code):
    emp_key = _clip(emp_code, 5)
    header = (
        FiPnThFirstMonthPension.objects.filter(emp_cd=emp_key)
        .order_by("-date_created", "-fmpen_id")
        .first()
    )
    if not header:
        return None
    return {
        "fmpen_id": header.fmpen_id,
        "bill_no": header.bill_no,
        "pension_month": header.pension_month,
        "pension_year": header.pension_yr,
        "ca_no": header.ca_no,
        "original_fpension_amt": (
            float(header.original_fpension_amt)
            if header.original_fpension_amt is not None
            else None
        ),
        "payable_pension": (
            float(header.payable_pension)
            if header.payable_pension is not None
            else None
        ),
        "generated": True,
    }


def _insert_detail_line(
    *,
    fmpen_id,
    emp_cd,
    earn_dedn_type,
    earn_dedn_cd,
    amount,
    user_code,
    today,
):
    if not earn_dedn_cd or amount is None:
        return
    amt = _dec(amount)
    if amt == 0:
        return
    FiPnTdFirstMonthPension.objects.create(
        fmpen_id=fmpen_id,
        earn_dedn_type=earn_dedn_type,
        earn_dedn_cd=earn_dedn_cd,
        amount=amt,
        emp_cd=emp_cd,
        original_amt=amt,
        arrear_amt=Decimal("0"),
        date_created=today,
        created_by=user_code,
    )


@transaction.atomic
def generate_first_month_pension(emp_code, user=None):
    """
    Post first-month pension bill in MySQL (header + detail + pensioner).

    Prerequisites: calculated PensionSummary, saved PensionProposal with CA no.
    Commutation application required except VR (voluntary retirement).
    """
    emp_key = _clip(emp_code, 5)
    if not emp_key:
        raise FirstMonthPensionError("Employee code is required.")

    case = PensionCase.objects.filter(emp_code=emp_key).first()
    if not case:
        raise FirstMonthPensionError("Pension case not found.")

    try:
        summary = case.summary
    except PensionSummary.DoesNotExist as exc:
        raise FirstMonthPensionError(
            "Calculate and save pension amounts before first pension generation."
        ) from exc

    proposal = PensionProposal.objects.filter(emp_cd=emp_key).first()
    if not proposal:
        raise FirstMonthPensionError("Pension proposal not found.")
    ca_number = _clip(resolve_proposal_ca_number(proposal, emp_key), 22)
    if not ca_number:
        raise FirstMonthPensionError("CA number is missing in pension proposal.")
    backfill_proposal_ca_number(proposal, ca_number)

    comm = CommutationApplication.objects.filter(emp_cd=emp_key).first()
    defer_commutation = (
        (case.separation_type or "").strip().upper() == "VR"
        or (proposal.separation_type or "").strip().upper() == "VR"
    )
    if defer_commutation:
        comm_pct = 0.0
    elif comm and comm.commutation_per is not None:
        comm_pct = float(comm.commutation_per)
    else:
        comm_pct = float(case.commutation_percent or 40)

    pension_month, pension_year = _pension_period(proposal, summary)

    existing = FiPnThFirstMonthPension.objects.filter(
        emp_cd=emp_key,
        pension_month=pension_month,
        pension_yr=pension_year,
    ).first()
    if existing:
        raise FirstMonthPensionError(
            f"First-month pension already generated for {pension_month:02d}/{pension_year} "
            f"(FMPEN_ID={existing.fmpen_id})."
        )

    fin_yr = _resolve_fin_year_for_month(pension_month, pension_year)
    npen_serial = _allocate_serial(DOC_ABV_FIRST_PENSION, fin_yr)
    fmpen_id = _format_fmpen_id(pension_year, npen_serial)

    original_pension = _dec(summary.pension_amount)
    if defer_commutation:
        commuted_monthly = Decimal("0")
        payable_pension = original_pension
    else:
        commuted_monthly = (original_pension * Decimal(str(comm_pct)) / Decimal("100")).quantize(
            Decimal("0.01")
        )
        payable_pension = (original_pension - commuted_monthly).quantize(Decimal("0.01"))
    gratuity = _dec(summary.gratuity_amount)

    user_code = _user_code(user)
    today = timezone.localdate()
    pension_type = _clip(proposal.pension_type, 1, "N") or "N"
    bank_cd = _clip(proposal.bank_cd, 6)
    lic_bank_cd = _clip(proposal.lic_bank_cd, 6)

    FiPnThFirstMonthPension.objects.create(
        fmpen_id=fmpen_id,
        pension_type=pension_type,
        pension_month=pension_month,
        pension_yr=pension_year,
        ca_no=ca_number,
        ca_date=proposal.pension_proposal_date or today,
        original_fpension_amt=original_pension,
        payable_pension=payable_pension,
        date_of_execution=today,
        bill_no="",
        date_created=today,
        created_by=user_code,
        emp_cd=emp_key,
        bank_cd=bank_cd,
        base_cpi=proposal.retirement_cpi,
        lic_bank_cd=lic_bank_cd,
        pen_proc_tag="Y",
    )

    pension_cd = resolve_earndedn_cd(MAP_PENSION, "E")
    comm_cd = resolve_earndedn_cd(MAP_COMMUTATION, "E")
    grat_cd = resolve_earndedn_cd(MAP_GRATUITY, "E")

    _insert_detail_line(
        fmpen_id=fmpen_id,
        emp_cd=emp_key,
        earn_dedn_type="E",
        earn_dedn_cd=pension_cd,
        amount=payable_pension,
        user_code=user_code,
        today=today,
    )
    if not defer_commutation and comm and summary.commutation_amount:
        _insert_detail_line(
            fmpen_id=fmpen_id,
            emp_cd=emp_key,
            earn_dedn_type="E",
            earn_dedn_cd=comm_cd,
            amount=summary.commutation_amount,
            user_code=user_code,
            today=today,
        )
    if gratuity > 0:
        _insert_detail_line(
            fmpen_id=fmpen_id,
            emp_cd=emp_key,
            earn_dedn_type="E",
            earn_dedn_cd=grat_cd,
            amount=gratuity,
            user_code=user_code,
            today=today,
        )

    skip_codes = {c for c in (pension_cd, comm_cd, grat_cd) if c}
    for line in PensionProposalEarndedn.objects.filter(ca_number=ca_number).order_by(
        "earndedn_cd", "earn_dedn_type"
    ):
        if line.earndedn_cd in skip_codes:
            continue
        _insert_detail_line(
            fmpen_id=fmpen_id,
            emp_cd=emp_key,
            earn_dedn_type=line.earn_dedn_type,
            earn_dedn_cd=line.earndedn_cd,
            amount=line.amount,
            user_code=user_code,
            today=today,
        )

    adm = FiXxMhEmpAdm.objects.filter(emp_cd=emp_key).first()
    fin = FiXxMhEmpFin.objects.filter(emp_cd=emp_key).first()
    per = FiXxMhEmpPer.objects.filter(emp_cd=emp_key).first()

    FiPnMhPensioner.objects.update_or_create(
        ca_number=ca_number,
        defaults={
            "emp_cd": emp_key,
            "original_pension_amt": original_pension,
            "effective_stdt_pension": summary.pension_start_date,
            "commuted_portion": commuted_monthly,
            "payable_pension": payable_pension,
            "gratuity": gratuity,
            "commutation_per": Decimal(str(comm_pct)),
            "relief": Decimal("0"),
            "pension_emoluments": _dec(case.last_basic),
            "gratuity_emoluments": _dec(case.last_basic),
            "tccs_yr": summary.tccs_years,
            "tccs_month": summary.tccs_months,
            "tccs_days": summary.tccs_days,
            "tqs_yr": summary.tqs_years,
            "tqs_month": summary.tqs_months,
            "tqs_days": summary.tqs_days,
            "name": _employee_name(emp_key) or _clip(proposal.emp_name, 62),
            "pension_option": _clip(proposal.pension_option, 1, "G")[:1],
            "base_cpi": proposal.retirement_cpi,
            "bank_cd": bank_cd,
            "lic_bank_cd": lic_bank_cd,
            "account_no": _clip(proposal.account_no, 20),
            "pension_roll_no": _clip(proposal.pension_roll_no, 22),
            "sex": _clip(per.sex, 1) if per else "",
            "dob": per.birth_dt if per else case.birth_date,
            "desig_cd": adm.desig_cd if adm else None,
            "emp_ret_dt": case.retirement_date,
            "app_class": fin.emp_class if fin else None,
            "date_commutation": comm.commutation_dt if comm and not defer_commutation else None,
            "date_created": today,
            "created_by": user_code,
        },
    )

    return {
        "fmpen_id": fmpen_id,
        "bill_no": "",
        "fin_year": fin_yr,
        "pension_month": pension_month,
        "pension_year": pension_year,
        "original_fpension_amt": float(original_pension),
        "payable_pension": float(payable_pension),
        "commutation_amount": float(summary.commutation_amount or 0),
        "gratuity_amount": float(gratuity),
        "emp_cd": emp_key,
        "ca_number": ca_number,
    }
