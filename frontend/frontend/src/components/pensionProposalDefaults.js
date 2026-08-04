export const emptyEarningRow = {
  type: "E",
  code: "",
  desc: "",
  amount: "",
  deduction_priority: "",
};

export const defaultEarningRows = () => [
  { ...emptyEarningRow },
  { ...emptyEarningRow },
  { ...emptyEarningRow },
  { ...emptyEarningRow },
];

function toInputDate(dateStr) {
  if (!dateStr) return "";
  if (/^\d{4}-\d{2}-\d{2}/.test(String(dateStr))) return String(dateStr).slice(0, 10);
  const parts = String(dateStr).split("-");
  if (parts.length === 3 && parts[0].length <= 2) {
    return `${parts[2]}-${parts[1]}-${parts[0]}`;
  }
  return dateStr;
}

/** Round Y/M/D tenure to whole years (31Y 9M → 32 Yrs). */
export function formatServiceTenureYearsOnly(value) {
  if (!value) return "";
  const s = String(value).trim();
  const parts = s.match(/^(\d+)\s*Y(?:\s*(\d+)\s*M)?(?:\s*(\d+)\s*D)?/i);
  if (parts) {
    const years = parseInt(parts[1], 10);
    const months = parseInt(parts[2] || "0", 10);
    const days = parseInt(parts[3] || "0", 10);
    const rounded = months > 0 || days > 0 ? years + 1 : years;
    return `${rounded} Yrs`;
  }
  const yrsOnly = s.match(/^(\d+)\s*Yrs?$/i);
  if (yrsOnly) return `${yrsOnly[1]} Yrs`;
  return s;
}

function parseDateParts(dateStr) {
  if (!dateStr) return null;
  const text = String(dateStr).trim();
  if (/^\d{4}-\d{2}-\d{2}/.test(text)) {
    const [year, month] = text.slice(0, 10).split("-");
    return { month: parseInt(month, 10), year: parseInt(year, 10) };
  }
  const parts = text.split("-");
  if (parts.length === 3 && parts[0].length <= 2) {
    return { month: parseInt(parts[1], 10), year: parseInt(parts[2], 10) };
  }
  return null;
}

function resolveStartPeriod(employee) {
  const db = employee?.proposal_defaults || {};
  const intake = employee?.process_intake_data || {};
  const sepType = (
    db.separation_type ||
    intake.separation_type ||
    ""
  )
    .trim()
    .toUpperCase();
  const sepDate =
    db.separation_date ||
    intake.separation_date ||
    "";

  if (sepType === "VR" && sepDate) {
    const parts = parseDateParts(sepDate);
    if (parts) {
      return { start_month: parts.month, start_year: parts.year };
    }
  }

  if (db.start_month != null && db.start_year != null) {
    return { start_month: db.start_month, start_year: db.start_year };
  }

  const ret = employee?.expected_retirement_date || "";
  const retParts = ret.split("-");
  return {
    start_month: retParts[1] ?? "",
    start_year: retParts[2] ?? "",
  };
}

export function applyVrStartPeriod(form, employee) {
  const db = employee?.proposal_defaults || {};
  const intake = employee?.process_intake_data || {};
  const sepType = (
    form.separation_type ||
    db.separation_type ||
    intake.separation_type ||
    ""
  )
    .trim()
    .toUpperCase();
  const sepDate =
    form.separation_date ||
    toInputDate(db.separation_date) ||
    toInputDate(intake.separation_date) ||
    "";
  if (sepType !== "VR" || !sepDate) {
    return form;
  }
  const parts = parseDateParts(sepDate);
  if (!parts) {
    return form;
  }
  return {
    ...form,
    start_month: parts.month,
    start_year: parts.year,
  };
}

function resolveServiceTenure(employee) {
  const db = employee?.proposal_defaults || {};
  const raw =
    employee?.amount_data?.total_service ||
    db.service_tenure ||
    "";
  return formatServiceTenureYearsOnly(raw);
}

function fieldOr(dbValue, fallback = "") {
  if (dbValue === null || dbValue === undefined || dbValue === "") return fallback;
  return dbValue;
}

export function buildEmptyProposalForm(employee) {
  const db = employee?.proposal_defaults || {};
  const intake = employee?.process_intake_data || {};
  const { start_month, start_year } = resolveStartPeriod(employee);

  const earningRows =
    Array.isArray(db.earning_deductions) && db.earning_deductions.length > 0
      ? db.earning_deductions.map((row) => ({
          type: row.type || "E",
          code: row.code || "",
          desc: row.desc || "",
          amount: row.amount ?? "",
          deduction_priority: row.deduction_priority ?? "",
        }))
      : defaultEarningRows();

  return {
    id: null,
    emp_cd: employee?.emp_id || "",
    emp_name: employee?.name || "",
    employee_status: fieldOr(db.employee_status, "P"),
    ca_number: fieldOr(db.ca_number, employee?.proposal_data?.ca_number || ""),
    pension_type: fieldOr(db.pension_type),
    pension_proposal_no: fieldOr(db.pension_proposal_no),
    eligible_double_family_pension: Boolean(db.eligible_double_family_pension),
    separation_type: fieldOr(
      db.separation_type,
      intake.separation_type || ""
    ),
    separation_date:
      toInputDate(db.separation_date) ||
      toInputDate(intake.separation_date) ||
      "",
    implemented_year: fieldOr(db.implemented_year, ""),
    implemented_month: fieldOr(db.implemented_month, ""),
    service_tenure: resolveServiceTenure(employee),
    pension_option: fieldOr(db.pension_option),
    option_given_by: fieldOr(db.option_given_by),
    regn_no: fieldOr(db.regn_no),
    regn_date: toInputDate(db.regn_date) || "",
    start_month: db.start_month ?? start_month,
    start_year: db.start_year ?? start_year,
    pension_roll_no: fieldOr(db.pension_roll_no),
    pension_proposal_date: toInputDate(db.pension_proposal_date) || "",
    double_family_pension_upto_date:
      toInputDate(db.double_family_pension_upto_date) || "",
    provisional_pension_pct: fieldOr(db.provisional_pension_pct, ""),
    bank_cd: fieldOr(db.bank_cd),
    bank_name: fieldOr(db.bank_name),
    account_no: fieldOr(db.account_no),
    vigilance_clearance_ref_no: fieldOr(db.vigilance_clearance_ref_no),
    vigilance_clearance_ref_dt:
      toInputDate(db.vigilance_clearance_ref_dt) || "",
    lic_bank_cd: fieldOr(db.lic_bank_cd),
    lic_bank_name: fieldOr(db.lic_bank_name),
    vr_ref_no: fieldOr(db.vr_ref_no),
    vr_ref_dt: toInputDate(db.vr_ref_dt) || "",
    compassionate_allowance: fieldOr(db.compassionate_allowance),
    quarter_status: fieldOr(db.quarter_status),
    nominee_eform: fieldOr(db.nominee_eform),
    compassionate_allowance_amt: fieldOr(db.compassionate_allowance_amt, ""),
    port_city_resident: fieldOr(db.port_city_resident),
    gratuity_option: fieldOr(db.gratuity_option, ""),
    retirement_cpi: fieldOr(db.retirement_cpi, ""),
    id_card_submitted: Boolean(db.id_card_submitted),
    vigilance_cleared: Boolean(db.vigilance_cleared),
    incentive_holder: fieldOr(db.incentive_holder),
    held_up_flag: fieldOr(db.held_up_flag),
    held_gratuity_amt: fieldOr(db.held_gratuity_amt, ""),
    held_recovery_amt: fieldOr(db.held_recovery_amt, ""),
    held_recovery_date: toInputDate(db.held_recovery_date) || "",
    held_recovery_ref_no: fieldOr(db.held_recovery_ref_no),
    held_recovery_remarks: fieldOr(db.held_recovery_remarks),
    extra_tccs_enabled: Boolean(db.extra_tccs_enabled),
    extra_tccs_years: Number(db.extra_tccs_years || 0),
    extra_tccs_months: Number(db.extra_tccs_months || 0),
    extra_tccs_days: Number(db.extra_tccs_days || 0),
    earning_deductions: earningRows,
  };
}
