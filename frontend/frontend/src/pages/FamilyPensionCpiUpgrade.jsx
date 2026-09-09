import { useCallback, useEffect, useRef, useState } from "react";
import { useSearchParams } from "react-router-dom";
import API from "../services/Api";
import "../styles/FirstPensionCase.css";

function apiErrorMessage(err, fallback) {
  const data = err?.response?.data;
  if (typeof data?.error === "string" && data.error.trim()) return data.error;
  if (typeof data?.detail === "string" && data.detail.trim()) return data.detail;
  return fallback;
}

function fmtAmt(n) {
  if (n == null || n === "") return "—";
  const v = Number(n);
  if (Number.isNaN(v)) return String(n);
  return v.toLocaleString("en-IN");
}

/**
 * Report → CPI-Upgrade
 * Generate / refresh fi_pn_cpi_consolidation for an employee (older claims)
 * before arrear calculation.
 */
export default function FamilyPensionCpiUpgrade() {
  const [searchParams, setSearchParams] = useSearchParams();
  const [employeeId, setEmployeeId] = useState("");
  const [result, setResult] = useState(null);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [generating, setGenerating] = useState(false);
  const urlEmpLoadedRef = useRef(false);

  const loadStatus = useCallback(async (code) => {
    const emp = String(code || "").trim();
    if (!emp) {
      setError("Enter Employee ID");
      return;
    }
    setLoading(true);
    setError("");
    setMessage("");
    try {
      const { data } = await API.get("family-pension/cpi-upgrade/", {
        params: { emp_cd: emp },
      });
      setResult(data);
      if (data?.found) {
        setMessage(
          `Loaded ${data.rows?.length || 0} CPI basic row(s) for ${emp}.`
        );
      } else {
        setMessage(
          data?.message ||
            "No CPI basics yet — click Generate CPI Basics."
        );
      }
    } catch (err) {
      setResult(null);
      setError(apiErrorMessage(err, "Could not load CPI consolidation"));
    } finally {
      setLoading(false);
    }
  }, []);

  const generateBasics = useCallback(async () => {
    const emp = String(employeeId || "").trim();
    if (!emp) {
      setError("Enter Employee ID");
      return;
    }
    setGenerating(true);
    setError("");
    setMessage("");
    try {
      const { data } = await API.post("family-pension/cpi-upgrade/", {
        emp_cd: emp,
      });
      setResult(data);
      setMessage(
        data?.message ||
          `Generated ${data?.rows?.length || 0} CPI basic row(s).`
      );
      setSearchParams({ emp_cd: emp }, { replace: true });
    } catch (err) {
      setError(apiErrorMessage(err, "Could not generate CPI basics"));
    } finally {
      setGenerating(false);
    }
  }, [employeeId, setSearchParams]);

  useEffect(() => {
    const q = searchParams.get("emp_cd") || searchParams.get("emp_id") || "";
    if (q && !urlEmpLoadedRef.current) {
      urlEmpLoadedRef.current = true;
      setEmployeeId(q);
      loadStatus(q);
    }
  }, [searchParams, loadStatus]);

  const busy = loading || generating;
  const rows = result?.rows || [];

  return (
    <div className="fpc-page">
      <div className="container-fluid py-3">
        <div className="card shadow-sm border-0 mb-3">
          <div className="card-body">
            <div className="d-flex flex-wrap align-items-center justify-content-between gap-2 mb-2">
              <h4 className="mb-0">CPI-Upgrade</h4>
              <span className="text-muted small">
                Generate CPI-wise basics into{" "}
                <code>fi_pn_cpi_consolidation</code> for arrear
              </span>
            </div>
            <p className="text-muted small mb-3">
              Use this for older employees before Arrear. Class 3/4 stores
              607 / 1708 / 126 / 198 / 277 / 359; class 1/2 stores 1708 / 126 /
              277 (no 359).
            </p>

            <div className="row g-2 align-items-end">
              <div className="col-md-3">
                <label className="form-label mb-1">Employee ID</label>
                <input
                  className="form-control"
                  value={employeeId}
                  maxLength={5}
                  disabled={busy}
                  onChange={(e) => setEmployeeId(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter") loadStatus(employeeId);
                  }}
                  placeholder="e.g. 07530"
                />
              </div>
              <div className="col-md-auto d-flex gap-2">
                <button
                  type="button"
                  className="btn btn-outline-secondary"
                  disabled={busy || !String(employeeId).trim()}
                  onClick={() => loadStatus(employeeId)}
                >
                  {loading ? "Loading…" : "Load"}
                </button>
                <button
                  type="button"
                  className="btn btn-primary"
                  disabled={busy || !String(employeeId).trim()}
                  onClick={generateBasics}
                >
                  {generating ? "Generating…" : "Generate CPI Basics"}
                </button>
              </div>
            </div>

            {error ? (
              <div className="alert alert-danger mt-3 mb-0 py-2">{error}</div>
            ) : null}
            {message && !error ? (
              <div className="alert alert-success mt-3 mb-0 py-2">{message}</div>
            ) : null}
          </div>
        </div>

        {result ? (
          <div className="card shadow-sm border-0">
            <div className="card-body">
              <div className="row g-2 mb-3 small">
                <div className="col-md-3">
                  <div className="text-muted">Employee</div>
                  <strong>
                    {result.emp_cd}
                    {result.emp_name ? ` — ${result.emp_name}` : ""}
                  </strong>
                </div>
                <div className="col-md-3">
                  <div className="text-muted">Claim / Case</div>
                  <strong>
                    {result.claim_id || "—"}
                    {result.case_no != null ? ` / ${result.case_no}` : ""}
                  </strong>
                </div>
                <div className="col-md-2">
                  <div className="text-muted">Class</div>
                  <strong>{result.emp_class ?? "—"}</strong>
                </div>
                <div className="col-md-2">
                  <div className="text-muted">Last Pay</div>
                  <strong>{fmtAmt(result.last_pay)}</strong>
                </div>
                <div className="col-md-2">
                  <div className="text-muted">Separation</div>
                  <strong>{result.separation_dt || "—"}</strong>
                </div>
              </div>

              {rows.length ? (
                <div className="table-responsive">
                  <table className="table table-sm table-bordered mb-0">
                    <thead className="table-light">
                      <tr>
                        <th>CPI</th>
                        <th className="text-end">Basic</th>
                        <th>Emp Class</th>
                        <th>Claim ID</th>
                        <th>Created</th>
                      </tr>
                    </thead>
                    <tbody>
                      {rows.map((r) => (
                        <tr key={`${r.claim_id}-${r.cpi}`}>
                          <td>{r.cpi}</td>
                          <td className="text-end">{fmtAmt(r.basic)}</td>
                          <td>{r.emp_class ?? "—"}</td>
                          <td>{r.claim_id}</td>
                          <td>{r.date_created || "—"}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : (
                <div className="text-muted">No CPI basic rows stored yet.</div>
              )}
            </div>
          </div>
        ) : null}
      </div>
    </div>
  );
}
