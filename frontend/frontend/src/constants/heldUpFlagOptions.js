/**
 * HELD_GRAT_FLG — form label "Held Up Flg".
 * Which payment component is withheld (FI_PN_MH_PENSION_PROPOSAL_E.fmb).
 *
 * Amt. field:
 *   - Enabled for G, H, P, C, R, S
 *   - Required for H (partial), P, C, R, S
 *   - G (full) uses calculated full gratuity; Amt. stays editable but optional
 */
export const HELD_UP_FLAG_OPTIONS = [
  { value: "N", label: "Not Appl" },
  { value: "G", label: "Gratuity Full" },
  { value: "H", label: "Gratuity Partial" },
  { value: "C", label: "Commutation" },
  { value: "R", label: "Relief" },
  { value: "P", label: "Pension" },
];

/** Amt. input enabled (not greyed out). */
export const HELD_FLAGS_AMOUNT_ENABLED = ["G", "H", "P", "C", "R", "S"];

/** Amt. must be entered / positive. */
export const HELD_FLAGS_REQUIRING_AMT = ["H", "P", "C", "R", "S"];

export function normalizeHeldUpFlag(value) {
  const code = String(value || "").trim().toUpperCase();
  if (!code) return "";
  if (code === "GP") return "H";
  return code;
}

export function heldFlagAmountEnabled(flag) {
  return HELD_FLAGS_AMOUNT_ENABLED.includes(normalizeHeldUpFlag(flag));
}

export function heldFlagRequiresAmount(flag) {
  return HELD_FLAGS_REQUIRING_AMT.includes(normalizeHeldUpFlag(flag));
}

export function heldFlagIsActive(flag) {
  const code = normalizeHeldUpFlag(flag);
  return Boolean(code) && code !== "N";
}
