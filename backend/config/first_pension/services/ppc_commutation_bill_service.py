"""
FI_PN_TH_Commutation_Bill_Gen.fmb — PPC bill from SEPCOM rows (step 3).

Reads FI_PN_TH_SEPCOM / FI_PN_TD_SEPCOM (COM_PROC_TAG='C'), creates
FI_PN_TH_PENSION_BILL (BILL_TYPE='C', BILL_NO like PPC/...), updates
SEPCOM.BILL_NO and CommutationApplication.bill_no / Oracle IMPL_BILL_NO.
"""

from collections import defaultdict
from decimal import Decimal

from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from master_data.models import FiXxXxMDFinCtrl, FiPnMhEarndedn

from ..models import CommutationApplication, PensionProposal
from ..oracle_mirror import (
    FiPnMhApplication,
    FiPnMhPmthsetup,
    FiPnTdSepcom,
    FiPnThPensionBill,
    FiPnThSepcom,
)
from .pension_bill_service import (
    PensionBillError,
    _clip,
    _dec,
    _employee_name,
    _resolve_fin_year_for_month,
    _user_code,
    assert_month_not_closed,
)
from .sepcom_commutation_generation_service import (
    COM_PROC_TAG,
    _get_comm_app,
    refresh_sepcom_commutation_amounts,
    resolve_commutation_amounts_for_sepcom,
)


DOC_ABV_PPC = "PPC"
BILL_TYPE_COMMUTATION = "C"


def _format_ppc_bill_no(bill_month, bill_year, serial):
    return f"PPC/{int(bill_month):02d}/{int(bill_year)}/{int(serial)}"


def _allocate_ppc_serial(fin_yr, bill_month, bill_year):
    try:
        ctrl = FiXxXxMDFinCtrl.objects.select_for_update().get(
            fin_yr=fin_yr,
            doc_abv=DOC_ABV_PPC,
        )
        serial = int(ctrl.l_trn_no or 0) + 1
        ctrl.l_trn_no = serial
        ctrl.save(update_fields=["l_trn_no"])
        return serial
    except FiXxXxMDFinCtrl.DoesNotExist:
        prefix = f"PPC/{int(bill_month):02d}/{int(bill_year)}/"
        max_serial = 0
        for bill_no in FiPnThPensionBill.objects.filter(
            bill_no__startswith=prefix
        ).values_list("bill_no", flat=True):
            parts = str(bill_no).split("/")
            if len(parts) == 4:
                try:
                    max_serial = max(max_serial, int(parts[3]))
                except ValueError:
                    continue
        return max_serial + 1


def _ensure_month_setup(bill_month, bill_year, user_code, today):
    setup, _ = FiPnMhPmthsetup.objects.get_or_create(
        bill_type=BILL_TYPE_COMMUTATION,
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


def _sum_sepcom_earn_dedn(header):
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
    lines = FiPnTdSepcom.objects.filter(sepcom_id=header.sepcom_id)
    earn = Decimal("0")
    dedn = Decimal("0")
    for line in lines:
        amt = _dec(line.amount)
        if line.earn_dedn_type == "E" or line.earn_dedn_cd in earn_codes:
            earn += amt
        elif line.earn_dedn_type == "D" or line.earn_dedn_cd in dedn_codes:
            dedn += amt
        else:
            earn += amt
    return earn, dedn


def _posted_bill_no(header, comm=None):
    comm = comm or _get_comm_app(header.emp_cd if header else "")
    if header and str(header.bill_no or "").strip():
        return str(header.bill_no).strip()
    if comm and str(comm.bill_no or "").strip():
        return str(comm.bill_no).strip()
    return ""


def _sync_sepcom_bill_no(header, bill_no, *, user_code, today):
    if not header or not bill_no or str(header.bill_no or "").strip():
        if header and bill_no and not str(header.bill_no or "").strip():
            header.bill_no = _clip(bill_no, 22)
            header.date_modified = today
            header.modified_by = user_code
            header.save(update_fields=["bill_no", "date_modified", "modified_by"])
        return
    if str(header.bill_no or "").strip() != str(bill_no).strip():
        header.bill_no = _clip(bill_no, 22)
        header.date_modified = today
        header.modified_by = user_code
        header.save(update_fields=["bill_no", "date_modified", "modified_by"])


def _commutation_display_amounts(header, *, refresh=False, user=None):
    if refresh:
        amounts = refresh_sepcom_commutation_amounts(header, user=user)
    else:
        amounts = resolve_commutation_amounts_for_sepcom(header)
    earn, dedn = _sum_sepcom_earn_dedn(header)
    if amounts:
        lump = float(amounts["lump_sum"])
        return {
            "commutation_lump_sum": lump,
            "gross_earn": lump,
            "gross_dedn": float(dedn),
            "commutation_percent": float(amounts["commutation_percent"]),
            "pension_amount": float(amounts["pension_amount"]),
            "amounts": amounts,
        }
    return {
        "commutation_lump_sum": float(header.original_com_amt or earn),
        "gross_earn": float(earn),
        "gross_dedn": float(dedn),
        "commutation_percent": None,
        "pension_amount": None,
        "amounts": None,
    }


def _validate_ppc_candidate(header, *, bill_month=None, bill_year=None):
    if not header:
        return False, "SEPCOM not generated. Run commutation generation first."

    comm = _get_comm_app(header.emp_cd)
    posted_bill = _posted_bill_no(header, comm)
    if posted_bill:
        return False, f"Already billed on {posted_bill}."

    if bill_month is not None and int(header.sepcom_month) != int(bill_month):
        return False, (
            f"SEPCOM month is {int(header.sepcom_month):02d}, "
            f"not {int(bill_month):02d}."
        )
    if bill_year is not None and int(header.sepcom_yr) != int(bill_year):
        return False, (
            f"SEPCOM year is {int(header.sepcom_yr)}, not {int(bill_year)}."
        )

    if not str(header.bank_cd or "").strip():
        return False, "Bank code missing on SEPCOM header."

    earn, _ = _sum_sepcom_earn_dedn(header)
    if earn <= 0:
        return False, "SEPCOM has no commutation earning lines."

    return True, ""


def serialize_ppc_candidate(header, *, bill_month=None, bill_year=None, refresh=False, user=None):
    comm = _get_comm_app(header.emp_cd)
    posted_bill = _posted_bill_no(header, comm)
    ready, block_reason = _validate_ppc_candidate(
        header, bill_month=bill_month, bill_year=bill_year
    )
    display = _commutation_display_amounts(
        header, refresh=refresh and not posted_bill, user=user
    )
    comm_pct = display["commutation_percent"]
    if comm_pct is None and comm and comm.commutation_per is not None:
        comm_pct = float(comm.commutation_per)
    return {
        "emp_cd": header.emp_cd,
        "emp_name": _employee_name(header.emp_cd),
        "sepcom_id": header.sepcom_id,
        "appcn_no": header.appcn_no or (str(comm.appcn_no) if comm else ""),
        "ca_no": header.ca_no,
        "bank_cd": header.bank_cd,
        "commutation_lump_sum": display["commutation_lump_sum"],
        "commutation_per": comm_pct,
        "gross_earn": display["gross_earn"],
        "gross_dedn": display["gross_dedn"],
        "sepcom_month": header.sepcom_month,
        "sepcom_year": header.sepcom_yr,
        "ref_no": comm.ref_no if comm else "",
        "bill_no": posted_bill,
        "ready_for_bill": ready,
        "block_reason": block_reason,
        "stored_sepcom_amt": float(header.original_com_amt or 0),
    }


def list_ppc_candidates(*, bill_month, bill_year, emp_cd=None, user=None):
    qs = FiPnThSepcom.objects.filter(
        com_proc_tag=COM_PROC_TAG,
    ).filter(Q(bill_no="") | Q(bill_no__isnull=True))

    if emp_cd:
        qs = qs.filter(emp_cd=_clip(emp_cd, 5))

    rows = []
    for header in qs.order_by("bank_cd", "emp_cd"):
        comm = _get_comm_app(header.emp_cd)
        if _posted_bill_no(header, comm):
            continue
        candidate = serialize_ppc_candidate(
            header,
            bill_month=bill_month,
            bill_year=bill_year,
            refresh=True,
            user=user,
        )
        if emp_cd:
            rows.append(candidate)
        elif candidate["ready_for_bill"]:
            rows.append(candidate)
    return rows


def list_ppc_bills(*, bill_month, bill_year):
    rows = FiPnThPensionBill.objects.filter(
        bill_month=int(bill_month),
        bill_yr=int(bill_year),
        bill_type=BILL_TYPE_COMMUTATION,
        bill_no__startswith="PPC",
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
        }
        for b in rows
    ]


def get_ppc_employee_status(emp_cd):
    comm = _get_comm_app(emp_cd)
    header = None
    if comm:
        header = (
            FiPnThSepcom.objects.filter(emp_cd=_clip(emp_cd, 5))
            .order_by("-sepcom_yr", "-sepcom_month")
            .first()
        )

    if not comm and not header:
        return {
            "has_commutation_application": False,
            "sepcom_generated": False,
            "sepcom_id": "",
            "bill_no": "",
            "ready_for_ppc": False,
            "ppc_bill": None,
        }

    bill_no = _posted_bill_no(header, comm)

    bill = FiPnThPensionBill.objects.filter(bill_no=bill_no).first() if bill_no else None
    ready, block_reason = (
        _validate_ppc_candidate(header) if header else (False, "SEPCOM not generated.")
    )
    if bill_no:
        ready = False
        if not block_reason:
            block_reason = f"Already billed on {bill_no}."

    if header and bill_no and not str(header.bill_no or "").strip():
        _sync_sepcom_bill_no(
            header,
            bill_no,
            user_code=_user_code(None),
            today=timezone.localdate(),
        )

    return {
        "has_commutation_application": bool(comm),
        "sepcom_generated": bool(header),
        "sepcom_id": header.sepcom_id if header else "",
        "impl_fpen_combill": comm.impl_fpen_combill if comm else "",
        "appcn_no": comm.appcn_no if comm else "",
        "ref_no": comm.ref_no if comm else "",
        "bill_no": bill_no,
        "sepcom_month": header.sepcom_month if header else None,
        "sepcom_year": header.sepcom_yr if header else None,
        "ready_for_ppc": ready,
        "block_reason": block_reason,
        "ppc_bill": (
            {
                "bill_no": bill.bill_no,
                "total_amt_earned": float(bill.total_amt_earned or 0),
                "bank_cd": bill.bank_cd or "",
            }
            if bill
            else None
        ),
    }


def _sync_bill_to_application(comm, bill_no, user_code, today):
    if not comm:
        return
    comm.bill_no = _clip(bill_no, 50)
    comm.save(update_fields=["bill_no"])

    qs = FiPnMhApplication.objects.filter(emp_cd=_clip(comm.emp_cd, 5))
    if comm.appcn_no:
        qs = qs.filter(appcn_no=str(comm.appcn_no))
    mirror = qs.order_by("-appcn_dt").first()
    if mirror:
        mirror.impl_bill_no = _clip(bill_no, 22)
        mirror.date_modified = today
        mirror.modified_by = user_code
        mirror.save(update_fields=["impl_bill_no", "date_modified", "modified_by"])


@transaction.atomic
def generate_ppc_bills(
    *,
    bill_month,
    bill_year,
    emp_cds,
    user=None,
    include_same_bank_unselected=False,
):
    if not emp_cds:
        raise PensionBillError(
            "Select at least one pensioner for PPC bill generation."
        )

    assert_month_not_closed(BILL_TYPE_COMMUTATION, bill_month, bill_year)

    user_code = _user_code(user)
    today = timezone.localdate()
    fin_yr = _resolve_fin_year_for_month(bill_month, bill_year)

    selected_headers = []
    for raw in emp_cds:
        header = (
            FiPnThSepcom.objects.filter(
                emp_cd=_clip(raw, 5),
                sepcom_month=int(bill_month),
                sepcom_yr=int(bill_year),
                com_proc_tag=COM_PROC_TAG,
            )
            .filter(Q(bill_no="") | Q(bill_no__isnull=True))
            .first()
        )
        if not header:
            raise PensionBillError(
                f"{raw}: SEPCOM not found for {int(bill_month):02d}/{int(bill_year)}."
            )
        ready, reason = _validate_ppc_candidate(
            header, bill_month=bill_month, bill_year=bill_year
        )
        if not ready:
            raise PensionBillError(f"{header.emp_cd}: {reason}")
        refresh_sepcom_commutation_amounts(header, user=user)
        selected_headers.append(header)

    if include_same_bank_unselected:
        bank_codes = {h.bank_cd for h in selected_headers if h.bank_cd}
        extra = FiPnThSepcom.objects.filter(
            com_proc_tag=COM_PROC_TAG,
            sepcom_month=int(bill_month),
            sepcom_yr=int(bill_year),
            bank_cd__in=bank_codes,
        ).filter(Q(bill_no="") | Q(bill_no__isnull=True))
        for header in extra:
            if header in selected_headers:
                continue
            ready, _ = _validate_ppc_candidate(
                header, bill_month=bill_month, bill_year=bill_year
            )
            if ready:
                selected_headers.append(header)

    by_bank = defaultdict(list)
    for header in selected_headers:
        by_bank[header.bank_cd or ""].append(header)

    created_bills = []
    for bank_cd, headers in by_bank.items():
        total_earn = Decimal("0")
        total_dedn = Decimal("0")
        for header in headers:
            earn, dedn = _sum_sepcom_earn_dedn(header)
            total_earn += earn
            total_dedn += dedn

        serial = _allocate_ppc_serial(fin_yr, bill_month, bill_year)
        bill_no = _format_ppc_bill_no(bill_month, bill_year, serial)

        FiPnThPensionBill.objects.create(
            bill_no=bill_no,
            bill_type=BILL_TYPE_COMMUTATION,
            bill_month=int(bill_month),
            bill_yr=int(bill_year),
            bank_cd=_clip(bank_cd, 6),
            total_amt_earned=total_earn,
            total_amt_deducted=total_dedn,
            date_created=today,
            created_by=user_code,
            gen_lic_tag="F",
        )

        for header in headers:
            header.bill_no = bill_no
            header.date_modified = today
            header.modified_by = user_code
            header.save(update_fields=["bill_no", "date_modified", "modified_by"])
            comm = _get_comm_app(header.emp_cd)
            _sync_bill_to_application(comm, bill_no, user_code, today)

        created_bills.append(
            {
                "bill_no": bill_no,
                "bank_cd": bank_cd,
                "total_amt_earned": float(total_earn),
                "total_amt_deducted": float(total_dedn),
                "pensioner_count": len(headers),
                "emp_cds": [h.emp_cd for h in headers],
                "sepcom_ids": [h.sepcom_id for h in headers],
            }
        )

    setup = _ensure_month_setup(bill_month, bill_year, user_code, today)
    setup.bill_process_flg = 1
    setup.date_modified = today
    setup.modified_by = user_code
    setup.save(update_fields=["bill_process_flg", "date_modified", "modified_by"])

    return {
        "bills": created_bills,
        "fin_year": fin_yr,
        "bill_month": int(bill_month),
        "bill_year": int(bill_year),
        "bill_type": BILL_TYPE_COMMUTATION,
    }
