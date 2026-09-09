import { useCallback, useEffect, useRef, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import FirstPensionEmployeeWorkflow from "../components/FirstPensionEmployeeWorkflow";
import { loadFirstPensionEmployeeByCode } from "../utils/loadFirstPensionEmployee";
import "../styles/FirstPensionCase.css";

const STEP_META = {
  esr: {
    searchTitle: "First Pension — ESR Check",
    formTitle: "ESR Check",
    hint: "Search employee, then review Personal, Admin, Finance and Salary.",
  },
  nopay: {
    searchTitle: "First Pension — No-pay",
    formTitle: "No-pay Entry",
    hint: "Search employee, then enter / edit no-pay days.",
  },
  commutation: {
    searchTitle: "First Pension — Commutation",
    formTitle: "Commutation",
    hint: "Search employee, then enter commutation application.",
  },
  proposal: {
    searchTitle: "First Pension — Proposal",
    formTitle: "Pension Proposal",
    hint: "Search employee, then open pension proposal.",
  },
  amount: {
    searchTitle: "First Pension — Amount",
    formTitle: "Amount (Calculation)",
    hint: "Search employee, then calculate pension, commutation and gratuity.",
  },
  bill: {
    searchTitle: "First Pension — Bill & Journal",
    formTitle: "Bill & Journal",
    hint: "Search employee, then generate PPN / PPC bill and journal vouchers.",
  },
  reports: {
    searchTitle: "First Pension — Reports",
    formTitle: "Reports",
    hint: "Search employee, then print LIC, sanction, advice and bill reports.",
  },
};

export default function FirstPensionCase({ step = "esr" }) {
  const meta = STEP_META[step] || STEP_META.nopay;
  const [searchParams, setSearchParams] = useSearchParams();

  const [employeeId, setEmployeeId] = useState("");
  const [employee, setEmployee] = useState(null);
  const [message, setMessage] = useState("");
  const [loading, setLoading] = useState(false);
  const [workflowPhase, setWorkflowPhase] = useState("idle");
  const urlEmpLoadedRef = useRef(false);

  const loadEmployee = useCallback(async (rawCode) => {
    const code = String(rawCode || "").trim();
    if (!code) {
      setMessage("Please enter Employee ID");
      return;
    }

    setLoading(true);
    setMessage("");
    setWorkflowPhase("idle");

    try {
      const { detail, loadWarning } = await loadFirstPensionEmployeeByCode(code);
      setEmployee(detail);
      setEmployeeId(detail?.emp_id || code);
      setWorkflowPhase(step === "esr" ? "basic" : "form");
      setMessage(
        loadWarning ||
          (detail?.cache_message ? detail.cache_message : "") ||
          (detail?.partial
            ? "Limited employee data available (Oracle unavailable)."
            : "")
      );
    } catch (error) {
      setEmployee(null);
      setWorkflowPhase("idle");
      setMessage(
        error.response?.data?.error ||
          error.response?.data?.message ||
          "Employee not found"
      );
      console.error(error);
    } finally {
      setLoading(false);
    }
  }, [step]);

  useEffect(() => {
    urlEmpLoadedRef.current = false;
    setEmployee(null);
    setWorkflowPhase("idle");
    setMessage("");
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

  const handleEmployeeUpdate = (patch) => {
    setEmployee((prev) => ({ ...(prev || {}), ...patch }));
  };

  const handlePhaseChange = useCallback((phase) => {
    setWorkflowPhase(phase);
  }, []);

  const handleSearchAnother = () => {
    setEmployee(null);
    setWorkflowPhase("idle");
    setMessage("");
    setEmployeeId("");
  };

  const keepSearchVisible = step === "esr" && workflowPhase !== "intake";
  const headerTitle =
    step === "esr" && workflowPhase === "intake"
      ? `Pension Processing — ${employee?.name || employee?.emp_id || ""}`
      : step === "esr"
        ? `ESR Check — ${employee?.name || employee?.emp_id || ""}`
        : `${meta.formTitle} — ${employee?.name || employee?.emp_id || ""}`;

  const empQs = employee?.emp_id
    ? `?emp=${encodeURIComponent(employee.emp_id)}`
    : "";

  return (
    <div className="first-pension-page container-fluid mt-3 mt-md-4 px-2 px-md-3">
      <div className="row justify-content-center">
        <div className="col-12 col-xl-11">
          {(!employee || keepSearchVisible) && (
            <div className="card shadow first-pension-search-card">
              <div className="card-header bg-primary text-white">
                <h4 className="mb-0">{meta.searchTitle}</h4>
              </div>
              <div className="card-body smpk-form">
                <p className="text-muted small mb-3">{meta.hint}</p>
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

                {!employee && message ? (
                  <div className="alert alert-danger mt-3 mb-0" role="status">
                    {message}
                  </div>
                ) : null}
              </div>
            </div>
          )}

          {employee && (
            <div className="card shadow first-pension-workflow-card">
              <div className="card-header bg-primary text-white py-2">
                <h4 className="mb-0 h5">{headerTitle}</h4>
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
                  {!keepSearchVisible ? (
                    <button
                      type="button"
                      className="btn btn-outline-secondary btn-sm"
                      onClick={handleSearchAnother}
                    >
                      Search another employee
                    </button>
                  ) : null}
                </div>

                <FirstPensionEmployeeWorkflow
                  employee={employee}
                  step={step}
                  onPhaseChange={handlePhaseChange}
                  onEmployeeUpdate={handleEmployeeUpdate}
                />

                {employee.emp_id ? (
                  <p className="text-muted small mt-3 mb-0">
                    Workflow:{" "}
                    <Link to={`/dashboard/firstpension/esr-check${empQs}`}>
                      ESR Check
                    </Link>{" "}
                    →{" "}
                    <Link to={`/dashboard/firstpension/nopay${empQs}`}>
                      No-pay
                    </Link>{" "}
                    →{" "}
                    <Link to={`/dashboard/firstpension/commutation${empQs}`}>
                      Commutation
                    </Link>{" "}
                    →{" "}
                    <Link to={`/dashboard/firstpension/proposal${empQs}`}>
                      Proposal
                    </Link>{" "}
                    →{" "}
                    <Link to={`/dashboard/firstpension/amount${empQs}`}>
                      Amount
                    </Link>{" "}
                    →{" "}
                    <Link to={`/dashboard/firstpension/bill${empQs}`}>
                      Bill & Journal
                    </Link>{" "}
                    →{" "}
                    <Link to={`/dashboard/firstpension/reports${empQs}`}>
                      Reports
                    </Link>
                  </p>
                ) : null}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
