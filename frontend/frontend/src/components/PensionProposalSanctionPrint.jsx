import "../styles/PensionProposalSanctionReport.css";

function ReportPage({ report, page }) {
  return (
    <section className="proposal-sanction-print__page">
      <header className="proposal-sanction-print__header">
        <div className="proposal-sanction-print__org">{report.org_name}</div>
        <div className="proposal-sanction-print__title">{report.report_title}</div>
        <div className="proposal-sanction-print__meta-top">
          <span>
            Page : {page.page_no} of {page.total_pages}
          </span>
          <span>Run Date : {report.run_date}</span>
        </div>
      </header>

      <table className="proposal-sanction-print__table">
        <thead>
          <tr>
            <th>Report No. / Roll No.</th>
            <th>Name</th>
            <th>
              Nature of Service
              <br />
              Emp Cd
              <br />
              Designation / Department
            </th>
            <th>Entered in Service</th>
            <th>Retired From</th>
            <th>Reasons for and age on Retirement</th>
            <th>Pension admissible under the Rules</th>
            <th>Remarks</th>
          </tr>
        </thead>
        <tbody>
          <tr>
            <td className="cell-top">
              <div>{page.case_no}</div><br />
              <div>{page.roll_no}</div>
            </td>
            <td className="cell-top">
              <div className="proposal-sanction-print__name">{page.name}</div><br />
              <div><b>Schemes :</b> <br/>{page.scheme}</div><br/>
              <div><b>Last Pay :</b> <br/>{page.last_pay}</div><br/>
              <div><b>Avg. Emoluments :</b> <br/>{page.avg_emoluments}</div>
            </td>
            <td className="cell-top">
              <div>{page.nature_of_service}</div><hr></hr><br/>
              <div>Emp Cd : {page.emp_cd}</div><hr></hr><br/>
              <div>{page.department}</div>
            </td>
            <td className="cell-top">{page.entered_service}</td>
            <td className="cell-top">{page.retired_from}</td>
            <td className="cell-top">
              <div>{page.retirement_reason}</div>
              <div>Age : {page.retirement_age}</div>
              <ul className="proposal-sanction-print__notes">
                {page.notes.map((note) => (
                  <li key={note}>{note}</li>
                ))}
              </ul>
            </td>
            <td className="cell-top">{page.pension_admissible_text}</td>
            <td className="cell-top">{page.remarks}</td>
          </tr>
        </tbody>
      </table>
      <br></br>
      <footer className="proposal-sanction-print__footer">
        <div>Sanctioned</div>
        <div>Recommended By</div>
      </footer>
    </section>
  );
}

export default function PensionProposalSanctionPrint({ report }) {
  if (!report?.pages?.length) return null;

  return (
    <div className="proposal-sanction-print">
      {report.pages.map((page) => (
        <ReportPage key={page.emp_cd} report={report} page={page} />
      ))}
    </div>
  );
}
