# SMPK First Pension — Code Handover Document

**Audience:** Junior developer taking over maintenance and enhancements  
**Module:** First Pension processing (Django backend + React frontend)  
**Last updated:** June 2026  

> **PDF (recommended for handover):** [`FIRST_PENSION_CODE_HANDOVER.pdf`](./FIRST_PENSION_CODE_HANDOVER.pdf)  
> **Quick start only:** [`FIRST_PENSION_QUICK_START.md`](./FIRST_PENSION_QUICK_START.md)  
> **Regenerate PDF:** `python docs/generate_handover_pdf.py`

**Backend root:** `SMPK/backend/config/first_pension/`  
**Frontend root:** `SMPK/frontend/frontend/src/components/` (pension UI)  
**API prefix:** `first-pension/` (mounted in Django `config/api/urls.py`)

---

## Table of contents

1. [What this system does](#1-what-this-system-does)
2. [End-to-end business workflow](#2-end-to-end-business-workflow)
3. [Architecture overview](#3-architecture-overview)
4. [Normal retirement vs VR (Voluntary Retirement)](#4-normal-retirement-vs-vr-voluntary-retirement)
5. [Oracle Forms mapping](#5-oracle-forms-mapping)
6. [Database models (business meaning)](#6-database-models-business-meaning)
7. [Backend — function reference by file](#7-backend--function-reference-by-file)
8. [Frontend — function reference by file](#8-frontend--function-reference-by-file)
9. [Complete API endpoint index](#9-complete-api-endpoint-index)
10. [How to run and test locally](#10-how-to-run-and-test-locally)
11. [Known gaps and pending work](#11-known-gaps-and-pending-work)

---

## 1. What this system does

SMPK First Pension is a port of the Oracle Forms pension workflow used at Syama Prasad Mookerjee Port, Kolkata. It lets finance/pension staff:

1. Record employee separation and service adjustments (no-pay, dies-non)
2. Enter pension proposal and commutation application
3. Calculate pension, commutation lump sum, and gratuity
4. Generate first-month pension (FMPEN) and bank bills (PPN)
5. For **separate commutation** (mainly VR): generate SEPCOM → PPC bill → reports
6. Print sanction reports, LIC reports, bill abstracts, and journal summaries

**Design principle:** Business rules follow Oracle Forms (`.fmb`) behaviour. MySQL tables prefixed `fi_pn_*` mirror Oracle `FINANCE.FI_PN_*` tables.

---

## 2. End-to-end business workflow

### UI tab order (`EmployeeProcessTabs.jsx`)

| Step | Tab | Business step | Must complete before |
|------|-----|---------------|----------------------|
| 1 | Basic Info | Read-only employee snapshot | — |
| 2 | Commutation | Commutation application (+ SEPCOM for COM) | Proposal recommended |
| 3 | No-Pay | Service adjustment days | Employee selected |
| 4 | Proposal | Pension proposal header + earn/dedn | No-pay saved |
| 5 | Amount | Calculate pension / gratuity / commutation | Proposal + commutation % |
| 6 | Bill & Journal | PPN bill, PPC bill, JV | Amount + first-month generate |
| 7 | Reports | LIC, sanction, commutation, abstract, JV summary | Relevant bill generated |

### Typical path — normal retirement (RT)

```
No-Pay → Proposal → Commutation (PEN) → Amount → First-month generate → PPN Bill → JV → Reports
```

- Commutation is **with first pension** (`impl_fpen_combill = PEN`).
- Lump sum calculated on Amount tab using age rate table.

### Typical path — voluntary retirement (VR)

```
No-Pay → Proposal (VR) → Amount (pension + gratuity only) → PPN Bill → Reports
        ↓ (later, when employee applies)
Commutation (COM) → SEPCOM → PPC Bill → Commutation Sanction report
```

- First bill has **no commutation line**.
- Separate commutation uses 4 Oracle steps (application → SEPCOM → PPC → report).

---

## 3. Architecture overview

```
┌─────────────────┐     REST JSON      ┌──────────────────────────────┐
│  React UI       │ ◄──────────────► │  Django first_pension app     │
│  (components/)  │   first-pension/ │  views / *_api.py             │
└─────────────────┘                  │  services/*.py (business logic)│
                                     │  pension_calculation.py       │
                                     └──────────────┬───────────────┘
                                                    │
                    ┌───────────────────────────────┼───────────────────────────────┐
                    ▼                               ▼                               ▼
            SMPK local tables              Oracle mirror tables              master_data app
            (PensionCase, etc.)            (fi_pn_th_*, fi_pn_mh_*)         (banks, fin ctrl)
```

| Layer | Responsibility |
|-------|----------------|
| **`*_api.py` / `views.py`** | HTTP validation, auth, audit logging, call services |
| **`services/*.py`** | Oracle-equivalent business processes (bills, SEPCOM, reports) |
| **`pension_calculation.py`** | Pure financial formulas (TCCS, TQS, pension, gratuity) |
| **`oracle_mirror.py`** | Django models → existing MySQL Oracle mirror tables |
| **`models.py`** | SMPK workflow tables (case, proposal, commutation application) |
| **React components** | One tab or sub-workflow per component; call API via `services/Api.js` |

---

## 4. Normal retirement vs VR (Voluntary Retirement)

| Topic | Normal (RT) | VR |
|-------|-------------|-----|
| Separation type | `RT` | `VR` |
| Commutation timing | With first pension (`PEN`) | Deferred (`COM` = separate) |
| Amount tab commutation | Calculated and saved | Shows **Deferred**; amount = 0 |
| SEPCOM / PPC | Not used | Required for commutation payment |
| Pension for commutation lump sum | Same as Amount tab summary | Should use **disbursed pension** from pensioner/application (Oracle); SMPK currently uses summary — see §11 |
| Age rate table | `fi_pn_md_commrate_rupee` | Same table |
| Age reference date | MO cert date if application >12 months after separation; else application received date | Same rule |

**Key functions:** `is_voluntary_retirement()`, `build_amount_lookup_payload()` in `pension_calculation.py`.

---

## 5. Oracle Forms mapping

| Oracle Form | SMPK implementation |
|-------------|---------------------|
| `FI_PN_MH_APPLICATION.fmb` | `CommutationApplicationEntry.jsx` + `CommutationCreateAPIView` |
| `FI_PN_FIRST_PENSION_PROCESS.fmb` | `pension_calculation.py` + `first_month_pension_service.py` |
| `FI_PN_COMUTATION_GENERATION.fmb` | `sepcom_commutation_generation_service.py` + `PensionSepcomGeneration.jsx` |
| `FI_PN_TH_Commutation_Bill_Gen.fmb` | `ppc_commutation_bill_service.py` + `PensionPpcBillGeneration.jsx` |
| `SEP_COMM_REP1.fmb` | `sep_comm_report_service.py` |
| First pension bill generation | `pension_bill_service.generate_pension_bills` |
| LIC report | `pension_bill_service.build_lic_report` |
| JV generation | `voucher_generation_service.py` |

---

## 6. Database models (business meaning)

### SMPK local (`models.py`)

| Model | Business purpose |
|-------|------------------|
| `PensionCase` | Employee snapshot + no-pay inputs + separation; one row per employee |
| `PensionSummary` | Calculated service (TCCS/TQS) and amounts after Amount tab calculate |
| `CommutationApplication` | Commutation application form data (one per employee) |
| `PensionProposal` | Pension proposal header (CA number, bank, separation, holds) |
| `PensionProposalEarndedn` | Proposal earn/deduction grid lines |

### Oracle mirrors (`oracle_mirror.py`)

| Model | Oracle table | Business purpose |
|-------|--------------|------------------|
| `FiPnMhApplication` | `FI_PN_MH_APPLICATION` | Commutation application mirror |
| `FiPnMhPensionProposal` | `FI_PN_MH_PENSION_PROPOSAL` | Proposal header mirror |
| `FiPnMhPensioner` | `FI_PN_MH_PENSIONER` | Active pensioner (pension, commuted portion) |
| `FiPnThFirstMonthPension` | `FI_PN_TH_FIRST_MONTH_PENSION` | First-month bill header (FMPEN_ID) |
| `FiPnTdFirstMonthPension` | `FI_PN_TD_FIRST_MONTH_PENSION` | First-month earn/dedn lines |
| `FiPnThPensionBill` | `FI_PN_TH_PENSION_BILL` | Bank bill header (PPN or PPC) |
| `FiPnThSepcom` / `FiPnTdSepcom` | `FI_PN_TH/TD_SEPCOM` | Separate commutation generation |
| `FiPnMdCommrateRupee` | `FI_PN_MD_COMMRATE_RUPEE` | Commutation rate by age |
| `FiPnThJv` / `FiPnTdJv` | Journal voucher header/detail |
| `FiPnMhPmthsetup` | Month open/close control per bill type |

---

## 7. Backend — function reference by file

> **Convention:** Each entry = **Function** → **Business logic** → **Called from**

---

### `urls.py`

Route definitions only. All paths under `first-pension/`. See [§9 API index](#9-complete-api-endpoint-index).

---

### `views.py`

| Function / Class | Business logic | Called from |
|------------------|----------------|-------------|
| `_format_date_for_api` | Formats date for JSON (`YYYY-MM-DD`) | Serializers |
| `_parse_optional_date` | Parses optional date from request | Commutation save |
| `_apply_commutation_fields` | Maps POST body → `CommutationApplication`; sets restoration = commutation + 15 years; VR defaults `impl_fpen_combill=COM` | Commutation API |
| `serialize_no_pay_data` | Builds no-pay GET response | NoPayLookupAPIView |
| `_get_pension_case_for_employee` | Finds `PensionCase` by emp code variants | Multiple views |
| `_parse_dd_mm_yyyy` | Parses `DD-MM-YYYY` dates | Legacy process |
| `serialize_commutation_application` | Full commutation form JSON | Commutation API |
| `_enrich_commutation_data_from_proposal` | Fills CA/bank from proposal if missing | Employee search |
| **`PensionProcessView`** | **Legacy:** one-shot create case + inline calculation (prefer Amount tab flow) | POST `process/` |
| **`PensionReportView`** | Legacy single-case report | GET `report/<id>/` |
| **`PensionCaseListView`** | Lists all pension cases | GET `cases/` |
| **`_build_employee_db_context`** | Assembles flags: intake, no-pay, proposal, commutation, amount done | Employee search |
| **`EmployeeSearchAPIView`** | Hub: Oracle employee + all tab completion state | GET `employees/<id>/` |
| **`NoPayLookupAPIView`** | Load no-pay days for employee | GET `no-pay/employee/` |
| **`NoPayEntryAPIView`** | Create/update `PensionCase` with service adjustments | POST/PUT `no-pay/` |
| **`CommutationCreateAPIView`** | Create/update commutation application; allocate `appcn_no` | POST/PUT `commutation/` |
| `_sync_commutation_to_oracle` | Push to Oracle mirror (may be disabled) | Commutation save |

---

### `pension_calculation.py`

| Function | Business logic | Notes |
|----------|----------------|-------|
| `PensionCalculationError` | Exception for calculation failures | |
| `round_up_to_rupee` | `ceil()` — used for SEPCOM lump sum | Oracle `Ceil` |
| `highest_side_round` | Floor +1 if fraction > 0.009 | Oracle `FFUNC_HIGHEST_SIDE_ROUND`; used for integrated commutation |
| `calculate_normal_pension` | Government: 50% of emoluments; Port: emoluments × min(TQS,30) / 80; floor Rs 1850 | Port of `FFUNC_NORMAL_PENSION` |
| `get_pension_option_for_employee` | Reads G/P from proposal | |
| `get_commutation_application_for_employee` | Finds `CommutationApplication` | |
| `get_commutation_percent_for_employee` | Reads commutation %; errors if not saved when required | |
| `reload_pension_case_from_db` | Fresh `PensionCase` + related data | Always use before calculate |
| `get_separation_type_for_employee` | RT / VR / etc. from proposal or case | |
| `is_voluntary_retirement` | True if separation type = VR | Defers commutation |
| `fetch_calculation_inputs_from_db` | Merges case, commutation %, Oracle oldbill overrides for no-pay | |
| **`calculate_pension_financials`** | **Core math:** TCCS/TQS from join/retire dates; pension; commutation via rate table; gratuity (cap 20 lakh) | Pure function |
| `serialize_amount_data` | Amount tab display structure | |
| **`run_pension_calculation_for_case`** | **Runs calculate + saves `PensionSummary`** | Amount Calculate API |
| `format_total_service` / `format_service_tenure_years_only` | Display helpers | Proposal UI |
| `get_service_components_for_case` | Service Y/M/D for display | |
| **`build_amount_lookup_payload`** | GET amount tab: inputs + summary + VR flags + first-month status | Amount Lookup API |

**Commutation formula (integrated):**

```
monthly_commuted = trunc(pension × comm% / 100)
lump_sum = highest_side_round(monthly_commuted × rate_per_rupee)
```

**Gratuity:** `(basic + DA) × 15 × qualifying_years / 26`, cap Rs 20,00,000.

---

### `pension_amount_api.py`

| Class | Business logic |
|-------|----------------|
| `PensionAmountLookupAPIView` | GET fresh amount tab state via `build_amount_lookup_payload` |
| `PensionAmountCalculateAPIView` | POST → `run_pension_calculation_for_case` + audit |
| `FirstMonthPensionGenerateAPIView` | POST → `generate_first_month_pension` (creates FMPEN + pensioner) |

---

### `pension_bill_api.py`

Thin DRF wrappers. Each POST logs audit via `audit.services.log_audit`.

| Class | Delegates to | Business step |
|-------|--------------|---------------|
| `PensionBillStatusAPIView` | `get_employee_bill_status` | Employee bill pipeline state |
| `PensionBillCandidatesAPIView` | `list_bill_candidates` | Who can be billed this month |
| `PensionBillGenerateAPIView` | `generate_pension_bills` | Create PPN bills |
| `PensionBillMonthStatusAPIView` | `get_month_setup_status` | Month open/closed |
| `PensionBillReprocessCandidatesAPIView` | `list_reprocess_candidates` | Bills needing regeneration |
| `PensionBillReprocessAPIView` | `reprocess_pension_bills` | Regenerate bill totals |
| `PensionBillCloseMonthAPIView` | `close_pension_bill_month` | Close pension bill month |
| `PensionBillPpnListAPIView` | `list_ppn_bills` | PPN list for LOV |
| `PensionLicReportAPIView` | `build_lic_report` | LIC treasurer report |
| `PensionBillAbstractReportAPIView` | `build_bill_abstract_report` | Payment abstract |
| `PensionJournalSummaryReportAPIView` | `build_journal_summary_report` | JV summary print |
| `PensionJournalSummaryBillsAPIView` | `list_bills_for_journal_report` | Bills for JV LOV |
| `PensionProposalSanctionReportAPIView` | `build_proposal_sanction_report` | Pension sanction letter |
| `PensionSepcomStatusAPIView` | `get_sepcom_status` | SEPCOM readiness |
| `PensionSepcomGenerateAPIView` | `generate_sepcom_for_employees` | Create SEPCOM rows |
| `PensionSepCommReportAPIView` | `build_sep_comm_report` | Separate commutation report |
| `PensionPpcBillStatusAPIView` | `get_ppc_employee_status` | PPC pipeline state |
| `PensionPpcBillCandidatesAPIView` | `list_ppc_candidates` | SEPCOM rows ready for PPC |
| `PensionPpcBillGenerateAPIView` | `generate_ppc_bills` | Create PPC bills |
| `PensionPpcBillListAPIView` | `list_ppc_bills` | PPC bills for month |
| `PensionCommutationBillReportAPIView` | `build_commutation_bill_report` | Commutation sanction (PEN path) |
| `PensionVoucherStatusAPIView` | `get_voucher_status` | JV exists for bill? |
| `PensionVoucherPreviewAPIView` | `preview_ppn_voucher` | Dry-run JV lines |
| `PensionVoucherGenerateAPIView` | `generate_ppn_voucher` | Post JV |
| `PensionManualJournalTemplateAPIView` | `blank_manual_journal_template` | Empty manual JV form |
| `PensionManualJournalSummaryAPIView` | `get_journal_summary` | JV summary lookup |
| `PensionManualJournalListAPIView` | `list_journals` | List JVs for period |
| `PensionManualJournalSaveAPIView` | `save_manual_journal` | Save manual JV with balance check |

---

### `services/commutation_rate_service.py`

| Function | Business logic |
|----------|----------------|
| `CommutationRateError` | Missing DOB, age, or rate in master |
| `age_next_birthday` | Oracle `FFUNC_AGE_NEXT_BIRTHDAY` — age for rate table lookup |
| `resolve_age_reference_date` | If application received >12 months after separation → MO certification date; else application received date |
| `get_rate_per_rupee` | Reads `fi_pn_md_commrate_rupee` by `AGE_YRS`, latest `WEF_DT` ≤ reference date |
| `resolve_commutation_context` | Collects DOB, dates, computed age for an employee |
| **`compute_commutation_amounts`** | `trunc(pension×comm%/100) × rate × share%/100`, rounded |
| **`compute_commutation_for_employee`** | End-to-end commutation math for one emp_cd |

---

### `services/commutation_defaults_service.py`

| Function | Business logic |
|----------|----------------|
| `load_commutation_defaults` | Prefill commutation form from Oracle `FiPnMhApplication`; sets VR flag and default `COM` |

---

### `services/sepcom_commutation_generation_service.py`

Oracle step 2 — `FI_PN_COMUTATION_GENERATION.fmb`

| Function | Business logic |
|----------|----------------|
| `SepcomGenerationError` | SEPCOM-specific errors |
| `_format_sepcom_id` | `SEP/MM/YYYY/serial` |
| `_allocate_sepcom_serial` | Next serial from fin control or max+1 |
| `_get_comm_app` | Find commutation application |
| `_commutation_period` | Bill month/year from commutation or application date |
| `_resolve_bank_cd` | Bank from commutation app or proposal |
| **`calculate_commutation_amount`** | Lump sum from pension summary + commutation app + age rate |
| **`get_sepcom_status`** | Readiness flags for UI |
| `_can_generate_sepcom` | Validates COM mode, no duplicate SEPCOM, amounts, bank |
| `_sync_mirror_commutation_amt` | Updates Oracle application mirror commutation amount |
| `_update_pensioner_commuted_portion` | Sets `commuted_portion` on pensioner master |
| **`generate_sepcom_for_employees`** | Creates `FiPnThSepcom` + `FiPnTdSepcom` (earn code 203) |

---

### `services/ppc_commutation_bill_service.py`

Oracle step 3 — `FI_PN_TH_Commutation_Bill_Gen.fmb`

| Function | Business logic |
|----------|----------------|
| `_format_ppc_bill_no` | `PPC/MM/YYYY/serial` |
| `_allocate_ppc_serial` | Serial from fin control |
| `_ensure_month_setup` | Creates month setup row for bill type C |
| `_sum_sepcom_earn_dedn` | Sums SEPCOM TD lines by earn/dedn type |
| `_validate_ppc_candidate` | SEPCOM exists, not already billed, bank present, amounts > 0 |
| `serialize_ppc_candidate` | One row for PPC candidate grid |
| **`list_ppc_candidates`** | Eligible SEPCOM headers for month |
| **`get_ppc_employee_status`** | Per-employee PPC state for UI |
| **`generate_ppc_bills`** | Groups by bank; creates `FiPnThPensionBill` type C; links SEPCOM + application bill_no |
| `list_ppc_bills` | Lists PPC bills for month |

---

### `services/sep_comm_report_service.py`

Oracle step 4 — `SEP_COMM_REP1.fmb`

| Function | Business logic |
|----------|----------------|
| `_build_sepcom_page` | One report page from SEPCOM header + TD lines |
| **`build_sep_comm_report`** | Full report payload; enriches with sanction narrative from commutation report |

---

### `services/commutation_bill_report_service.py`

| Function | Business logic |
|----------|----------------|
| `_build_row` | One employee sanction letter row (pension, MO cert, age narrative, lump sum) |
| **`build_commutation_bill_report`** | Recommendation & Sanction of Commutation (used for PEN and as fallback) |

---

### `services/first_month_pension_service.py`

| Function | Business logic |
|----------|----------------|
| **`get_first_month_status`** | Whether FMPEN already posted for employee |
| **`generate_first_month_pension`** | Allocates FMPEN_ID + PPN bill no; posts header/detail; creates/updates pensioner; **skips commutation line for VR** |

---

### `services/pension_bill_service.py`

| Function | Business logic |
|----------|----------------|
| `please_sum_pension` | Sums pension amounts for bill type/month |
| **`list_bill_candidates`** | FMPEN rows ready for PPN billing |
| **`generate_pension_bills`** | Oracle `FPROC_BILL_GENERATE` — group by bank, allocate PPN numbers |
| **`get_employee_bill_status`** | Employee position in PPN pipeline |
| **`build_lic_report`** | LIC treasurer report; ID card holdup line when not submitted |
| `list_reprocess_candidates` / **`reprocess_pension_bills`** | Regenerate when source data changed |
| **`close_pension_bill_month`** | Close month in `FiPnMhPmthsetup` |
| `repair_orphan_pension_bill` | CLI repair for broken bill links |

---

### `services/commutation_appcn_service.py` *(if present in repo)*

| Function | Business logic |
|----------|----------------|
| `get_next_appcn_no_with_fallback` | Next application number from Oracle or local max+1 |
| `resolve_appcn_no_for_create` | Uses submitted or auto-allocated appcn_no |

---

### `pension_proposal_api.py` *(referenced in urls.py)*

| Class / Function | Business logic |
|------------------|----------------|
| `PensionProposalLookupAPIView` | Load proposal or Oracle defaults |
| `PensionProposalAPIView` | Save proposal + earn/dedn grid |
| `validate_pension_proposal_data` | Oracle-equivalent validation rules |
| Bank / EarnDedn API views | Master data LOVs for proposal form |

---

### `process_intake_api.py` *(referenced in urls.py)*

| Class / Function | Business logic |
|------------------|----------------|
| `ProcessIntakeLookupAPIView` | Separation intake status |
| `ProcessIntakeAPIView` | Save separation type/date on case + proposal |

---

### `utils/amount_words.py`

| Function | Business logic |
|----------|----------------|
| `rupees_amount_in_words` | Indian numbering — amount in words for report footers |

---

## 8. Frontend — function reference by file

> **Note:** Full UI references additional components (`NoPayEntry`, `PensionProposalEntry`, `PensionReports`, etc.) imported by `EmployeeProcessTabs.jsx`. Only files currently under `src/components/` are listed in detail below.

---

### `EmployeeProcessTabs.jsx`

| Function | Business logic |
|----------|----------------|
| `formatAge` | Display `{years, months, days}` |
| `INFO_FIELDS` | Basic Info grid field definitions |
| **`EmployeeProcessTabs`** | Renders 7 workflow tabs and child components |

**Tabs rendered:** Basic Info → Commutation → No-Pay → Proposal → Amount → Bill & Journal → Reports

---

### `CommutationApplicationEntry.jsx`

| Function | Business logic |
|----------|----------------|
| `toInputDate` | Normalize dates for `<input type="date">` |
| `restorationFromCommutation` | Restoration date = commutation date + 15 years |
| `resolveBankFromMaster` | Bank code → description |
| `isVoluntaryRetirement` | Detect VR → default Separate Commutation |
| `buildNewCommutationForm` | New form defaults from employee/proposal |
| `mapCommutationDataToForm` | Saved record → form state |
| **`CommutationApplicationEntry`** | Main form: load/save commutation application |

**API calls:**

- `GET banks/`, `GET banks/<code>/`
- `GET commutation/` (next appcn_no)
- `POST commutation/`, `PUT commutation/<id>/`

**Key fields:** `impl_fpen_combill` (PEN vs COM), `commutation_per`, dates, bank, ref_no, bill_no, MO certificate.

---

### `PensionSepcomGeneration.jsx`

| Function | Business logic |
|----------|----------------|
| `formatMoney` | Indian number format |
| `loadStatus` | GET SEPCOM status; sync bill month/year from response |
| `handleGenerate` | POST SEPCOM generation for employee |
| **`PensionSepcomGeneration`** | Step 2 separate commutation UI |

**API:** `GET sepcom/status/employee/`, `POST sepcom/generate/`

**Prerequisites:** Commutation application saved with `COM`; amount calculated; bank present.

---

### `PensionAmountEntry.jsx`

| Function | Business logic |
|----------|----------------|
| `formatMoney` | Display formatting |
| `loadFromDb` | GET amount tab state |
| `handleCalculate` | POST calculate → saves summary |
| `handleFirstPensionGenerate` | POST first-month generate (FMPEN) |
| **`PensionAmountEntry`** | Amount tab UI |

**API:** `GET amount/employee/`, `POST amount/calculate/`, `POST amount/first-month-generate/`

**UI rules:** Blocks calculate if no-pay missing; shows VR deferred commutation message.

---

### `PensionBillJournalTabs.jsx`

| Function | Business logic |
|----------|----------------|
| **`PensionBillJournalTabs`** | Sub-tabs: PPN Bill, PPC Bill, Journal Voucher, Manual Journal |
| `useEmployeeBillContext` | Hook: shared bill no / JV period (from `hooks/useEmployeeBillContext.js`) |
| `refreshBillContext` | Reload on tab show |

**Child components:** `PensionBillGeneration`, `PensionPpcBillGeneration`, `PensionVoucherGeneration`, `PensionManualJournal`

---

### `PensionPpcBillGeneration.jsx`

| Function | Business logic |
|----------|----------------|
| `loadData` | PPC status + month close + candidates; auto-set month/year from `sepcom_month/year` |
| `toggleRow` | Select employees for batch PPC |
| `handleGenerate` | POST PPC bill generation |
| **`PensionPpcBillGeneration`** | Separate commutation bill UI |

**API:** `GET ppc/status/`, `GET month-status/`, `GET ppc/candidates/`, `POST ppc/generate/`

**Important:** Use SEPCOM month/year (e.g. 01/2024), not current calendar year.

---

### `PensionCommutationBillReport.jsx`

| Function | Business logic |
|----------|----------------|
| `loadReport` | Tries `sep-comm-report` first; falls back to `commutation-report` |
| `handlePrint` | Browser print |
| **`PensionCommutationBillReport`** | Commutation Sanction report tab |

---

### `PensionLicReportPrint.jsx`

| Function | Business logic |
|----------|----------------|
| `LicReportPage` | Renders one LIC report page (presentational) |
| **`PensionLicReportPrint`** | Print layout for LIC report |

No API calls — parent loads data and passes `report` prop.

---

### Expected components (imported but may live outside current `src/` snapshot)

| Component | Tab | Purpose |
|-----------|-----|---------|
| `NoPayEntry` | No-Pay | Save no-pay / dies-non days |
| `PensionProposalEntry` | Proposal | Pension proposal form |
| `PensionBillGeneration` | Bill → PPN | First pension bill generation |
| `PensionVoucherGeneration` | Bill → JV | Auto journal voucher |
| `PensionManualJournal` | Bill → Manual JV | Manual journal entry |
| `PensionReports` | Reports | Container for all report sub-tabs |
| `PensionBillContextBar` | Bill / Reports | Shows bill no, JV period, refresh |
| `PensionCommutationBillPrint` | Reports | Print layout for commutation sanction |
| `services/Api.js` | All | Axios wrapper for backend |
| `hooks/useEmployeeBillContext.js` | Bill | Bill status hook |

---

## 9. Complete API endpoint index

| Method | Path | Purpose |
|--------|------|---------|
| GET | `employees/<emp_id>/` | Employee hub + workflow flags |
| GET/POST | `process-intake/...` | Separation intake |
| GET/POST/PUT | `no-pay/...` | No-pay entry |
| GET/POST/PUT | `pension-proposal/...` | Proposal |
| GET/POST/PUT | `commutation/...` | Commutation application |
| GET | `amount/employee/<code>/` | Amount tab load |
| POST | `amount/calculate/` | Run calculation |
| POST | `amount/first-month-generate/` | Post FMPEN |
| GET | `pension-bill/status/employee/<code>/` | PPN bill status |
| GET | `pension-bill/candidates/` | PPN candidates |
| POST | `pension-bill/generate/` | Generate PPN |
| GET | `pension-bill/sepcom/status/employee/<code>/` | SEPCOM status |
| POST | `pension-bill/sepcom/generate/` | Generate SEPCOM |
| GET | `pension-bill/ppc/status/employee/<code>/` | PPC status |
| GET | `pension-bill/ppc/candidates/` | PPC candidates |
| POST | `pension-bill/ppc/generate/` | Generate PPC |
| GET | `pension-bill/lic-report/` | LIC report |
| GET | `pension-bill/commutation-report/` | Commutation sanction |
| GET | `pension-bill/sep-comm-report/` | Separate commutation report |
| GET | `pension-bill/proposal-sanction-report/` | Pension sanction |
| GET | `pension-bill/bill-abstract-report/` | Bill abstract |
| GET | `pension-bill/journal-summary-report/` | JV summary |
| GET/POST | `pension-bill/voucher/...` | Auto JV |
| GET/POST | `pension-bill/manual-journal/...` | Manual JV |

Full route list: `first_pension/urls.py`.

---

## 10. How to run and test locally

### Backend

```bash
cd SMPK/backend/config
../venv/Scripts/python.exe manage.py runserver
```

### Frontend

```bash
cd SMPK/frontend/frontend
npm install
npm run dev
```

### Suggested test employees

| emp_cd | Type | Use for |
|--------|------|---------|
| 42230 | Normal RT | Full PEN flow; amounts should match Oracle |
| 43186 | VR | Separate COM flow; SEPCOM → PPC → report |

### Debug tips

1. Always check `GET first-pension/employees/<id>/` for workflow flags first.
2. Amount issues → trace `run_pension_calculation_for_case` → `calculate_pension_financials`.
3. SEPCOM amount → trace `calculate_commutation_amount` → `commutation_rate_service`.
4. Report failures → check Django console for `FieldError` or missing prerequisites.
5. Oracle mirror tables (`fi_pn_*`) are read/write — compare with SMPK local tables.

---

## 11. Known gaps and pending work

| Item | Description |
|------|-------------|
| VR SEPCOM pension source | SEPCOM uses `PensionSummary.pension_amount`; Oracle uses disbursed pension from pensioner/application — can mismatch (see emp 43186) |
| Oracle sync on save | `_sync_*_to_oracle` functions may be disabled — local save works; mirror may lag |
| Frontend completeness | Some tab components referenced but not in minimal `src/` snapshot — verify full deployment tree |
| SEPCOM delete/regenerate | Oracle `FPROC_DELETE` not yet ported |
| Nominee split | Multiple SEPCOM rows per employee not implemented |
| PPC JV | Journal voucher for PPC bills (parallel to PPN PNJV) |

---

## Quick reference — who calls whom

```
Amount Calculate
  → run_pension_calculation_for_case
    → calculate_pension_financials
      → commutation_rate_service.compute_commutation_amounts

First-month Generate
  → generate_first_month_pension
    → FiPnThFirstMonthPension, FiPnMhPensioner

PPN Bill Generate
  → generate_pension_bills
    → FiPnThPensionBill (type N)

SEPCOM Generate
  → generate_sepcom_for_employees
    → calculate_commutation_amount
    → FiPnThSepcom, FiPnTdSepcom

PPC Bill Generate
  → generate_ppc_bills
    → FiPnThPensionBill (type C)

Commutation Report
  → build_sep_comm_report (COM) OR build_commutation_bill_report (PEN)
```

---

*Document maintained for SMPK First Pension handover. For questions about Oracle business rules, refer to `.fmb` files in repo root (e.g. `FI_PN_COMUTATION_GENERATION.fmb`).*
