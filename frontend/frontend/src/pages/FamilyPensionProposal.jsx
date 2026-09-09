import { useCallback, useEffect, useRef, useState } from "react";
import { useSearchParams } from "react-router-dom";
import PensionProposalEntry from "../components/PensionProposalEntry";
import { loadFirstPensionEmployeeByCode } from "../utils/loadFirstPensionEmployee";
import "../styles/FirstPensionCase.css";

/**
 * Family Pension → Proposal
 * Same pension proposal form as First Pension (PensionProposalEntry).
 */
export default function FamilyPensionProposal() {
  const [searchParams, setSearchParams] = useSearchParams();

  const [employeeId, setEmployeeId] = useState("");
  const [employee, setEmployee] = useState(null);
  const [message, setMessage] = useState("");
  const [loading, setLoading] = useState(false);
  const urlEmpLoadedRef = useRef(false);

  const loadEmployee = useCallback(async (rawCode) => {
    const code = String(rawCode || "").trim();
    if (!code) {
      setMessage("Please enter Employee ID");
      return;
    }

    setLoading(true);
    setMessage("");

    try {
      const { detail, loadWarning } = await loadFirstPensionEmployeeByCode(code);
      setEmployee(detail);
      setEmployeeId(code);
      setMessage(
        loadWarning ||
          (detail?.cache_message ? detail.cache_message : "") ||
          (detail?.partial
            ? "Limited employee data available (Oracle unavailable)."
            : "")
      );
    } catch (error) {
      setEmployee(null);
      setMessage(
        error.response?.data?.error ||
          error.response?.data?.message ||
          error.message ||
          "Employee not found"
      );
      console.error(error);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (urlEmpLoadedRef.current) return;
    const fromUrl = searchParams.get("emp");
    if (!fromUrl) return;
    urlEmpLoadedRef.current = true;
    loadEmployee(fromUrl);
    setSearchParams({}, { replace: true });
  }, [loadEmployee, searchParams, setSearchParams]);

  const handleSearch = (e) => {
    e.preventDefault();
    loadEmployee(employeeId);
  };

  const handleSearchAnother = () => {
    setEmployee(null);
    setMessage("");
    setEmployeeId("");
  };

  return (
    <div className="first-pension-page container-fluid mt-3 mt-md-4 px-2 px-md-3 first-pension-page--tabs">
      <div className="row justify-content-center">
        <div className="col-12 col-xl-11">
          {!employee && (
            <div className="card shadow first-pension-search-card">
              <div className="card-header bg-primary text-white">
                <h4 className="mb-0">Family Pension — Proposal</h4>
              </div>
              <div className="card-body smpk-form">
                <form onSubmit={handleSearch}>
                  <div className="row g-3 align-items-end">
                    <div className="col-12 col-lg-8">
                      <label className="form-label">Employee ID</label>
                      <input
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

                {message && (
                  <div className="alert alert-danger mt-3 mb-0" role="status">
                    {message}
                  </div>
                )}
              </div>
            </div>
          )}

          {employee && (
            <div className="card shadow first-pension-workflow-card">
              <div className="card-header bg-primary text-white py-2">
                <h4 className="mb-0 h5">
                  Pension Proposal — {employee.name || employee.emp_id}
                </h4>
              </div>

              <div className="card-body">
                {message && (
                  <div className="alert alert-warning py-2" role="status">
                    {message}
                  </div>
                )}
                <div className="first-pension-employee-bar">
                  <strong>
                    {employee.emp_id} — {employee.name}
                  </strong>
                  <button
                    type="button"
                    className="btn btn-outline-secondary btn-sm"
                    onClick={handleSearchAnother}
                  >
                    Search another employee
                  </button>
                </div>

                <div className="first-pension-workflow">
                  <PensionProposalEntry employee={employee} />
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
