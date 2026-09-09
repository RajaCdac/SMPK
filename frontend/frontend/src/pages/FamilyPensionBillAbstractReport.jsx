import { useRef, useState } from "react";
import API from "../services/Api";
import PensionBillAbstractReportPrint from "../components/PensionBillAbstractReportPrint";
import { printPensionReport } from "../utils/pensionReportPrint";
import "../styles/PensionBillAbstractReport.css";
import "../styles/pension-report-print.css";
import "../styles/FamilyPensionSanctionReport.css";

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

/**
 * Report: PFN Bill Abstract — Oracle FI_PN_BILL_ABSTRACT (per employee PFN bill).
 */
export default function FamilyPensionBillAbstractReport() {
  const [empCd, setEmpCd] = useState("");
  const [clmcaId, setClmcaId] = useState("");
  const [billNo, setBillNo] = useState("");
  const [report, setReport] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const empRef = useRef(null);

  const loadReport = async (opts = {}) => {
    const emp = String(opts.emp_cd ?? empCd ?? "").trim();
    const cid = String(opts.clmca_id ?? clmcaId ?? "").trim();
    const bno = String(opts.bill_no ?? billNo ?? "").trim();
    if (!emp && !cid && !bno) {
      setError("Enter Emp ID, Claim ID, or Bill No");
      empRef.current?.focus();
      return;
    }

    setLoading(true);
    setError("");
    setMessage("");
    setReport(null);
    if (emp) setEmpCd(emp);
    if (cid) setClmcaId(cid);
    if (bno) setBillNo(bno);

    try {
      const params = {};
      if (bno) params.bill_no = bno;
      if (cid) params.clmca_id = cid;
      if (emp) params.emp_cd = emp;

      const { data } = await API.get("family-pension/bill-abstract-report/", {
        params,
      });
      if (data?.error) {
        setError(data.error);
        return;
      }
      setReport(data);
      const row = data?.rows?.[0];
      setMessage(
        `Bill abstract loaded` +
          (data.bill_no ? ` · ${data.bill_no}` : "") +
          (row?.rendered ? ` · ${row.rendered}` : "") +
          (row?.net_payable_display ? ` · Net ${row.net_payable_display}` : "")
      );
    } catch (err) {
      setError(apiErrorMessage(err, "Could not load bill abstract"));
    } finally {
      setLoading(false);
    }
  };

  const onSubmit = (e) => {
    e.preventDefault();
    loadReport({
      emp_cd: empRef.current?.value ?? empCd,
      clmca_id: clmcaId,
      bill_no: billNo,
    });
  };

  const onPrint = (e) => {
    if (!report?.rows?.length) {
      setError("Load a bill abstract first");
      return;
    }
    printPensionReport(e, {
      selector: "#fp-bill-abstract-print-root .bill-abstract-print",
    });
  };

  return (
    <div className="container-fluid mt-3 mt-md-4 px-2 px-md-3 family-pension-sanction-report">
      <div className="row justify-content-center">
        <div className="col-12 col-xl-11">
          <div className="card shadow">
            <div className="card-header bg-primary text-white d-flex flex-wrap justify-content-between align-items-center gap-2">
              <h4 className="mb-0">Bill Abstract</h4>
              <button
                type="button"
                className="btn btn-light btn-sm"
                onClick={onPrint}
                disabled={!report?.rows?.length || loading}
              >
                Print
              </button>
            </div>
            <div className="card-body">
              <form
                className="row g-2 align-items-end mb-3"
                onSubmit={onSubmit}
              >
                <div className="col-12 col-sm-4 col-md-3">
                  <label className="form-label mb-1" htmlFor="fp-abs-emp">
                    Emp ID
                  </label>
                  <input
                    id="fp-abs-emp"
                    ref={empRef}
                    className="form-control"
                    value={empCd}
                    onChange={(e) => setEmpCd(e.target.value)}
                    placeholder="e.g. 44962"
                    autoComplete="off"
                    autoFocus
                  />
                </div>
                <div className="col-12 col-sm-4 col-md-3">
                  <label className="form-label mb-1" htmlFor="fp-abs-claim">
                    Claim ID
                  </label>
                  <input
                    id="fp-abs-claim"
                    className="form-control"
                    value={clmcaId}
                    onChange={(e) => setClmcaId(e.target.value)}
                    placeholder="Optional"
                    autoComplete="off"
                  />
                </div>
                <div className="col-12 col-sm-4 col-md-3">
                  <label className="form-label mb-1" htmlFor="fp-abs-bill">
                    Bill No
                  </label>
                  <input
                    id="fp-abs-bill"
                    className="form-control"
                    value={billNo}
                    onChange={(e) => setBillNo(e.target.value)}
                    placeholder="PFN… (optional)"
                    autoComplete="off"
                  />
                </div>
                <div className="col-auto">
                  <button
                    type="submit"
                    className="btn btn-primary"
                    disabled={loading}
                  >
                    {loading ? "Loading…" : "Show Abstract"}
                  </button>
                </div>
              </form>

              {error ? (
                <div className="alert alert-danger py-2" role="alert">
                  {error}
                </div>
              ) : null}
              {message && !error ? (
                <div className="alert alert-success py-2" role="status">
                  {message}
                </div>
              ) : null}

              {report?.rows?.length ? (
                <div
                  id="fp-bill-abstract-print-root"
                  className="bill-abstract-preview border rounded bg-white p-2 overflow-auto"
                >
                  <PensionBillAbstractReportPrint report={report} />
                </div>
              ) : (
                <p className="text-muted mb-0">
                  Enter Emp ID (or Claim ID / PFN bill number) to load the bill
                  abstract. The PFN bill must already be generated under Bill
                  Generation.
                </p>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
