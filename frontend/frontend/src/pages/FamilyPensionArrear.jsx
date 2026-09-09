import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useSearchParams } from "react-router-dom";
import API from "../services/Api";
import FamilyPensionArrearPrint, {
  printFamilyPensionArrearSheet,
} from "../components/FamilyPensionArrearPrint";
import "../styles/FirstPensionCase.css";

const MONTHS = [
  { value: 1, label: "January (01)" },
  { value: 2, label: "February (02)" },
  { value: 3, label: "March (03)" },
  { value: 4, label: "April (04)" },
  { value: 5, label: "May (05)" },
  { value: 6, label: "June (06)" },
  { value: 7, label: "July (07)" },
  { value: 8, label: "August (08)" },
  { value: 9, label: "September (09)" },
  { value: 10, label: "October (10)" },
  { value: 11, label: "November (11)" },
  { value: 12, label: "December (12)" },
];

/** Last calendar day of month as ISO (Oracle form: Feb always 28). */
function arrearUptoIso(month, year) {
  const m = Number(month);
  const y = Number(year);
  if (!m || m < 1 || m > 12 || !y || y < 1900 || y > 2100) return "";
  if (m === 2) return `${y}-02-28`;
  const last = new Date(y, m, 0).getDate();
  return `${y}-${String(m).padStart(2, "0")}-${String(last).padStart(2, "0")}`;
}

function parseIsoToMonthYear(isoDate) {
  if (!isoDate) return { month: "", year: "" };
  const s = String(isoDate).slice(0, 10);
  const m = s.match(/^(\d{4})-(\d{2})/);
  if (!m) return { month: "", year: "" };
  return { year: Number(m[1]), month: Number(m[2]) };
}

function sheetFromResponse(data) {
  if (!data) return null;
  const ug = data.upgrade || {};
  return {
    emp_cd: data.emp_cd || ug.emp_cd,
    emp_name: data.emp_name,
    applicant_name: data.applicant_name,
    case_no: data.case_no ?? ug.case_no,
    claim_id: data.claim_id || ug.claim_id,
    pensioner_death_dt: data.pensioner_death_dt || ug.pensioner_death_dt,
    generated_basic: data.generated_basic ?? ug.generated_basic,
    upgraded_basic: data.upgraded_basic ?? ug.upgraded_basic,
    arrear_upto: data.arrear_upto || ug.arrear_upto,
    arrear_pension: data.arrear_pension ?? ug.arrear_pension,
    arrear_relief: data.arrear_relief ?? ug.arrear_relief,
    total_payable:
      data.total_payable != null
        ? data.total_payable
        : (Number(data.arrear_pension) || 0) +
          (Number(data.arrear_relief) || 0),
    details: data.details || [],
  };
}

function yearOptions(centerYear) {
  const y = centerYear || new Date().getFullYear();
  const start = Math.min(2010, y - 5);
  const end = Math.max(y + 2, 2030);
  const list = [];
  for (let i = end; i >= start; i -= 1) list.push(i);
  return list;
}

/**
 * Family Pension → Arrear
 * Inputs: Employee ID + Arrear Upto Month / Year.
 * DA changes WEF 01 / 04 / 07 / 10. Detail sheet print matches Oracle.
 */
export default function FamilyPensionArrear() {
  const [searchParams, setSearchParams] = useSearchParams();
  const [employeeId, setEmployeeId] = useState("");
  const [uptoMonth, setUptoMonth] = useState("");
  const [uptoYear, setUptoYear] = useState("");
  const [sheet, setSheet] = useState(null);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [calculating, setCalculating] = useState(false);
  const urlEmpLoadedRef = useRef(false);

  const years = useMemo(() => yearOptions(new Date().getFullYear()), []);

  const uptoIso = useMemo(
    () => arrearUptoIso(uptoMonth, uptoYear),
    [uptoMonth, uptoYear]
  );

  const inputsReady =
    Boolean(String(employeeId || "").trim()) &&
    Boolean(uptoMonth) &&
    Boolean(uptoYear) &&
    Boolean(uptoIso);

  const applyMonthYearFromData = (data) => {
    const from = parseIsoToMonthYear(
      data?.arrear_upto || data?.upgrade?.arrear_upto
    );
    if (from.month) setUptoMonth(from.month);
    if (from.year) setUptoYear(from.year);
  };

  const loadByEmp = useCallback(async (rawCode) => {
    const code = String(rawCode || "").trim();
    if (!code) {
      setError("Please enter Employee ID");
      return false;
    }
    setLoading(true);
    setError("");
    setMessage("");
    try {
      const { data } = await API.get("family-pension/calculate-277-arrear/", {
        params: { emp_cd: code },
      });
      if (!data?.found) {
        setSheet(null);
        setEmployeeId(code);
        setError(
          data?.message ||
            "No 277 upgrade / arrear record found for this Employee ID. Upgrade first, then calculate arrear."
        );
        return false;
      }
      const next = sheetFromResponse(data);
      setSheet(next);
      setEmployeeId(code);
      applyMonthYearFromData(data);
      if (!next.details?.length) {
        setMessage(
          "Upgrade found. Enter Upto Month & Year, then click Calculate Arrear."
        );
      } else {
        setMessage(
          "Loaded saved arrear. Change Upto Month / Year and re-calculate if needed."
        );
      }
      return true;
    } catch (err) {
      setSheet(null);
      setError(
        err.response?.data?.error ||
          err.message ||
          "Could not load arrear data"
      );
      return false;
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (urlEmpLoadedRef.current) return;
    const fromUrl = searchParams.get("emp");
    if (!fromUrl) return;
    urlEmpLoadedRef.current = true;
    loadByEmp(fromUrl);
    setSearchParams({}, { replace: true });
  }, [loadByEmp, searchParams, setSearchParams]);

  const handleSearch = async (e) => {
    e.preventDefault();
    await loadByEmp(employeeId);
  };

  const handleCalculate = async (e) => {
    if (e) e.preventDefault();
    const code = String(employeeId || sheet?.emp_cd || "").trim();
    if (!code) {
      setError("Please enter Employee ID");
      return;
    }
    if (!uptoMonth || !uptoYear) {
      setError("Please enter Arrear Upto Month and Year");
      return;
    }
    const upto = arrearUptoIso(uptoMonth, uptoYear);
    if (!upto) {
      setError("Invalid Arrear Upto Month / Year");
      return;
    }

    setCalculating(true);
    setError("");
    setMessage("");
    try {
      // Ensure upgrade row is loaded for this emp first if needed
      if (!sheet || String(sheet.emp_cd) !== code) {
        const ok = await loadByEmp(code);
        if (!ok) {
          setCalculating(false);
          return;
        }
      }

      const { data } = await API.post("family-pension/calculate-277-arrear/", {
        emp_cd: code,
        arrear_upto: upto,
        update_monthly_bill: true,
      });
      setSheet(sheetFromResponse(data));
      setMessage(
        `${data?.message || "Arrear calculation completed."} Upto ${String(
          uptoMonth
        ).padStart(2, "0")}/${uptoYear} (${upto}).`
      );
    } catch (err) {
      setError(
        err.response?.data?.error ||
          err.message ||
          "Arrear calculation failed"
      );
    } finally {
      setCalculating(false);
    }
  };

  const handleSearchAnother = () => {
    setSheet(null);
    setMessage("");
    setError("");
    setEmployeeId("");
    setUptoMonth("");
    setUptoYear("");
  };

  const monthYearFields = (
    <>
      <div className="col-6 col-md-3">
        <label className="form-label">
          Upto Month <span className="text-danger">*</span>
        </label>
        <select
          className="form-select"
          value={uptoMonth}
          onChange={(e) =>
            setUptoMonth(e.target.value ? Number(e.target.value) : "")
          }
          disabled={loading || calculating}
          required
        >
          <option value="">Select month</option>
          {MONTHS.map((m) => (
            <option key={m.value} value={m.value}>
              {m.label}
            </option>
          ))}
        </select>
      </div>
      <div className="col-6 col-md-3">
        <label className="form-label">
          Upto Year <span className="text-danger">*</span>
        </label>
        <select
          className="form-select"
          value={uptoYear}
          onChange={(e) =>
            setUptoYear(e.target.value ? Number(e.target.value) : "")
          }
          disabled={loading || calculating}
          required
        >
          <option value="">Select year</option>
          {years.map((y) => (
            <option key={y} value={y}>
              {y}
            </option>
          ))}
        </select>
      </div>
    </>
  );

  return (
    <div className="first-pension-page container-fluid mt-3 mt-md-4 px-2 px-md-3 first-pension-page--tabs">
      <div className="row justify-content-center">
        <div className="col-12 col-xl-11">
          {!sheet && (
            <div className="card shadow first-pension-search-card">
              <div className="card-header bg-primary text-white">
                <h4 className="mb-0">Family Pension — Arrear</h4>
              </div>
              <div className="card-body smpk-form">
                <p className="text-muted small mb-3">
                  Enter <strong>Employee ID</strong> and arrear{" "}
                  <strong>Upto Month / Year</strong>. Calculation runs through
                  the last day of that month (DA changes on 01 / 04 / 07 / 10).
                </p>
                <form
                  onSubmit={(e) => {
                    e.preventDefault();
                    if (inputsReady) handleCalculate();
                    else loadByEmp(employeeId);
                  }}
                >
                  <div className="row g-3 align-items-end">
                    <div className="col-12 col-md-4">
                      <label className="form-label">
                        Employee ID <span className="text-danger">*</span>
                      </label>
                      <input
                        type="text"
                        className="form-control"
                        placeholder="Employee ID"
                        value={employeeId}
                        onChange={(e) => setEmployeeId(e.target.value)}
                        disabled={loading || calculating}
                        autoComplete="off"
                        required
                      />
                    </div>
                    {monthYearFields}
                    <div className="col-12 col-md-2 d-grid">
                      <button
                        type="button"
                        className="btn btn-outline-primary"
                        disabled={loading || !employeeId.trim()}
                        onClick={handleSearch}
                      >
                        {loading ? "…" : "Search"}
                      </button>
                    </div>
                    <div className="col-12 col-md-3 d-grid">
                      <button
                        type="submit"
                        className="btn btn-primary"
                        disabled={
                          loading || calculating || !inputsReady
                        }
                      >
                        {calculating ? "Calculating…" : "Calculate Arrear"}
                      </button>
                    </div>
                  </div>
                  {uptoIso && (
                    <div className="form-text mt-2">
                      Arrear will be calculated up to{" "}
                      <strong>{uptoIso}</strong> (last day of selected month).
                    </div>
                  )}
                </form>
                {error && (
                  <div className="alert alert-danger mt-3 mb-0" role="alert">
                    {error}
                  </div>
                )}
              </div>
            </div>
          )}

          {sheet && (
            <div className="card shadow first-pension-workflow-card">
              <div className="card-header bg-primary text-white py-2">
                <h4 className="mb-0 h5">
                  Arrear Calculation — {sheet.emp_cd}
                  {sheet.emp_name ? ` — ${sheet.emp_name}` : ""}
                </h4>
              </div>
              <div className="card-body">
                {message && (
                  <div className="alert alert-info py-2" role="status">
                    {message}
                  </div>
                )}
                {error && (
                  <div className="alert alert-danger py-2" role="alert">
                    {error}
                  </div>
                )}

                <div className="first-pension-employee-bar mb-3">
                  <strong>
                    {sheet.emp_cd}
                    {sheet.emp_name ? ` — ${sheet.emp_name}` : ""}
                    {sheet.claim_id ? ` · ${sheet.claim_id}` : ""}
                  </strong>
                  <button
                    type="button"
                    className="btn btn-outline-secondary btn-sm"
                    onClick={handleSearchAnother}
                  >
                    Search another employee
                  </button>
                </div>

                <form
                  className="row g-3 align-items-end mb-3 smpk-form"
                  onSubmit={handleCalculate}
                >
                  {monthYearFields}
                  <div className="col-12 col-md-6 d-flex flex-wrap gap-2">
                    <button
                      type="submit"
                      className="btn btn-primary"
                      disabled={calculating || !uptoMonth || !uptoYear}
                    >
                      {calculating ? "Calculating…" : "Calculate Arrear"}
                    </button>
                    <button
                      type="button"
                      className="btn btn-outline-primary"
                      onClick={printFamilyPensionArrearSheet}
                      disabled={!sheet.details?.length}
                    >
                      Print detail sheet
                    </button>
                  </div>
                  {uptoIso && (
                    <div className="col-12 form-text">
                      Arrear upto: <strong>{uptoIso}</strong>
                      {sheet.arrear_upto
                        ? ` · Last calculated: ${sheet.arrear_upto}`
                        : ""}
                    </div>
                  )}
                </form>

                <div className="fp-arrear-print-screen">
                  <FamilyPensionArrearPrint data={sheet} />
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
