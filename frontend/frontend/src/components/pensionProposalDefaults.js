export const emptyEarningRow = {
  type: "EARN",
  code: "",
  desc: "",
  amount: "",
  deduction_priority: "",
};

export const defaultEarningRows = () => [
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

export function buildEmptyProposalForm(employee) {
  const ret = employee?.expected_retirement_date || "";
  const parts = ret.split("-");
  const db = employee?.proposal_defaults || {};
  const serviceParts = [];
  if (employee?.join_date) serviceParts.push(`From ${employee.join_date}`);
  if (ret) serviceParts.push(`to ${ret}`);

  return {
    id: null,
    emp_cd: employee?.emp_id || "",
    emp_name: employee?.name || "",
    employee_status: "EMPLOYEE",
    ca_number: "",
    pension_type: "",
    pension_proposal_no: "",
    eligible_double_family_pension: false,
    separation_type: db.separation_type || "",
    separation_date: toInputDate(db.separation_date) || "",
    implemented_year: db.implemented_year ?? parts[2] ?? "",
    implemented_month: db.implemented_month ?? parts[1] ?? "",
    service_tenure: serviceParts.join(" ") || "",
    pension_option: "",
    option_given_by: "",
    regn_no: "",
    regn_date: "",
    start_month: db.start_month ?? parts[1] ?? "",
    start_year: db.start_year ?? parts[2] ?? "",
    pension_roll_no: "",
    pension_proposal_date: "",
    double_family_pension_upto_date: "",
    provisional_pension_pct: "",
    bank_cd: db.bank_cd || "",
    bank_name: db.bank_name || "",
    account_no: db.account_no || "",
    vigilance_clearance_ref_no: "",
    vigilance_clearance_ref_dt: "",
    lic_bank_cd: "",
    lic_bank_name: "",
    vr_ref_no: "",
    vr_ref_dt: "",
    compassionate_allowance: "",
    quarter_status: "",
    nominee_eform: "",
    compassionate_allowance_amt: "",
    port_city_resident: "",
    gratuity_option: "",
    retirement_cpi: "",
    id_card_submitted: false,
    vigilance_cleared: false,
    incentive_holder: "",
    held_up_flag: "",
    held_gratuity_amt: "",
    extra_tccs_enabled: false,
    extra_tccs_years: 0,
    extra_tccs_months: 0,
    extra_tccs_days: 0,
    earning_deductions: defaultEarningRows(),
  };
}
