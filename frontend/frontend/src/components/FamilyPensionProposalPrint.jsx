import smpLogo from "../assets/images/SMP_Logo.png";
import "../styles/FamilyPensionProposalReport.css";

function ReportPage({ report, page }) {
  return (
    <section className="fp-proposal-print__page">
      <header className="fp-proposal-print__header">
        <img
          src={smpLogo}
          alt="SMP Kolkata"
          className="fp-proposal-print__logo"
        />
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
            <th className="col-report">Report No.</th>
            <th className="col-name">Name</th>
            <th className="col-nature">Nature of Service</th>
            <th className="col-date">Entered in Service</th>
            <th className="col-date">Retired From</th>
            <th className="col-reason">
              Reasons for and age on Retirement
            </th>
            <th className="col-remarks">Remarks</th>
          </tr>
        </thead>
        <tbody>
          <tr>
            <td className="cell-top">{page.report_no}</td>
            <td className="cell-top">
              <div className="fp-proposal-print__name">{page.name}</div>
            </td>
            <td className="cell-top">
              <div>
                <b>Emp Cd</b> : {page.emp_cd}
              </div>
              <div>
                <b>Designation</b> : {page.designation}
              </div>
              <div>
                <b>Department</b> : {page.department}
              </div>
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
            <td className="cell-top">{page.entered_service}</td>
            <td className="cell-top">{page.retired_from}</td>
            <td className="cell-top">
              <div>{page.retirement_reason}</div>
              <ol className="fp-proposal-print__notes">
                {(page.notes || []).map((note) => (
                  <li key={note}>{note}</li>
                ))}
              </ol>
            </td>
            <td className="cell-top">
              <div className="fp-proposal-print__remarks">
                {(page.remarks || "").split("\n").map((line) => (
                  <div key={line}>{line}</div>
                ))}
              </div>
            </td>
          </tr>
        </tbody>
      </table>

      <footer className="fp-proposal-print__footer">
        <div>
          <div>Sanctioned</div>
          <div>FA&amp;CAO</div>
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
          key={`${page.clmca_id}-${page.emp_cd}`}
          report={report}
          page={page}
        />
      ))}
    </div>
  );
}
