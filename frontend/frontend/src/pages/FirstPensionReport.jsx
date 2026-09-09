import { useCallback, useEffect, useRef, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { REPORT_SECTIONS } from "../components/PensionReports";
import { loadFirstPensionEmployeeByCode } from "../utils/loadFirstPensionEmployee";
import "../styles/FirstPensionCase.css";
import "../styles/PensionReports.css";

const LAST_EMP_KEY = "fp-report-emp";

export default function FirstPensionReport({ section = "sanction" }) {
  const meta =
    REPORT_SECTIONS.find((item) => item.key === section) ||
    REPORT_SECTIONS.find((item) => item.key === "sanction");
  const SectionComponent = meta.Component;

  const [searchParams, setSearchParams] = useSearchParams();
  const [employeeId, setEmployeeId] = useState("");
  const [employee, setEmployee] = useState(null);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const urlEmpLoadedRef = useRef(false);
  const empRef = useRef(null);

  const loadEmployee = useCallback(async (rawCode) => {
    const code = String(rawCode || "").trim();
    if (!code) {
      setError("Enter Employee ID");
      return;
    }

    setLoading(true);
    setError("");
    setMessage("");
    setEmployee(null);

    try {
      const { detail, loadWarning } = await loadFirstPensionEmployeeByCode(code);
      setEmployee(detail);
      setEmployeeId(detail?.emp_id || code);
      sessionStorage.setItem(LAST_EMP_KEY, detail?.emp_id || code);
      setMessage(
        loadWarning ||
          `Report loaded for ${detail?.emp_id || code}${
            detail?.name ? ` — ${detail.name}` : ""
          }.`
      );
    } catch (err) {
      setEmployee(null);
      setError(
        err.response?.data?.error ||
          err.response?.data?.message ||
          err.message ||
          "Employee not found"
      );
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    empRef.current?.focus();
  }, [section]);

  useEffect(() => {
    if (urlEmpLoadedRef.current) return;
    const fromUrl = searchParams.get("emp");
    let saved = "";
    try {
      saved = sessionStorage.getItem(LAST_EMP_KEY) || "";
    } catch {
      saved = "";
    }
    const code = fromUrl || saved;
    if (!code) return;
    urlEmpLoadedRef.current = true;
    setEmployeeId(code);
    loadEmployee(code);
    if (fromUrl) {
      setSearchParams({}, { replace: true });
    }
  }, [loadEmployee, searchParams, setSearchParams]);

  const handleSearch = (e) => {
    e.preventDefault();
    loadEmployee(employeeId);
  };

  return (
    <div className="first-pension-page fp-report-page container-fluid mt-3 mt-md-4 px-2 px-md-3">
      <div className="row justify-content-center">
        <div className="col-12 col-xl-11">
          <div className="card shadow first-pension-search-card">
            <div className="card-header bg-primary text-white">
              <h4 className="mb-0">{meta.title}</h4>
            </div>
            <div className="card-body smpk-form">
              <p className="text-muted small mb-3">
                Search by Employee ID to load this report in the print format.
              </p>
              <form onSubmit={handleSearch}>
                <div className="row g-3 align-items-end">
                  <div className="col-12 col-lg-8">
                    <label className="form-label">Employee ID</label>
                    <input
                      ref={empRef}
                      type="text"
                      className="form-control"
                      placeholder="Enter Employee ID and press Search or Enter"
                      value={employeeId}
                      onChange={(e) => setEmployeeId(e.target.value)}
                      disabled={loading}
                      autoComplete="off"
                    />
                  </div>
                  <div className="col-12 col-lg-4">
                    <button
                      type="submit"
                      className="btn btn-primary w-100"
                      disabled={loading || !employeeId.trim()}
                    >
                      {loading ? "Loading…" : "Search"}
                    </button>
                  </div>
                </div>
              </form>

              {error ? (
                <div className="alert alert-danger mt-3 mb-0" role="status">
                  {error}
                </div>
              ) : null}
              {message && !error ? (
                <div className="alert alert-success mt-3 mb-0" role="status">
                  {message}
                </div>
              ) : null}
            </div>
          </div>

          {employee ? (
            <div className="card shadow first-pension-workflow-card">
              <div className="card-header bg-primary text-white py-2">
                <h4 className="mb-0 h5">
                  {meta.title} — {employee.emp_id}
                  {employee.name ? ` (${employee.name})` : ""}
                </h4>
              </div>
              <div className="card-body">
                <SectionComponent
                  employee={employee}
                  idPrefix={`fp-menu-${meta.key}`}
                />
              </div>
            </div>
          ) : (
            <p className="text-muted mt-2 mb-0">
              Enter an Employee ID to preview and print this report.
            </p>
          )}
        </div>
      </div>
    </div>
  );
}
