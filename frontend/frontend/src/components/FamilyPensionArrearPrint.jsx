import "../styles/FamilyPensionArrearPrint.css";

function pad2(n) {
  return String(n).padStart(2, "0");
}

function fmtDate(value) {
  if (!value) return "";
  const s = String(value).trim();
  // YYYY-MM-DD
  const m = s.match(/^(\d{4})-(\d{2})-(\d{2})/);
  if (m) return `${m[3]}/${m[2]}/${m[1]}`;
  // already DD/MM/YYYY
  if (/^\d{2}\/\d{2}\/\d{4}/.test(s)) return s.slice(0, 10);
  try {
    const d = new Date(s);
    if (!Number.isNaN(d.getTime())) {
      return `${pad2(d.getDate())}/${pad2(d.getMonth() + 1)}/${d.getFullYear()}`;
    }
  } catch {
    /* ignore */
  }
  return s;
}

function fmtAmt(value) {
  if (value == null || value === "") return "";
  const n = Number(value);
  if (Number.isNaN(n)) return String(value);
  return n.toLocaleString("en-IN", {
    maximumFractionDigits: 0,
  });
}

function fmtDa(value) {
  if (value == null || value === "") return "";
  const n = Number(value);
  if (Number.isNaN(n)) return String(value);
  return n.toLocaleString("en-IN", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
}

function nowStamp(d = new Date()) {
  return `${pad2(d.getDate())}/${pad2(d.getMonth() + 1)}/${d.getFullYear()} ${pad2(
    d.getHours()
  )}:${pad2(d.getMinutes())}:${pad2(d.getSeconds())}`;
}

/**
 * Detailed Sheet For Arrear Calculation (Oracle print layout).
 */
export default function FamilyPensionArrearPrint({ data, pageNo = 1, pageCount = 1 }) {
  if (!data) return null;

  const rows = Array.isArray(data.details) ? data.details : [];
  const pensionTotal =
    data.arrear_pension != null
      ? Number(data.arrear_pension)
      : rows.reduce((s, r) => s + (Number(r.arr_pen) || 0), 0);
  const reliefTotal =
    data.arrear_relief != null
      ? Number(data.arrear_relief)
      : rows.reduce((s, r) => s + (Number(r.arr_rlf) || 0), 0);
  const payable =
    data.total_payable != null
      ? Number(data.total_payable)
      : pensionTotal + reliefTotal;

  const empLabel = [data.emp_cd, data.emp_name].filter(Boolean).join(" - ");
  const printedAt = data.printed_at || nowStamp();

  return (
    <div className="fp-arrear-print" id="family-pension-arrear-print">
      <div className="fp-arrear-print__page">
        <div className="fp-arrear-print__band">
          <span>{printedAt}</span>
          <span>
            Page {pageNo} of {pageCount}
          </span>
        </div>

        <div className="fp-arrear-print__title">
          Detailed Sheet For Arrear Calculation
        </div>

        <table className="fp-arrear-print__meta">
          <tbody>
            <tr>
              <td className="lbl">Employee Code &amp; Name</td>
              <td className="sep">:</td>
              <td className="val" colSpan={4}>
                {empLabel}
              </td>
            </tr>
            <tr>
              <td className="lbl">Applicant Name</td>
              <td className="sep">:</td>
              <td className="val" colSpan={4}>
                {data.applicant_name || ""}
              </td>
            </tr>
            <tr>
              <td className="lbl">Case No</td>
              <td className="sep">:</td>
              <td className="val">{data.case_no ?? ""}</td>
              <td className="lbl">Claim ID</td>
              <td className="sep">:</td>
              <td className="val">{data.claim_id || ""}</td>
            </tr>
            <tr>
              <td className="lbl">Pensioner Death Date</td>
              <td className="sep">:</td>
              <td className="val">{fmtDate(data.pensioner_death_dt)}</td>
              <td className="lbl">Generated Basic</td>
              <td className="sep">:</td>
              <td className="val">{fmtAmt(data.generated_basic)}</td>
            </tr>
            <tr>
              <td className="lbl">Upgraded Basic</td>
              <td className="sep">:</td>
              <td className="val">{fmtAmt(data.upgraded_basic)}</td>
              <td className="lbl">Pension Arrear Payable</td>
              <td className="sep">:</td>
              <td className="val">{fmtAmt(pensionTotal)}</td>
            </tr>
            <tr>
              <td className="lbl">Relief Arrear Payable</td>
              <td className="sep">:</td>
              <td className="val" colSpan={4}>
                {fmtAmt(reliefTotal)}
              </td>
            </tr>
          </tbody>
        </table>

        <table className="fp-arrear-print__table">
          <colgroup>
            <col style={{ width: "16%" }} />
            <col style={{ width: "16%" }} />
            <col style={{ width: "22%" }} />
            <col style={{ width: "18%" }} />
            <col style={{ width: "28%" }} />
          </colgroup>
          <thead>
            <tr>
              <th colSpan={2}>Period</th>
              <th rowSpan={2}>Pension Arrear</th>
              <th rowSpan={2}>DA%</th>
              <th rowSpan={2}>Relief Arrear</th>
            </tr>
            <tr>
              <th>From</th>
              <th>To</th>
            </tr>
          </thead>
          <tbody>
            {rows.length === 0 ? (
              <tr>
                <td colSpan={5} className="fp-arrear-print__empty">
                  No arrear detail lines
                </td>
              </tr>
            ) : (
              rows.map((r, i) => (
                <tr key={`${r.period_from}-${r.period_to}-${i}`}>
                  <td className="ctr">{fmtDate(r.period_from)}</td>
                  <td className="ctr">{fmtDate(r.period_to)}</td>
                  <td className="num">{fmtAmt(r.arr_pen)}</td>
                  <td className="ctr">{fmtDa(r.da_pct)}</td>
                  <td className="num">{fmtAmt(r.arr_rlf)}</td>
                </tr>
              ))
            )}
            <tr>
              <td colSpan={2} className="tot-lbl">
                Total :-
              </td>
              <td className="num tot-lbl">{fmtAmt(pensionTotal)}</td>
              <td />
              <td className="num tot-lbl">{fmtAmt(reliefTotal)}</td>
            </tr>
            <tr>
              <td colSpan={4} className="payable">
                Total Payable &gt;&gt;
              </td>
              <td className="num tot-lbl">{fmtAmt(payable)}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  );
}

export function printFamilyPensionArrearSheet() {
  const source = document.getElementById("family-pension-arrear-print");
  if (!source) {
    window.print();
    return;
  }

  let portal = document.getElementById("fp-arrear-print-portal");
  if (!portal) {
    portal = document.createElement("div");
    portal.id = "fp-arrear-print-portal";
    document.body.appendChild(portal);
  }
  const clone = source.cloneNode(true);
  clone.id = "family-pension-arrear-print-clone";
  portal.replaceChildren(clone);
  document.documentElement.classList.add("fp-arrear-printing");

  const cleanup = () => {
    document.documentElement.classList.remove("fp-arrear-printing");
    portal.replaceChildren();
    window.removeEventListener("afterprint", cleanup);
  };
  window.addEventListener("afterprint", cleanup);
  window.print();
  // Fallback cleanup if afterprint does not fire
  setTimeout(cleanup, 1500);
}
