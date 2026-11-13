/**
 * Methodology-2 proportionate pension.
 *
 * Mirrors backend methodology2/services/proportionate_pension.py:
 *   - TQS round: <3m → Y; 3–8m → Y+0.5; 9–11m → Y+1
 *   - Date tested = calculation date, one day before retirement
 *     (retiring on 01-Jan-2007 is calculated as on 31-Dec-2006)
 *   - Calc date up to 31-Dec-2006: full at rounded TQS ≥ 20; else factor = TQS/20
 *   - Calc date from 01-Jan-2007: full at rounded TQS ≥ 10 (e.g. 9y 9m);
 *     below 10 → not eligible for pension
 *     (death in harness: below 10 → proportionate x TQS/10)
 *
 * Backend applies the amounts; this file is for UI labels / local checks.
 */

export const FULL_PENSION_TQS_YEARS = 20;
export const POST_2007_FROM = "2007-01-01";
export const POST_2007_MIN_TQS_YEARS = 10;

// CR 10-11-2026 (emp 45654): the TQS-10 cut-off is only for retirement / VR etc.
const DEATH_IN_HARNESS_TYPES = new Set([
  "DEATH", "DT", "DH", "D", "DE", "DIED IN HARNESS", "DEATH IN HARNESS",
]);

export function isDeathInHarness(retirementType) {
  return DEATH_IN_HARNESS_TYPES.has(String(retirementType || "").trim().toUpperCase());
}

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

/**
 * @returns {{ applied: boolean, fullPension: boolean, eligible: boolean, factor: number, roundedTqs: number|null, note: string }}
 */
export function resolveServiceFactor({
  retirementDate = null,
  tqsYr = null,
  tqsMonth = null,
  tqsDays = null,
  retirementType = null,
} = {}) {
  const full = { applied: false, fullPension: true, eligible: true, factor: 1, roundedTqs: null };
  if (tqsYr == null && tqsMonth == null && tqsDays == null) {
    return { ...full, note: "TQS not supplied." };
  }
  const iso = asIsoDate(retirementDate);
  if (!iso) {
    return { ...full, note: "Retirement date not supplied." };
  }
  const roundedTqs = roundTqsYearsOracle(tqsYr, tqsMonth);
  const calc = new Date(`${iso}T00:00:00Z`);
  calc.setUTCDate(calc.getUTCDate() - 1);
  const asOn = calc.toISOString().slice(0, 10);
  const asOnText = asOn.split("-").reverse().join("-");
  if (asOn >= POST_2007_FROM) {
    if (roundedTqs >= POST_2007_MIN_TQS_YEARS) {
      return {
        ...full,
        applied: true,
        roundedTqs,
        note: `Calculated as on ${asOnText} (from 01-01-2007): rounded TQS ${roundedTqs} >= ${POST_2007_MIN_TQS_YEARS} -> full pension.`,
      };
    }
    // CR 10-11-2026 (emp 45654): death in harness → TQS/10, not "not eligible".
    if (isDeathInHarness(retirementType)) {
      return {
        applied: true,
        fullPension: false,
        eligible: true,
        factor: roundedTqs / POST_2007_MIN_TQS_YEARS,
        roundedTqs,
        note: `Calculated as on ${asOnText} (from 01-01-2007, death in harness): rounded TQS ${roundedTqs} < ${POST_2007_MIN_TQS_YEARS} -> proportionate x (${roundedTqs}/${POST_2007_MIN_TQS_YEARS}).`,
      };
    }
    return {
      applied: true,
      fullPension: false,
      eligible: false,
      factor: 0,
      roundedTqs,
      note: `Calculated as on ${asOnText} (from 01-01-2007): rounded TQS ${roundedTqs} < ${POST_2007_MIN_TQS_YEARS} years -> not eligible for pension.`,
    };
  }
  if (roundedTqs >= FULL_PENSION_TQS_YEARS) {
    return {
      ...full,
      applied: true,
      roundedTqs,
      note: `Calculated as on ${asOnText} (up to 31-12-2006): rounded TQS ${roundedTqs} >= ${FULL_PENSION_TQS_YEARS} -> full pension.`,
    };
  }
  const factor = roundedTqs / FULL_PENSION_TQS_YEARS;
  return {
    applied: true,
    fullPension: false,
    eligible: true,
    factor,
    roundedTqs,
    note: `Calculated as on ${asOnText} (up to 31-12-2006): rounded TQS ${roundedTqs} < ${FULL_PENSION_TQS_YEARS} -> proportionate x (${roundedTqs}/${FULL_PENSION_TQS_YEARS}).`,
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

/** TQS below the minimum for the retirement date: no pension. */
export function isPensionNotEligible(pension) {
  return pension?.proportionate?.eligible === false;
}
