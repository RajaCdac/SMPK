import smpLogo from "../assets/images/SMP_Logo.png";
import "../styles/PensionSeparateCommutationBillReport.css";

function FieldPair({ label, value }) {
  return (
    <div className="sepcom-bill-print__field">
      <span className="sepcom-bill-print__label">{label}</span>
      <span className="sepcom-bill-print__value">{value ?? ""}</span>
    </div>
  );
}

function ReportPage({ report, page }) {
  return (
    <section className="sepcom-bill-print__page">
      <header className="sepcom-bill-print__header">
        <img
          src={smpLogo}
          alt="SMP Kolkata"
          className="sepcom-bill-print__logo"
        />
        <div className="sepcom-bill-print__heading">
          <div className="sepcom-bill-print__org">{report.org_name}</div>
          <div className="sepcom-bill-print__title">{report.report_title}</div>
          <div className="sepcom-bill-print__module">
            MODULE : {report.module_name}
          </div>
        </div>
        <div className="sepcom-bill-print__meta-top">
          <span>PAGE NO. : {page.page_no}</span>
          <span>RUNNING DATE : {report.run_date}</span>
        </div>
      </header>

      <div className="sepcom-bill-print__details">
        <div className="sepcom-bill-print__details-col">
          <FieldPair label="Bill No :" value={page.bill_no} />
          <FieldPair label="Employee Code and Name :" value={page.employee_label} />
          <FieldPair label="C.A. No. :" value={page.ca_no} />
          <FieldPair
            label="Original Pension Amt. :"
            value={page.original_pension_amt_display}
          />
          <FieldPair label="Appcn No. :" value={page.appcn_no} />
          <FieldPair label="Appcn Dt. :" value={page.appcn_dt} />
          <FieldPair
            label="Commuted Portion :"
            value={page.commuted_portion_display}
          />
        </div>
        <div className="sepcom-bill-print__details-col">
          <FieldPair label="Commutation Year :" value={page.commutation_year} />
          <FieldPair label="Commutation Month :" value={page.commutation_month} />
          <FieldPair label="Bank :" value={page.bank} />
          <FieldPair
            label="Commutation % :"
            value={page.commutation_percent_display}
          />
        </div>
      </div>

      <table className="sepcom-bill-print__table">
        <thead>
          <tr>
            <th>Earning/Deduction</th>
            <th className="amount">Original Amt.</th>
            <th className="amount">Amount</th>
          </tr>
        </thead>
        <tbody>
          {page.line_items.map((line) => (
            <tr key={`${line.earn_dedn_type}-${line.earn_dedn_cd}`}>
              <td>{line.description}</td>
              <td className="amount">{line.original_amt_display}</td>
              <td className="amount">{line.amount_display}</td>
            </tr>
          ))}
          <tr className="sepcom-bill-print__total-row">
            <td>Total :</td>
            <td className="amount">{page.total_original_amt_display}</td>
            <td className="amount">{page.total_amount_display}</td>
          </tr>
        </tbody>
      </table>

      <footer className="sepcom-bill-print__footer">
        <div className="sepcom-bill-print__sign-left">
          <div>Senior Accounts Officer</div>
          <div>Pension Section</div>
        </div>
        <div className="sepcom-bill-print__ack-box">Acknowledgement</div>
        <div className="sepcom-bill-print__sign-right">
          <div>Sanctioned</div>
          <div>F.A. &amp; C.A.O</div>
        </div>
      </footer>
    </section>
  );
}

export default function PensionSeparateCommutationBillPrint({ report }) {
  if (!report?.pages?.length) return null;

  return (
    <div className="sepcom-bill-print">
      {report.pages.map((page) => (
        <ReportPage key={page.emp_cd || page.sepcom_id} report={report} page={page} />
      ))}
    </div>
  );
}
