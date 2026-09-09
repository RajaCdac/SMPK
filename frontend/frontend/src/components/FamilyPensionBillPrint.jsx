import "../styles/FamilyPensionBillPrint.css";

/**
 * Oracle-style First Family Pension Bill (landscape monospaced).
 * Matches FI_PN First Family Pension Bill print layout.
 */
export default function FamilyPensionBillPrint({ bill }) {
  const p = bill?.print;
  if (!bill?.bill_no || !p) return null;

  const dashed = "----------------------------------------------------------------------------------------------------";
  const detailLines = p.detail_lines || [];

  return (
    <div className="fp-bill-print" aria-hidden="true">
      <section className="fp-bill-print__page">
        <div className="fp-bill-print__sheet">
          {/* Title */}
          <div className="fp-bill-print__title-row">
            <div className="fp-bill-print__org">{p.org_name || "KOLKATA PORT TRUST"}</div>
            <div className="fp-bill-print__page-no">
              Page {p.page_no || 1} of {p.total_pages || 1}
            </div>
          </div>
          <div className="fp-bill-print__subtitle">{p.report_title}</div>

          <div className="fp-bill-print__rule">{dashed}</div>

          {/* Bill meta */}
          <div className="fp-bill-print__meta">
            <span>
              Bill No&nbsp;&nbsp;: {p.bill_no || bill.bill_no}
            </span>
            <span className="fp-bill-print__meta-date">
              Bill Date : {p.bill_date}
            </span>
          </div>

          <div className="fp-bill-print__rule">{dashed}</div>

          {/* Pensioner block */}
          <div className="fp-bill-print__pair">
            <span className="left">** Name : {p.deceased_name}</span>
            <span className="right">Roll No: {p.roll_no || ""}</span>
          </div>
          <div className="fp-bill-print__pair">
            <span className="left">Case No.: {p.case_no || ""}</span>
            <span className="right">Designation: {p.designation || ""}</span>
          </div>
          <div className="fp-bill-print__pair">
            <span className="left">{p.beneficiary || ""}</span>
            <span className="right">Department: {p.department || ""}</span>
          </div>
          <div className="fp-bill-print__pair">
            <span className="left" />
            <span className="right">
              Retirement Date: {p.retirement_date || ""}
            </span>
          </div>

          <div className="fp-bill-print__rule">{dashed}</div>

          {/* Earnings header */}
          <div className="fp-bill-print__earn-head">
            <span>Month {p.month_label}</span>
            <span className="fp-bill-print__col-amt">Amount</span>
          </div>
          <div className="fp-bill-print__earn-head muted">
            <span>Earn/Dedn Desc</span>
            <span className="fp-bill-print__col-amt" />
          </div>

          {/* Detail lines + hold-up note */}
          <div className="fp-bill-print__earn-body">
            <div className="fp-bill-print__earn-left">
              {detailLines.map((ln, i) => (
                <div key={`${ln.desc}-${i}`} className="fp-bill-print__earn-row">
                  <span className="desc">{ln.desc}</span>
                  <span className="amt">{ln.amount_disp}</span>
                </div>
              ))}
              <div className="fp-bill-print__earn-row totals">
                <span className="desc">Gross Earn</span>
                <span className="amt">{p.gross_earn_disp}</span>
              </div>
              <div className="fp-bill-print__earn-row totals">
                <span className="desc">Gross Dedn</span>
                <span className="amt">{p.gross_dedn_disp}</span>
              </div>
              <div className="fp-bill-print__earn-row totals">
                <span className="desc">Net Earn</span>
                <span className="amt">{p.net_earn_disp}</span>
              </div>
            </div>
            {p.hold_up_disp ? (
              <div className="fp-bill-print__hold">{p.hold_up_disp}</div>
            ) : null}
          </div>

          <div className="fp-bill-print__words">{p.amount_in_words}</div>

          {/* Footer summary + acknowledgement */}
          <div className="fp-bill-print__bottom">
            <div className="fp-bill-print__bottom-left">
              <div>No. of cases&nbsp;&nbsp;{p.no_of_cases || 1}</div>
              <div className="fp-bill-print__ack-label">Acknowledgement:</div>
              <div className="fp-bill-print__ack-box" />
            </div>
            <div className="fp-bill-print__bottom-right">
              <div className="fp-bill-print__sum-row">
                <span>Gross Earn</span>
                <span>{p.gross_earn_commas}</span>
              </div>
              <div className="fp-bill-print__sum-row">
                <span>Gross Dedn</span>
                <span>{p.gross_dedn_commas}</span>
              </div>
              <div className="fp-bill-print__sum-row">
                <span>Net Earn</span>
                <span>{p.net_earn_commas}</span>
              </div>
            </div>
          </div>

          {/* Signatures */}
          <div className="fp-bill-print__sign">
            <div>
              <div>Sr. Acc Officer</div>
              <div>Pension Section</div>
              <div>Kolkata Port Trust</div>
            </div>
            <div className="right">
              <div>Financial Adviser And Chief Acc Officer</div>
              <div>Kolkata Port Trust</div>
            </div>
          </div>
        </div>
      </section>
    </div>
  );
}
