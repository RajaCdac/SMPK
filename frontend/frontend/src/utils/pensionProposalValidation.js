/** Validation rules aligned with FI_PN_MH_PENSION_PROPOSAL_E.fmb */

import {
  heldFlagIsActive,
  heldFlagRequiresAmount,
  normalizeHeldUpFlag,
} from "../constants/heldUpFlagOptions";
import {
  normalizeWithholdReason,
  withholdReasonIsActive,
} from "../constants/withholdReasonOptions";

export { heldFlagRequiresAmount, heldFlagIsActive, normalizeHeldUpFlag };

function parseIsoDate(value) {
  const s = String(value || "").trim().slice(0, 10);
  if (!/^\d{4}-\d{2}-\d{2}$/.test(s)) return null;
  const d = new Date(`${s}T00:00:00`);
  return Number.isNaN(d.getTime()) ? null : d;
}

function yyyyMmFromDate(value) {
  const d = parseIsoDate(value);
  if (!d) return null;
  return d.getFullYear() * 100 + (d.getMonth() + 1);
}

function isAfter(a, b) {
  const da = parseIsoDate(a);
  const db = parseIsoDate(b);
  if (!da || !db) return false;
  return da.getTime() > db.getTime();
}

function isBlank(value) {
  return value === null || value === undefined || String(value).trim() === "";
}

function isPositiveNumber(value) {
  if (isBlank(value)) return false;
  const n = Number(value);
  return !Number.isNaN(n) && n > 0;
}

export function validatePensionProposalForm(form, { recordExists = false } = {}) {
  const errors = [];

  if (isBlank(form.separation_date)) {
    errors.push(
      "Separation date is not available. Update employee master (FI_XX_MH_EMP_ADM) first."
    );
  }
  if (isBlank(form.separation_type)) {
    errors.push(
      "Separation type is not available. Update employee master first."
    );
  }
  if (isBlank(form.ca_number)) {
    errors.push(
      "CA No. is required (links the earning/deduction grid to fi_pn_md_pension_proposal)."
    );
  }
  if (isBlank(form.pension_type)) {
    errors.push("Pension Type is required.");
  }

  const sepYm = yyyyMmFromDate(form.separation_date);
  const startMonth = Number(form.start_month);
  const startYear = Number(form.start_year);
  if (sepYm && startMonth >= 1 && startMonth <= 12 && startYear > 0) {
    const startYm = startYear * 100 + startMonth;
    if (startYm < sepYm) {
      errors.push(
        "Start month and year cannot be less than Separation Date."
      );
    }
  }

  if (
    String(form.pension_type || "").toUpperCase() === "N" &&
    !isBlank(form.vigilance_clearance_ref_dt) &&
    !isBlank(form.separation_date) &&
    isAfter(form.vigilance_clearance_ref_dt, form.separation_date)
  ) {
    errors.push(
      "Vigilance clearance date cannot be after Separation Date for Normal Pension."
    );
  }

  if (
    !isBlank(form.double_family_pension_upto_date) &&
    !isBlank(form.separation_date) &&
    isAfter(form.separation_date, form.double_family_pension_upto_date)
  ) {
    errors.push(
      "Double Family Pension upto date must not be before Separation Date."
    );
  }

  if (String(form.pension_type || "").toUpperCase() === "P") {
    if (isBlank(form.provisional_pension_pct)) {
      errors.push("Please enter Provisional Pension percentage.");
    } else {
      const pct = Number(form.provisional_pension_pct);
      if (Number.isNaN(pct) || pct < 0 || pct > 100) {
        errors.push("Provisional Pension % must be between 0 and 100.");
      }
    }
  }

  if (String(form.pension_type || "").toUpperCase() === "C" && recordExists) {
    if (isBlank(form.compassionate_allowance)) {
      errors.push("Compassionate Allowance option is required for this pension type.");
    }
    if (!isPositiveNumber(form.compassionate_allowance_amt)) {
      errors.push("Compassionate Allowance amount is required for this pension type.");
    }
  }

  if (heldFlagRequiresAmount(form.held_up_flag)) {
    if (!isPositiveNumber(form.held_gratuity_amt)) {
      errors.push("Held amount is required for the selected Held Up flag.");
    }
  }

  const recoveryFields = [
    form.held_recovery_amt,
    form.held_recovery_date,
    form.held_recovery_ref_no,
    form.held_recovery_remarks,
  ];
  const hasRecovery = recoveryFields.some((v) => !isBlank(v));
  if (hasRecovery) {
    if (!isPositiveNumber(form.held_recovery_amt)) {
      errors.push("Amount recovered is required when recording a recovery.");
    }
    if (isBlank(form.held_recovery_date)) {
      errors.push("Recovery date is required when recording a recovery.");
    }
  }

  const implMonth = form.implemented_month;
  if (!isBlank(implMonth)) {
    const m = Number(implMonth);
    if (Number.isNaN(m) || m < 1 || m > 12) {
      errors.push("Implementation month must be between 1 and 12.");
    }
  }

  const rows = form.earning_deductions || [];
  const codesSeen = new Set();
  rows.forEach((row, index) => {
    const code = String(row.code || "").trim();
    if (!code) return;

    if (codesSeen.has(code)) {
      errors.push(`Duplicate earning/deduction code ${code} in row ${index + 1}.`);
    }
    codesSeen.add(code);

    if (String(row.type || "").toUpperCase().startsWith("D")) {
      if (!isPositiveNumber(row.amount) && !isBlank(row.amount)) {
        errors.push(`Invalid amount for deduction code ${code} (row ${index + 1}).`);
      } else if (isBlank(row.amount)) {
        errors.push(`Amount is required for deduction code ${code} (row ${index + 1}).`);
      }
    }
  });

  return errors;
}

export function sanitizePensionProposalForm(form) {
  const next = { ...form };
  next.held_up_flag = normalizeHeldUpFlag(next.held_up_flag);
  next.quarter_status = normalizeWithholdReason(next.quarter_status);
  next.earning_deductions = (next.earning_deductions || []).map((row) => {
    const type = String(row.type || "E").toUpperCase();
    const isDeduction = type.startsWith("D");
    return {
      ...row,
      deduction_priority: isDeduction ? row.deduction_priority : "",
    };
  });
  return next;
}
