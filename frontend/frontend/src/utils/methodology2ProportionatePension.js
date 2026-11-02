/**
 * Methodology-2 proportionate pension (every retirement date).
 *
 * Mirrors backend methodology2/services/proportionate_pension.py:
 *   - TQS round: <3m → Y; 3–8m → Y+0.5; 9–11m → Y+1
 *   - Full at rounded TQS ≥ 20 (e.g. 19y 9m); else factor = TQS/20
 *
 * Backend applies the amounts; this file is for UI labels / local checks.
 */

export const FULL_PENSION_TQS_YEARS = 20;

export function roundTqsYearsOracle(tqsYears, tqsMonths) {
  const years = Number(tqsYears) || 0;
  const months = Number(tqsMonths) || 0;
  if (months < 3) return years;
  if (months < 9) return years + 0.5;
  return years + 1;
}

/**
 * @returns {{ applied: boolean, fullPension: boolean, factor: number, roundedTqs: number|null, note: string }}
 */
export function resolveServiceFactor({
  tqsYr = null,
  tqsMonth = null,
  tqsDays = null,
} = {}) {
  if (tqsYr == null && tqsMonth == null && tqsDays == null) {
    return {
      applied: false,
      fullPension: true,
      factor: 1,
      roundedTqs: null,
      note: "TQS not supplied.",
    };
  }
  const roundedTqs = roundTqsYearsOracle(tqsYr, tqsMonth);
  if (roundedTqs >= FULL_PENSION_TQS_YEARS) {
    return {
      applied: true,
      fullPension: true,
      factor: 1,
      roundedTqs,
      note: `Rounded TQS ${roundedTqs} >= ${FULL_PENSION_TQS_YEARS} -> full pension.`,
    };
  }
  const factor = roundedTqs / FULL_PENSION_TQS_YEARS;
  return {
    applied: true,
    fullPension: false,
    factor,
    roundedTqs,
    note: `Rounded TQS ${roundedTqs} < ${FULL_PENSION_TQS_YEARS} -> proportionate x (${roundedTqs}/${FULL_PENSION_TQS_YEARS}).`,
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
