import "../styles/Methodology2ConsolidationPrint.css";
import {
  ensureClass12OpeningBasic,
  formatCardValue,
} from "../utils/methodology2RevisionCards";

const PRINT_TITLE =
  "Consolidation of Pension as per Methodology-2 and comparison between M-1 & M-2 for 2017 & 2022";
const PRINT_TITLE_CLASS12 =
  "Consolidation of Pension as per Methodology-2 and comparison between M-1 & M-2 for 2017";

function money(value) {
  if (value === null || value === undefined || value === "") return "—";
  return `₹ ${formatCardValue(value)}`;
}

/** Class 1/2 LIC bunching. Absent when the employee has no bunch basic. */
function bunchingParts(snapshot) {
  const bunch = snapshot?.m1_bunching;
  if (!bunch || typeof bunch !== "object") return null;
  const basic = Number(bunch.basic_pension);
  const extra = Number(bunch.bunch_basic);
  const total = Number(
    bunch.m1_bunched != null ? bunch.m1_bunched : basic + extra
  );
  if (Number.isNaN(basic) || Number.isNaN(extra) || extra === 0) return null;
  if (Number.isNaN(total)) return null;
  return { basic, extra, total };
}

function employee277Column(col, snapshot) {
  const kind = String(col?.kind || "").trim().toLowerCase();
  if (kind === "family" || kind === "enhanced") return false;
  if (!kind && !snapshot?.is_employee_pension) return false;
  const cpi = Number(col?.cpi);
  if (cpi === 359) return false;
  const key = String(col?.key || "");
  if (key.startsWith("359")) return false;
  return true;
}

const REVISION_YEARS = [
  1979, 1984, 1988, 1993, 1997, 2007, 2012, 2017, 2022,
];

/** Class 1/2 stages only — last revision is 2017 (no 2022). */
const CLASS12_REVISION_YEARS = [1984, 1987, 1992, 1997, 2007, 2017];

/** Strip mistaken "As per 2022…" from class 1/2 titles (2017 is last). */
function stripClass12AsPer2022(title) {
  return String(title || "")
    .replace(/\s*[—\-]\s*As per\s+2022\s+(?:Wage|Pay)\s+Revision Order/gi, "")
    .trim();
}

/** Class 1/2 uses "Pay Revision Order" (not Wage). */
function class12PayRevisionTitle(title) {
  return String(title || "").replace(/Wage Revision Order/gi, "Pay Revision Order");
}

/** Class 1/2 last row: Basic Pay… → Notional Pay… (except final 01.01.2017). */
function class12NotionalizeLastDescription(desc) {
  const text = String(desc || "").trim();
  if (!text) return text;
  if (/^Basic\s+Pay\s+as\s+on\s+01\.01\.2017$/i.test(text)) return text;
  if (/Notional/i.test(text)) return text;
  if (/^Basic\s+[Pp]ay\b/.test(text)) {
    return text.replace(/^Basic\s+[Pp]ay/, "Notional Pay");
  }
  return text;
}

/** Same note class 3/4 prints on its Notional Pay line. */
function class12RoundNote(desc) {
  const text = String(desc || "").trim();
  if (!text || /Rounded to the next 10/i.test(text)) return text;
  if (/minimum basic/i.test(text)) return text;
  if (/^Basic\s+Pay\s+as\s+on\s+01\.01\.2017$/i.test(text)) return text;
  if (/Notional/i.test(text) || /Basic Pay Over/i.test(text)) {
    return `${text} (Rounded to the next 10 Rupees)`;
  }
  return text;
}

/** e.g. 1997 block → "As per 2007 Wage Revision Order" (class 3/4)
 *  class 1/2 → "As per 2007 Pay Revision Order" (no As per 2022 on 2017).
 */
function blockTitleWithWageOrder(block, { class12 = false } = {}) {
  let title = block?.title || "";
  if (class12) {
    title = class12PayRevisionTitle(stripClass12AsPer2022(title));
    if (/As per\s+\d{4}\s+Pay Revision Order/i.test(title)) return title;
    const m = String(block?.revision_key || title).match(/(\d{4})/);
    if (!m) return title;
    const idx = CLASS12_REVISION_YEARS.indexOf(Number(m[1]));
    if (idx < 0 || idx >= CLASS12_REVISION_YEARS.length - 1) return title;
    return `${title} — As per ${CLASS12_REVISION_YEARS[idx + 1]} Pay Revision Order`;
  }
  if (/As per\s+\d{4}\s+Wage Revision Order/i.test(title)) return title;
  const m = String(block?.revision_key || title).match(/(\d{4})/);
  if (!m) return title;
  const idx = REVISION_YEARS.indexOf(Number(m[1]));
  if (idx < 0 || idx >= REVISION_YEARS.length - 1) return title;
  return `${title} — As per ${REVISION_YEARS[idx + 1]} Wage Revision Order`;
}

/** Last Pay shows actual stage; stagnation labelled in braces when present. */
function lastPayWithStagnation(lastPay, stagnationAmount) {
  const base = money(lastPay);
  if (base === "—") return base;
  const stag = Number(stagnationAmount);
  if (
    stagnationAmount === null ||
    stagnationAmount === undefined ||
    stagnationAmount === "" ||
    Number.isNaN(stag) ||
    stag === 0
  ) {
    return base;
  }
  return `${base} (Stagnation amount ${formatCardValue(stag)})`;
}

/** Doctor last pay is pay + NPA. Label the NPA the way stagnation is labelled. */
function lastPayWithNpa(display, npaAmount) {
  if (display === "—") return display;
  const npa = Number(npaAmount);
  if (
    npaAmount === null ||
    npaAmount === undefined ||
    npaAmount === "" ||
    Number.isNaN(npa) ||
    npa === 0
  ) {
    return display;
  }
  return `${display} (npa ${formatCardValue(npa)})`;
}

/** "MACP 16400-40500" → "16400-40500". Empty when this is not a MACP case. */
function macpTrackScale(scale) {
  const match = String(scale || "").match(/^MACP\s+(.+)$/i);
  return match ? match[1].trim() : "";
}

/** Later CPI cards: "(23600-56300)" → "(MACP Scale 23600-56300)". */
function withMacpBeforeScale(title) {
  const text = String(title || "");
  if (/MACP\s+Scale/i.test(text)) return text;
  return text.replace(
    /\((\d[\d\s,]*-\s*\d[\d\s,]*)\)/,
    "(MACP Scale $1)"
  );
}

function formatDateEnIn(raw) {
  if (!raw) return "—";
  const d = new Date(raw);
  if (Number.isNaN(d.getTime())) return String(raw);
  return `${d.getDate()}/${d.getMonth() + 1}/${d.getFullYear()}`;
}

function tqsDisplay(snapshot) {
  if (snapshot.tqs) return String(snapshot.tqs);
  const { tqs_yr: yr, tqs_month: mo, tqs_days: days } = snapshot;
  if (yr == null && mo == null && days == null) return "—";
  return `${yr || 0} Y / ${mo || 0} M / ${days || 0} D`;
}

function EmpCell({ label, value, colSpan, prominent }) {
  return (
    <td
      colSpan={colSpan}
      className={prominent ? "m2-consol-print__emp-cell--prominent" : undefined}
    >
      <span className="label">{label}:</span>
      <span className={prominent ? "m2-consol-print__case-no" : undefined}>
        {value || "—"}
      </span>
    </td>
  );
}

/** Base M2 / Diff for top EMP PENSION rows (no OA). */
function columnAmounts(col) {
  const m2BaseRaw =
    col.m2_base != null && col.m2_base !== "" ? col.m2_base : col.m2;
  const m2Base =
    m2BaseRaw != null && m2BaseRaw !== "" ? Number(m2BaseRaw) : null;
  const m1 = col.m1 != null && col.m1 !== "" ? Number(col.m1) : null;
  const baseDiff =
    m2Base != null && m1 != null && !Number.isNaN(m2Base) && !Number.isNaN(m1)
      ? m2Base - m1
      : col.diff != null && col.diff !== ""
        ? Number(col.diff)
        : null;
  return {
    m2Base: Number.isNaN(m2Base) ? null : m2Base,
    baseDiff: Number.isNaN(baseDiff) ? null : baseDiff,
  };
}

/**
 * Old-age print amounts (benefit part only + separate pension-with-OA table).
 * OA_M2 = M2×%, OA_M1 = M1×% (0 when % = 0).
 * Payable = max(M2,M1); OA benefit = max(OA_M2,OA_M1); Revised = payable + OA.
 */
function oldAgeCalcAmounts(col) {
  const pct = Number(col.oldage_percent || 0);
  const m2BaseRaw =
    col.m2_base != null && col.m2_base !== "" ? col.m2_base : col.m2;
  const m2Base =
    m2BaseRaw != null && m2BaseRaw !== "" ? Number(m2BaseRaw) : null;
  const m1 = col.m1 != null && col.m1 !== "" ? Number(col.m1) : null;

  const fromBackend = (key) => {
    const v = col[key];
    if (v == null || v === "") return null;
    const n = Number(v);
    return Number.isNaN(n) ? null : n;
  };

  let oaM2 = fromBackend("oa_benefit_m2");
  let oaM1 = fromBackend("oa_benefit_m1");
  // Prefer benefit-only fields; do not use legacy m2_oa_basic (= full enhanced).
  if (oaM2 == null && m2Base != null && !Number.isNaN(m2Base)) {
    oaM2 =
      pct > 0 ? Math.round(((m2Base * pct) / 100) * 100) / 100 : 0;
  }
  if (oaM1 == null && m1 != null && !Number.isNaN(m1)) {
    oaM1 = pct > 0 ? Math.round(((m1 * pct) / 100) * 100) / 100 : 0;
  }
  if (oaM2 == null) oaM2 = 0;
  if (oaM1 == null) oaM1 = 0;

  let oaDiff = fromBackend("oa_diff");
  if (oaDiff == null) {
    oaDiff = Math.round((oaM2 - oaM1) * 100) / 100;
  }

  let payable = fromBackend("payable_basic");
  if (payable == null) {
    if (m2Base != null && m1 != null) payable = Math.max(m2Base, m1);
    else payable = m2Base ?? m1;
  }

  let oaBenefit = fromBackend("oa_benefit");
  if (oaBenefit == null) oaBenefit = Math.max(oaM2, oaM1);

  let revised = fromBackend("revised_total_basic");
  if (revised == null && payable != null) {
    revised = Math.round((payable + oaBenefit) * 100) / 100;
  }

  return { oaM2, oaM1, oaDiff, payable, oaBenefit, revised, pct };
}

function buildFallbackColumns(snapshot) {
  const isEmployeePension = !!snapshot.is_employee_pension;
  const m2_277 = isEmployeePension
    ? snapshot.m2_pension_277
    : snapshot.m2_family_pension_277;
  const m2_359 = isEmployeePension
    ? snapshot.m2_pension_359
    : snapshot.m2_family_pension_359;
  const m1_277 = snapshot.m1_family_pension_277;
  const m1_359 = snapshot.m1_family_pension_359;
  const diff = (m2, m1) =>
    m2 != null && m1 != null ? Number(m2) - Number(m1) : null;
  const cat = String(snapshot.category || "").trim();
  const class12 = cat === "1" || cat === "2";
  const cols = [
    {
      key: "277",
      header_lines: ["In 2017 (277 CPI)"],
      m2: m2_277,
      m1: m1_277,
      diff: diff(m2_277, m1_277),
    },
  ];
  // Class 1/2 last CPI is 277 — do not invent a blank 359 column.
  if (!class12) {
    cols.push({
      key: "359",
      header_lines: ["In 2022 (359 CPI)"],
      m2: m2_359,
      m1: m1_359,
      diff: diff(m2_359, m1_359),
    });
  }
  return cols;
}

/** Drop leftover 359/2022 columns for class 1/2 (old snapshots / blank cols). */
function columnsForSnapshot(snapshot, comparison) {
  const raw =
    Array.isArray(comparison.columns) && comparison.columns.length
      ? comparison.columns
      : buildFallbackColumns(snapshot);
  const cat = String(snapshot.category || "").trim();
  const class12 =
    cat === "1" ||
    cat === "2" ||
    comparison.class12_omit_359 === true ||
    comparison.class12_continuous_277 === true;
  if (!class12) return raw;
  return raw.filter((col) => {
    if (!col || typeof col !== "object") return false;
    const cpi = Number(col.cpi);
    if (cpi === 359) return false;
    const key = String(col.key || "");
    if (key.startsWith("359")) return false;
    const hdr = `${(col.header_lines || []).join(" ")} ${col.header || ""}`;
    if (/359\s*CPI|In\s+2022/i.test(hdr) && !/277/.test(hdr)) return false;
    return true;
  });
}

/**
 * A4 portrait consolidation print — layout matches bulk PDF (bulk_consolidation.html).
 * When DOD splits a CPI period, comparison table gains extra columns.
 */
export default function Methodology2ConsolidationPrint({ snapshot }) {
  if (!snapshot) return null;

  const generatedOn = formatDateEnIn(new Date());
  const retirementDate = formatDateEnIn(snapshot.retirement_date);
  const dateOfBirth = formatDateEnIn(
    snapshot.date_of_birth || snapshot.dob || null
  );
  const hasDob = !!(snapshot.date_of_birth || snapshot.dob);
  const tqs = tqsDisplay(snapshot);

  const rawBlocks = snapshot.revision_blocks || [];
  const comparison = snapshot.pension_comparison || {};
  const columns = columnsForSnapshot(snapshot, comparison);
  const cat = String(snapshot.category || "").trim();
  const isClass12 =
    cat === "1" ||
    cat === "2" ||
    comparison.class12_omit_359 === true ||
    comparison.class12_continuous_277 === true;
  const blocks = isClass12
    ? ensureClass12OpeningBasic(rawBlocks)
    : rawBlocks;

  const macpTrack = macpTrackScale(snapshot.scale);
  let lastPayDisplay = lastPayWithNpa(
    lastPayWithStagnation(
      snapshot.last_pay ?? snapshot.average_pay,
      snapshot.stagnation_amount ?? comparison.stagnation_amount
    ),
    snapshot.npa_amount ?? comparison.npa_amount
  );
  if (macpTrack && lastPayDisplay !== "—") {
    lastPayDisplay = `${lastPayDisplay} (MACP Scale ${macpTrack})`;
  }
  const averagePayDisplay = money(
    snapshot.average_pay ?? snapshot.last_pay
  );

  const isEmployeePension = !!snapshot.is_employee_pension;
  const bunching =
    isClass12 && isEmployeePension ? bunchingParts(snapshot) : null;
  const m1Particulars = bunching
    ? "Pension fixed as per Methodology-1 with bunching"
    : "Pension fixed as per Methodology-1";
  const hasDeathSplit = !!(
    comparison.has_death_split ||
    snapshot.date_of_death ||
    comparison.double_fpension_upto ||
    comparison.rate_cutover
  );
  const familyName =
    comparison.family_pensioner_name || snapshot.pensioner_name || "";
  const showFamilyName =
    hasDeathSplit || (!isEmployeePension && !!familyName);
  const dodDisplay =
    comparison.date_of_death_display ||
    (snapshot.date_of_death ? formatDateEnIn(snapshot.date_of_death) : "");
  const familyPensionerDobDisplay =
    comparison.family_pensioner_dob_display ||
    formatDateEnIn(
      comparison.family_pensioner_dob ||
        snapshot.family_pensioner_dob ||
        null
    );
  const showFamilyPensionerDob =
    (!isEmployeePension || showFamilyName) && !!familyPensionerDobDisplay;
  const doubleFpUptoDisplay =
    comparison.double_fpension_upto_display ||
    (comparison.double_fpension_upto
      ? formatDateEnIn(comparison.double_fpension_upto)
      : "");
  const sectionTitle =
    comparison.section_title ||
    (isEmployeePension ? "EMPLOYEE PENSION" : "FAMILY PENSION");
  const showOldAgeCalcTable =
    comparison.has_oldage_calc_table ||
    comparison.has_oldage_split ||
    columns.some((c) => Number(c.oldage_percent || 0) > 0);

  const familyExtraCells = [];
  if (dodDisplay) {
    familyExtraCells.push({
      label: "Date of Death (D.O.D.)",
      value: dodDisplay,
    });
  }
  if (showFamilyPensionerDob) {
    familyExtraCells.push({
      label: "DOB of Family Pensioner",
      value: familyPensionerDobDisplay,
    });
  }
  if (doubleFpUptoDisplay) {
    familyExtraCells.push({
      label: "Enhanced FP upto",
      value: doubleFpUptoDisplay,
    });
  }

  return (
    <div
      id="methodology2-consolidation-print"
      className="m2-consol-print-wrap"
    >
      <div className="m2-consol-print">
        <h3 className="m2-consol-print__title">
          {isClass12 ? PRINT_TITLE_CLASS12 : PRINT_TITLE}
        </h3>
        <h4 className="m2-consol-print__subtitle">
          Pension Calculation Report (Generated on: {generatedOn})
        </h4>
        <div className="m2-consol-print__generated" />

        <table className="m2-consol-print__emp-grid">
          <tbody>
            {showFamilyName ? (
              <tr>
                <EmpCell label="Employee Name" value={snapshot.name} />
                <EmpCell label="Family Pensioner Name" value={familyName} />
                <EmpCell
                  label="Type of Retirement"
                  value={snapshot.retirement_type}
                />
              </tr>
            ) : (
              <tr>
                <EmpCell
                  label="Employee Name"
                  value={snapshot.name}
                  colSpan={2}
                />
                <EmpCell
                  label="Type of Retirement"
                  value={snapshot.retirement_type}
                />
              </tr>
            )}
            <tr>
              <EmpCell label="Emp ID" value={snapshot.emp_cd} />
              <EmpCell
                label="Case NO"
                value={snapshot.case_no}
                prominent
              />
              <EmpCell label="Roll No" value={snapshot.roll_no} />
            </tr>
            {hasDob ? (
              <>
                <tr>
                  <EmpCell label="Retirement Date" value={retirementDate} />
                  <EmpCell label="Date of Birth" value={dateOfBirth} />
                  <EmpCell label="Category" value={snapshot.category} />
                </tr>
                <tr>
                  <EmpCell label="TQS" value={tqs} />
                  <EmpCell label="Average Pay" value={averagePayDisplay} />
                  <EmpCell label="Last Pay" value={lastPayDisplay} />
                </tr>
                <tr>
                  <EmpCell
                    label="Designation"
                    value={snapshot.designation}
                    colSpan={3}
                  />
                </tr>
              </>
            ) : (
              <>
                <tr>
                  <EmpCell label="Retirement Date" value={retirementDate} />
                  <EmpCell label="TQS" value={tqs} />
                  <EmpCell label="Category" value={snapshot.category} />
                </tr>
                <tr>
                  <EmpCell label="Designation" value={snapshot.designation} />
                  <EmpCell label="Average Pay" value={averagePayDisplay} />
                  <EmpCell label="Last Pay" value={lastPayDisplay} />
                </tr>
              </>
            )}
            {familyExtraCells.length ? (
              <tr>
                {familyExtraCells.map((cell, idx) => {
                  const remaining = familyExtraCells.length - idx;
                  const colSpan =
                    remaining === 1 ? 4 - familyExtraCells.length : 1;
                  return (
                    <EmpCell
                      key={cell.label}
                      label={cell.label}
                      value={cell.value}
                      colSpan={colSpan}
                    />
                  );
                })}
              </tr>
            ) : null}
          </tbody>
        </table>

        {blocks.map((block, blockIdx) => {
          const blockTitle = blockTitleWithWageOrder(block, {
            class12: isClass12,
          });
          const titled =
            macpTrack && blockIdx > 0
              ? withMacpBeforeScale(blockTitle)
              : blockTitle;
          return (
          <table
            key={block.revision_key || block.title}
            className="m2-consol-print__cpi-wrap"
          >
            <tbody>
              <tr>
                <td className="wrap-cell">
                  <table className="m2-consol-print__cpi-card">
                    <colgroup>
                      <col className="code-col" />
                      <col />
                      <col className="amt-col" />
                    </colgroup>
                    <tbody>
                      <tr className="m2-consol-print__block-title-row">
                        <td colSpan={3}>{titled}</td>
                      </tr>
                      {(block.rows || []).map((row, idx) => {
                        const rows = block.rows || [];
                        let desc = row.description;
                        if (isClass12) {
                          if (idx === rows.length - 1) {
                            desc = class12NotionalizeLastDescription(desc);
                          }
                          desc = class12RoundNote(desc);
                        }
                        return (
                        <tr key={row.row || row.description || idx}>
                          <td className="code">
                            {String(row.code || "").trim() ||
                              (idx < 26
                                ? String.fromCharCode(65 + idx)
                                : String(idx + 1))}
                          </td>
                          <td>{desc}</td>
                          <td className="amt">
                            {money(row.value)}
                          </td>
                        </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </td>
              </tr>
            </tbody>
          </table>
          );
        })}

        <div className="m2-consol-print__fp-title">{sectionTitle}</div>
        <table className="m2-consol-print__fp-wrap">
          <tbody>
            <tr>
              <td className="wrap-cell">
                <table className="m2-consol-print__fp-table">
                  <colgroup>
                    <col className="part-col" />
                    {columns.map((col) => (
                      <col key={`c-${col.key || col.header}`} />
                    ))}
                  </colgroup>
                  <thead>
                    <tr>
                      <th>Particulars</th>
                      {columns.map((col) => (
                        <th key={col.key || col.header}>
                          {(col.header_lines || [col.header || ""]).map(
                            (line, idx) =>
                              idx === 0 ? (
                                <span key={line}>{line}</span>
                              ) : (
                                <span key={line} className="sub">
                                  {line}
                                </span>
                              )
                          )}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    <tr>
                      <td className="part">
                        Pension fixed as per Methodology-2
                      </td>
                      {columns.map((col) => (
                        <td
                          key={`m2-${col.key || col.header}`}
                          className="amt"
                        >
                          {money(columnAmounts(col).m2Base)}
                        </td>
                      ))}
                    </tr>
                    <tr>
                      <td className="part">{m1Particulars}</td>
                      {columns.map((col) => {
                        const useBunch =
                          bunching && employee277Column(col, snapshot);
                        return (
                          <td
                            key={`m1-${col.key || col.header}`}
                            className="amt"
                          >
                            {useBunch
                              ? `₹ ${formatCardValue(bunching.total)} (${formatCardValue(bunching.basic)} + ${formatCardValue(bunching.extra)})`
                              : money(col.m1)}
                          </td>
                        );
                      })}
                    </tr>
                    <tr>
                      <td className="part">Difference</td>
                      {columns.map((col) => {
                        const useBunch =
                          bunching && employee277Column(col, snapshot);
                        const m2 = columnAmounts(col).m2Base;
                        const diff = useBunch
                          ? m2 != null
                            ? m2 - bunching.total
                            : null
                          : columnAmounts(col).baseDiff;
                        return (
                          <td
                            key={`diff-${col.key || col.header}`}
                            className="amt"
                          >
                            {money(diff)}
                          </td>
                        );
                      })}
                    </tr>
                    {showOldAgeCalcTable ? (
                      <>
                        <tr className="m2-consol-print__oa-section">
                          <td colSpan={columns.length + 1}>
                            Old Age Benefit Calculation Details
                          </td>
                        </tr>
                        <tr>
                          <td className="part">Old Age Benefit as per M2</td>
                          {columns.map((col) => (
                            <td
                              key={`oam2-${col.key || col.header}`}
                              className="amt"
                            >
                              {money(oldAgeCalcAmounts(col).oaM2)}
                            </td>
                          ))}
                        </tr>
                        <tr>
                          <td className="part">Old Age Benefit as per M1</td>
                          {columns.map((col) => (
                            <td
                              key={`oam1-${col.key || col.header}`}
                              className="amt"
                            >
                              {money(oldAgeCalcAmounts(col).oaM1)}
                            </td>
                          ))}
                        </tr>
                        <tr>
                          <td className="part">Difference</td>
                          {columns.map((col) => (
                            <td
                              key={`oadiff-${col.key || col.header}`}
                              className="amt"
                            >
                              {money(oldAgeCalcAmounts(col).oaDiff)}
                            </td>
                          ))}
                        </tr>
                      </>
                    ) : null}
                  </tbody>
                </table>
              </td>
            </tr>
          </tbody>
        </table>

        {showOldAgeCalcTable ? (
          <>
            <div className="m2-consol-print__fp-title">
              PENSION WITH OLD AGE BENEFIT
            </div>
            <table className="m2-consol-print__fp-wrap">
              <tbody>
                <tr>
                  <td className="wrap-cell">
                    <table className="m2-consol-print__fp-table">
                      <colgroup>
                        <col className="part-col" />
                        {columns.map((col) => (
                          <col key={`oa2c-${col.key || col.header}`} />
                        ))}
                      </colgroup>
                      <thead>
                        <tr>
                          <th>Particulars</th>
                          {columns.map((col) => (
                            <th key={`oa2-${col.key || col.header}`}>
                              {(col.header_lines || [col.header || ""]).map(
                                (line, idx) =>
                                  idx === 0 ? (
                                    <span key={line}>{line}</span>
                                  ) : (
                                    <span key={line} className="sub">
                                      {line}
                                    </span>
                                  )
                              )}
                            </th>
                          ))}
                        </tr>
                      </thead>
                      <tbody>
                        <tr>
                          <td className="part">
                            Payable Basic Pension (Higher of M1 & M2)
                          </td>
                          {columns.map((col) => (
                            <td
                              key={`pay-${col.key || col.header}`}
                              className="amt"
                            >
                              {money(oldAgeCalcAmounts(col).payable)}
                            </td>
                          ))}
                        </tr>
                        <tr>
                          <td className="part">
                            Old Age Benefit (Higher of M1 & M2)
                          </td>
                          {columns.map((col) => (
                            <td
                              key={`oaben-${col.key || col.header}`}
                              className="amt"
                            >
                              {money(oldAgeCalcAmounts(col).oaBenefit)}
                            </td>
                          ))}
                        </tr>
                        <tr>
                          <td className="part">Revised Basic Pension</td>
                          {columns.map((col) => (
                            <td
                              key={`rev-${col.key || col.header}`}
                              className="amt"
                            >
                              {money(oldAgeCalcAmounts(col).revised)}
                            </td>
                          ))}
                        </tr>
                      </tbody>
                    </table>
                  </td>
                </tr>
              </tbody>
            </table>
          </>
        ) : null}

        <table className="m2-consol-print__footer">
          <tbody>
            <tr>
              <td>FA &amp; CAO</td>
              <td className="right">AO GR-1</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  );
}
