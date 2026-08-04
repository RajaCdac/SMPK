import "../styles/PensionJournalSummary.css";

export default function PensionJournalSummaryPrint({ report }) {
  if (!report) return null;

  const { header, rows = [], totals, footer } = report;

  return (
    <div className="journal-summary-print">
      <div className="journal-summary-print__topbar">
        <div />
        <div className="journal-summary-print__topbar-right">
          <div>Run Date: {report.run_date}</div>
          <div>{report.page_text}</div>
        </div>
      </div>

      <header className="journal-summary-print__header">
        <div className="journal-summary-print__org">{report.org_name}</div>
        <div className="journal-summary-print__title">{report.report_title}</div>
        <div className="journal-summary-print__period">{report.period_text}</div>
      </header>

      <div className="journal-summary-print__body">
        <div className="journal-summary-print__meta-block">
          <div>
            <span className="journal-summary-print__meta-label">Bill No-</span>
            {header.bill_no}
          </div>
          <div>
            <span className="journal-summary-print__meta-label">Abstract No.</span>
            {header.abstract_no || "—"}
          </div>
          <div>
            <span className="journal-summary-print__meta-label">Abstract Date:</span>
            {header.abstract_dt || "—"}
          </div>
          <div>
            <span className="journal-summary-print__meta-label">Voucher No.&amp; Dt.</span>
            {header.voucher_no_dt}
          </div>
          <div>
            <span className="journal-summary-print__meta-label">Voucher Type</span>
            {header.voucher_type}
          </div>
        </div>

        <div className="journal-summary-print__table-wrap">
          <table className="journal-summary-print__table">
            <thead>
              <tr>
                <th rowSpan={2}>Zonal Cd Description</th>
                <th colSpan={3}>Allocation</th>
                <th colSpan={2}>Amount</th>
              </tr>
              <tr>
                <th>1st</th>
                <th>2nd</th>
                <th>3rd</th>
                <th>Dr.</th>
                <th>Cr.</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((row) => (
                <tr key={`${row.sl_no}-${row.aloc_cd1}-${row.dr_cr_flag}`}>
                  <td>{row.zonal_label}</td>
                  <td className="text-center">{row.aloc_cd1}</td>
                  <td className="text-center">{row.aloc_cd2}</td>
                  <td className="text-center">{row.aloc_cd3}</td>
                  <td className="text-end">{row.dr_amount}</td>
                  <td className="text-end">{row.cr_amount}</td>
                </tr>
              ))}
            </tbody>
            <tfoot>
              <tr>
                <th colSpan={4} className="text-end">
                  TOTAL:
                </th>
                <th className="text-end">{totals.debit_display}</th>
                <th className="text-end">{totals.credit_display}</th>
              </tr>
            </tfoot>
          </table>

          {header.narration ? (
            <div className="journal-summary-print__narration-box">
              <div className="journal-summary-print__narration-label">Narration</div>
              <div>{header.narration}</div>
            </div>
          ) : null}
        </div>
      </div>

      <footer className="journal-summary-print__footer">
        <div>
          <div>{footer.left_title}</div>
          <div>{footer.left_subtitle}</div>
        </div>
        <div>{footer.right_title}</div>
      </footer>
    </div>
  );
}
