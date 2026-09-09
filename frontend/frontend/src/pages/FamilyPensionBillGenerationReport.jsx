import { useCallback, useEffect, useRef, useState } from "react";
import API from "../services/Api";
import FamilyPensionBillPrint from "../components/FamilyPensionBillPrint";
import { printPensionReport } from "../utils/pensionReportPrint";
import "../styles/FamilyPensionBillPrint.css";
import "../styles/pension-report-print.css";
import "../styles/FamilyPensionSanctionReport.css";

const MONTH_OPTIONS = [
  ["1", "JAN"],
  ["2", "FEB"],
  ["3", "MAR"],
  ["4", "APR"],
  ["5", "MAY"],
  ["6", "JUN"],
  ["7", "JUL"],
  ["8", "AUG"],
  ["9", "SEP"],
  ["10", "OCT"],
  ["11", "NOV"],
  ["12", "DEC"],
];

function billYearChoices(center) {
  const y = Number(center) || new Date().getFullYear();
  const years = [];
  for (let i = y + 1; i >= y - 20; i -= 1) years.push(String(i));
  if (center && !years.includes(String(center))) years.unshift(String(center));
  return years;
}

function apiErrorMessage(err, fallback = "Request failed") {
  const data = err?.response?.data;
  if (!data) return err?.message || fallback;
  if (typeof data === "string") return data.slice(0, 400);
  if (data.error) return String(data.error);
  if (data.detail) {
    return typeof data.detail === "string"
      ? data.detail
      : JSON.stringify(data.detail);
  }
  return fallback;
}

function isAlreadyBilled(msg) {
  return String(msg || "")
    .toLowerCase()
    .includes("already billed");
}

function billKindLabel(billType) {
  return billType === "M" ? "Monthly" : "First";
}

function billStatusMessage(billData) {
  if (!billData?.bill_no) return "";
  const kind = billKindLabel(String(billData.bill_type || "").toUpperCase());
  const earned =
    billData.total_amt_earned != null
      ? ` · Earned ₹${billData.total_amt_earned}`
      : "";
  const deducted = billData.total_amt_deducted
    ? ` · Deducted ₹${billData.total_amt_deducted}`
    : "";
  if (billData.source === "existing") {
    return `${kind} bill ${billData.bill_no}${earned}${deducted}`;
  }
  return (
    `${kind} bill generated: ${billData.bill_no}${earned}${deducted}` +
    ` · ${billData.lines?.length || 0} line(s)`
  );
}

export default function FamilyPensionBillGenerationReport() {
  const now = new Date();
  const [empCd, setEmpCd] = useState("");
  const [clmcaId, setClmcaId] = useState("");
  const [dispName, setDispName] = useState("");
  const [matches, setMatches] = useState([]);
  const [bill, setBill] = useState(null);
  const [billType, setBillType] = useState("N");
  const [billMonth, setBillMonth] = useState(String(now.getMonth() + 1));
  const [billYear, setBillYear] = useState(String(now.getFullYear()));
  const [loading, setLoading] = useState(false);
  const [billLoading, setBillLoading] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const empRef = useRef(null);

  const loadBill = useCallback(
    async (opts = {}) => {
      const cid = String(opts.clmca_id ?? clmcaId ?? "").trim();
      const emp = String(opts.emp_cd ?? empCd ?? "").trim();
      const billNo = String(opts.bill_no ?? "").trim();
      const type = String(opts.bill_type ?? billType ?? "N").toUpperCase() || "N";
      const month = String(opts.month ?? billMonth ?? "");
      const year = String(opts.year ?? billYear ?? "");
      if (!cid && !emp && !billNo) {
        setError("Enter Emp Code or Claim ID to load the bill");
        return null;
      }

      setBillLoading(true);
      setError("");
      try {
        const params = { bill_type: type };
        if (billNo) params.bill_no = billNo;
        if (cid) params.clmca_id = cid;
        if (emp) params.emp_cd = emp;
        params.month = month;
        params.year = year;
        const { data } = await API.get("family-pension/bill-print/", { params });
        if (data?.error) {
          setBill(null);
          setError(data.error);
          return null;
        }
        setBill(data);
        setMessage(billStatusMessage(data));
        return data;
      } catch (err) {
        setBill(null);
        setError(apiErrorMessage(err, "Could not load PFN bill"));
        return null;
      } finally {
        setBillLoading(false);
      }
    },
    [clmcaId, empCd, billType, billMonth, billYear]
  );

  const applyClaim = useCallback(
    async (claim) => {
      setClmcaId(claim.clmca_id || "");
      setEmpCd(claim.emp_cd || "");
      setDispName(claim.disp_name || claim.applicant_name || "");
      setMatches([]);
      setBill(null);
      const loaded = await loadBill({
        clmca_id: claim.clmca_id,
        emp_cd: claim.emp_cd,
      });
      if (!loaded) {
        setMessage(
          `Claim ${claim.clmca_id} loaded. No ${billKindLabel(billType)} PFN bill yet — use Generate Bill after First FP.`
        );
        setError("");
      }
    },
    [loadBill, billType]
  );

  const loadClaim = async (opts = {}) => {
    const cid = String(opts.clmca_id ?? clmcaId ?? "").trim();
    const emp = String(opts.emp_cd ?? empCd ?? "").trim();
    if (!cid && !emp) {
      setError("Enter Emp Code or Claim ID");
      return;
    }

    setLoading(true);
    setError("");
    setMessage("");
    setBill(null);
    try {
      const params = {};
      if (cid) params.clmca_id = cid;
      else params.emp_cd = emp;

      const { data } = await API.get("family-pension/claim/", { params });
      if (data?.claim) {
        await applyClaim(data.claim);
      } else if (data?.matches?.length) {
        setMatches(data.matches);
        if (emp) setEmpCd(emp);
        setMessage(
          data.message ||
            `${data.matches.length} claim(s) found — select one to preview.`
        );
      } else {
        setError(data?.error || "Claim not found for this employee");
      }
    } catch (err) {
      setError(apiErrorMessage(err, "Failed to load claim"));
    } finally {
      setLoading(false);
    }
  };

  const searchByEmp = () => {
    const emp = String(empRef.current?.value ?? empCd ?? "").trim();
    if (!emp) {
      setError("Enter Emp Code");
      return;
    }
    setEmpCd(emp);
    setClmcaId("");
    loadClaim({ emp_cd: emp, clmca_id: "" });
  };

  const postGenerate = async (regenerate = false) => {
    const payload = {
      clmca_id: clmcaId,
      emp_cd: empCd || undefined,
      bill_type: billType,
      regenerate,
    };
    if (billType === "M" || billType === "N") {
      payload.month = Number(billMonth);
      payload.year = Number(billYear);
    }
    const { data } = await API.post("family-pension/generate-bill/", payload);
    if (data?.error) {
      throw new Error(data.error);
    }
    return data;
  };

  const handleGenerateBill = async () => {
    if (!clmcaId) {
      setError("Search Emp Code and load a claim first");
      return;
    }
    const kind = billKindLabel(billType);
    const period = ` for ${billMonth}/${billYear}`;
    if (
      !window.confirm(
        `Generate ${kind} Family Pension Bill (PFN) for claim ${clmcaId}` +
          (empCd ? ` / emp ${empCd}` : "") +
          `${period}?` +
          (billType === "M"
            ? "\nFirst disbursement includes unpaid months from WEF; later months are the current month only."
            : "\nFirst FP is the monthly rate. This disbursement bill pays pension + DA from WEF through this month (processing delay).")
      )
    ) {
      return;
    }

    setGenerating(true);
    setError("");
    try {
      const data = await postGenerate(false);
      setBill(data);
      setMessage(billStatusMessage(data));
    } catch (err) {
      const msg = apiErrorMessage(err, "Bill generation failed");
      if (isAlreadyBilled(msg)) {
        if (window.confirm(`${msg}\n\nRegenerate and issue a new PFN bill?`)) {
          try {
            const data = await postGenerate(true);
            setBill(data);
            setMessage(billStatusMessage(data));
            setError("");
          } catch (err2) {
            setError(apiErrorMessage(err2, "Bill regenerate failed"));
          }
        } else if (window.confirm("Load the existing PFN bill instead?")) {
          await loadBill({ clmca_id: clmcaId, emp_cd: empCd });
        } else {
          setError(msg);
        }
      } else {
        setError(msg);
      }
    } finally {
      setGenerating(false);
    }
  };

  const handlePrint = () => {
    if (!bill?.print || !bill?.bill_no) {
      setError("Load or generate a bill before printing");
      return;
    }
    printPensionReport(null, {
      selector: "#family-pension-bill-print-root .fp-bill-print",
      orientation: "landscape",
    });
  };

  useEffect(() => {
    empRef.current?.focus();
  }, []);

  const busy = loading || billLoading || generating;
  const kind = billKindLabel(billType);

  return (
    <div className="fps-sanction-page container-fluid mt-2 px-2 px-md-3">
      <div className="fps-sanction-title">
        FAMILY PENSION BILL GENERATION
      </div>

      <div className="fps-sanction-toolbar smpk-form">
        <div className="fps-sanction-toolbar-row">
          <div className="fps-sanction-toolbar-left">
            <div className="fps-sanction-radio" role="radiogroup" aria-label="Bill type">
              <label>
                <input
                  type="radio"
                  name="fp-bill-type"
                  checked={billType === "N"}
                  disabled={busy}
                  onChange={() => {
                    setBillType("N");
                    setBill(null);
                  }}
                />
                First Bill
              </label>
              <label>
                <input
                  type="radio"
                  name="fp-bill-type"
                  checked={billType === "M"}
                  disabled={busy}
                  onChange={() => {
                    setBillType("M");
                    setBill(null);
                  }}
                />
                Monthly Bill
              </label>
            </div>
            <label className="fps-sanction-label">
              Bill Month
              <select
                className="form-select form-select-sm"
                value={billMonth}
                disabled={busy}
                onChange={(e) => setBillMonth(e.target.value)}
              >
                {MONTH_OPTIONS.map(([value, label]) => (
                  <option key={value} value={value}>
                    {label}
                  </option>
                ))}
              </select>
            </label>
            <label className="fps-sanction-label">
              Bill Year
              <select
                className="form-select form-select-sm"
                value={billYear}
                disabled={busy}
                onChange={(e) => setBillYear(e.target.value)}
              >
                {billYearChoices(billYear).map((y) => (
                  <option key={y} value={y}>
                    {y}
                  </option>
                ))}
              </select>
            </label>
          </div>
        </div>

        <div className="fps-sanction-toolbar-row">
          <div className="fps-sanction-toolbar-left">
            <label className="fps-sanction-label">
              Emp Code
              <input
                ref={empRef}
                type="text"
                className="form-control form-control-sm"
                value={empCd}
                maxLength={6}
                placeholder="Enter"
                disabled={busy}
                onChange={(e) => setEmpCd(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter") {
                    e.preventDefault();
                    searchByEmp();
                  }
                }}
              />
            </label>
            <button
              type="button"
              className="btn btn-sm btn-primary"
              disabled={busy}
              onClick={searchByEmp}
            >
              {loading ? "Searching…" : "Search"}
            </button>

            <label className="fps-sanction-label">
              Claim ID
              <input
                type="text"
                className="form-control form-control-sm"
                value={clmcaId}
                placeholder="Optional"
                disabled={busy}
                onChange={(e) => setClmcaId(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter") {
                    e.preventDefault();
                    loadClaim({
                      clmca_id: e.currentTarget.value,
                      emp_cd: "",
                    });
                  }
                }}
              />
            </label>
            <button
              type="button"
              className="btn btn-sm btn-outline-primary"
              disabled={busy}
              onClick={() => loadClaim()}
            >
              Load
            </button>
          </div>

          <div className="fps-sanction-toolbar-right">
            <button
              type="button"
              className="btn btn-sm btn-info text-white"
              disabled={busy || !clmcaId}
              onClick={handleGenerateBill}
              title={
                billType === "M"
                  ? "Generate monthly PFN. First disbursement includes unpaid months from WEF."
                  : "Generate first disbursement PFN: pension + DA from WEF through this month."
              }
            >
              {generating ? "Billing…" : `Generate ${kind} Bill`}
            </button>
            <button
              type="button"
              className="btn btn-sm btn-outline-secondary"
              disabled={busy || (!clmcaId && !empCd)}
              onClick={() => loadBill()}
            >
              {billLoading ? "Loading…" : "Refresh Bill"}
            </button>
            <button
              type="button"
              className="btn btn-sm btn-success"
              disabled={busy || !bill?.print}
              onClick={handlePrint}
            >
              Print
            </button>
          </div>
        </div>

        {dispName || clmcaId ? (
          <div className="fps-sanction-emp-meta">
            {dispName ? (
              <span>
                <strong>Name:</strong> {dispName}
              </span>
            ) : null}
            {clmcaId ? (
              <span>
                <strong>Claim:</strong> {clmcaId}
              </span>
            ) : null}
            {bill?.bill_no ? (
              <span>
                <strong>Bill:</strong> {bill.bill_no}
              </span>
            ) : null}
            <span>
              <strong>Type:</strong> {kind}
            </span>
          </div>
        ) : null}

        {message ? <div className="fps-sanction-msg ok">{message}</div> : null}
        {error ? <div className="fps-sanction-msg err">{error}</div> : null}

        {matches.length > 0 ? (
          <div className="fps-sanction-match-list">
            {matches.map((m) => (
              <button
                key={m.clmca_id}
                type="button"
                className="btn btn-sm btn-outline-primary"
                disabled={busy}
                onClick={() =>
                  loadClaim({ clmca_id: m.clmca_id, emp_cd: m.emp_cd || "" })
                }
              >
                {m.clmca_id}
                {m.ca_no ? ` · CA ${m.ca_no}` : ""}
              </button>
            ))}
          </div>
        ) : null}
      </div>

      <div className="fps-sanction-preview-wrap">
        {!bill?.print && !billLoading ? (
          <div className="fps-sanction-preview-empty">
            Search by Emp Code to load the claim, then generate the {kind}{" "}
            Family Pension Bill (PFN) and print.
          </div>
        ) : null}
        {billLoading ? (
          <div className="fps-sanction-preview-loading">Loading bill…</div>
        ) : null}
        <div
          id="family-pension-bill-print-root"
          className="fps-sanction-preview fps-bill-preview"
          aria-hidden={!bill?.print}
        >
          <FamilyPensionBillPrint bill={bill} />
        </div>
      </div>
    </div>
  );
}
