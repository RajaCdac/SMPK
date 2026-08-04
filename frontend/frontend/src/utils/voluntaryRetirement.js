/** True when employee separation type is Voluntary Retirement (VR). */
export function isVoluntaryRetirement(employee) {
  if (!employee) return false;

  const defaults = employee.commutation_defaults || {};
  if (defaults.is_voluntary_retirement) return true;

  if (employee.amount_data?.is_voluntary_retirement) return true;
  if (employee.amount_data?.defer_commutation) return true;

  const fromIntake = (employee.process_intake_data?.separation_type || "")
    .trim()
    .toUpperCase();
  const fromProposal = (employee.proposal_data?.separation_type || "")
    .trim()
    .toUpperCase();

  return fromIntake === "VR" || fromProposal === "VR";
}
