import "../styles/PensionBillAbstractReport.css";

function EmployeePanel({ employee }) {
  if (!employee) return null;
  return (
    <div className="bill-abstract-print__employee">
      <div>
        <span className="bill-abstract-print__emp-label">Emp CD :</span> {employee.emp_cd}
      </div>
      <div>
        <span className="bill-abstract-print__emp-label">Retirement Dt. :</span>{" "}
        {employee.retirement_dt}
      </div>
      <div>
        <span className="bill-abstract-print__emp-label">Bank :</span> {employee.bank}
      </div>
      <div>
        <span className="bill-abstract-print__emp-label">Address :</span> {employee.address}
      </div>
      <div>
        <span className="bill-abstract-print__emp-label">IFSC :</span> {employee.ifsc}
      </div>
      <div>
        <span className="bill-abstract-print__emp-label">A/c No :</span> {employee.account_no}
      </div>
      {employee.payment_not_before ? (
        <div className="bill-abstract-print__payment-note">
          ** PAYMENT SHOULD NOT BE MADE BEFORE {employee.payment_not_before} **
        </div>
      ) : null}
    </div>
  );
}

export default function PensionBillAbstractReportPrint({ report }) {
  const { header, rows, totals, amount_words, footer } = report;

  return (
    <div className="bill-abstract-print">
      <header className="bill-abstract-print__header">
        <div className="bill-abstract-print__org">{report.org_name}</div>
        <div className="bill-abstract-print__title">{report.report_title}</div>
      </header>

      <div className="bill-abstract-print__abstract-meta">
        <span>
          <strong>Abstract No.</strong> {header.abstract_no}
        </span>
        <span>
          <strong>Abstract Dated</strong> {header.abstract_dt}
        </span>
      </div>

      <table className="bill-abstract-print__main-table">
        <thead>
          <tr>
            <th colSpan={2}>Bill Register</th>
            <th rowSpan={2}>Rendered</th>
            <th rowSpan={2}>Amount Passed</th>
            <th rowSpan={2}>Deduction</th>
            <th rowSpan={2}>Net Amount Payable</th>
            <th colSpan={3}>Details of cheque drawn</th>
          </tr>
          <tr>
            <th>No</th>
            <th>Date</th>
            <th>Cheque No</th>
            <th>Amt in Favour of Parties</th>
            <th>Amt in Favour of Treasurer</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row, index) => (
            <tr key={`${row.bill_reg_no}-${index}`}>
              <td>{row.bill_reg_no}</td>
              <td>{row.bill_reg_dt}</td>
              <td className="rendered">{row.rendered}</td>
              <td className="amount">{row.amount_passed_display}</td>
              <td className="amount">{row.deduction_display}</td>
              <td className="amount">{row.net_payable_display}</td>
              <td>{row.cheque_no}</td>
              <td className="amount">{row.amt_parties_display}</td>
              <td className="amount">{row.amt_treasurer_display}</td>
            </tr>
          ))}
        </tbody>
        <tfoot>
          <tr>
            <td colSpan={3}>
              <strong>TOTAL</strong>
            </td>
            <td className="amount">{totals.amount_passed_display}</td>
            <td className="amount">{totals.deduction_display}</td>
            <td className="amount">{totals.net_payable_display}</td>
            <td />
            <td className="amount">{totals.amt_parties_display}</td>
            <td className="amount">{totals.amt_treasurer_display}</td>
          </tr>
        </tfoot>
      </table>

      {rows.map((row, index) => (
        <EmployeePanel key={`emp-${index}`} employee={row.employee} />
      ))}

      <div className="bill-abstract-print__words">
        <div>
          <strong>Passed for</strong> {amount_words.passed_for}
        </div>
        <div>
          <strong>Net Amount Payable</strong> {amount_words.net_payable}
        </div>
      </div>

      <div className="bill-abstract-print__footer-grid">
        <div className="bill-abstract-print__sign-block">
          <div>{footer.left_signatory}</div>
        </div>
        <div className="bill-abstract-print__sign-block">
          <div>{footer.center_signatory}</div>
        </div>
        <div className="bill-abstract-print__sign-block bill-abstract-print__sign-block--cert">
          <div>{footer.certification}</div>
          <div className="bill-abstract-print__sign-line" />
          <div>{footer.right_signatory}</div>
        </div>
        <div className="bill-abstract-print__treasurer-block">
          <div>{footer.treasurer_heading}</div>
          <div>{footer.unpaid_misc}</div>
          <div>{footer.unpaid_abstract}</div>
          <div>
            <strong>{footer.grand_total}</strong>
          </div>
        </div>
      </div>
    </div>
  );
}
