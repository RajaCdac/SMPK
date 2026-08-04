/**
 * QUARTER_STATUS — form label "Reasons to Withhold".
 * Why payment is blocked (clearances / attachments) per FMB list.
 */
export const WITHHOLD_REASON_OPTIONS = [
  { value: "V", label: "Quater Clearence" },
  { value: "O", label: "Electricity Clearence" },
  { value: "Q", label: "Quter & Elec Clearence" },
  { value: "A", label: "Court Attachement" },
  { value: "S", label: "Qtr Elec Crt Charges" },
  { value: "T", label: "Qtr clear & Crt Attachemnt" },
  { value: "U", label: "Elec & Crt Attachement" },
  { value: "M", label: "Co-Operative Credit Society" },
];

/** Map legacy numeric codes from early SMPK UI to Oracle-aligned values. */
const LEGACY_WITHHOLD_CODES = {
  "1": "O",
  "2": "Q",
};

export function normalizeWithholdReason(value) {
  const code = String(value || "").trim().toUpperCase();
  if (!code) return "";
  return LEGACY_WITHHOLD_CODES[code] || code;
}

export function withholdReasonIsActive(value) {
  return Boolean(normalizeWithholdReason(value));
}
