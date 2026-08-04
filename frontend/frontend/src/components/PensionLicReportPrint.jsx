import smpLogo from "../assets/images/SMP_Logo.png";
import "../styles/PensionLicReport.css";

function DashedRule() {
  return <hr className="lic-report-print__rule" />;
}

function MetaInline({ label, value }) {
  return (
    <span className="lic-report-print__inline-field">
      <span className="lic-report-print__label">{label}</span>
      <span>{value || ""}</span>
    </span>
  );
}

function LicReportPage({ report, page }) {
  const { bill, org_name, report_title, bank_wise_heading } = report;

  return (
    <section className="lic-report-print__page">
      <header className="lic-report-print__header">
        <img src={smpLogo} alt="SMP Kolkata" className="lic-report-print__logo" />
        <div>
          <div className="lic-report-print__org">{org_name}</div>
          <div className="lic-report-print__title">{report_title}</div>
        </div>
        <div className="lic-report-print__page-no">
          Page {page.page_no} of {page.total_pages}
        </div>
      </header>

      <DashedRule />

      <div className="lic-report-print__meta">
        <div className="lic-report-print__meta-line">
          <MetaInline label="BILL No. :" value={bill.bill_no} />
          <MetaInline label="MM/YYYY :" value={bill.mm_yyyy} />
        </div>
        <div className="lic-report-print__meta-line">
          <MetaInline label="ABST No. :" value="" />
          <MetaInline label="DATE :" value="" />
        </div>
      </div>

      <DashedRule />

      <div className="lic-report-print__detail-line">
        <MetaInline label="Roll No. :" value={page.roll_no} />
        <MetaInline label="Case No. :" value={page.case_no} />
        <MetaInline label="Base CPI :" value={page.base_cpi} />
        <MetaInline label="Sepn. Date :" value={page.sepn_date} />
      </div>

      <div className="lic-report-print__detail-line">
        <MetaInline label="Name :" value={page.name} />
        <MetaInline label="A/c No. :" value={page.account_no} />
      </div>

      <div className="lic-report-print__detail-line">
        <MetaInline label="Desgn :" value={page.designation} />
      </div>

      <div className="lic-report-print__body-cols">
        <div className="lic-report-print__col-earn">
          <div className="lic-report-print__month-label">
            Month : {page.month_label}
          </div>
          <table className="lic-report-print__earn-table">
            <thead>
              <tr>
                <th>Earn/Dedn Desc</th>
                <th className="amount">Amount</th>
              </tr>
            </thead>
            <tbody>
              {page.line_items.map((line) => (
                <tr key={`${line.earn_dedn_type}-${line.earn_dedn_cd}`}>
                  <td>{line.description}</td>
                  <td className="amount">{line.amount_display}</td>
                </tr>
              ))}
              <tr className="summary">
                <td>Gross Earn</td>
                <td className="amount">{page.gross_earn_display}</td>
              </tr>
              <tr className="summary">
                <td>Gross Dedn</td>
                <td className="amount">{page.gross_dedn_display}</td>
              </tr>
              <tr className="summary">
                <td>Net Earn</td>
                <td className="amount">{page.net_earn_display}</td>
              </tr>
            </tbody>
          </table>
        </div>

        <div className="lic-report-print__col-ack">
          <div className="lic-report-print__ack-label">Acknowledgement</div>
          <div className="lic-report-print__ack-box" />
        </div>

        <div className="lic-report-print__col-treasury">
          <div>Treasurer</div>
          <div>From Gratuity</div>
          {page.treasurer_holdup_line ? (
            <div className="lic-report-print__holdup">{page.treasurer_holdup_line}</div>
          ) : null}
          <div>S.A.O.P.S</div>
        </div>
      </div>

      <DashedRule />

      <div className="lic-report-print__bank-total">
        <div>Bank-wise Total figures :</div>
        <div>{bank_wise_heading}</div>
        <div className="line">
          <span>No. of cases :</span>
          <span>{page.no_of_cases}</span>
        </div>
        <div className="line">
          <span>Gross Earn :</span>
          <span>{page.gross_earn_display}</span>
          <span className="lic-report-print__words">
            ({page.gross_earn_words})
          </span>
        </div>
        <div className="line">
          <span>Gross Dedn :</span>
          <span>{page.gross_dedn_display}</span>
        </div>
        <div className="line">
          <span>Net Earn :</span>
          <span>{page.net_earn_display}</span>
          <span className="lic-report-print__words">({page.net_earn_words})</span>
        </div>
      </div>

      <DashedRule />

      <footer className="lic-report-print__footer">
        <div className="lic-report-print__sign">
          <div>Sr. Acc Officer</div>
          <div>Pension Section</div>
          <div>Kolkata Port Trust</div>
        </div>
        <div className="lic-report-print__sign">
          <div>Financial Adviser And Chief Acc Officer</div>
          <div>Kolkata Port Trust</div>
        </div>
      </footer>
    </section>
  );
}

export default function PensionLicReportPrint({ report }) {
  if (!report?.pages?.length) return null;

  return (
    <div className="lic-report-print">
      {report.pages.map((page) => (
        <LicReportPage key={page.fmpen_id} report={report} page={page} />
      ))}
    </div>
  );
}
