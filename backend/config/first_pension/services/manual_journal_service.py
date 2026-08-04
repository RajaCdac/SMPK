"""
Manual journal voucher entry — port of FI_PN_T_H_JRVOUCHR_E.fmb (BLKBT_ENTRY + BLKBT_D_JV).
MySQL writes only; Oracle cash/billpass posting is not replicated.
"""

from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from ..oracle_mirror import FiPnTdJv, FiPnThJv, FiPnThPensionBill
from .journal_narration_service import build_default_journal_narration
from .voucher_generation_service import (
    VoucherGenerationError,
    _allocate_pnjv_serial,
    _clip,
    _dec,
    _parse_optional_date,
    _resolve_fin_year_for_jv_month,
    _user_code,
)

TRAN_TYPE_MANUAL = "PNJV/N"


class ManualJournalError(VoucherGenerationError):
    pass


def _format_manual_voucher_no(fin_yr, mth, serial):
    return f"PNJV/N/{int(fin_yr)}/{int(mth)}/{int(serial):05d}"


def _empty_line():
    return {
        "sl_no": 0,
        "zonal_cd": 0,
        "aloc_cd1": "",
        "aloc_cd2": "",
        "aloc_cd3": "",
        "dr_cr_flag": "D",
        "amount": 0,
        "remarks": "",
    }


def _serialize_line(row):
    return {
        "sl_no": row.sl_no,
        "zonal_cd": row.zonal_cd,
        "aloc_cd1": row.aloc_cd1,
        "aloc_cd2": row.aloc_cd2 or "",
        "aloc_cd3": row.aloc_cd3 or "",
        "dr_cr_flag": row.dr_cr_flag,
        "amount": float(row.amount or 0),
        "remarks": row.remarks or "",
    }


def _normalize_lines(raw_lines):
    lines = []
    for index, raw in enumerate(raw_lines or [], start=1):
        zonal = raw.get("zonal_cd")
        aloc1 = _clip(raw.get("aloc_cd1"), 4)
        amount = _dec(raw.get("amount"))
        dr_cr = _clip(raw.get("dr_cr_flag"), 1, "D").upper()
        if dr_cr not in ("D", "C"):
            raise ManualJournalError(f"Line {index}: Dr/Cr must be D or C.")
        if not zonal and not aloc1 and not amount:
            continue
        if not zonal or not aloc1:
            raise ManualJournalError(
                f"Line {index}: zonal_cd and aloc_cd1 are required."
            )
        if amount <= 0:
            raise ManualJournalError(f"Line {index}: amount must be greater than zero.")
        lines.append(
            {
                "sl_no": index,
                "zonal_cd": int(zonal),
                "aloc_cd1": aloc1,
                "aloc_cd2": _clip(raw.get("aloc_cd2"), 4),
                "aloc_cd3": _clip(raw.get("aloc_cd3"), 7),
                "dr_cr_flag": dr_cr,
                "amount": amount,
                "remarks": _clip(raw.get("remarks"), 60),
            }
        )
    if not lines:
        raise ManualJournalError("At least one journal line is required.")
    return lines


def compute_journal_totals(lines):
    """FPROC_TOTAMT / BLK_CONTROL debit and credit summary."""
    debit = credit = Decimal("0")
    for line in lines:
        amt = _dec(line.get("amount") if isinstance(line, dict) else line.amount)
        flag = (
            line.get("dr_cr_flag")
            if isinstance(line, dict)
            else line.dr_cr_flag
        )
        if flag == "D":
            debit += amt
        elif flag == "C":
            credit += amt
    return debit, credit


def _assert_balanced(lines):
    """FPROC_DEBIT_CREDIT_CHECK."""
    debit, credit = compute_journal_totals(lines)
    if debit != credit:
        raise ManualJournalError(
            "Debit and credit amounts must be the same. "
            f"Debit={debit}, Credit={credit}."
        )
    return debit


def get_journal_summary(*, voucher_no):
    voucher_no = _clip(voucher_no, 25)
    header = FiPnThJv.objects.filter(voucher_no=voucher_no).first()
    if not header:
        raise ManualJournalError(f"Journal voucher {voucher_no} not found.")

    detail_qs = FiPnTdJv.objects.filter(voucher_no=voucher_no).order_by("sl_no")
    lines = [_serialize_line(row) for row in detail_qs]
    debit, credit = compute_journal_totals(lines)

    return {
        "voucher_no": header.voucher_no,
        "voucher_dt": header.voucher_dt.isoformat() if header.voucher_dt else "",
        "yr": header.yr,
        "mth": header.mth,
        "tran_type": header.tran_type or "",
        "ref_no": header.ref_no or "",
        "ref_dt": header.ref_dt.isoformat() if header.ref_dt else "",
        "narration": header.narration or "",
        "tot_amt": float(header.tot_amt or debit),
        "lines": lines,
        "debit_amt": float(debit),
        "credit_amt": float(credit),
        "balanced": debit == credit,
        "line_count": len(lines),
    }


def find_journal_for_ref(*, ref_no):
    ref_no = _clip(ref_no, 25)
    if not ref_no:
        return None
    header = (
        FiPnThJv.objects.filter(ref_no=ref_no)
        .order_by("-voucher_dt", "-voucher_no")
        .first()
    )
    if not header:
        return None
    return get_journal_summary(voucher_no=header.voucher_no)


def list_journals(*, ref_no="", yr=None, mth=None, limit=50):
    qs = FiPnThJv.objects.all().order_by("-voucher_dt", "-voucher_no")
    if ref_no:
        qs = qs.filter(ref_no=_clip(ref_no, 25))
    if yr is not None:
        qs = qs.filter(yr=int(yr))
    if mth is not None:
        qs = qs.filter(mth=int(mth))
    qs = qs[: max(1, min(int(limit or 50), 200))]

    results = []
    for header in qs:
        lines = FiPnTdJv.objects.filter(voucher_no=header.voucher_no)
        debit, credit = compute_journal_totals(lines)
        results.append(
            {
                "voucher_no": header.voucher_no,
                "voucher_dt": header.voucher_dt.isoformat()
                if header.voucher_dt
                else "",
                "tran_type": header.tran_type or "",
                "ref_no": header.ref_no or "",
                "narration": (header.narration or "")[:120],
                "tot_amt": float(header.tot_amt or debit),
                "debit_amt": float(debit),
                "credit_amt": float(credit),
                "yr": header.yr,
                "mth": header.mth,
            }
        )
    return results


@transaction.atomic
def save_manual_journal(
    *,
    voucher_no="",
    voucher_dt=None,
    jv_month,
    jv_year,
    ref_no="",
    ref_dt=None,
    narration="",
    tran_type=TRAN_TYPE_MANUAL,
    lines,
    user=None,
):
    """
    Create or replace a manual journal voucher (FProc_TLB_Save without Oracle billpass).
    """
    jv_month = int(jv_month)
    jv_year = int(jv_year)
    fin_yr = _resolve_fin_year_for_jv_month(jv_month, jv_year)
    user_code = _user_code(user)
    today = timezone.localdate()
    voucher_dt = _parse_optional_date(voucher_dt) or today
    ref_dt = _parse_optional_date(ref_dt)
    normalized = _normalize_lines(lines)
    total_dr = _assert_balanced(normalized)

    existing_no = _clip(voucher_no, 25)
    if existing_no:
        if not FiPnThJv.objects.filter(voucher_no=existing_no).exists():
            raise ManualJournalError(f"Voucher {existing_no} not found for update.")
        out_voucher_no = existing_no
        FiPnTdJv.objects.filter(voucher_no=out_voucher_no).delete()
    else:
        serial = _allocate_pnjv_serial(fin_yr, user_code, today)
        out_voucher_no = _format_manual_voucher_no(fin_yr, jv_month, serial)

    ref_no = _clip(ref_no, 25)
    detail_rows = []
    for sl_no, line in enumerate(normalized, start=1):
        detail_rows.append(
            FiPnTdJv(
                voucher_no=out_voucher_no,
                voucher_dt=voucher_dt,
                yr=fin_yr,
                mth=jv_month,
                sl_no=sl_no,
                zonal_cd=line["zonal_cd"],
                aloc_cd1=line["aloc_cd1"],
                aloc_cd2=line["aloc_cd2"],
                aloc_cd3=line["aloc_cd3"],
                dr_cr_flag=line["dr_cr_flag"],
                type_cd=1,
                amount=line["amount"],
                ref=ref_no,
                remarks=line["remarks"],
                created_by=user_code,
                created_on=today,
            )
        )

    if not str(narration or "").strip():
        narration = build_default_journal_narration(emp_cd=None, bill_no=ref_no or None)

    FiPnThJv.objects.update_or_create(
        voucher_no=out_voucher_no,
        defaults={
            "yr": fin_yr,
            "mth": jv_month,
            "voucher_dt": voucher_dt,
            "tran_type": _clip(tran_type, 10, TRAN_TYPE_MANUAL),
            "ref_no": ref_no,
            "ref_dt": ref_dt,
            "narration": _clip(narration, 500),
            "tot_amt": total_dr,
            "created_by": user_code,
            "created_on": today,
            "voucher_for": "P",
        },
    )
    FiPnTdJv.objects.bulk_create(detail_rows)

    if ref_no:
        bill = FiPnThPensionBill.objects.filter(bill_no=ref_no).first()
        if bill:
            bill.voucher_no = out_voucher_no
            bill.date_modified = today
            bill.modified_by = user_code
            bill.save(update_fields=["voucher_no", "date_modified", "modified_by"])

    debit, credit = compute_journal_totals(normalized)
    return {
        "voucher_no": out_voucher_no,
        "voucher_dt": voucher_dt.isoformat(),
        "fin_yr": fin_yr,
        "jv_month": jv_month,
        "jv_year": jv_year,
        "ref_no": ref_no,
        "tot_amt": float(total_dr),
        "debit_amt": float(debit),
        "credit_amt": float(credit),
        "line_count": len(detail_rows),
        "tran_type": _clip(tran_type, 10, TRAN_TYPE_MANUAL),
    }


def blank_manual_journal_template(*, ref_no="", jv_month=None, jv_year=None, emp_cd=None):
    today = timezone.localdate()
    month = int(jv_month or today.month)
    year = int(jv_year or today.year)
    narration = build_default_journal_narration(emp_cd=emp_cd, bill_no=ref_no or None)
    return {
        "voucher_no": "",
        "voucher_dt": today.isoformat(),
        "jv_month": month,
        "jv_year": year,
        "tran_type": TRAN_TYPE_MANUAL,
        "ref_no": ref_no or "",
        "ref_dt": "",
        "narration": narration,
        "default_narration": narration,
        "lines": [_empty_line(), _empty_line()],
        "debit_amt": 0,
        "credit_amt": 0,
    }
