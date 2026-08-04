/** Map dashboard retirement row → employee shape used by process tabs. */
export function buildEmployeeFromDashboardRow(emp) {
  return {
    emp_id: emp.emp_code,
    name: emp.name,
    join_date: emp.joining_date,
    expected_retirement_date: emp.retirement_date,
    birth_date: emp.birth_date,
    designation: emp.designation,
    scale: emp.scale,
    basic_amount: emp.last_basic,
    class: emp.class,
    age_on_appointment: emp.age_on_appointment,
    age_on_retirement: emp.age_on_retirement,
    process_intake_completed: false,
    process_intake_data: null,
    commutation_exists: false,
    commutation_data: null,
    no_pay_exists: false,
    no_pay_data: null,
    proposal_exists: false,
    proposal_data: null,
    amount_exists: false,
    amount_data: null,
    partial: false,
  };
}

export function mergeEmployeeDetail(dashboardRow, apiData, intakeData) {
  const base = buildEmployeeFromDashboardRow(dashboardRow);
  const merged = {
    ...base,
    ...(apiData || {}),
    emp_id: apiData?.emp_id ?? base.emp_id,
  };

  if (intakeData) {
    merged.process_intake_completed = intakeData.completed;
    merged.process_intake_data = intakeData.intake_data;
  }

  if (merged.process_intake_completed === undefined) {
    merged.process_intake_completed = Boolean(
      merged.process_intake_data?.separation_type &&
        merged.process_intake_data?.separation_date
    );
  }

  return merged;
}
