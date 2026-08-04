import smpLogo from "../assets/images/SMP_Logo.png";
import "../styles/PensionCommutationBillReport.css";

function FieldRow({ label, value }) {
  return (
    <div className="comm-sanction-print__field">
      <span className="comm-sanction-print__label">{label}</span>
      <span className="comm-sanction-print__value">{value || ""}</span>
    </div>
  );
}

function ReportPage({ report, page }) {
  return (
    <section className="comm-sanction-print__page">
      <header className="comm-sanction-print__header">
        <img
          src={smpLogo}
          alt="SMP Kolkata"
          className="comm-sanction-print__logo"
        />
        <div className="comm-sanction-print__heading">
          <div className="comm-sanction-print__org">{report.org_name}</div>
          <div className="comm-sanction-print__title">{report.report_title}</div>
        </div>
        <div className="comm-sanction-print__meta-top">
          <span>
            Page : {page.page_no} of {page.total_pages}
          </span>
          <span>Run Date : {report.run_date}</span>
        </div>
      </header>

      <div className="comm-sanction-print__fields">
        <FieldRow label="F.A. & C.A.O's Report :" value={page.fa_cao_report} />
        <FieldRow label="Name of Pensioner :" value={page.pensioner_name} />
        <FieldRow label="Designation etc. :" value={page.designation} />
        <FieldRow label="Amount of Pension :" value={page.pension_amount} />
        <FieldRow
          label="Particulars of sanction :"
          value={page.sanction_particulars}
        />
        <FieldRow
          label="Amount sought to be commuted :"
          value={page.amount_sought_commuted}
        />
        <FieldRow
          label="Reasons for commutation :"
          value={page.commutation_reasons}
        />
        <FieldRow
          label="Particulars of Medical Certificate of average expectations of life :"
          //value={page.medical_certificate}
          value="'NIL'"

        />
        <FieldRow
          label="Particulars of Previous commutations, if any :"
          value={page.previous_commutations}
        />
      </div>

      <p className="comm-sanction-print__narrative">{page.sanction_narrative}</p>
      <p className="comm-sanction-print__words">
        ({page.commutation_amount_words})
      </p>
      <p ></p>
      <footer className="comm-sanction-print__footer">
        <div className="comm-sanction-print__sign">
          <div>Fnancal Adviser and</div>
          <div>Chief Accounts Officer</div>
          
        </div>
        
        <div className="comm-sanction-print__sign">
          <div>Sanctioned</div>
          <p></p>
          <div>For Dy. Chairman</div>
        </div>
      </footer>
    </section>
  );
}

export default function PensionCommutationBillPrint({ report }) {
  if (!report?.pages?.length) return null;

  return (
    <div className="comm-sanction-print">
      {report.pages.map((page) => (
        <ReportPage key={page.emp_cd} report={report} page={page} />
      ))}
    </div>
  );
}
