import { useCallback, useEffect, useRef, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import NoPayEntry from "../components/NoPayEntry";
import PensionProposalEntry from "../components/PensionProposalEntry";
import { loadFirstPensionEmployeeByCode } from "../utils/loadFirstPensionEmployee";
import "../styles/FirstPensionCase.css";
import "../styles/FamilyPensionDashboard.css";

const STEP_META = {
  nopay: {
    title: "Die-in-Harness — No-pay Entry",
    cardTitle: "No-Pay Entry",
    hint: "Search employee, then enter / edit no-pay days (same form as first pension).",
  },
  proposal: {
    title: "Die-in-Harness — Pension Proposal",
    cardTitle: "Pension Proposal",
    hint: "Search employee, then open pension proposal (same form as first pension).",
  },
};

/**
 * Die-in-Harness stepped screens: no-pay then pension proposal.
 * @param {{ step?: "nopay" | "proposal" }} props
 */
export default function DieInHarness({ step = "nopay" }) {
  const meta = STEP_META[step] || STEP_META.nopay;
  const [searchParams, setSearchParams] = useSearchParams();
  const [employeeId, setEmployeeId] = useState("");
  const [employee, setEmployee] = useState(null);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const urlEmpLoadedRef = useRef(false);

  const loadEmployee = useCallback(async (rawCode) => {
    const code = String(rawCode || "").trim();
    if (!code) {
      setError("Please enter Employee ID");
      return;
    }

    setLoading(true);
    setError("");
    setMessage("");

    try {
      const { detail } = await loadFirstPensionEmployeeByCode(code);
      setEmployee(detail);
      setEmployeeId(detail?.emp_id || code);
      setMessage("");
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

  // Deep-link from No-pay → Proposal: /die-in-harness/proposal?emp=44377
  useEffect(() => {
    urlEmpLoadedRef.current = false;
  }, [step]);

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
    setError("");
    setEmployeeId("");
  };

  return (
    <div className="first-pension-page container-fluid mt-3 mt-md-4 px-2 px-md-3">
      <div className="row justify-content-center">
        <div className="col-12 col-xl-11">
          <header className="mb-3">
            <h1 className="h4 mb-1">{meta.title}</h1>
            <p className="text-muted mb-0 small">{meta.hint}</p>
          </header>

          {!employee && (
            <div className="card shadow first-pension-search-card">
              <div className="card-header bg-primary text-white">
                <h4 className="mb-0 h5">Employee Search</h4>
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
                        maxLength={10}
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
                  <div className="alert alert-danger mt-3 mb-0" role="alert">
                    {error}
                  </div>
                ) : null}
              </div>
            </div>
          )}

          {employee ? (
            <div className="card shadow first-pension-workflow-card">
              <div className="card-header bg-primary text-white py-2">
                <h4 className="mb-0 h5">
                  {meta.cardTitle} — {employee.name || employee.emp_id}
                </h4>
              </div>
              <div className="card-body">
                {message ? (
                  <div className="alert alert-warning py-2" role="status">
                    {message}
                  </div>
                ) : null}
                {error ? (
                  <div className="alert alert-danger py-2" role="alert">
                    {error}
                  </div>
                ) : null}

                <div className="first-pension-employee-bar">
                  <strong>
                    {employee.emp_id} — {employee.name || "—"}
                  </strong>
                  <button
                    type="button"
                    className="btn btn-outline-secondary btn-sm"
                    onClick={handleSearchAnother}
                  >
                    Search another employee
                  </button>
                </div>

                <section className="mt-3">
                  <h5 className="employee-process-tabs__section-title">
                    {meta.cardTitle}
                  </h5>
                  {step === "proposal" ? (
                    <PensionProposalEntry
                      employee={employee}
                      showClaimNext
                      claimNextTo={`/dashboard/die-in-harness/claim?emp=${encodeURIComponent(
                        employee.emp_id || ""
                      )}`}
                    />
                  ) : (
                    <NoPayEntry
                      employee={employee}
                      showProposalNext
                      proposalNextTo={`/dashboard/die-in-harness/proposal?emp=${encodeURIComponent(
                        employee.emp_id || ""
                      )}`}
                    />
                  )}
                </section>

                {step === "nopay" && employee.emp_id ? (
                  <p className="text-muted small mt-3 mb-0">
                    Workflow: No-pay →{" "}
                    <Link
                      to={`/dashboard/die-in-harness/proposal?emp=${encodeURIComponent(
                        employee.emp_id
                      )}`}
                    >
                      Pension Proposal
                    </Link>{" "}
                    → Pension Application
                  </p>
                ) : null}
                {step === "proposal" && employee.emp_id ? (
                  <p className="text-muted small mt-3 mb-0">
                    Workflow: No-pay → Pension Proposal →{" "}
                    <Link
                      to={`/dashboard/die-in-harness/claim?emp=${encodeURIComponent(
                        employee.emp_id
                      )}`}
                    >
                      Pension Application
                    </Link>
                  </p>
                ) : null}
              </div>
            </div>
          ) : null}
        </div>
      </div>
    </div>
  );
}
