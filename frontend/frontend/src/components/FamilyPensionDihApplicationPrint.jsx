import "../styles/FamilyPensionDihApplicationReport.css";

function CellLines({ lines }) {
  if (!lines?.length) return null;
  return (
    <>
      {lines.map((line, idx) => (
        <span key={`${idx}-${line.slice(0, 24)}`}>
          {idx > 0 ? <br /> : null}
          {line}
        </span>
      ))}
    </>
  );
}

function ReportPage({ report, page }) {
  const remarks = Array.isArray(page.remarks)
    ? page.remarks
    : String(page.remarks || "")
        .split("\n")
        .filter(Boolean);
  const reasonNotes = page.reason_notes || [];
  const employeeName =
    page.name_line_employee || page.employee_name || "";
  const pensionerName =
    page.name_line_pensioner || page.pensioner_name || "";

  return (
    <section className="fp-dih-print__page">
      <table className="fp-dih-print__layout" cellPadding={0} cellSpacing={0}>
        <tbody>
          <tr>
            <td className="fp-dih-print__header-left" />
            <td className="fp-dih-print__header-center">
              <table className="fp-dih-print__inner" cellPadding={0} cellSpacing={0}>
                <tbody>
                  <tr>
                    <td className="fp-dih-print__org">{report.org_name}</td>
                  </tr>
                  <tr>
                    <td className="fp-dih-print__title">{report.report_title}</td>
                  </tr>
                </tbody>
              </table>
            </td>
            <td className="fp-dih-print__header-right">
              <table className="fp-dih-print__inner" cellPadding={0} cellSpacing={0}>
                <tbody>
                  <tr>
                    <td>Run Date : {report.run_date}</td>
                  </tr>
                  <tr>
                    <td>
                      Page {page.page_no} of {page.total_pages}
                    </td>
                  </tr>
                </tbody>
              </table>
            </td>
          </tr>
        </tbody>
      </table>

      <table className="fp-dih-print__table" cellPadding={0} cellSpacing={0}>
        <thead>
          <tr>
            <th>
              Case No.
              <br />
              / Roll No.
            </th>
            <th>
              Name of Fam.
              <br />
              Pensioner
              <br />
              Name of Employee
            </th>
            <th colSpan={3}>
              Nature of Service
              <br />
              Empno/Designation/Department
            </th>
            <th>
              Entered
              <br />
              in Service
            </th>
            <th>
              Retired
              <br />
              From
            </th>
            <th>Reasons for and age on Retirement</th>
            <th>
              Pension Admissible
              <br />
              Under the Rules
            </th>
            <th>Remarks</th>
          </tr>
        </thead>
        <tbody>
          <tr>
            <td rowSpan={2} className="cell-top">
              {page.case_no || page.report_no}
              {page.roll_no ? (
                <>
                  <br />
                  {page.roll_no}
                </>
              ) : null}
            </td>
            <td rowSpan={2} className="cell-top">
              {employeeName}
              {pensionerName ? (
                <>
                  <br />
                  {pensionerName}
                </>
              ) : null}
            </td>
            <td colSpan={3} rowSpan={2} className="cell-top cell-nature-stack">
              {page.designation}
              <br />
              {page.emp_cd}
              <br />
              {page.department}
              <br />
              {page.pension_scheme}
              <br />
              <b>Pay</b> : {page.pay || "0"}
              <br />
              <b>Spl Pay</b> : {page.spl_pay ?? "0"}
            </td>
            <td className="cell-top cell-center">{page.entered_service}</td>
            <td className="cell-top cell-center">{page.retired_from}</td>
            <td className="cell-top cell-reason">
              {page.expired_reason || page.retirement_reason}
            </td>
            <td rowSpan={2} className="cell-top cell-admissible">
              {page.dcr_gratuity_line}
            </td>
            <td rowSpan={2} className="cell-top cell-remarks">
              <CellLines lines={remarks} />
            </td>
          </tr>
          <tr>
            <td colSpan={3} className="cell-top cell-reason-block">
              <CellLines lines={reasonNotes} />
            </td>
          </tr>
        </tbody>
      </table>

      <table className="fp-dih-print__footer-table" cellPadding={0} cellSpacing={0}>
        <tbody>
          <tr>
            <td className="fp-dih-print__footer-left">
              <table className="fp-dih-print__inner" cellPadding={0} cellSpacing={0}>
                <tbody>
                  <tr>
                    <td>SANCTIONED</td>
                  </tr>
                  <tr>
                    <td>FA&amp;CAO</td>
                  </tr>
                  <tr>
                    <td className="fp-dih-print__sign-space">&nbsp;</td>
                  </tr>
                </tbody>
              </table>
            </td>
            <td className="fp-dih-print__footer-right">
              <table
                className="fp-dih-print__inner fp-dih-print__inner-right"
                cellPadding={0}
                cellSpacing={0}
              >
                <tbody>
                  <tr>
                    <td>Senior Accounts Officer</td>
                  </tr>
                  <tr>
                    <td>Pension Section.</td>
                  </tr>
                </tbody>
              </table>
            </td>
          </tr>
        </tbody>
      </table>
    </section>
  );
}

export default function FamilyPensionDihApplicationPrint({ report }) {
  if (!report?.pages?.length) return null;

  return (
    <div id="family-pension-dih-print" className="fp-dih-print">
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
