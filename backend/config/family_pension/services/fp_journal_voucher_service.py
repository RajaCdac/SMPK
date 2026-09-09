"""Family pension journal voucher — PFN bills (Oracle FI_PN_T_H_JRVOUCHR_E)."""

from family_pension.services.fp_bill_abstract_report_service import (
    FpBillAbstractReportError,
    _resolve_bill_no,
)
from first_pension.services.journal_summary_report_service import (
    JournalSummaryReportError,
    build_journal_summary_report,
)
from first_pension.services.voucher_generation_service import (
    VoucherGenerationError,
    generate_pfn_voucher,
    get_voucher_status,
    preview_pfn_voucher,
)


class FpJournalVoucherError(Exception):
    pass


def resolve_pfn_bill_no(*, bill_no=None, clmca_id=None, emp_cd=None) -> str:
    try:
        return _resolve_bill_no(bill_no=bill_no, clmca_id=clmca_id, emp_cd=emp_cd)
    except FpBillAbstractReportError as exc:
        raise FpJournalVoucherError(str(exc)) from exc


def fp_voucher_status(*, bill_no=None, clmca_id=None, emp_cd=None):
    bill_key = resolve_pfn_bill_no(
        bill_no=bill_no, clmca_id=clmca_id, emp_cd=emp_cd
    )
    try:
        payload = get_voucher_status(bill_no=bill_key)
    except VoucherGenerationError as exc:
        raise FpJournalVoucherError(str(exc)) from exc
    payload["resolved_bill_no"] = bill_key
    return payload


def fp_voucher_preview(*, bill_no, jv_month, jv_year):
    bill_key = resolve_pfn_bill_no(bill_no=bill_no)
    try:
        return preview_pfn_voucher(
            bill_no=bill_key, jv_month=int(jv_month), jv_year=int(jv_year)
        )
    except VoucherGenerationError as exc:
        raise FpJournalVoucherError(str(exc)) from exc


def fp_voucher_generate(
    *,
    bill_no,
    jv_month,
    jv_year,
    abstract_no="",
    abstract_date=None,
    narration="",
    user=None,
    regenerate=False,
    voucher_no="",
):
    bill_key = resolve_pfn_bill_no(bill_no=bill_no)
    try:
        return generate_pfn_voucher(
            bill_no=bill_key,
            jv_month=int(jv_month),
            jv_year=int(jv_year),
            abstract_no=abstract_no,
            abstract_date=abstract_date,
            narration=narration,
            user=user,
            regenerate=regenerate,
            voucher_no=voucher_no,
        )
    except VoucherGenerationError as exc:
        raise FpJournalVoucherError(str(exc)) from exc


def fp_journal_summary_report(*, yr, mth, ref_no):
    try:
        return build_journal_summary_report(
            yr=int(yr), mth=int(mth), ref_no=ref_no
        )
    except JournalSummaryReportError as exc:
        raise FpJournalVoucherError(str(exc)) from exc
