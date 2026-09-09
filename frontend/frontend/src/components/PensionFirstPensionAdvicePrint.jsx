import "../styles/PensionFirstPensionAdviceReport.css";

function SignatureBlock({ page, showLeftCode = true }) {
  return (
    <div className="fp-advice-print__signature">
      <div className="fp-advice-print__signature-left">
        {showLeftCode ? page.signatory_left_code : null}
      </div>
      <div className="fp-advice-print__signature-right">
        <div className="fp-advice-print__signature-space" aria-hidden="true" />
        {(page.signatory_title || []).map((line) => (
          <div key={line}>{line}</div>
        ))}
      </div>
    </div>
  );
}

function AdviceLetter({ page }) {
  const bodyParas = page.body_paragraphs || page.paragraphs || [];

  return (
    <section className="fp-advice-print__page">
      <header className="fp-advice-print__org">{page.org_name}</header>

      <div className="fp-advice-print__meta">
        <span>No. {page.advice_ref_no}</span>
        <div className="fp-advice-print__meta-right">
          <div>{page.department_label}</div>
          <div>Date : {page.report_date}</div>
        </div>
      </div>

      <div className="fp-advice-print__to-block">
        <div>To,</div>
        <div className="fp-advice-print__recipient">{page.recipient_name}</div>
      </div>

      <div className="fp-advice-print__subject">Sub : {page.subject}</div>

      <div className="fp-advice-print__refs">
        <div>Pension Case No {page.pension_case_no}</div>
        <div>Pension Roll No {page.pension_roll_no}</div>
        <div>Through : {page.through_office}</div>
      </div>

      <div className="fp-advice-print__body">
        {bodyParas.map((text, index) => (
          <p key={index}>{text}</p>
        ))}
      </div>

      {/* Signature before Copy to — CVF left, space then FA & CAO */}
      <SignatureBlock page={page} showLeftCode />

      <div className="fp-advice-print__copy-to">
        <div className="fp-advice-print__copy-to-label">
          Copy to: {page.copy_to_office}
        </div>
        <p>{page.copy_to_text}</p>
      </div>

      {/* Signature space after Copy-to paragraph */}
      <SignatureBlock page={page} showLeftCode />
    </section>
  );
}

export default function PensionFirstPensionAdvicePrint({ report }) {
  if (!report?.pages?.length) return null;

  return (
    <div className="fp-advice-print">
      {report.pages.map((page) => (
        <div key={page.emp_cd} className="fp-advice-print__letter">
          <AdviceLetter page={page} />
        </div>
      ))}
    </div>
  );
}
