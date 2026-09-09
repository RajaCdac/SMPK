from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from audit.services import log_audit
from family_pension.services.claim_service import (
    empty_claim_form,
    find_claims_by_emp,
    get_claim_by_id,
    list_relations,
    lookup_bank,
    prefill_from_emp,
    save_claim,
)
from family_pension.services.list_service import (
    datatable_family_pensioners,
    family_pensioner_summary,
    list_family_pensioners,
)
from family_pension.services.first_fpension_service import (
    FirstFamilyPensionError,
    generate_first_family_pension,
)
from family_pension.services.first_fp_bill_service import (
    FirstFpBillError,
    generate_first_fp_bill,
    load_first_fp_bill_print,
)
from family_pension.services.fp_bill_abstract_report_service import (
    FpBillAbstractReportError,
    build_fp_bill_abstract_report,
)
from family_pension.services.fp_journal_voucher_service import (
    FpJournalVoucherError,
    fp_journal_summary_report,
    fp_voucher_generate,
    fp_voucher_preview,
    fp_voucher_status,
)
from family_pension.services.proposal_report_service import (
    FamilyPensionProposalReportError,
    build_family_pension_proposal_report,
)
from family_pension.services.dnh_proposal_report_service import (
    build_family_pension_dnh_proposal_report,
    build_family_pension_dnh_proposal_report_batch,
    list_dnh_claims_for_period,
)
from family_pension.services.fp_277_arrear_service import (
    Fp277ArrearError,
    calculate_fp_277_arrear,
    get_upgrade_status,
    upsert_upgrade_header,
)
from family_pension.services.cpi_consolidation_service import (
    CpiUpgradeError,
    generate_cpi_upgrade_for_employee,
    get_cpi_upgrade_status,
)
from family_pension.services.recovery_deduction_service import (
    RecoveryDeductionError,
    delete_recovery_line,
    get_earndedn_description,
    list_earndedn_codes,
    lookup_recovery_context,
    save_recovery_line,
)
from family_pension.services.nominee_service import (
    NomineeError,
    create_nominee,
    get_nominee_bundle,
)
from family_pension.services.esr_service import (
    datatable_emp_admin,
    datatable_emp_finance,
    datatable_emp_personal,
    get_emp_admin,
    get_emp_finance,
    get_emp_personal,
    get_emp_personal_status,
    summary_emp_admin,
    summary_emp_finance,
    summary_emp_personal,
    update_emp_personal_status,
)
from family_pension.services.esr_salary_service import (
    SalarySaveError,
    datatable_emp_salary,
    get_emp_salary,
    save_emp_salary_month,
    summary_emp_salary,
)

FAMILY_PENSION_MODULE = "FAMILY_PENSION"


def _claim_audit_snapshot(claim):
    if not claim:
        return None
    return {
        "clmca_id": claim.get("clmca_id"),
        "emp_cd": claim.get("emp_cd"),
        "clm_ca_type": claim.get("clm_ca_type"),
        "ca_no": claim.get("ca_no"),
        "appcn_no": claim.get("appcn_no"),
        "appcn_status": claim.get("appcn_status"),
        "double_fpen_eligibility": claim.get("double_fpen_eligibility"),
        "double_fpen_upto": claim.get("double_fpen_upto"),
        "dod_emp_pensioner": claim.get("dod_emp_pensioner"),
        "last_basic_at_ret": claim.get("last_basic_at_ret"),
        "applicant_count": len(claim.get("applicants") or []),
    }


class FamilyPensionerListAPIView(APIView):
    """
    Family pensioner list from fi_pn_mh_familypensioner.

    - Default → DataTables server-side JSON
    - ?all=1 → full list (legacy)
    - ?summary=1 → dashboard analytics cards
    """

    def get(self, request):
        try:
            if str(request.query_params.get("summary") or "").lower() in (
                "1",
                "true",
                "yes",
            ):
                return Response(family_pensioner_summary())

            if str(request.query_params.get("all") or "").lower() in (
                "1",
                "true",
                "yes",
            ):
                rows = list_family_pensioners()
                return Response({"count": len(rows), "results": rows})

            payload = datatable_family_pensioners(request.query_params)
            return Response(payload)
        except Exception as exc:
            return Response(
                {
                    "error": (
                        "Could not read family pensioners "
                        f"(smpk_pension.fi_pn_mh_familypensioner): {exc}"
                    )
                },
                status=status.HTTP_502_BAD_GATEWAY,
            )


class FamilyPensionClaimAPIView(APIView):
    """Load / save Family Pension Claim (FI_PN_MH_FPENSION_CLAIM_E)."""

    def get(self, request):
        claim_id = (request.query_params.get("clmca_id") or "").strip()
        emp_cd = (request.query_params.get("emp_cd") or "").strip()
        prefill = str(request.query_params.get("prefill") or "").lower() in (
            "1",
            "true",
            "yes",
        )
        clm_ca_type = (request.query_params.get("clm_ca_type") or "").strip()

        try:
            if claim_id:
                claim = get_claim_by_id(claim_id)
                if not claim:
                    return Response(
                        {"error": f"Claim {claim_id} not found"},
                        status=status.HTTP_404_NOT_FOUND,
                    )
                return Response({"exists": True, "claim": claim})

            if emp_cd and prefill:
                result = prefill_from_emp(emp_cd, clm_ca_type=clm_ca_type)
                if result.get("error"):
                    return Response(
                        result, status=status.HTTP_404_NOT_FOUND
                    )
                return Response(result)

            if emp_cd:
                matches = find_claims_by_emp(emp_cd)
                if not matches:
                    return Response(
                        {
                            "exists": False,
                            "error": f"No claim found for employee {emp_cd}",
                            "matches": [],
                        },
                        status=status.HTTP_404_NOT_FOUND,
                    )
                if len(matches) == 1:
                    claim = get_claim_by_id(matches[0]["clmca_id"])
                    return Response(
                        {"exists": True, "claim": claim, "matches": matches}
                    )
                return Response(
                    {
                        "exists": True,
                        "matches": matches,
                        "claim": None,
                        "message": "Multiple claims found — select Claim ID",
                    }
                )

            return Response(
                {
                    "claim": empty_claim_form(),
                    "exists": False,
                    "message": "Provide clmca_id or emp_cd",
                }
            )
        except Exception as exc:
            return Response(
                {
                    "error": (
                        "Could not read family pension claim "
                        f"(smpk_pension.fi_pn_mh_fpen_caclaim): {exc}"
                    )
                },
                status=status.HTTP_502_BAD_GATEWAY,
            )

    def post(self, request):
        user = getattr(request.user, "username", None) or "SMPK"
        body = request.data or {}
        existing_id = str(body.get("clmca_id") or "").strip()
        old_claim = get_claim_by_id(existing_id) if existing_id else None
        try:
            result = save_claim(body, user_id=user)
        except Exception as exc:
            return Response(
                {"error": f"Could not save claim: {exc}"},
                status=status.HTTP_502_BAD_GATEWAY,
            )
        if result.get("error"):
            return Response(result, status=status.HTTP_400_BAD_REQUEST)

        claim = result.get("claim") if isinstance(result, dict) else None
        if not isinstance(claim, dict):
            claim = result if isinstance(result, dict) and result.get("clmca_id") else None
        clmca_id = (
            (claim or {}).get("clmca_id")
            or existing_id
            or "unknown"
        )
        log_audit(
            request,
            table_name="fi_pn_mh_fpen_caclaim",
            record_id=clmca_id,
            action="UPDATE" if old_claim else "CREATE",
            module=FAMILY_PENSION_MODULE,
            old_data=_claim_audit_snapshot(old_claim),
            new_data=_claim_audit_snapshot(claim),
        )
        return Response(result)


class FamilyPensionRelationListAPIView(APIView):
    def get(self, request):
        try:
            return Response({"results": list_relations()})
        except Exception as exc:
            return Response(
                {"error": str(exc)},
                status=status.HTTP_502_BAD_GATEWAY,
            )


class FamilyPensionBankLookupAPIView(APIView):
    """Oracle bank LOV: name + branch for BANK_CD."""

    def get(self, request):
        bank_cd = (request.query_params.get("bank_cd") or "").strip()
        if not bank_cd:
            return Response(
                {"error": "bank_cd is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            return Response(lookup_bank(bank_cd))
        except Exception as exc:
            return Response(
                {"error": str(exc)},
                status=status.HTTP_502_BAD_GATEWAY,
            )


class FamilyPensionProposalReportAPIView(APIView):
    """
    Recommendation & Sanction of Family Pension (NORMAL) print data.
    FI_PN_MH_FPENSION_PROPOSAL_RPT / fi_pn_mh_Fpension_Appl.
    """

    def get(self, request):
        clmca_id = (request.query_params.get("clmca_id") or "").strip()
        emp_cd = (request.query_params.get("emp_cd") or "").strip()
        if not clmca_id and not emp_cd:
            return Response(
                {"error": "Provide clmca_id or emp_cd"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            report = build_family_pension_proposal_report(
                clmca_id=clmca_id or None,
                emp_cd=emp_cd or None,
            )
            return Response(report)
        except FamilyPensionProposalReportError as exc:
            return Response(
                {"error": str(exc)},
                status=status.HTTP_404_NOT_FOUND,
            )
        except Exception as exc:
            return Response(
                {"error": f"Could not build family pension proposal report: {exc}"},
                status=status.HTTP_502_BAD_GATEWAY,
            )


class FamilyPensionDnhProposalReportAPIView(APIView):
    """
    Die-in-Harness family pension proposal / sanction (with deduction notes).

    FI_PN_MH_FPENSION_DNH_PROPOSAL_RPT → fi_pn_mh_fpension_dnh_appl.
    Query: clmca_id= or emp_cd= (single), or from_dt= + to_dt= (+ optional emp_cd list).
    """

    def get(self, request):
        clmca_id = (request.query_params.get("clmca_id") or "").strip()
        emp_cd = (request.query_params.get("emp_cd") or "").strip()
        from_dt = (request.query_params.get("from_dt") or "").strip()
        to_dt = (request.query_params.get("to_dt") or "").strip()
        list_only = str(request.query_params.get("list") or "").lower() in (
            "1",
            "true",
            "yes",
        )

        try:
            if list_only and from_dt and to_dt:
                return Response(
                    {
                        "claims": list_dnh_claims_for_period(
                            from_dt=from_dt, to_dt=to_dt
                        )
                    }
                )

            if clmca_id or emp_cd:
                report = build_family_pension_dnh_proposal_report(
                    clmca_id=clmca_id or None,
                    emp_cd=emp_cd or None,
                )
                return Response(report)

            if from_dt and to_dt:
                emp_list = [
                    x.strip()
                    for x in (request.query_params.get("emp_cds") or "").split(",")
                    if x.strip()
                ]
                report = build_family_pension_dnh_proposal_report_batch(
                    from_dt=from_dt,
                    to_dt=to_dt,
                    emp_cds=emp_list or None,
                )
                return Response(report)

            return Response(
                {"error": "Provide clmca_id, emp_cd, or from_dt and to_dt"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except FamilyPensionProposalReportError as exc:
            return Response(
                {"error": str(exc)},
                status=status.HTTP_404_NOT_FOUND,
            )
        except Exception as exc:
            return Response(
                {"error": f"Could not build die-in-harness proposal report: {exc}"},
                status=status.HTTP_502_BAD_GATEWAY,
            )


class FamilyPensionGenerateFirstAPIView(APIView):
    """
    Generate First Family Pension (type N).

    Amount from Methodology I; inserts into familypensioner + first-month TH/TD.
    Body: { clmca_id, month?, year?, regenerate? }
    """

    def post(self, request):
        data = request.data or {}
        clmca_id = str(data.get("clmca_id") or "").strip()
        if not clmca_id:
            return Response(
                {"error": "clmca_id is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user = getattr(request.user, "username", None) or "SMPK"
        month = data.get("month")
        year = data.get("year")
        regenerate = str(data.get("regenerate") or "").lower() in (
            "1",
            "true",
            "yes",
        )

        try:
            result = generate_first_family_pension(
                clmca_id=clmca_id,
                month=month,
                year=year,
                user_id=user,
                regenerate=regenerate,
            )
            log_audit(
                request,
                table_name="fi_pn_th_first_month_fpension",
                record_id=clmca_id,
                action="UPDATE" if regenerate else "CREATE",
                module=FAMILY_PENSION_MODULE,
                old_data={"regenerate": regenerate},
                new_data={
                    "clmca_id": clmca_id,
                    "emp_cd": result.get("emp_cd"),
                    "month": result.get("month"),
                    "year": result.get("year"),
                    "wef_dt": result.get("wef_dt"),
                    "methodology1": result.get("methodology1"),
                    "dcr_gratuity": {
                        "amount": (result.get("dcr_gratuity") or {}).get(
                            "amount"
                        ),
                    },
                    "double_fpension": {
                        "eligible": (result.get("double_fpension") or {}).get(
                            "eligible"
                        ),
                        "payable_fp_amt": (
                            result.get("double_fpension") or {}
                        ).get("payable_fp_amt"),
                        "double_fpen_upto": (
                            result.get("double_fpension") or {}
                        ).get("double_fpen_upto"),
                    },
                    "bills": [
                        {
                            "fam_fmpen_id": b.get("fam_fmpen_id"),
                            "sl_no": b.get("sl_no"),
                            "fpension_amt": b.get("fpension_amt"),
                            "gratuity_amt": b.get("gratuity_amt"),
                        }
                        for b in (result.get("bills") or [])
                    ],
                },
            )
            return Response(result)
        except FirstFamilyPensionError as exc:
            return Response(
                {"error": str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except Exception as exc:
            return Response(
                {"error": f"Could not generate First Family Pension: {exc}"},
                status=status.HTTP_502_BAD_GATEWAY,
            )


class FamilyPensionBillGenerateAPIView(APIView):
    """
    Family Pension Bill (PFN) for one claim/employee.

    Oracle FI_PN_First_Family_Pension_Bill.fmb / FPROC_BILL_GENERATE
    Body: { clmca_id, emp_cd?, month?, year?, bill_type: N|M, regenerate? }
    bill_type N = First Bill, M = Monthly Bill.
    """

    def post(self, request):
        data = request.data or {}
        clmca_id = str(data.get("clmca_id") or "").strip()
        if not clmca_id:
            return Response(
                {"error": "clmca_id is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user = getattr(request.user, "username", None) or "SMPK"
        regenerate = str(data.get("regenerate") or "").lower() in (
            "1",
            "true",
            "yes",
        )
        bill_type = str(data.get("bill_type") or "N").strip().upper() or "N"
        month = data.get("month")
        year = data.get("year")
        try:
            month = int(month) if month not in (None, "") else None
            year = int(year) if year not in (None, "") else None
        except (TypeError, ValueError):
            return Response(
                {"error": "month and year must be numbers"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            result = generate_first_fp_bill(
                clmca_id=clmca_id,
                emp_cd=data.get("emp_cd"),
                bill_type=bill_type,
                month=month,
                year=year,
                user_id=user,
                regenerate=regenerate,
                bank_cd=str(data.get("bank_cd") or "NOBANK"),
            )
            log_audit(
                request,
                table_name="fi_pn_th_pension_bill",
                record_id=result.get("bill_no") or clmca_id,
                action="UPDATE" if regenerate else "CREATE",
                module=FAMILY_PENSION_MODULE,
                old_data={"regenerate": regenerate, "clmca_id": clmca_id},
                new_data={
                    "bill_no": result.get("bill_no"),
                    "emp_cd": result.get("emp_cd"),
                    "clmca_id": result.get("clmca_id"),
                    "bill_type": result.get("bill_type"),
                    "bill_month": result.get("bill_month"),
                    "bill_year": result.get("bill_year"),
                    "total_amt_earned": result.get("total_amt_earned"),
                    "total_amt_deducted": result.get("total_amt_deducted"),
                    "lines": result.get("lines"),
                },
            )
            return Response(result)
        except FirstFpBillError as exc:
            return Response(
                {"error": str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except Exception as exc:
            return Response(
                {"error": f"Could not generate family pension bill: {exc}"},
                status=status.HTTP_502_BAD_GATEWAY,
            )


class FamilyPensionBillPrintAPIView(APIView):
    """
    Load existing PFN bill for print (Oracle FI_PN_FPENBILL_GEN / LIC).

    Query: bill_no= and/or clmca_id= and/or emp_cd=
    (+ optional bill_type, month, year, gen_lic_tag=L)
    """

    def get(self, request):
        try:
            result = load_first_fp_bill_print(
                bill_no=request.query_params.get("bill_no"),
                clmca_id=request.query_params.get("clmca_id"),
                emp_cd=request.query_params.get("emp_cd"),
                bill_type=request.query_params.get("bill_type"),
                month=request.query_params.get("month"),
                year=request.query_params.get("year"),
                gen_lic_tag=request.query_params.get("gen_lic_tag"),
                print_style=request.query_params.get("print_style"),
            )
            return Response(result)
        except FirstFpBillError as exc:
            return Response(
                {"error": str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except Exception as exc:
            return Response(
                {"error": f"Could not load family pension bill: {exc}"},
                status=status.HTTP_502_BAD_GATEWAY,
            )


class FamilyPensionBillAbstractReportAPIView(APIView):
    """
    PFN bill abstract for one employee/claim (Oracle FI_PN_BILL_ABSTRACT PFN branch).

    Query: bill_no= and/or clmca_id= and/or emp_cd=
    """

    def get(self, request):
        try:
            report = build_fp_bill_abstract_report(
                bill_no=request.query_params.get("bill_no"),
                clmca_id=request.query_params.get("clmca_id"),
                emp_cd=request.query_params.get("emp_cd"),
            )
            return Response(report)
        except FpBillAbstractReportError as exc:
            return Response(
                {"error": str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except Exception as exc:
            return Response(
                {"error": f"Could not load family pension bill abstract: {exc}"},
                status=status.HTTP_502_BAD_GATEWAY,
            )


class FamilyPensionJournalVoucherStatusAPIView(APIView):
    """
    PFN journal voucher status (Oracle FI_PN_T_H_JRVOUCHR_E).

    Query: bill_no= and/or clmca_id= and/or emp_cd=
    """

    def get(self, request):
        try:
            payload = fp_voucher_status(
                bill_no=request.query_params.get("bill_no"),
                clmca_id=request.query_params.get("clmca_id"),
                emp_cd=request.query_params.get("emp_cd"),
            )
            return Response(payload)
        except FpJournalVoucherError as exc:
            return Response(
                {"error": str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except Exception as exc:
            return Response(
                {"error": f"Could not load journal voucher status: {exc}"},
                status=status.HTTP_502_BAD_GATEWAY,
            )


class FamilyPensionJournalVoucherPreviewAPIView(APIView):
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
                fp_voucher_preview(
                    bill_no=bill_no,
                    jv_month=jv_month,
                    jv_year=jv_year,
                )
            )
        except FpJournalVoucherError as exc:
            return Response(
                {"error": str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )


class FamilyPensionJournalVoucherGenerateAPIView(APIView):
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
            result = fp_voucher_generate(
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
                module="FAMILY_PENSION",
            )
            return Response(
                {
                    "message": (
                        "Family pension journal voucher regenerated successfully."
                        if result.get("regenerated")
                        else "Family pension journal voucher generated successfully."
                    ),
                    **result,
                }
            )
        except FpJournalVoucherError as exc:
            return Response(
                {"error": str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )


class FamilyPensionJournalSummaryReportAPIView(APIView):
    """
    Summary of Journal for a PFN bill (Oracle FI_PN_TD_JV_RPT).

    Query: yr=, mth=, ref_no= or bill_no=
    """

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
                fp_journal_summary_report(yr=yr, mth=mth, ref_no=ref_no)
            )
        except FpJournalVoucherError as exc:
            return Response(
                {"error": str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except Exception as exc:
            return Response(
                {"error": f"Could not load journal summary: {exc}"},
                status=status.HTTP_502_BAD_GATEWAY,
            )


class FamilyPension277UpgradeAPIView(APIView):
    """
    277 upgrade header (fi_pn_family_277_upgrade).

    GET  ?claim_id= or ?emp_cd= → header + detail lines
    POST body: claim_id, pensioner_death_dt, generated_basic, upgraded_basic,
               emp_cd?, case_no?, emp_class?, generated_cpi?, arrear_upto?
    """

    def get(self, request):
        claim_id = str(request.query_params.get("claim_id") or "").strip()
        emp_cd = str(request.query_params.get("emp_cd") or "").strip()
        if not claim_id and not emp_cd:
            return Response(
                {"error": "claim_id or emp_cd is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            return Response(get_upgrade_status(claim_id=claim_id, emp_cd=emp_cd))
        except Exception as exc:
            return Response(
                {"error": f"Could not load 277 upgrade: {exc}"},
                status=status.HTTP_502_BAD_GATEWAY,
            )

    def post(self, request):
        data = request.data or {}
        claim_id = str(data.get("claim_id") or data.get("clmca_id") or "").strip()
        if not claim_id:
            return Response(
                {"error": "claim_id is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        user = getattr(request.user, "username", None) or "SMPK"
        try:
            row = upsert_upgrade_header(
                claim_id=claim_id,
                emp_cd=data.get("emp_cd"),
                case_no=data.get("case_no"),
                emp_class=data.get("emp_class"),
                pensioner_death_dt=data.get("pensioner_death_dt"),
                generated_cpi=data.get("generated_cpi"),
                upgraded_cpi=data.get("upgraded_cpi", 277),
                generated_basic=data.get("generated_basic"),
                upgraded_basic=data.get("upgraded_basic"),
                arrear_upto=data.get("arrear_upto"),
                user_id=user,
            )
            log_audit(
                request,
                table_name="fi_pn_family_277_upgrade",
                record_id=claim_id,
                action="UPDATE",
                module=FAMILY_PENSION_MODULE,
                old_data=None,
                new_data={
                    "claim_id": claim_id,
                    "upgraded_basic": row.get("upgraded_basic"),
                    "generated_basic": row.get("generated_basic"),
                    "upgraded_cpi": row.get("upgraded_cpi"),
                },
            )
            return Response({"ok": True, "upgrade": row})
        except Fp277ArrearError as exc:
            return Response(
                {"error": str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except Exception as exc:
            return Response(
                {"error": f"Could not save 277 upgrade: {exc}"},
                status=status.HTTP_502_BAD_GATEWAY,
            )


class FamilyPension277ArrearAPIView(APIView):
    """
    Calculate FP 277-upgrade arrears (Oracle form trigger).

    Entry is by Employee ID (emp_cd) for the Family Pension → Arrear menu.

    GET  ?emp_cd= or ?claim_id= → current upgrade + detail sheet data
    POST body: {
      emp_cd and/or claim_id,
      arrear_upto,              # last day of month (Feb must be 28)
      dry_run?: bool,
      update_monthly_bill?: bool  # default true — type M earn 209/208
    }
    """

    def get(self, request):
        claim_id = str(request.query_params.get("claim_id") or "").strip()
        emp_cd = str(request.query_params.get("emp_cd") or "").strip()
        if not claim_id and not emp_cd:
            return Response(
                {"error": "emp_cd or claim_id is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            return Response(get_upgrade_status(claim_id=claim_id, emp_cd=emp_cd))
        except Exception as exc:
            return Response(
                {"error": f"Could not load arrear status: {exc}"},
                status=status.HTTP_502_BAD_GATEWAY,
            )

    def post(self, request):
        data = request.data or {}
        claim_id = str(data.get("claim_id") or data.get("clmca_id") or "").strip()
        emp_cd = str(data.get("emp_cd") or data.get("emp_id") or "").strip()
        if not claim_id and not emp_cd:
            return Response(
                {"error": "emp_cd or claim_id is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        user = getattr(request.user, "username", None) or "SMPK"
        dry = str(data.get("dry_run") or "").lower() in ("1", "true", "yes")
        update_bill = str(
            data.get("update_monthly_bill", "true")
        ).lower() not in ("0", "false", "no")

        try:
            result = calculate_fp_277_arrear(
                claim_id=claim_id or None,
                emp_cd=emp_cd or None,
                arrear_upto=data.get("arrear_upto"),
                user_id=user,
                dry_run=dry,
                update_monthly_bill=update_bill,
            )
            if not dry:
                log_audit(
                    request,
                    table_name="fi_pn_family_277_upgrade",
                    record_id=result.get("claim_id") or claim_id or emp_cd,
                    action="UPDATE",
                    module=FAMILY_PENSION_MODULE,
                    old_data=None,
                    new_data={
                        "claim_id": result.get("claim_id"),
                        "emp_cd": result.get("emp_cd"),
                        "arrear_upto": result.get("arrear_upto"),
                        "arrear_pension": result.get("arrear_pension"),
                        "arrear_relief": result.get("arrear_relief"),
                        "detail_count": result.get("detail_count"),
                    },
                )
            return Response(result)
        except Fp277ArrearError as exc:
            return Response(
                {"error": str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except Exception as exc:
            return Response(
                {"error": f"Could not calculate 277 arrear: {exc}"},
                status=status.HTTP_502_BAD_GATEWAY,
            )


class FamilyPensionNomineeAPIView(APIView):
    """
    Oracle FI_XX_MD_NOMIN_PN_E — employee nominee master (FI_XX_MD_NOMINEE).
    GET  ?emp_cd=xxxxx  → employee + nominee list
    POST {emp_cd, ...}  → add nominee
    """

    def get(self, request):
        emp_cd = (request.query_params.get("emp_cd") or "").strip()
        if not emp_cd:
            return Response(
                {"error": "emp_cd is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            return Response(get_nominee_bundle(emp_cd))
        except NomineeError as exc:
            return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as exc:
            return Response(
                {"error": str(exc)},
                status=status.HTTP_502_BAD_GATEWAY,
            )

    def post(self, request):
        data = request.data or {}
        user_code = ""
        try:
            user = request.user
            if user and getattr(user, "is_authenticated", False):
                user_code = (
                    str(getattr(user, "username", "") or "")[:5]
                    or str(getattr(user, "id", "") or "")[:5]
                )
        except Exception:
            pass
        try:
            result = create_nominee(data, user_code=user_code)
            return Response(result, status=status.HTTP_201_CREATED)
        except NomineeError as exc:
            return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as exc:
            return Response(
                {"error": str(exc)},
                status=status.HTTP_502_BAD_GATEWAY,
            )


class EsrPersonalAPIView(APIView):
    """
    ESR Personal — fi_xx_mh_emp_per.

    - GET ?emp_cd= → single employee detail
    - GET ?emp_cd=&status_check=1 → Personal Information Status (claim gate)
    - GET ?summary=1 → dashboard analytics cards
    - GET (DataTables draw/start/length/…) → server-side list
    - PATCH/POST { emp_cd, status } → update Personal Information Status
    """

    def get(self, request):
        emp_cd = (request.query_params.get("emp_cd") or "").strip()
        try:
            if emp_cd and str(
                request.query_params.get("status_check") or ""
            ).lower() in ("1", "true", "yes"):
                result = get_emp_personal_status(emp_cd)
                if result.get("found") is False:
                    return Response(result, status=status.HTTP_404_NOT_FOUND)
                if result.get("error"):
                    return Response(
                        result, status=status.HTTP_400_BAD_REQUEST
                    )
                return Response(result)

            if emp_cd:
                result = get_emp_personal(emp_cd)
                if result.get("found") is False:
                    return Response(result, status=status.HTTP_404_NOT_FOUND)
                if result.get("error"):
                    return Response(
                        result, status=status.HTTP_400_BAD_REQUEST
                    )
                return Response(result)

            if str(request.query_params.get("summary") or "").lower() in (
                "1",
                "true",
                "yes",
            ):
                return Response(summary_emp_personal())

            return Response(datatable_emp_personal(request.query_params))
        except Exception as exc:
            return Response(
                {
                    "error": (
                        "Could not read employee personal record "
                        f"(fi_xx_mh_emp_per): {exc}"
                    )
                },
                status=status.HTTP_502_BAD_GATEWAY,
            )

    def patch(self, request):
        return self._update_status(request)

    def post(self, request):
        """Update Personal Information Status (same as PATCH)."""
        return self._update_status(request)

    def _update_status(self, request):
        body = request.data or {}
        emp_cd = str(body.get("emp_cd") or "").strip()
        status_cd = str(body.get("status") or body.get("STATUS") or "").strip()
        user = getattr(request.user, "username", None) or "SMPK"
        try:
            result = update_emp_personal_status(
                emp_cd, status_cd, user_id=user
            )
        except Exception as exc:
            return Response(
                {
                    "error": (
                        "Could not update Personal Information Status "
                        f"(fi_xx_mh_emp_per): {exc}"
                    )
                },
                status=status.HTTP_502_BAD_GATEWAY,
            )
        if result.get("found") is False:
            return Response(result, status=status.HTTP_404_NOT_FOUND)
        if result.get("error"):
            return Response(result, status=status.HTTP_400_BAD_REQUEST)

        log_audit(
            request,
            table_name="fi_xx_mh_emp_per",
            record_id=emp_cd,
            action="UPDATE",
            module=FAMILY_PENSION_MODULE,
            old_data={"STATUS": result.get("old_status")},
            new_data={"STATUS": result.get("status")},
        )
        return Response(result)


class EsrAdminAPIView(APIView):
    """
    ESR Admin — fi_xx_mh_emp_adm.

    - GET ?emp_cd= → single employee detail
    - GET ?summary=1 → dashboard analytics cards
    - GET (DataTables draw/start/length/…) → server-side list
    """

    def get(self, request):
        emp_cd = (request.query_params.get("emp_cd") or "").strip()
        try:
            if emp_cd:
                result = get_emp_admin(emp_cd)
                if result.get("found") is False:
                    return Response(result, status=status.HTTP_404_NOT_FOUND)
                if result.get("error"):
                    return Response(
                        result, status=status.HTTP_400_BAD_REQUEST
                    )
                return Response(result)

            if str(request.query_params.get("summary") or "").lower() in (
                "1",
                "true",
                "yes",
            ):
                return Response(summary_emp_admin())

            return Response(datatable_emp_admin(request.query_params))
        except Exception as exc:
            return Response(
                {
                    "error": (
                        "Could not read employee admin record "
                        f"(fi_xx_mh_emp_adm): {exc}"
                    )
                },
                status=status.HTTP_502_BAD_GATEWAY,
            )


class EsrFinanceAPIView(APIView):
    """
    ESR Finance — fi_xx_mh_emp_fin.

    - GET ?emp_cd= → single employee detail
    - GET ?summary=1 → dashboard analytics cards
    - GET (DataTables draw/start/length/…) → server-side list
    """

    def get(self, request):
        emp_cd = (request.query_params.get("emp_cd") or "").strip()
        try:
            if emp_cd:
                result = get_emp_finance(emp_cd)
                if result.get("found") is False:
                    return Response(result, status=status.HTTP_404_NOT_FOUND)
                if result.get("error"):
                    return Response(
                        result, status=status.HTTP_400_BAD_REQUEST
                    )
                return Response(result)

            if str(request.query_params.get("summary") or "").lower() in (
                "1",
                "true",
                "yes",
            ):
                return Response(summary_emp_finance())

            return Response(datatable_emp_finance(request.query_params))
        except Exception as exc:
            return Response(
                {
                    "error": (
                        "Could not read employee finance record "
                        f"(fi_xx_mh_emp_fin): {exc}"
                    )
                },
                status=status.HTTP_502_BAD_GATEWAY,
            )


class EsrSalaryAPIView(APIView):
    """
    ESR Salary — fi_pr_th_salout (+ DA from fi_pr_td_salout).

    - GET ?emp_cd= → last N months salary with basic & DA
    - GET ?summary=1 → dashboard analytics cards
    - GET (DataTables …) → employee list (latest month)
    - POST → save one month (basic rate + 001/007 lines) for next-month draft
    """

    def get(self, request):
        emp_cd = (request.query_params.get("emp_cd") or "").strip()
        try:
            if emp_cd:
                months = request.query_params.get("months") or 10
                try:
                    months = int(months)
                except (TypeError, ValueError):
                    months = 10
                result = get_emp_salary(emp_cd, months=months)
                if result.get("found") is False:
                    return Response(result, status=status.HTTP_404_NOT_FOUND)
                if result.get("error"):
                    return Response(
                        result, status=status.HTTP_400_BAD_REQUEST
                    )
                return Response(result)

            if str(request.query_params.get("summary") or "").lower() in (
                "1",
                "true",
                "yes",
            ):
                return Response(summary_emp_salary())

            return Response(datatable_emp_salary(request.query_params))
        except Exception as exc:
            return Response(
                {
                    "error": (
                        "Could not read salary records "
                        f"(fi_pr_th_salout / fi_pr_td_salout): {exc}"
                    )
                },
                status=status.HTTP_502_BAD_GATEWAY,
            )

    def post(self, request):
        user_code = ""
        try:
            user = request.user
            if user is not None and getattr(user, "is_authenticated", False):
                user_code = (
                    getattr(user, "username", None)
                    or getattr(user, "emp_cd", None)
                    or ""
                )
        except Exception:
            user_code = ""
        try:
            result = save_emp_salary_month(
                request.data if isinstance(request.data, dict) else {},
                user_code=str(user_code or "")[:5],
            )
            return Response(result, status=status.HTTP_200_OK)
        except SalarySaveError as exc:
            return Response(
                {"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as exc:
            return Response(
                {
                    "error": (
                        "Could not save salary month "
                        f"(fi_pr_th_salout / fi_pr_td_salout): {exc}"
                    )
                },
                status=status.HTTP_502_BAD_GATEWAY,
            )


class FamilyPensionCpiUpgradeAPIView(APIView):
    """
    Report → CPI-Upgrade: generate / view fi_pn_cpi_consolidation rows.

    GET  ?emp_cd= or ?claim_id= → existing CPI basics (if any)
    POST body: { emp_cd and/or claim_id } → compute via Methodology and upsert
    """

    def get(self, request):
        claim_id = str(request.query_params.get("claim_id") or "").strip()
        emp_cd = str(request.query_params.get("emp_cd") or "").strip()
        if not claim_id and not emp_cd:
            return Response(
                {"error": "emp_cd or claim_id is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            return Response(
                get_cpi_upgrade_status(claim_id=claim_id or None, emp_cd=emp_cd or None)
            )
        except Exception as exc:
            return Response(
                {"error": f"Could not load CPI consolidation: {exc}"},
                status=status.HTTP_502_BAD_GATEWAY,
            )

    def post(self, request):
        data = request.data or {}
        claim_id = str(data.get("claim_id") or data.get("clmca_id") or "").strip()
        emp_cd = str(data.get("emp_cd") or data.get("emp_id") or "").strip()
        if not claim_id and not emp_cd:
            return Response(
                {"error": "emp_cd or claim_id is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        user = getattr(request.user, "username", None) or "SMPK"
        try:
            result = generate_cpi_upgrade_for_employee(
                claim_id=claim_id or None,
                emp_cd=emp_cd or None,
                user_id=user,
            )
            log_audit(
                request,
                table_name="fi_pn_cpi_consolidation",
                record_id=result.get("claim_id") or emp_cd,
                action="UPSERT",
                module=FAMILY_PENSION_MODULE,
                old_data=None,
                new_data={
                    "claim_id": result.get("claim_id"),
                    "emp_cd": result.get("emp_cd"),
                    "emp_class": result.get("emp_class"),
                    "row_count": len(result.get("rows") or []),
                },
            )
            return Response(result)
        except CpiUpgradeError as exc:
            return Response(
                {"error": str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except Exception as exc:
            return Response(
                {"error": f"Could not generate CPI basics: {exc}"},
                status=status.HTTP_502_BAD_GATEWAY,
            )


class FamilyPensionRecoveryLookupAPIView(APIView):
    """Load FP bill header + earn/dedn lines for month/year/emp (Oracle form)."""

    def get(self, request):
        try:
            data = lookup_recovery_context(
                month=request.query_params.get("month"),
                year=request.query_params.get("year"),
                emp_cd=request.query_params.get("emp_cd"),
            )
            return Response(data)
        except RecoveryDeductionError as exc:
            return Response(
                {"error": str(exc)},
                status=status.HTTP_404_NOT_FOUND,
            )
        except Exception as exc:
            return Response(
                {"error": f"Could not load recovery context: {exc}"},
                status=status.HTTP_502_BAD_GATEWAY,
            )


class FamilyPensionRecoveryCodesAPIView(APIView):
    """Earn/dedn master codes (optional type=E|D)."""

    def get(self, request):
        earn_type = request.query_params.get("type") or ""
        code = str(request.query_params.get("code") or "").strip()
        try:
            if code:
                row = get_earndedn_description(code, earn_type)
                if not row:
                    return Response(
                        {"error": "Code not found in earn/dedn master."},
                        status=status.HTTP_404_NOT_FOUND,
                    )
                return Response(row)
            return Response({"codes": list_earndedn_codes(earn_type=earn_type)})
        except Exception as exc:
            return Response(
                {"error": f"Could not load earn/dedn codes: {exc}"},
                status=status.HTTP_502_BAD_GATEWAY,
            )


class FamilyPensionRecoveryLineAPIView(APIView):
    """Save or delete a TD earn/dedn line."""

    def post(self, request):
        data = request.data or {}
        user = getattr(request.user, "username", None) or "SMPK"
        try:
            result = save_recovery_line(
                fam_fmpen_id=data.get("fam_fmpen_id"),
                earn_dedn_type=data.get("earn_dedn_type") or data.get("type"),
                earn_dedn_cd=data.get("earn_dedn_cd") or data.get("code"),
                amount=data.get("amount"),
                user_id=user,
            )
            log_audit(
                request,
                table_name="fi_pn_td_first_month_fpension",
                record_id=result.get("fam_fmpen_id"),
                action="UPSERT",
                module=FAMILY_PENSION_MODULE,
                old_data=None,
                new_data={
                    "earn_dedn_type": result.get("earn_dedn_type"),
                    "earn_dedn_cd": result.get("earn_dedn_cd"),
                    "amount": result.get("amount"),
                    "action": result.get("action"),
                },
            )
            return Response(result)
        except RecoveryDeductionError as exc:
            return Response(
                {"error": str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except Exception as exc:
            return Response(
                {"error": f"Could not save line: {exc}"},
                status=status.HTTP_502_BAD_GATEWAY,
            )

    def delete(self, request):
        data = request.data or {}
        if not data:
            data = request.query_params
        try:
            result = delete_recovery_line(
                fam_fmpen_id=data.get("fam_fmpen_id"),
                earn_dedn_type=data.get("earn_dedn_type") or data.get("type"),
                earn_dedn_cd=data.get("earn_dedn_cd") or data.get("code"),
            )
            log_audit(
                request,
                table_name="fi_pn_td_first_month_fpension",
                record_id=str(data.get("fam_fmpen_id") or ""),
                action="DELETE",
                module=FAMILY_PENSION_MODULE,
                old_data={
                    "earn_dedn_type": data.get("earn_dedn_type") or data.get("type"),
                    "earn_dedn_cd": data.get("earn_dedn_cd") or data.get("code"),
                },
                new_data=None,
            )
            return Response(result)
        except RecoveryDeductionError as exc:
            return Response(
                {"error": str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except Exception as exc:
            return Response(
                {"error": f"Could not delete line: {exc}"},
                status=status.HTTP_502_BAD_GATEWAY,
            )
