import "../styles/FamilyPensionLicBillPrint.css";

/**
 * Oracle First_Fpen_Bill_Report_Lic layout (portrait monospaced).
 * Matches FI_PN_FPENBILL_LIC / sample First Family Pension Bill print.
 */
export default function FamilyPensionLicBillPrint({ bill }) {
  const p = bill?.print;
  if (!bill?.bill_no || !p) return null;

  const dashed =
    "--------------------------------------------------------------------------------";
  const detailLines = p.detail_lines || [];
  const remarks = p.remarks || [];

  return (
    <div className="fp-lic-bill-print" aria-hidden="true">
      <section className="fp-lic-bill-print__page">
        <div className="fp-lic-bill-print__sheet">
          <div className="fp-lic-bill-print__header">
            <div className="fp-lic-bill-print__page-no">
              Page {p.page_no || 1} of {p.total_pages || 1}
            </div>
            <div className="fp-lic-bill-print__org">
              {p.org_name || "KOLKATA PORT TRUST"}
            </div>
          </div>

          <div className="fp-lic-bill-print__rule">{dashed}</div>
          <div className="fp-lic-bill-print__subtitle">{p.report_title}</div>
          <div className="fp-lic-bill-print__rule">{dashed}</div>

          <div className="fp-lic-bill-print__meta">
            <span>Bill No&nbsp;&nbsp;: {p.bill_no || bill.bill_no}</span>
            <span>Bill Date : {p.bill_date}</span>
          </div>

          <div className="fp-lic-bill-print__rule">{dashed}</div>

          <div className="fp-lic-bill-print__identity">
            <div className="fp-lic-bill-print__identity-left">
              <div>
                <span className="lbl">Name :</span> {p.deceased_name}
              </div>
              <div>
                <span className="lbl">Case No. :</span> {p.case_no || ""}
              </div>
              <div>
                <span className="lbl">Roll No:</span> {p.roll_no || ""}
              </div>
              <div>
                <span className="lbl">Designation:</span> {p.designation || ""}
              </div>
              <div>
                <span className="lbl">Department:</span>{" "}
                {p.org_department || p.department || ""}
              </div>
              <div>
                <span className="lbl">Retirement Date:</span>{" "}
                {p.retirement_date || ""}
              </div>
            </div>
            <div className="fp-lic-bill-print__identity-right">
              {p.beneficiary || ""}
            </div>
          </div>

          <div className="fp-lic-bill-print__rule">{dashed}</div>

          <div className="fp-lic-bill-print__earn-head">
            <span>Month {p.month_label}</span>
            <span className="amt">Amount</span>
          </div>
          <div className="fp-lic-bill-print__earn-head muted">
            <span>Earn/Dedn Desc</span>
            <span className="amt" />
          </div>

          <div className="fp-lic-bill-print__earn-body">
            {detailLines.map((ln, i) => (
              <div key={`${ln.desc}-${i}`} className="fp-lic-bill-print__earn-row">
                <span className="desc">{ln.desc}</span>
                <span className="amt">{ln.amount_disp}</span>
              </div>
            ))}
            <div className="fp-lic-bill-print__earn-row totals">
              <span className="desc">Gross Earn</span>
              <span className="amt">{p.gross_earn_disp}</span>
            </div>
            <div className="fp-lic-bill-print__earn-row totals">
              <span className="desc">Gross Dedn</span>
              <span className="amt">{p.gross_dedn_disp}</span>
            </div>
            <div className="fp-lic-bill-print__earn-row totals">
              <span className="desc">Net Earn</span>
              <span className="amt">{p.net_earn_disp}</span>
            </div>
          </div>

          <div className="fp-lic-bill-print__words">{p.amount_in_words}</div>

          {/*
            Layout (Oracle LIC sample):
              left blank | Acknowledgement + box
              page totals | Treasurer + remarks  (same line as Treasurer)
          */}
          <div className="fp-lic-bill-print__bottom">
            <div className="fp-lic-bill-print__bottom-spacer" aria-hidden="true" />
            <div className="fp-lic-bill-print__ack">
              <div className="fp-lic-bill-print__ack-label">Acknowledgement:</div>
              <div className="fp-lic-bill-print__ack-box" />
            </div>

            <div className="fp-lic-bill-print__footer-sum">
              <div className="fp-lic-bill-print__sum-row">
                <span>No. of cases</span>
                <span>{p.no_of_cases || 1}</span>
              </div>
              <div className="fp-lic-bill-print__sum-row">
                <span>Gross Earn</span>
                <span>{p.gross_earn_commas}</span>
              </div>
              <div className="fp-lic-bill-print__sum-row">
                <span>Gross Dedn</span>
                <span>{p.gross_dedn_commas}</span>
              </div>
              <div className="fp-lic-bill-print__sum-row">
                <span>Net Earn</span>
                <span>{p.net_earn_commas}</span>
              </div>
            </div>

            <div className="fp-lic-bill-print__ack-tail">
              <div className="fp-lic-bill-print__treasurer">Treasurer:</div>
              <div className="fp-lic-bill-print__remarks">
                {remarks.map((line, i) => (
                  <div key={`rm-${i}`}>{line}</div>
                ))}
              </div>
            </div>
          </div>
        </div>
      </section>
    </div>
  );
}
