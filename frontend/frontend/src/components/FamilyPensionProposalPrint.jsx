import "../styles/FamilyPensionProposalReport.css";

function ReportPage({ report, page }) {
  const remarkLines = String(page.remarks || "").split("\n").filter(Boolean);

  return (
    <section className="fp-proposal-print__page">
      <header className="fp-proposal-print__header">
        <div className="fp-proposal-print__header-center">
          <div className="fp-proposal-print__org">{report.org_name}</div>
          <div className="fp-proposal-print__title">{report.report_title}</div>
        </div>
        <div className="fp-proposal-print__meta">
          <div>Run Date : {report.run_date}</div>
          <div>
            Page {page.page_no} of {page.total_pages}
          </div>
        </div>
      </header>

      <table className="fp-proposal-print__table">
        <thead>
          <tr>
            <th className="col-report" rowSpan={2}>
              Report No.
            </th>
            <th className="col-name" rowSpan={2}>
              Name
            </th>
            <th className="col-nature-head" colSpan={3}>
              Nature of Service
            </th>
            <th className="col-date" rowSpan={2}>
              Entered
              <br />
              in Service
            </th>
            <th className="col-date" rowSpan={2}>
              Retired
              <br />
              From
            </th>
            <th className="col-reason" rowSpan={2}>
              Reasons for and age on Retirement
            </th>
            <th className="col-remarks" rowSpan={2}>
              Remarks
            </th>
          </tr>
          <tr>
            <th className="col-emp">Emp Cd</th>
            <th className="col-desig">Designation</th>
            <th className="col-dept">Department</th>
          </tr>
        </thead>
        <tbody>
          <tr className="fp-proposal-print__data-row">
            <td className="cell-top cell-report" rowSpan={2}>
              {page.report_no}
            </td>
            <td className="cell-top cell-name" rowSpan={2}>
              <div className="fp-proposal-print__name-wrap">
                <div
                  className="fp-proposal-print__photo-box"
                  aria-label="Photograph to be fixed here"
                />
                <div className="fp-proposal-print__name">{page.name}</div>
              </div>
            </td>
            <td className="cell-top">{page.emp_cd}</td>
            <td className="cell-top">{page.designation}</td>
            <td className="cell-top">{page.department}</td>
            <td className="cell-top" rowSpan={2}>
              {page.entered_service}
            </td>
            <td className="cell-top" rowSpan={2}>
              {page.retired_from}
            </td>
            <td className="cell-top cell-reason" rowSpan={2}>
              <div>{page.retirement_reason}</div>
              <ol className="fp-proposal-print__notes">
                {(page.notes || []).map((note) => (
                  <li key={note}>{note}</li>
                ))}
              </ol>
            </td>
            <td className="cell-top cell-remarks" rowSpan={2}>
              <div className="fp-proposal-print__remarks">
                {remarkLines.map((line) => (
                  <div key={line}>{line}</div>
                ))}
              </div>
            </td>
          </tr>
          <tr className="fp-proposal-print__pay-row">
            <td colSpan={3} className="cell-pay">
              <div>
                <b>Pay</b> : {page.pay}
              </div>
              <div>
                <b>Last Pension Basic</b> : {page.last_pension_basic || ""}
              </div>
              <div>
                <b>On CPI</b> : {page.on_cpi || ""}
              </div>
            </td>
          </tr>
        </tbody>
      </table>

      <footer className="fp-proposal-print__footer">
        <div className="fp-proposal-print__id-card-box">
          <div>PENSION IDENTITY CARD</div>
          <div>ISSUED AND HANDED OVER ON</div>
          <div className="fp-proposal-print__sign-line">&nbsp;</div>
        </div>
        <div className="fp-proposal-print__sign-block">
          <div>Sanctioned</div>
          <div>FA&amp;CAO</div>
          <div className="fp-proposal-print__sign-space" />
        </div>
        <div className="fp-proposal-print__sign-block">
          <div>PPO Book Received</div>
          <div className="fp-proposal-print__sign-space" />
        </div>
        <div className="fp-proposal-print__footer-right">
          <div>Senior Accounts Officer</div>
          <div>Pension Section.</div>
        </div>
      </footer>
    </section>
  );
}

export default function FamilyPensionProposalPrint({ report }) {
  if (!report?.pages?.length) return null;

  return (
    <div id="family-pension-proposal-print" className="fp-proposal-print">
      {report.pages.map((page) => (
        <ReportPage
          key={`${page.clmca_id || "page"}-${page.emp_cd}-${page.page_no}`}
          report={report}
          page={page}
        />
      ))}
    </div>
  );
}
