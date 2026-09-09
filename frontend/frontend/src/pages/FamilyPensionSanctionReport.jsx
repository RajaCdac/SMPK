import { useCallback, useEffect, useRef, useState } from "react";
import API from "../services/Api";
import FamilyPensionProposalPrint from "../components/FamilyPensionProposalPrint";
import { printPensionReport } from "../utils/pensionReportPrint";
import "../styles/FamilyPensionProposalReport.css";
import "../styles/pension-report-print.css";
import "../styles/FamilyPensionSanctionReport.css";
import "../styles/FamilyPensionDihApplicationReport.css";

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

export default function FamilyPensionSanctionReport({
  apiPath = "family-pension/proposal-sanction-report/",
  pageTitle = "SANCTION OF FAMILY PENSION (NORMAL)",
  PrintComponent = FamilyPensionProposalPrint,
  printSelector = "#family-pension-sanction-print-root .fp-proposal-print",
}) {
  const [empCd, setEmpCd] = useState("");
  const [clmcaId, setClmcaId] = useState("");
  const [dispName, setDispName] = useState("");
  const [matches, setMatches] = useState([]);
  const [report, setReport] = useState(null);
  const [loading, setLoading] = useState(false);
  const [reportLoading, setReportLoading] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const empRef = useRef(null);

  const loadReport = useCallback(async (opts = {}) => {
    const cid = String(opts.clmca_id ?? clmcaId ?? "").trim();
    const emp = String(opts.emp_cd ?? empCd ?? "").trim();
    if (!cid && !emp) {
      setError("Enter Emp Code or Claim ID to load the report");
      return null;
    }

    setReportLoading(true);
    setError("");
    try {
      const params = {};
      if (cid) params.clmca_id = cid;
      else params.emp_cd = emp;
      const { data } = await API.get(apiPath, { params });
      if (data?.error) {
        setReport(null);
        setError(data.error);
        return null;
      }
      setReport(data);
      setMessage(
        `Report loaded${emp ? ` for ${emp}` : ""}${cid ? ` (${cid})` : ""}.`
      );
      return data;
    } catch (err) {
      setReport(null);
      setError(apiErrorMessage(err, "Could not load sanction report"));
      return null;
    } finally {
      setReportLoading(false);
    }
  }, [clmcaId, empCd, apiPath]);

  const applyClaim = useCallback(
    (claim) => {
      setClmcaId(claim.clmca_id || "");
      setEmpCd(claim.emp_cd || "");
      setDispName(claim.disp_name || "");
      setMatches([]);
      loadReport({
        clmca_id: claim.clmca_id,
        emp_cd: claim.emp_cd,
      });
    },
    [loadReport]
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
    setReport(null);
    try {
      const params = {};
      if (cid) params.clmca_id = cid;
      else params.emp_cd = emp;

      const { data } = await API.get("family-pension/claim/", { params });
      if (data?.claim) {
        applyClaim(data.claim);
        setMessage(`Loaded claim ${data.claim.clmca_id}`);
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

  const handlePrint = () => {
    if (!report?.pages?.length) {
      setError("Load a report before printing");
      return;
    }
    printPensionReport(null, {
      selector: printSelector,
      orientation: "landscape",
    });
  };

  useEffect(() => {
    empRef.current?.focus();
  }, []);

  const busy = loading || reportLoading;

  return (
    <div className="fps-sanction-page container-fluid mt-2 px-2 px-md-3">
      <div className="fps-sanction-title">{pageTitle}</div>

      <div className="fps-sanction-toolbar smpk-form">
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
                    loadClaim({ clmca_id: e.currentTarget.value, emp_cd: "" });
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
              className="btn btn-sm btn-outline-secondary"
              disabled={busy || (!clmcaId && !empCd)}
              onClick={() => loadReport()}
            >
              {reportLoading ? "Loading…" : "Refresh Report"}
            </button>
            <button
              type="button"
              className="btn btn-sm btn-success"
              disabled={busy || !report?.pages?.length}
              onClick={handlePrint}
            >
              Print
            </button>
          </div>
        </div>

        {dispName ? (
          <div className="fps-sanction-emp-meta">
            <span>
              <strong>Name:</strong> {dispName}
            </span>
            {clmcaId ? (
              <span>
                <strong>Claim:</strong> {clmcaId}
              </span>
            ) : null}
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
        {!report?.pages?.length && !reportLoading ? (
          <div className="fps-sanction-preview-empty">
            Search by Emp Code to preview the First Family Pension sanction
            report. Landscape print is available once the report is loaded.
          </div>
        ) : null}
        {reportLoading ? (
          <div className="fps-sanction-preview-loading">Loading report…</div>
        ) : null}
        <div
          id="family-pension-sanction-print-root"
          className="fps-sanction-preview"
          aria-hidden={!report?.pages?.length}
        >
          <PrintComponent report={report} />
        </div>
      </div>
    </div>
  );
}
