import "../styles/Methodology2ConsolidationPrint.css";
import { formatCardValue } from "../utils/methodology2RevisionCards";

const PRINT_TITLE =
  "Consolidation of Pension as per Methodology-2 and comparison between M-1 & M-2 for 2017 & 2022";

function money(value) {
  if (value === null || value === undefined || value === "") return "—";
  return `₹ ${formatCardValue(value)}`;
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
 * Old-age print calc: M2′=M2+M2×%, M1′=M1+M1×%, payable=max, revised=payable.
 * Uses backend fields when present; otherwise derives from base + percent.
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

  let m2Oa = fromBackend("m2_oa_basic");
  let m1Oa = fromBackend("m1_oa_basic");
  if (m2Oa == null && m2Base != null && !Number.isNaN(m2Base)) {
    m2Oa = Math.round((m2Base + (m2Base * pct) / 100) * 100) / 100;
  }
  if (m1Oa == null && m1 != null && !Number.isNaN(m1)) {
    m1Oa = Math.round((m1 + (m1 * pct) / 100) * 100) / 100;
  }

  let oaDiff = fromBackend("oa_diff");
  if (oaDiff == null && m2Oa != null && m1Oa != null) {
    oaDiff = Math.round((m2Oa - m1Oa) * 100) / 100;
  }

  let payable = fromBackend("payable_basic");
  if (payable == null) {
    if (m2Oa != null && m1Oa != null) payable = Math.max(m2Oa, m1Oa);
    else payable = m2Oa ?? m1Oa;
  }

  let revised = fromBackend("revised_total_basic");
  if (revised == null) revised = payable;

  return { m2Oa, m1Oa, oaDiff, payable, revised, pct };
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
  return [
    {
      key: "277",
      header_lines: ["In 2017 (277 CPI)"],
      m2: m2_277,
      m1: m1_277,
      diff: diff(m2_277, m1_277),
    },
    {
      key: "359",
      header_lines: ["In 2022 (359 CPI)"],
      m2: m2_359,
      m1: m1_359,
      diff: diff(m2_359, m1_359),
    },
  ];
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

  const blocks = snapshot.revision_blocks || [];
  const comparison = snapshot.pension_comparison || {};
  const columns =
    Array.isArray(comparison.columns) && comparison.columns.length
      ? comparison.columns
      : buildFallbackColumns(snapshot);

  const lastPayDisplay = lastPayWithStagnation(
    snapshot.last_pay ?? snapshot.average_pay,
    snapshot.stagnation_amount ?? comparison.stagnation_amount
  );
  const averagePayDisplay = money(
    snapshot.average_pay ?? snapshot.last_pay
  );

  const isEmployeePension = !!snapshot.is_employee_pension;
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
  const doubleFpUptoDisplay =
    comparison.double_fpension_upto_display ||
    (comparison.double_fpension_upto
      ? formatDateEnIn(comparison.double_fpension_upto)
      : "");
  const sectionTitle =
    comparison.section_title ||
    (isEmployeePension ? "EMPLOYEE PENSION" : "FAMILY PENSION");
  const showOldAgeCalcTable =
    !!isEmployeePension &&
    (comparison.has_oldage_calc_table ||
      comparison.has_oldage_split ||
      columns.some((c) => Number(c.oldage_percent || 0) > 0));

  return (
    <div
      id="methodology2-consolidation-print"
      className="m2-consol-print-wrap"
    >
      <div className="m2-consol-print">
        <h3 className="m2-consol-print__title">{PRINT_TITLE}</h3>
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
            {dodDisplay || doubleFpUptoDisplay ? (
              <tr>
                {dodDisplay ? (
                  <EmpCell
                    label="Date of Death"
                    value={dodDisplay}
                    colSpan={doubleFpUptoDisplay ? 1 : 3}
                  />
                ) : null}
                {doubleFpUptoDisplay ? (
                  <EmpCell
                    label="Enhanced FP upto"
                    value={doubleFpUptoDisplay}
                    colSpan={dodDisplay ? 2 : 3}
                  />
                ) : null}
              </tr>
            ) : null}
          </tbody>
        </table>

        {blocks.map((block) => (
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
                        <td colSpan={3}>{block.title}</td>
                      </tr>
                      <tr className="m2-consol-print__block-header-row">
                        <td className="code"></td>
                        <td>Breakdown Component</td>
                        <td className="amt">Amount (Rs)</td>
                      </tr>
                      {(block.rows || []).map((row) => (
                        <tr key={row.row || row.description}>
                          <td className="code">{row.code || ""}</td>
                          <td>{row.description}</td>
                          <td className="amt">
                            {formatCardValue(row.value)}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </td>
              </tr>
            </tbody>
          </table>
        ))}

        <div className="m2-consol-print__fp-title">{sectionTitle}</div>
        <table className="m2-consol-print__fp-wrap">
          <tbody>
            <tr>
              <td className="wrap-cell">
                <table className="m2-consol-print__fp-table">
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
                      <td>Pension fixed as per Methodology-2</td>
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
                      <td>Pension fixed as per Methodology-1</td>
                      {columns.map((col) => (
                        <td
                          key={`m1-${col.key || col.header}`}
                          className="amt"
                        >
                          {money(col.m1)}
                        </td>
                      ))}
                    </tr>
                    <tr>
                      <td>Difference</td>
                      {columns.map((col) => (
                        <td
                          key={`diff-${col.key || col.header}`}
                          className="amt"
                        >
                          {money(columnAmounts(col).baseDiff)}
                        </td>
                      ))}
                    </tr>
                    {showOldAgeCalcTable ? (
                      <>
                        <tr className="m2-consol-print__oa-section">
                          <td colSpan={columns.length + 1}>
                            Old Age Benefit Calculation Details
                          </td>
                        </tr>
                        <tr>
                          <td>Basic Pension (M2) with Old Age Benefit</td>
                          {columns.map((col) => (
                            <td
                              key={`m2oa-${col.key || col.header}`}
                              className="amt"
                            >
                              {money(oldAgeCalcAmounts(col).m2Oa)}
                            </td>
                          ))}
                        </tr>
                        <tr>
                          <td>Basic pension (M1) with Old Age Benefit</td>
                          {columns.map((col) => (
                            <td
                              key={`m1oa-${col.key || col.header}`}
                              className="amt"
                            >
                              {money(oldAgeCalcAmounts(col).m1Oa)}
                            </td>
                          ))}
                        </tr>
                        <tr>
                          <td>Difference</td>
                          {columns.map((col) => (
                            <td
                              key={`oadiff-${col.key || col.header}`}
                              className="amt"
                            >
                              {money(oldAgeCalcAmounts(col).oaDiff)}
                            </td>
                          ))}
                        </tr>
                        <tr>
                          <td>Payable Basic Pension (Higher of M2 & M1)</td>
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
                          <td>Revised Basic Pension</td>
                          {columns.map((col) => (
                            <td
                              key={`rev-${col.key || col.header}`}
                              className="amt"
                            >
                              {money(oldAgeCalcAmounts(col).revised)}
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
