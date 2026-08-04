from audit.services import log_audit
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from .services.pension_bill_service import (
    PensionBillError,
    build_lic_report,
    close_pension_bill_month,
    generate_pension_bills,
    get_employee_bill_status,
    get_month_setup_status,
    list_bill_candidates,
    list_ppn_bills,
    list_reprocess_candidates,
    reprocess_pension_bills,
)
from .services.proposal_sanction_report_service import (
    ProposalSanctionReportError,
    build_proposal_sanction_report,
)
from .services.first_pension_advice_report_service import (
    FirstPensionAdviceReportError,
    build_first_pension_advice_report,
)
from .services.sepcom_commutation_generation_service import (
    generate_sepcom_for_employees,
    get_sepcom_status,
)
from .services.sep_comm_report_service import (
    build_sep_comm_report,
)
from .services.separate_commutation_bill_report_service import (
    build_separate_commutation_bill_report,
)
from .services.ppc_commutation_bill_service import (
    generate_ppc_bills,
    get_ppc_employee_status,
    list_ppc_bills,
    list_ppc_candidates,
)
from .services.commutation_bill_report_service import (
    CommutationBillReportError,
    build_commutation_bill_report,
)
from .services.bill_abstract_report_service import (
    BillAbstractReportError,
    build_bill_abstract_report,
)
from .services.journal_summary_report_service import (
    JournalSummaryReportError,
    build_journal_summary_report,
    list_bills_for_journal_report,
)
from .services.manual_journal_service import (
    ManualJournalError,
    blank_manual_journal_template,
    find_journal_for_ref,
    get_journal_summary,
    list_journals,
    save_manual_journal,
)
from .services.voucher_generation_service import (
    VoucherGenerationError,
    generate_ppn_voucher,
    get_voucher_status,
    preview_ppn_voucher,
)


class PensionBillStatusAPIView(APIView):
    def get(self, request, emp_code):
        return Response(get_employee_bill_status(emp_code))


class PensionBillCandidatesAPIView(APIView):
    def get(self, request):
        try:
            bill_month = int(request.query_params.get("bill_month", ""))
            bill_year = int(request.query_params.get("bill_year", ""))
        except (TypeError, ValueError):
            return Response(
                {"error": "bill_month and bill_year are required integers."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        bill_type = request.query_params.get("bill_type", "N")
        emp_cd = request.query_params.get("emp_code") or None
        candidates = list_bill_candidates(
            bill_month=bill_month,
            bill_year=bill_year,
            bill_type=bill_type,
            emp_cd=emp_cd,
        )
        return Response(
            {
                "bill_month": bill_month,
                "bill_year": bill_year,
                "bill_type": bill_type,
                "candidates": candidates,
            }
        )


class PensionBillGenerateAPIView(APIView):
    def post(self, request):
        try:
            bill_month = int(request.data.get("bill_month"))
            bill_year = int(request.data.get("bill_year"))
        except (TypeError, ValueError):
            return Response(
                {"error": "bill_month and bill_year are required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        bill_type = request.data.get("bill_type", "N")
        fmpen_ids = request.data.get("fmpen_ids") or []
        if not fmpen_ids and request.data.get("fmpen_id"):
            fmpen_ids = [request.data.get("fmpen_id")]

        try:
            result = generate_pension_bills(
                bill_month=bill_month,
                bill_year=bill_year,
                bill_type=bill_type,
                fmpen_ids=fmpen_ids,
                user=request.user,
                include_same_bank_unselected=bool(
                    request.data.get("include_same_bank_unselected")
                ),
            )
            log_audit(
                request,
                table_name="FI_PN_TH_PENSION_BILL",
                record_id=",".join(b["bill_no"] for b in result["bills"]),
                action="CREATE",
                old_data=None,
                new_data=result,
                module="FIRST_PENSION",
            )
            return Response(
                {
                    "message": "Pension bill generated successfully.",
                    **result,
                }
            )
        except PensionBillError as exc:
            return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)


class PensionBillMonthStatusAPIView(APIView):
    def get(self, request):
        try:
            bill_month = int(request.query_params.get("bill_month", ""))
            bill_year = int(request.query_params.get("bill_year", ""))
        except (TypeError, ValueError):
            return Response(
                {"error": "bill_month and bill_year are required integers."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        bill_type = request.query_params.get("bill_type", "N")
        return Response(
            get_month_setup_status(bill_type, bill_month, bill_year)
        )


class PensionBillReprocessCandidatesAPIView(APIView):
    def get(self, request):
        try:
            bill_month = int(request.query_params.get("bill_month", ""))
            bill_year = int(request.query_params.get("bill_year", ""))
        except (TypeError, ValueError):
            return Response(
                {"error": "bill_month and bill_year are required integers."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        bill_type = request.query_params.get("bill_type", "N")
        emp_cd = request.query_params.get("emp_code") or None
        return Response(
            {
                "bill_month": bill_month,
                "bill_year": bill_year,
                "bill_type": bill_type,
                "month_setup": get_month_setup_status(
                    bill_type, bill_month, bill_year
                ),
                "candidates": list_reprocess_candidates(
                    bill_month=bill_month,
                    bill_year=bill_year,
                    bill_type=bill_type,
                    emp_cd=emp_cd,
                ),
            }
        )


class PensionBillReprocessAPIView(APIView):
    def post(self, request):
        try:
            bill_month = int(request.data.get("bill_month"))
            bill_year = int(request.data.get("bill_year"))
        except (TypeError, ValueError):
            return Response(
                {"error": "bill_month and bill_year are required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        bill_type = request.data.get("bill_type", "N")
        fmpen_ids = request.data.get("fmpen_ids") or []
        if not fmpen_ids and request.data.get("fmpen_id"):
            fmpen_ids = [request.data.get("fmpen_id")]

        try:
            result = reprocess_pension_bills(
                bill_month=bill_month,
                bill_year=bill_year,
                bill_type=bill_type,
                fmpen_ids=fmpen_ids,
                user=request.user,
            )
            log_audit(
                request,
                table_name="FI_PN_TH_PENSION_BILL",
                record_id=",".join(b["bill_no"] for b in result["bills"]),
                action="UPDATE",
                old_data=None,
                new_data=result,
                module="FIRST_PENSION",
            )
            return Response(
                {
                    "message": "Pension bill reprocessed successfully.",
                    **result,
                }
            )
        except PensionBillError as exc:
            return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)


class PensionBillCloseMonthAPIView(APIView):
    def post(self, request):
        try:
            bill_month = int(request.data.get("bill_month"))
            bill_year = int(request.data.get("bill_year"))
        except (TypeError, ValueError):
            return Response(
                {"error": "bill_month and bill_year are required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        bill_type = request.data.get("bill_type", "N")
        try:
            result = close_pension_bill_month(
                bill_type=bill_type,
                bill_month=bill_month,
                bill_year=bill_year,
                user=request.user,
            )
            log_audit(
                request,
                table_name="FI_PN_MH_PMTHSETUP",
                record_id=f"{bill_type}/{bill_month}/{bill_year}",
                action="UPDATE",
                old_data=None,
                new_data=result,
                module="FIRST_PENSION",
            )
            return Response(
                {
                    "message": "Pension bill month closed.",
                    "month_setup": result,
                }
            )
        except PensionBillError as exc:
            return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)


class PensionBillPpnListAPIView(APIView):
    """PPN bills for month/year (LIC report bill LOV)."""

    def get(self, request):
        try:
            bill_month = int(request.query_params.get("bill_month", ""))
            bill_year = int(request.query_params.get("bill_year", ""))
        except (TypeError, ValueError):
            return Response(
                {"error": "bill_month and bill_year are required."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(
            {
                "bill_month": bill_month,
                "bill_year": bill_year,
                "bills": list_ppn_bills(bill_month=bill_month, bill_year=bill_year),
            }
        )


class PensionLicReportAPIView(APIView):
    def get(self, request):
        bill_no = (request.query_params.get("bill_no") or "").strip()
        if not bill_no:
            return Response(
                {"error": "bill_no is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        emp_codes = request.query_params.getlist("emp_code")
        if not emp_codes:
            single = request.query_params.get("emp_code")
            if single:
                emp_codes = [single]
        try:
            report = build_lic_report(bill_no, emp_codes=emp_codes or None)
            return Response(report)
        except PensionBillError as exc:
            return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)


class PensionBillAbstractReportAPIView(APIView):
    def get(self, request):
        bill_no = (request.query_params.get("bill_no") or "").strip()
        if not bill_no:
            return Response(
                {"error": "bill_no is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        emp_codes = request.query_params.getlist("emp_code")
        if not emp_codes:
            single = request.query_params.get("emp_code")
            if single:
                emp_codes = [single]
        try:
            report = build_bill_abstract_report(bill_no, emp_codes=emp_codes or None)
            return Response(report)
        except BillAbstractReportError as exc:
            return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)


class PensionJournalSummaryReportAPIView(APIView):
    def get(self, request):
        ref_no = (
            request.query_params.get("ref_no")
            or request.query_params.get("bill_no")
            or ""
        ).strip()
        try:
            yr = int(request.query_params.get("yr", ""))
            mth = int(request.query_params.get("mth", ""))
        except (TypeError, ValueError):
            return Response(
                {"error": "yr and mth are required integers."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not ref_no:
            return Response(
                {"error": "bill_no (ref_no) is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            return Response(
                build_journal_summary_report(yr=yr, mth=mth, ref_no=ref_no)
            )
        except JournalSummaryReportError as exc:
            return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)


class PensionJournalSummaryBillsAPIView(APIView):
    def get(self, request):
        try:
            yr = int(request.query_params.get("yr", ""))
            mth = int(request.query_params.get("mth", ""))
        except (TypeError, ValueError):
            return Response(
                {"error": "yr and mth are required integers."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(list_bills_for_journal_report(yr=yr, mth=mth))


class PensionProposalSanctionReportAPIView(APIView):
    def get(self, request):
        emp_codes = request.query_params.getlist("emp_code")
        if not emp_codes:
            single = request.query_params.get("emp_code")
            if single:
                emp_codes = [single]
        if not emp_codes:
            return Response(
                {"error": "emp_code is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            report = build_proposal_sanction_report(emp_codes=emp_codes)
            return Response(report)
        except ProposalSanctionReportError as exc:
            return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)


class PensionFirstPensionAdviceReportAPIView(APIView):
    def get(self, request):
        emp_codes = request.query_params.getlist("emp_code")
        if not emp_codes:
            single = request.query_params.get("emp_code")
            if single:
                emp_codes = [single]
        if not emp_codes:
            return Response(
                {"error": "emp_code is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            report = build_first_pension_advice_report(emp_codes=emp_codes)
            return Response(report)
        except FirstPensionAdviceReportError as exc:
            return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)


class PensionSepcomStatusAPIView(APIView):
    def get(self, request, emp_code):
        return Response(get_sepcom_status(emp_code))


class PensionSepcomGenerateAPIView(APIView):
    def post(self, request):
        try:
            bill_month = int(request.data.get("bill_month"))
            bill_year = int(request.data.get("bill_year"))
        except (TypeError, ValueError):
            return Response(
                {"error": "bill_month and bill_year are required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        emp_cds = request.data.get("emp_cds") or []
        if not emp_cds and request.data.get("emp_code"):
            emp_cds = [request.data.get("emp_code")]

        try:
            result = generate_sepcom_for_employees(
                bill_month=bill_month,
                bill_year=bill_year,
                emp_cds=emp_cds,
                user=request.user,
            )
            log_audit(
                request,
                table_name="FI_PN_TH_SEPCOM",
                record_id=",".join(r["sepcom_id"] for r in result["sepcom_records"]),
                action="CREATE",
                old_data=None,
                new_data=result,
                module="FIRST_PENSION",
            )
            return Response(
                {
                    "message": "Separate commutation (SEPCOM) generated successfully.",
                    **result,
                }
            )
        except PensionBillError as exc:
            return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)


class PensionSepCommReportAPIView(APIView):
    def get(self, request):
        emp_codes = request.query_params.getlist("emp_code")
        if not emp_codes:
            single = request.query_params.get("emp_code")
            if single:
                emp_codes = [single]
        sepcom_ids = request.query_params.getlist("sepcom_id")
        if not emp_codes and not sepcom_ids:
            return Response(
                {"error": "emp_code or sepcom_id is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            report = build_sep_comm_report(
                emp_codes=emp_codes or None,
                sepcom_ids=sepcom_ids or None,
            )
            return Response(report)
        except CommutationBillReportError as exc:
            return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)


class PensionSeparateCommutationBillReportAPIView(APIView):
    def get(self, request):
        emp_codes = request.query_params.getlist("emp_code")
        if not emp_codes:
            single = request.query_params.get("emp_code")
            if single:
                emp_codes = [single]
        sepcom_ids = request.query_params.getlist("sepcom_id")
        if not emp_codes and not sepcom_ids:
            return Response(
                {"error": "emp_code or sepcom_id is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            report = build_separate_commutation_bill_report(
                emp_codes=emp_codes or None,
                sepcom_ids=sepcom_ids or None,
            )
            return Response(report)
        except CommutationBillReportError as exc:
            return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)


class PensionPpcBillStatusAPIView(APIView):
    def get(self, request, emp_code):
        return Response(get_ppc_employee_status(emp_code))


class PensionPpcBillCandidatesAPIView(APIView):
    def get(self, request):
        try:
            bill_month = int(request.query_params.get("bill_month", ""))
            bill_year = int(request.query_params.get("bill_year", ""))
        except (TypeError, ValueError):
            return Response(
                {"error": "bill_month and bill_year are required integers."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        emp_cd = request.query_params.get("emp_code") or None
        return Response(
            {
                "bill_month": bill_month,
                "bill_year": bill_year,
                "bill_type": "C",
                "candidates": list_ppc_candidates(
                    bill_month=bill_month,
                    bill_year=bill_year,
                    emp_cd=emp_cd,
                    user=request.user,
                ),
            }
        )


class PensionPpcBillGenerateAPIView(APIView):
    def post(self, request):
        try:
            bill_month = int(request.data.get("bill_month"))
            bill_year = int(request.data.get("bill_year"))
        except (TypeError, ValueError):
            return Response(
                {"error": "bill_month and bill_year are required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        emp_cds = request.data.get("emp_cds") or []
        if not emp_cds and request.data.get("emp_code"):
            emp_cds = [request.data.get("emp_code")]

        try:
            result = generate_ppc_bills(
                bill_month=bill_month,
                bill_year=bill_year,
                emp_cds=emp_cds,
                user=request.user,
                include_same_bank_unselected=bool(
                    request.data.get("include_same_bank_unselected")
                ),
            )
            log_audit(
                request,
                table_name="FI_PN_TH_PENSION_BILL",
                record_id=",".join(b["bill_no"] for b in result["bills"]),
                action="CREATE",
                old_data=None,
                new_data=result,
                module="FIRST_PENSION",
            )
            return Response(
                {
                    "message": "PPC commutation bill generated successfully.",
                    **result,
                }
            )
        except PensionBillError as exc:
            return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)


class PensionPpcBillListAPIView(APIView):
    def get(self, request):
        try:
            bill_month = int(request.query_params.get("bill_month", ""))
            bill_year = int(request.query_params.get("bill_year", ""))
        except (TypeError, ValueError):
            return Response(
                {"error": "bill_month and bill_year are required integers."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(
            {
                "bill_month": bill_month,
                "bill_year": bill_year,
                "bills": list_ppc_bills(bill_month=bill_month, bill_year=bill_year),
            }
        )


class PensionCommutationBillReportAPIView(APIView):
    def get(self, request):
        emp_codes = request.query_params.getlist("emp_code")
        if not emp_codes:
            single = request.query_params.get("emp_code")
            if single:
                emp_codes = [single]
        if not emp_codes:
            return Response(
                {"error": "emp_code is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            report = build_commutation_bill_report(emp_codes=emp_codes)
            return Response(report)
        except CommutationBillReportError as exc:
            return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)


class PensionVoucherStatusAPIView(APIView):
    def get(self, request):
        bill_no = (request.query_params.get("bill_no") or "").strip()
        if not bill_no:
            return Response(
                {"error": "bill_no is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            return Response(get_voucher_status(bill_no=bill_no))
        except VoucherGenerationError as exc:
            return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)


class PensionVoucherPreviewAPIView(APIView):
    def get(self, request):
        bill_no = (request.query_params.get("bill_no") or "").strip()
        try:
            jv_month = int(request.query_params.get("jv_month", ""))
            jv_year = int(request.query_params.get("jv_year", ""))
        except (TypeError, ValueError):
            return Response(
                {"error": "bill_no, jv_month and jv_year are required."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not bill_no:
            return Response(
                {"error": "bill_no is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            return Response(
                preview_ppn_voucher(
                    bill_no=bill_no,
                    jv_month=jv_month,
                    jv_year=jv_year,
                )
            )
        except VoucherGenerationError as exc:
            return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)


class PensionVoucherGenerateAPIView(APIView):
    def post(self, request):
        bill_no = (request.data.get("bill_no") or "").strip()
        if not bill_no:
            return Response(
                {"error": "bill_no is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            jv_month = int(request.data.get("jv_month"))
            jv_year = int(request.data.get("jv_year"))
        except (TypeError, ValueError):
            return Response(
                {"error": "jv_month and jv_year are required integers."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        abstract_date = request.data.get("abstract_date") or None
        try:
            result = generate_ppn_voucher(
                bill_no=bill_no,
                jv_month=jv_month,
                jv_year=jv_year,
                abstract_no=request.data.get("abstract_no") or "",
                abstract_date=abstract_date,
                narration=request.data.get("narration") or "",
                user=request.user,
                regenerate=bool(request.data.get("regenerate")),
                voucher_no=request.data.get("voucher_no") or "",
            )
            log_audit(
                request,
                table_name="FI_PN_TH_JV",
                record_id=result["voucher_no"],
                action="UPDATE" if result.get("regenerated") else "CREATE",
                old_data=None,
                new_data=result,
                module="FIRST_PENSION",
            )
            return Response(
                {
                    "message": (
                        "Journal voucher regenerated successfully."
                        if result.get("regenerated")
                        else "Journal voucher generated successfully."
                    ),
                    **result,
                }
            )
        except VoucherGenerationError as exc:
            return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)


class PensionManualJournalTemplateAPIView(APIView):
    def get(self, request):
        ref_no = (request.query_params.get("ref_no") or "").strip()
        emp_code = (request.query_params.get("emp_code") or "").strip()
        jv_month = request.query_params.get("jv_month")
        jv_year = request.query_params.get("jv_year")
        try:
            month = int(jv_month) if jv_month else None
            year = int(jv_year) if jv_year else None
        except (TypeError, ValueError):
            return Response(
                {"error": "jv_month and jv_year must be integers when provided."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(
            blank_manual_journal_template(
                ref_no=ref_no,
                jv_month=month,
                jv_year=year,
                emp_cd=emp_code or None,
            )
        )


class PensionManualJournalSummaryAPIView(APIView):
    def get(self, request):
        voucher_no = (request.query_params.get("voucher_no") or "").strip()
        ref_no = (request.query_params.get("ref_no") or "").strip()
        try:
            if voucher_no:
                return Response(get_journal_summary(voucher_no=voucher_no))
            if ref_no:
                summary = find_journal_for_ref(ref_no=ref_no)
                if not summary:
                    return Response(
                        {"error": f"No journal voucher found for ref {ref_no}."},
                        status=status.HTTP_404_NOT_FOUND,
                    )
                return Response(summary)
            return Response(
                {"error": "voucher_no or ref_no is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except ManualJournalError as exc:
            return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)


class PensionManualJournalListAPIView(APIView):
    def get(self, request):
        ref_no = (request.query_params.get("ref_no") or "").strip()
        yr = request.query_params.get("yr")
        mth = request.query_params.get("mth")
        limit = request.query_params.get("limit", 50)
        try:
            year = int(yr) if yr else None
            month = int(mth) if mth else None
            lim = int(limit)
        except (TypeError, ValueError):
            return Response(
                {"error": "yr, mth and limit must be integers when provided."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(
            {
                "journals": list_journals(
                    ref_no=ref_no,
                    yr=year,
                    mth=month,
                    limit=lim,
                )
            }
        )


class PensionManualJournalSaveAPIView(APIView):
    def post(self, request):
        lines = request.data.get("lines")
        if not isinstance(lines, list):
            return Response(
                {"error": "lines must be an array."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            jv_month = int(request.data.get("jv_month"))
            jv_year = int(request.data.get("jv_year"))
        except (TypeError, ValueError):
            return Response(
                {"error": "jv_month and jv_year are required integers."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            result = save_manual_journal(
                voucher_no=request.data.get("voucher_no") or "",
                voucher_dt=request.data.get("voucher_dt") or None,
                jv_month=jv_month,
                jv_year=jv_year,
                ref_no=request.data.get("ref_no") or "",
                ref_dt=request.data.get("ref_dt") or None,
                narration=request.data.get("narration") or "",
                tran_type=request.data.get("tran_type") or "PNJV/N",
                lines=lines,
                user=request.user,
            )
            log_audit(
                request,
                table_name="FI_PN_TH_JV",
                record_id=result["voucher_no"],
                action="CREATE" if not request.data.get("voucher_no") else "UPDATE",
                old_data=None,
                new_data=result,
                module="FIRST_PENSION",
            )
            return Response(
                {
                    "message": "Manual journal voucher saved successfully.",
                    **result,
                    "summary": get_journal_summary(voucher_no=result["voucher_no"]),
                }
            )
        except ManualJournalError as exc:
            return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
