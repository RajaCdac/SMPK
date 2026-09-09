"""
FI_PN_COMUTATION_GENERATION.fmb — separate commutation generation (SEPCOM).

Step 2 of Oracle separate commutation:
  1. FI_PN_MH_APPLICATION.fmb — application entry
  2. FI_PN_COMUTATION_GENERATION.fmb — PLEASE_CALCULATE_COMM_AMT + PLEASE_GENERATE_COM_BILL
  3. FI_PN_TH_Commutation_Bill_Gen.fmb — FPROC_BILL_GENERATE_COM → PPC bill
  4. SEP_COMM_REP1.fmb — SEP_COMM_REP report
"""

from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from master_data.models import FiXxXxMDFinCtrl
from master_data.services.erndedn_map_service import MAP_COMMUTATION, resolve_earndedn_cd

from ..models import CommutationApplication, PensionCase, PensionProposal, PensionSummary
from ..oracle_mirror import FiPnMhApplication, FiPnMhPensioner, FiPnTdSepcom, FiPnThSepcom
from ..pension_calculation import reload_pension_case_from_db
from .commutation_rate_service import CommutationRateError, compute_commutation_for_employee
from .pension_bill_service import (
    PensionBillError,
    _clip,
    _dec,
    _resolve_fin_year_for_month,
    _user_code,
)


class SepcomGenerationError(PensionBillError):
    pass


DOC_ABV_SEP = "SEP"
COM_PROC_TAG = "C"


def _format_sepcom_id(bill_month, bill_year, serial):
    return f"SEP/{int(bill_month):02d}/{int(bill_year)}/{int(serial)}"


def _allocate_sepcom_serial(fin_yr, bill_month, bill_year):
    try:
        ctrl = FiXxXxMDFinCtrl.objects.select_for_update().get(
            fin_yr=fin_yr,
            doc_abv=DOC_ABV_SEP,
        )
        serial = int(ctrl.l_trn_no or 0) + 1
        ctrl.l_trn_no = serial
        ctrl.save(update_fields=["l_trn_no"])
        return serial
    except FiXxXxMDFinCtrl.DoesNotExist:
        prefix = f"SEP/{int(bill_month):02d}/{int(bill_year)}/"
        max_serial = 0
        for sepcom_id in FiPnThSepcom.objects.filter(
            sepcom_id__startswith=prefix
        ).values_list("sepcom_id", flat=True):
            parts = str(sepcom_id).split("/")
            if len(parts) == 4:
                try:
                    max_serial = max(max_serial, int(parts[3]))
                except ValueError:
                    continue
        return max_serial + 1


def _emp_cd_variants(emp_cd):
    emp_key = _clip(emp_cd, 5)
    variants = {emp_key}
    if emp_key.isdigit():
        variants.add(str(int(emp_key)))
        variants.add(str(int(emp_key)).zfill(5))
    return [v for v in variants if v]


def _get_comm_app(emp_cd):
    variants = _emp_cd_variants(emp_cd)
    if not variants:
        return None
    return CommutationApplication.objects.filter(emp_cd__in=variants).first()


def _period_from_ref(ref, start_mnth=None, fallback_year=None):
    if ref:
        return int(ref.month), int(ref.year)
    month = int(start_mnth or 1)
    year = int(fallback_year or timezone.localdate().year)
    return month, year


def _commutation_period(comm_app):
    ref = comm_app.commutation_dt or comm_app.appcn_dt
    fallback_year = None
    if comm_app.appcn_dt:
        fallback_year = comm_app.appcn_dt.year
    return _period_from_ref(ref, comm_app.comm_start_mnth, fallback_year)


def _oracle_application(emp_cd):
    variants = _emp_cd_variants(emp_cd)
    if not variants:
        return None
    return (
        FiPnMhApplication.objects.filter(emp_cd__in=variants)
        .order_by("-appcn_dt", "-appcn_no")
        .first()
    )


def _oracle_commutation_period(emp_cd):
    app = _oracle_application(emp_cd)
    if not app:
        return None
    ref = app.commutation_date or app.appcn_dt
    fallback_year = app.appcn_dt.year if app.appcn_dt else None
    return _period_from_ref(ref, app.comm_start_mnth, fallback_year)


def _resolve_bank_cd(comm_app, proposal):
    bank = _clip(comm_app.bank_cd, 6)
    if bank:
        return bank
    if proposal and proposal.bank_cd:
        return _clip(proposal.bank_cd, 6)
    return ""


def calculate_commutation_amount(case, comm_app):
    """PLEASE_CALCULATE_COMM_AMT — lump sum from pension × % × age rate table."""
    from .salout_transfer_service import resolve_emoluments_basic

    try:
        summary = case.summary
    except PensionSummary.DoesNotExist as exc:
        raise SepcomGenerationError(
            "Pension amounts not calculated. Run amount calculation first."
        ) from exc

    pension = float(summary.pension_amount or 0)
    salout_basic, source = resolve_emoluments_basic(
        comm_app.emp_cd,
        fallback_last_basic=float(case.last_basic),
    )
    if source == "salout" and salout_basic > 0:
        from ..pension_calculation import (
            calculate_normal_pension,
            get_pension_option_for_employee,
        )

        option = get_pension_option_for_employee(comm_app.emp_cd)
        tqs_years = int(summary.tqs_years or 0)
        salout_pension = calculate_normal_pension(
            emoluments=salout_basic,
            tqs_years=tqs_years,
            pension_option=option,
        )
        if abs(salout_pension - pension) > 1:
            pension = salout_pension

    if pension <= 0:
        raise SepcomGenerationError("Pension amount is missing in pension summary.")

    pct = float(
        comm_app.commutation_per
        if comm_app.commutation_per is not None
        else case.commutation_percent or 0
    )
    if pct <= 0:
        raise SepcomGenerationError("Commutation % is not set on the application.")

    try:
        amounts = compute_commutation_for_employee(
            comm_app.emp_cd,
            pension_amount=pension,
            commutation_percent=pct,
            comm_app=comm_app,
            case=case,
            use_highest_side_round=False,
        )
    except CommutationRateError as exc:
        raise SepcomGenerationError(str(exc)) from exc

    return amounts


def resolve_commutation_amounts_for_sepcom(header):
    """Current commutation figures from pension summary + salout (not stale SEPCOM)."""
    comm = _get_comm_app(header.emp_cd)
    if not comm:
        return None
    case = reload_pension_case_from_db(comm.emp_cd)
    if not case:
        return None
    try:
        return calculate_commutation_amount(case, comm)
    except SepcomGenerationError:
        return None


def refresh_sepcom_commutation_amounts(header, *, user=None):
    """
    Align FI_PN_TH/TD_SEPCOM with current pension when Oracle-synced rows are stale.
  """
    amounts = resolve_commutation_amounts_for_sepcom(header)
    if not amounts:
        return None

    lump = _dec(amounts["lump_sum"])
    stored = _dec(header.original_com_amt or 0)
    lines = list(
        FiPnTdSepcom.objects.filter(sepcom_id=header.sepcom_id).order_by(
            "earn_dedn_type", "earn_dedn_cd"
        )
    )
    line_total = sum(_dec(line.amount) for line in lines)
    if (
        abs(float(stored) - float(lump)) <= 1
        and lines
        and abs(float(line_total) - float(lump)) <= 1
    ):
        return amounts

    user_code = _user_code(user)
    today = timezone.localdate()
    header.original_com_amt = lump
    header.date_modified = today
    header.modified_by = user_code
    header.save(update_fields=["original_com_amt", "date_modified", "modified_by"])

    comm_cd = resolve_earndedn_cd(MAP_COMMUTATION, "E") or "203"
    lines = list(
        FiPnTdSepcom.objects.filter(sepcom_id=header.sepcom_id).order_by(
            "earn_dedn_type", "earn_dedn_cd"
        )
    )
    if lines:
        for line in lines:
            line.amount = lump
            line.original_amt = lump
            line.date_modified = today
            line.modified_by = user_code
            line.save(update_fields=["amount", "original_amt", "date_modified", "modified_by"])
    else:
        FiPnTdSepcom.objects.create(
            earn_dedn_type="E",
            earn_dedn_cd=comm_cd,
            amount=lump,
            date_created=today,
            created_by=user_code,
            sepcom_id=header.sepcom_id,
            emp_cd=_clip(header.emp_cd, 5),
            original_amt=lump,
            arrear_amt=Decimal("0"),
        )

    comm = _get_comm_app(header.emp_cd)
    if comm:
        _sync_mirror_commutation_amt(comm, amounts["lump_sum"], user_code, today)
        _update_pensioner_commuted_portion(
            header.emp_cd, amounts["monthly_commuted"], user_code, today
        )

    return amounts


def get_sepcom_status(emp_cd):
    comm = _get_comm_app(emp_cd)
    oracle_period = _oracle_commutation_period(emp_cd)
    if not comm:
        cm, cy = oracle_period or (1, timezone.localdate().year)
        return {
            "has_commutation_application": False,
            "impl_fpen_combill": "",
            "sepcom_month": cm,
            "sepcom_year": cy,
            "sepcom_generated": False,
            "sepcom_id": "",
            "bill_no": "",
            "original_com_amt": None,
            "ready_for_sepcom_generation": False,
            "block_reason": "Save commutation application first.",
        }

    cm, cy = _commutation_period(comm)
    header = (
        FiPnThSepcom.objects.filter(
            emp_cd=_clip(emp_cd, 5),
            sepcom_month=cm,
            sepcom_yr=cy,
            com_proc_tag=COM_PROC_TAG,
        )
        .order_by("-date_created")
        .first()
    )

    ready, reason = _can_generate_sepcom(comm)
    return {
        "has_commutation_application": True,
        "impl_fpen_combill": comm.impl_fpen_combill or "",
        "sepcom_month": cm,
        "sepcom_year": cy,
        "sepcom_generated": bool(header),
        "sepcom_id": header.sepcom_id if header else "",
        "bill_no": (header.bill_no if header else "") or comm.bill_no or "",
        "original_com_amt": (
            float(
                (resolve_commutation_amounts_for_sepcom(header) or {}).get("lump_sum")
                or header.original_com_amt
            )
            if header
            else None
        ),
        "ready_for_sepcom_generation": ready,
        "block_reason": reason,
    }


def _can_generate_sepcom(comm_app):
    impl = (comm_app.impl_fpen_combill or "").strip().upper()
    if impl != "COM":
        return False, "To Be Implemented from must be Separate Commutation (COM)."

    cm, cy = _commutation_period(comm_app)
    existing = FiPnThSepcom.objects.filter(
        emp_cd=_clip(comm_app.emp_cd, 5),
        sepcom_month=cm,
        sepcom_yr=cy,
        com_proc_tag=COM_PROC_TAG,
    ).first()
    if existing:
        if str(existing.bill_no or "").strip():
            return False, f"Already billed on {existing.bill_no}."
        return False, f"SEPCOM already generated ({existing.sepcom_id}). Delete to regenerate."

    case = reload_pension_case_from_db(comm_app.emp_cd)
    if not case:
        return False, "Pension case not found."

    try:
        calculate_commutation_amount(case, comm_app)
    except SepcomGenerationError as exc:
        return False, str(exc)

    if not _resolve_bank_cd(
        comm_app, PensionProposal.objects.filter(emp_cd=comm_app.emp_cd).first()
    ):
        return False, "Bank code is missing on commutation application."

    return True, ""


def _sync_mirror_commutation_amt(comm_app, lump_sum, user_code, today):
    qs = FiPnMhApplication.objects.filter(emp_cd=_clip(comm_app.emp_cd, 5))
    if comm_app.appcn_no:
        qs = qs.filter(appcn_no=str(comm_app.appcn_no))
    mirror = qs.order_by("-appcn_dt").first()
    if mirror:
        mirror.commutation_amt = _dec(lump_sum)
        mirror.date_modified = today
        mirror.modified_by = user_code
        mirror.save(update_fields=["commutation_amt", "date_modified", "modified_by"])


def _update_pensioner_commuted_portion(emp_cd, monthly_commuted, user_code, today):
    pensioner = FiPnMhPensioner.objects.filter(emp_cd=_clip(emp_cd, 5)).first()
    if not pensioner:
        return
    pensioner.commuted_portion = _dec(monthly_commuted)
    pensioner.date_modified = today
    pensioner.modified_by = user_code
    pensioner.save(update_fields=["commuted_portion", "date_modified", "modified_by"])


@transaction.atomic
def generate_sepcom_for_employees(
    *,
    bill_month,
    bill_year,
    emp_cds,
    user=None,
):
    """
    PLEASE_GENERATE_COM_BILL — create FI_PN_TH_SEPCOM + FI_PN_TD_SEPCOM rows.
    """
    if not emp_cds:
        raise SepcomGenerationError("Select at least one employee.")

    user_code = _user_code(user)
    today = timezone.localdate()

    created = []
    for raw in emp_cds:
        comm = _get_comm_app(raw)
        if not comm:
            raise SepcomGenerationError(f"Commutation application not found for {raw}.")

        ready, reason = _can_generate_sepcom(comm)
        if not ready:
            raise SepcomGenerationError(f"{comm.emp_cd}: {reason}")

        # Always post against commutation date (e.g. Aug 2004), not today's bill month.
        cm, cy = _commutation_period(comm)
        fin_yr = _resolve_fin_year_for_month(cm, cy)

        case = reload_pension_case_from_db(comm.emp_cd)
        amounts = calculate_commutation_amount(case, comm)
        proposal = PensionProposal.objects.filter(emp_cd=comm.emp_cd).first()
        bank_cd = _resolve_bank_cd(comm, proposal)
        ca_no = _clip(
            comm.ca_no or (proposal.ca_number if proposal else ""),
            22,
        )

        serial = _allocate_sepcom_serial(fin_yr, cm, cy)
        sepcom_id = _format_sepcom_id(cm, cy, serial)
        lump = _dec(amounts["lump_sum"])

        FiPnThSepcom.objects.create(
            sepcom_id=sepcom_id,
            sepcom_month=int(cm),
            sepcom_yr=int(cy),
            ca_no=ca_no,
            original_com_amt=lump,
            bill_no="",
            emp_cd=_clip(comm.emp_cd, 5),
            nomin_type="",
            com_proc_tag=COM_PROC_TAG,
            nomin_srl_no=0,
            date_created=today,
            created_by=user_code,
            bank_cd=bank_cd,
            pen_dedn_amt=Decimal("0"),
            appcn_no=str(comm.appcn_no or ""),
            appcn_dt=comm.appcn_dt,
        )

        comm_cd = resolve_earndedn_cd(MAP_COMMUTATION, "E") or "203"
        FiPnTdSepcom.objects.create(
            earn_dedn_type="E",
            earn_dedn_cd=comm_cd,
            amount=lump,
            date_created=today,
            created_by=user_code,
            sepcom_id=sepcom_id,
            emp_cd=_clip(comm.emp_cd, 5),
            original_amt=lump,
            arrear_amt=Decimal("0"),
        )

        _update_pensioner_commuted_portion(
            comm.emp_cd, amounts["monthly_commuted"], user_code, today
        )
        _sync_mirror_commutation_amt(comm, amounts["lump_sum"], user_code, today)

        created.append(
            {
                "sepcom_id": sepcom_id,
                "emp_cd": comm.emp_cd,
                "original_com_amt": float(lump),
                "commutation_percent": amounts["commutation_percent"],
                "monthly_commuted": amounts["monthly_commuted"],
                "sepcom_month": int(cm),
                "sepcom_year": int(cy),
            }
        )

    last = created[-1]
    return {
        "sepcom_records": created,
        "bill_month": last["sepcom_month"],
        "bill_year": last["sepcom_year"],
        "fin_year": _resolve_fin_year_for_month(last["sepcom_month"], last["sepcom_year"]),
    }
