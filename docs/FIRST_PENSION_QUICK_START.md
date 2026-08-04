# Quick Start Checklist — First Pension Module

Use this checklist on Day 1 and when processing a new employee.

---

## Day 1 — Environment setup

- [ ] Clone repo and open `SMPK/backend/config` + `SMPK/frontend/frontend`
- [ ] Backend: activate venv → `python manage.py runserver`
- [ ] Frontend: `npm install` → `npm run dev`
- [ ] Confirm API base URL in `frontend/src/services/Api.js` points to Django
- [ ] Read **§1–4** of the full handover doc (what / workflow / VR vs RT)
- [ ] Open Oracle `.fmb` reference folder at repo root (optional)

---

## Key files — read these first

| Priority | File | Why |
|----------|------|-----|
| 1 | `first_pension/urls.py` | All API routes |
| 2 | `first_pension/pension_calculation.py` | Pension / gratuity / commutation math |
| 3 | `first_pension/services/commutation_rate_service.py` | Age rate table lookup |
| 4 | `first_pension/services/pension_bill_service.py` | PPN bill + LIC report |
| 5 | `first_pension/services/sepcom_commutation_generation_service.py` | VR separate commutation step 2 |
| 6 | `first_pension/services/ppc_commutation_bill_service.py` | VR separate commutation step 3 |
| 7 | `components/EmployeeProcessTabs.jsx` | UI workflow shell |

---

## Normal retirement (RT) — processing checklist

Employee example: **42230**

- [ ] **No-Pay tab** — Save no-pay / dies-non days → `POST no-pay/`
- [ ] **Proposal tab** — Save proposal (separation RT, bank, CA) → `POST pension-proposal/`
- [ ] **Commutation tab** — Save application with **PEN** (with pension) → `POST commutation/`
- [ ] **Amount tab** — Calculate → `POST amount/calculate/` (check pension + commutation + gratuity)
- [ ] **Amount tab** — First-month generate → `POST amount/first-month-generate/`
- [ ] **Bill → PPN** — Generate bill for correct month/year
- [ ] **Bill → Journal Voucher** — Generate JV for PPN bill
- [ ] **Reports** — LIC report, Pension Sanction, Bill Abstract, Journal Summary

**Verify:** `PensionSummary.pension_amount` = Oracle `PEN_AMT`; commutation lump sum uses age from `fi_pn_md_commrate_rupee`.

---

## Voluntary retirement (VR) — two-phase checklist

Employee example: **43186**

### Phase A — First pension (no commutation)

- [ ] Proposal: separation type **VR**
- [ ] Commutation application can wait OR save early with **COM** for later
- [ ] Amount: pension + gratuity only (commutation shows **Deferred**)
- [ ] Bill → **PPN only** (no commutation line)
- [ ] Reports: LIC + Pension Sanction

### Phase B — Separate commutation (later)

- [ ] **Commutation tab** — Application saved, **COM** (Separate Commutation), bank, dates, comm %
- [ ] **Commutation tab** — **Generate SEPCOM** for correct month/year (e.g. 01/2024)
- [ ] **Bill → PPC** — Use **same month/year as SEPCOM** (not current year)
- [ ] **Reports → Commutation Sanction** — Uses `sep-comm-report` after SEPCOM

**Watch out:** SEPCOM amount must use **disbursed pension** (Oracle pensioner), not a recalculated higher summary — see Known Gaps in full doc.

---

## Debug cheat sheet

| Symptom | Check |
|---------|--------|
| Amount won't calculate | No-pay saved? Commutation % saved? (not required for VR) |
| Commutation report fails | SEPCOM generated? Backend error log (earn/dedn field names) |
| PPC shows no candidates | Bill month/year must match SEPCOM (e.g. 1/2024 not 2026) |
| Wrong commutation lump sum | Compare `PensionSummary.pension_amount` vs Oracle `PEN_AMT` |
| Wrong age rate | DOB + application received / MO cert date → `fi_pn_md_commrate_rupee` |

**Hub API:** `GET first-pension/employees/<emp_id>/` — shows which tabs are complete.

---

## API quick index (most used)

```
GET  employees/<id>/              Workflow hub
POST no-pay/                        No-pay save
POST pension-proposal/              Proposal save
POST commutation/                   Commutation application
GET  amount/employee/<id>/          Amount tab load
POST amount/calculate/              Run calculation
POST amount/first-month-generate/   Post FMPEN
POST pension-bill/generate/         PPN bill
GET  pension-bill/sepcom/status/    SEPCOM status
POST pension-bill/sepcom/generate/  SEPCOM create
POST pension-bill/ppc/generate/     PPC bill
GET  pension-bill/sep-comm-report/  VR commutation report
GET  pension-bill/commutation-report/  RT commutation report
GET  pension-bill/lic-report/       LIC report
```

---

## Oracle form → code map (memorize)

| Step | Oracle | SMPK service / UI |
|------|--------|-------------------|
| Application | FI_PN_MH_APPLICATION | CommutationApplicationEntry |
| Amount / FMPEN | FI_PN_FIRST_PENSION_PROCESS | pension_calculation + first_month_pension_service |
| SEPCOM | FI_PN_COMUTATION_GENERATION | sepcom_commutation_generation_service |
| PPC bill | FI_PN_TH_Commutation_Bill_Gen | ppc_commutation_bill_service |
| Sep report | SEP_COMM_REP1 | sep_comm_report_service |
| PPN bill | Bill generate FMB | pension_bill_service |

---

*Full function-by-function reference: see FIRST_PENSION_CODE_HANDOVER.md*
