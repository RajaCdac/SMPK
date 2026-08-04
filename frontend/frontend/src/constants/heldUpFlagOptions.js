/**
 * HELD_GRAT_FLG — form label "Held Up Flg".
 * Which payment component is withheld (FI_PN_MH_PENSION_PROPOSAL_E.fmb).
 * Amount (HELD_GRAT_AMT) required when flag is P, C, R, or S.
 */
export const HELD_UP_FLAG_OPTIONS = [
  { value: "N", label: "Not Appl" },
  { value: "G", label: "Gratuity Full" },
  { value: "H", label: "Gratuity Partial" },
  { value: "C", label: "Commutation" },
  { value: "R", label: "Relief" },
  { value: "P", label: "Pension" },
];

export const HELD_FLAGS_REQUIRING_AMT = ["P", "C", "R", "S"];

export function normalizeHeldUpFlag(value) {
  const code = String(value || "").trim().toUpperCase();
  if (!code) return "";
  if (code === "GP") return "H";
  return code;
}

export function heldFlagRequiresAmount(flag) {
  return HELD_FLAGS_REQUIRING_AMT.includes(normalizeHeldUpFlag(flag));
}

export function heldFlagIsActive(flag) {
  const code = normalizeHeldUpFlag(flag);
  return Boolean(code) && code !== "N";
}
