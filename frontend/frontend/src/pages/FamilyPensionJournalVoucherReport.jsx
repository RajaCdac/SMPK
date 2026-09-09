import { useRef, useState } from "react";
import API from "../services/Api";
import PensionJournalSummaryPrint from "../components/PensionJournalSummaryPrint";
import { printPensionReport } from "../utils/pensionReportPrint";
import "../styles/PensionJournalSummary.css";
import "../styles/pension-report-print.css";
import "../styles/FamilyPensionSanctionReport.css";

function apiErrorMessage(err, fallback = "Request failed") {
  if (err?.message === "Network Error" || err?.code === "ERR_NETWORK") {
    return (
      "Cannot reach the API server. Start Django on port 8000 and restart the " +
      "frontend dev server (Vite proxy /api → localhost:8000)."
    );
  }
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

function formatMoney(value) {
  if (value === null || value === undefined || value === "") return "—";
  const n = Number(value);
  if (Number.isNaN(n)) return "—";
  return n.toLocaleString("en-IN", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
}

/**
 * Report: PFN Journal Voucher + Summary of Journal (Oracle FI_PN_T_H_JRVOUCHR_E / FI_PN_TD_JV_RPT).
 */
export default function FamilyPensionJournalVoucherReport() {
  const [empCd, setEmpCd] = useState("");
  const [clmcaId, setClmcaId] = useState("");
  const [billNo, setBillNo] = useState("");
  const [jvMonth, setJvMonth] = useState("");
  const [jvYear, setJvYear] = useState("");
  const [abstractNo, setAbstractNo] = useState("");
  const [abstractDate, setAbstractDate] = useState("");
  const [narration, setNarration] = useState("");
  const [status, setStatus] = useState(null);
  const [preview, setPreview] = useState(null);
  const [summary, setSummary] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const empRef = useRef(null);

  const resolvedBill =
    status?.resolved_bill_no || status?.bill_no || billNo.trim();

  const applyStatus = (data) => {
    setStatus(data);
    const bno = data?.resolved_bill_no || data?.bill_no || "";
    if (bno) setBillNo(bno);
    if (data?.bill_month) setJvMonth(String(data.bill_month));
    if (data?.bill_yr) setJvYear(String(data.bill_yr));
    if (data?.bill_abstract_no) setAbstractNo(data.bill_abstract_no);
    if (data?.abstract_date) {
      setAbstractDate(String(data.abstract_date).slice(0, 10));
    }
    if (data?.jv?.narration) {
      setNarration(data.jv.narration);
    } else if (data?.default_narration) {
      setNarration(data.default_narration);
    }
  };

  const lookupParams = (opts = {}) => {
    const params = {};
    const bno = String(opts.bill_no ?? billNo ?? "").trim();
    const cid = String(opts.clmca_id ?? clmcaId ?? "").trim();
    const emp = String(opts.emp_cd ?? empCd ?? "").trim();
    if (bno) params.bill_no = bno;
    if (cid) params.clmca_id = cid;
    if (emp) params.emp_cd = emp;
    return params;
  };

  const loadStatus = async (opts = {}) => {
    const params = lookupParams(opts);
    if (!params.bill_no && !params.clmca_id && !params.emp_cd) {
      setError("Enter Emp ID, Claim ID, or Bill No");
      empRef.current?.focus();
      return null;
    }

    setLoading(true);
    setError("");
    setMessage("");
    setPreview(null);
    setSummary(null);

    try {
      const { data } = await API.get("family-pension/journal-voucher/status/", {
        params,
      });
      if (data?.error) {
        setError(data.error);
        setStatus(null);
        return null;
      }
      applyStatus(data);
      setMessage(
        `PFN bill loaded` +
          (data.resolved_bill_no ? ` · ${data.resolved_bill_no}` : "") +
          (data.has_voucher ? ` · JV ${data.voucher_no}` : "")
      );
      return data;
    } catch (err) {
      setError(apiErrorMessage(err, "Could not load bill / voucher status"));
      setStatus(null);
      return null;
    } finally {
      setLoading(false);
    }
  };

  const loadPreview = async () => {
    if (!resolvedBill || !jvMonth || !jvYear) {
      setError("Load a PFN bill and set JV month/year first");
      return;
    }
    setLoading(true);
    setError("");
    try {
      const { data } = await API.get("family-pension/journal-voucher/preview/", {
        params: {
          bill_no: resolvedBill,
          jv_month: jvMonth,
          jv_year: jvYear,
        },
      });
      if (data?.error) {
        setError(data.error);
        setPreview(null);
        return;
      }
      setPreview(data);
      setMessage("Journal lines preview loaded");
    } catch (err) {
      setError(apiErrorMessage(err, "Could not preview journal voucher"));
      setPreview(null);
    } finally {
      setLoading(false);
    }
  };

  const loadSummary = async (opts = {}) => {
    const ref = opts.ref_no || resolvedBill;
    const yr = opts.yr ?? jvYear;
    const mth = opts.mth ?? jvMonth;
    if (!ref || !yr || !mth) {
      setError("JV month, year, and bill number are required for journal summary");
      return null;
    }
    setLoading(true);
    setError("");
    try {
      const { data } = await API.get("family-pension/journal-summary-report/", {
        params: { yr, mth, ref_no: ref },
      });
      if (data?.error) {
        setError(data.error);
        setSummary(null);
        return null;
      }
      setSummary(data);
      setMessage(
        `Journal summary loaded` +
          (data.header?.voucher_no ? ` · ${data.header.voucher_no}` : "")
      );
      return data;
    } catch (err) {
      setError(apiErrorMessage(err, "Could not load journal summary"));
      setSummary(null);
      return null;
    } finally {
      setLoading(false);
    }
  };

  const handleGenerate = async (regenerate = false) => {
    if (!resolvedBill) {
      setError("Load a PFN bill first");
      return;
    }
    if (!jvMonth || !jvYear) {
      setError("JV month and year are required");
      return;
    }
    if (
      regenerate &&
      !window.confirm(
        `Regenerate journal voucher ${status?.voucher_no || ""}?`
      )
    ) {
      return;
    }

    setLoading(true);
    setError("");
    setMessage("");
    try {
      const { data } = await API.post(
        "family-pension/journal-voucher/generate/",
        {
          bill_no: resolvedBill,
          jv_month: Number(jvMonth),
          jv_year: Number(jvYear),
          abstract_no: abstractNo,
          abstract_date: abstractDate || null,
          narration,
          regenerate,
          voucher_no: regenerate ? status?.voucher_no || "" : "",
        }
      );
      if (data?.error) {
        setError(data.error);
        return;
      }
      setMessage(data.message || `Voucher ${data.voucher_no} saved`);
      const refreshed = await loadStatus({ bill_no: resolvedBill });
      if (refreshed) {
        await loadPreview();
        await loadSummary({
          ref_no: resolvedBill,
          yr: jvYear,
          mth: jvMonth,
        });
      }
    } catch (err) {
      setError(apiErrorMessage(err, "Journal voucher generation failed"));
    } finally {
      setLoading(false);
    }
  };

  const onSubmit = async (e) => {
    e.preventDefault();
    const emp = empRef.current?.value ?? empCd;
    if (emp) setEmpCd(emp);
    await loadStatus({
      emp_cd: emp,
      clmca_id: clmcaId,
      bill_no: billNo,
    });
  };

  const onPrint = (e) => {
    if (!summary?.rows?.length) {
      setError("Generate the journal voucher and load summary before printing");
      return;
    }
    printPensionReport(e, {
      selector: "#fp-journal-summary-print-root .journal-summary-print",
    });
  };

  return (
    <div className="container-fluid mt-3 mt-md-4 px-2 px-md-3 family-pension-sanction-report">
      <div className="row justify-content-center">
        <div className="col-12 col-xl-11">
          <div className="card shadow">
            <div className="card-header bg-primary text-white d-flex flex-wrap justify-content-between align-items-center gap-2">
              <h4 className="mb-0">Journal Voucher</h4>
              <button
                type="button"
                className="btn btn-light btn-sm"
                onClick={onPrint}
                disabled={!summary?.rows?.length || loading}
              >
                Print Summary
              </button>
            </div>
            <div className="card-body">
              <form
                className="row g-2 align-items-end mb-3"
                onSubmit={onSubmit}
              >
                <div className="col-12 col-sm-4 col-md-3">
                  <label className="form-label mb-1" htmlFor="fp-jv-emp">
                    Emp ID
                  </label>
                  <input
                    id="fp-jv-emp"
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
                  <label className="form-label mb-1" htmlFor="fp-jv-claim">
                    Claim ID
                  </label>
                  <input
                    id="fp-jv-claim"
                    className="form-control"
                    value={clmcaId}
                    onChange={(e) => setClmcaId(e.target.value)}
                    placeholder="Optional"
                    autoComplete="off"
                  />
                </div>
                <div className="col-12 col-sm-4 col-md-3">
                  <label className="form-label mb-1" htmlFor="fp-jv-bill">
                    Bill No
                  </label>
                  <input
                    id="fp-jv-bill"
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
                    {loading ? "Loading…" : "Load Bill"}
                  </button>
                </div>
              </form>

              {status ? (
                <>
                  <div className="row g-2 mb-3">
                    <div className="col-md-3">
                      <label className="form-label mb-1">PFN Bill No</label>
                      <input className="form-control" value={resolvedBill} readOnly />
                    </div>
                    <div className="col-md-2">
                      <label className="form-label mb-1">JV Month</label>
                      <input
                        type="number"
                        className="form-control"
                        min={1}
                        max={12}
                        value={jvMonth}
                        onChange={(e) => setJvMonth(e.target.value)}
                      />
                    </div>
                    <div className="col-md-2">
                      <label className="form-label mb-1">JV Year</label>
                      <input
                        type="number"
                        className="form-control"
                        min={2000}
                        max={2100}
                        value={jvYear}
                        onChange={(e) => setJvYear(e.target.value)}
                      />
                    </div>
                    <div className="col-md-2">
                      <label className="form-label mb-1">Abstract No</label>
                      <input
                        className="form-control"
                        value={abstractNo}
                        onChange={(e) => setAbstractNo(e.target.value)}
                      />
                    </div>
                    <div className="col-md-3">
                      <label className="form-label mb-1">Abstract Date</label>
                      <input
                        type="date"
                        className="form-control"
                        value={abstractDate}
                        onChange={(e) => setAbstractDate(e.target.value)}
                      />
                    </div>
                    <div className="col-12">
                      <label className="form-label mb-1">Narration</label>
                      <textarea
                        className="form-control"
                        rows={2}
                        value={narration}
                        onChange={(e) => setNarration(e.target.value)}
                      />
                    </div>
                  </div>

                  <div className="d-flex flex-wrap gap-2 mb-3">
                    <button
                      type="button"
                      className="btn btn-outline-secondary btn-sm"
                      onClick={loadPreview}
                      disabled={loading}
                    >
                      Preview Lines
                    </button>
                    <button
                      type="button"
                      className="btn btn-primary btn-sm"
                      onClick={() => handleGenerate(false)}
                      disabled={loading || Boolean(status?.has_voucher)}
                    >
                      Generate Voucher
                    </button>
                    {status?.has_voucher ? (
                      <button
                        type="button"
                        className="btn btn-outline-warning btn-sm"
                        onClick={() => handleGenerate(true)}
                        disabled={loading}
                      >
                        Regenerate
                      </button>
                    ) : null}
                    <button
                      type="button"
                      className="btn btn-outline-primary btn-sm"
                      onClick={() => loadSummary()}
                      disabled={loading || !status?.has_voucher}
                    >
                      Load Summary
                    </button>
                    {status?.voucher_no ? (
                      <span className="badge text-bg-success align-self-center">
                        {status.voucher_no}
                      </span>
                    ) : null}
                  </div>

                  {preview?.lines?.length ? (
                    <div className="table-responsive mb-3">
                      <table className="table table-sm table-bordered">
                        <thead className="table-light">
                          <tr>
                            <th>Dr/Cr</th>
                            <th>Zonal</th>
                            <th>Aloc 1</th>
                            <th>Aloc 2</th>
                            <th>Aloc 3</th>
                            <th className="text-end">Amount</th>
                          </tr>
                        </thead>
                        <tbody>
                          {preview.lines.map((line, index) => (
                            <tr
                              key={`${line.dr_cr_flag}-${line.aloc_cd1}-${index}`}
                              className={line.balancing ? "table-info" : ""}
                            >
                              <td>{line.dr_cr_flag}</td>
                              <td>{line.zonal_label || line.zonal_cd}</td>
                              <td>{line.aloc_cd1}</td>
                              <td>{line.aloc_cd2}</td>
                              <td>{line.aloc_cd3}</td>
                              <td className="text-end">
                                {formatMoney(line.amount)}
                              </td>
                            </tr>
                          ))}
                        </tbody>
                        <tfoot>
                          <tr>
                            <th colSpan={5}>Total Dr / Cr</th>
                            <th className="text-end">
                              {formatMoney(preview.total_dr)} /{" "}
                              {formatMoney(preview.total_cr)}
                            </th>
                          </tr>
                        </tfoot>
                      </table>
                    </div>
                  ) : null}
                </>
              ) : (
                <p className="text-muted mb-3">
                  Enter Emp ID (or Claim ID / PFN bill number) after bill
                  generation. Generate the journal voucher here, then print the
                  Summary of Journal.
                </p>
              )}

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

              {summary?.rows?.length ? (
                <div
                  id="fp-journal-summary-print-root"
                  className="journal-summary-preview border rounded bg-white p-2 overflow-auto"
                >
                  <PensionJournalSummaryPrint report={summary} />
                </div>
              ) : null}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
