import "../styles/Methodology2ConsolidationPrint.css";
import { formatCardValue } from "../utils/methodology2RevisionCards";

const PRINT_TITLE =
  "Consolidation of Pension as per Methodology-2 and comparison between M-1 & M-2 for 2017 & 2022";

function money(value) {
  if (value === null || value === undefined || value === "") return "—";
  return `₹ ${formatCardValue(value)}`;
}

function EmpCell({ label, value }) {
  return (
    <td>
      <span className="label">{label}:</span>
      <span>{value || "—"}</span>
    </td>
  );
}

/**
 * A4 portrait consolidation print.
 * Header title + footer signatories are print-only (not from DB).
 * All other fields come from the saved/live snapshot row.
 */
export default function Methodology2ConsolidationPrint({ snapshot }) {
  if (!snapshot) return null;

  const generatedOn = new Date().toLocaleDateString("en-IN");
  const retirementDate = snapshot.retirement_date
    ? new Date(snapshot.retirement_date).toLocaleDateString("en-IN")
    : "—";

  const blocks = snapshot.revision_blocks || [];
  const isEmployeePension = !!snapshot.is_employee_pension;
  const m2_277 = isEmployeePension
    ? snapshot.m2_pension_277
    : snapshot.m2_family_pension_277;
  const m2_359 = isEmployeePension
    ? snapshot.m2_pension_359
    : snapshot.m2_family_pension_359;
  const m1_277 = snapshot.m1_family_pension_277;
  const m1_359 = snapshot.m1_family_pension_359;
  const diff_277 =
    m2_277 != null && m1_277 != null
      ? Number(m2_277) - Number(m1_277)
      : null;
  const diff_359 =
    m2_359 != null && m1_359 != null
      ? Number(m2_359) - Number(m1_359)
      : null;

  return (
    <div
      id="methodology2-consolidation-print"
      className="m2-consol-print-wrap"
    >
      <div className="m2-consol-print">
        <h3 className="m2-consol-print__title">{PRINT_TITLE}</h3>
        <h4 className="m2-consol-print__subtitle">Pension Calculation Report</h4>
        <div className="m2-consol-print__generated">
          Generated on: {generatedOn}
        </div>

        <table className="m2-consol-print__emp-grid">
          <tbody>
            <tr>
              <EmpCell label="Employee Name" value={snapshot.name} />
              <EmpCell label="Emp ID" value={snapshot.emp_cd} />
            </tr>
            <tr>
              <EmpCell label="Case NO" value={snapshot.case_no} />
              <EmpCell label="Retirement Date" value={retirementDate} />
            </tr>
            <tr>
              <EmpCell label="Roll No" value={snapshot.roll_no} />
              <EmpCell label="Category" value={snapshot.category} />
            </tr>
            <tr>
              <EmpCell label="Designation" value={snapshot.designation} />
              <EmpCell label="TQS" value={snapshot.tqs} />
            </tr>
            <tr>
              <EmpCell
                label="Average Pay"
                value={
                  snapshot.average_pay != null
                    ? money(snapshot.average_pay)
                    : money(snapshot.last_pay)
                }
              />
              <EmpCell label="Last Pay" value={money(snapshot.last_pay)} />
            </tr>
            {!isEmployeePension && (
              <tr>
                <EmpCell
                  label="Pensioner Name"
                  value={snapshot.pensioner_name}
                />
                <td></td>
              </tr>
            )}
          </tbody>
        </table>

        {blocks.map((block) => (
          <div key={block.revision_key || block.title} className="m2-consol-print__block">
            <div className="m2-consol-print__block-title">{block.title}</div>
            <table className="m2-consol-print__block-table">
              <thead>
                <tr>
                  <th className="code"></th>
                  <th>Breakdown Component</th>
                  <th>Amount (₹)</th>
                </tr>
              </thead>
              <tbody>
                {(block.rows || []).map((row) => (
                  <tr key={row.row || row.description}>
                    <td className="code">{row.code || ""}</td>
                    <td>{row.description}</td>
                    <td className="amt">{formatCardValue(row.value)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ))}

        <div className="m2-consol-print__fp-title">
          {isEmployeePension ? "EMPLOYEE PENSION" : "FAMILY PENSION"}
        </div>
        <table className="m2-consol-print__fp-table">
          <thead>
            <tr>
              <th>Particulars</th>
              <th>In 2017 (277 CPI)</th>
              <th>In 2022 (359 CPI)</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td>Pension fixed as per Methodology-2</td>
              <td className="amt">{money(m2_277)}</td>
              <td className="amt">{money(m2_359)}</td>
            </tr>
            <tr>
              <td>Pension fixed as per Methodology-1</td>
              <td className="amt">{money(m1_277)}</td>
              <td className="amt">{money(m1_359)}</td>
            </tr>
            <tr>
              <td>Difference</td>
              <td className="amt">{money(diff_277)}</td>
              <td className="amt">{money(diff_359)}</td>
            </tr>
          </tbody>
        </table>

        <div className="m2-consol-print__footer">
          <span>FA &amp; CAO</span>
          <span>AO GR-1</span>
        </div>
      </div>
    </div>
  );
}
