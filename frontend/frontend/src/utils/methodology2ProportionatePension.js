/**
 * Methodology-2 proportionate pension (pre-01-Jan-2007 retirements).
 *
 * Mirrors backend methodology2/services/proportionate_pension.py:
 *   - Only when retirement < 2007-01-01
 *   - TQS round: <3m → Y; 3–8m → Y+0.5; 9–11m → Y+1
 *   - Full at rounded TQS ≥ 20 (e.g. 19y 9m); else factor = TQS/20
 *
 * Backend applies the amounts; this file is for UI labels / local checks.
 */

export const PRE_2007_RETIREMENT_CUTOFF = "2007-01-01";
export const FULL_PENSION_TQS_YEARS = 20;

export function roundTqsYearsOracle(tqsYears, tqsMonths) {
  const years = Number(tqsYears) || 0;
  const months = Number(tqsMonths) || 0;
  if (months < 3) return years;
  if (months < 9) return years + 0.5;
  return years + 1;
}

function asIsoDate(value) {
  if (!value) return null;
  const s = String(value).trim().slice(0, 10);
  return /^\d{4}-\d{2}-\d{2}$/.test(s) ? s : null;
}

/** True when retirement/separation is strictly before 01-Jan-2007. */
export function isPre2007Retirement(retirementDate) {
  const iso = asIsoDate(retirementDate);
  return !!iso && iso < PRE_2007_RETIREMENT_CUTOFF;
}

/**
 * @returns {{ applied: boolean, fullPension: boolean, factor: number, roundedTqs: number|null, note: string }}
 */
export function resolveServiceFactor({
  retirementDate,
  tqsYr = null,
  tqsMonth = null,
  tqsDays = null,
} = {}) {
  if (!isPre2007Retirement(retirementDate)) {
    return {
      applied: false,
      fullPension: true,
      factor: 1,
      roundedTqs: null,
      note: "Not applicable (retirement on/after 01-Jan-2007).",
    };
  }
  if (tqsYr == null && tqsMonth == null && tqsDays == null) {
    return {
      applied: false,
      fullPension: true,
      factor: 1,
      roundedTqs: null,
      note: "Pre-2007 retirement but TQS not supplied.",
    };
  }
  const roundedTqs = roundTqsYearsOracle(tqsYr, tqsMonth);
  if (roundedTqs >= FULL_PENSION_TQS_YEARS) {
    return {
      applied: true,
      fullPension: true,
      factor: 1,
      roundedTqs,
      note: `Pre-2007: rounded TQS ${roundedTqs} >= ${FULL_PENSION_TQS_YEARS} -> full pension.`,
    };
  }
  const factor = roundedTqs / FULL_PENSION_TQS_YEARS;
  return {
    applied: true,
    fullPension: false,
    factor,
    roundedTqs,
    note: `Pre-2007: rounded TQS ${roundedTqs} < ${FULL_PENSION_TQS_YEARS} -> proportionate x (${roundedTqs}/${FULL_PENSION_TQS_YEARS}).`,
  };
}

/** Prefer server meta on pension.proportionate when present. */
export function proportionateNoteFromPension(pension) {
  const meta = pension?.proportionate;
  if (!meta) return "";
  return String(meta.note || "");
}

export function isProportionateReduced(pension) {
  const meta = pension?.proportionate;
  if (!meta?.applied) return false;
  const factor = Number(meta.factor);
  return Number.isFinite(factor) && factor < 1;
}
