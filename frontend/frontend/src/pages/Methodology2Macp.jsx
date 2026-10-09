import { useCallback, useEffect, useState } from "react";
import API from "../services/Api";
import Methodology2PensionSummary from "../components/Methodology2OldAgePensionSummary";
import SmpkDataTable from "../components/DataTable/SmpkDataTable";

/**
 * Class 3 employees who received MACP into an Officers' scale.
 * Scale table and fitment live in macp_calculation_service.py.
 * This page does not use the ordinary Consolidation scale list or revision API.
 */
export default function Methodology2Macp() {
  const [empId, setEmpId] = useState("");
  const [employeeName, setEmployeeName] = useState("");
  const [loadingEmployee, setLoadingEmployee] = useState(false);
  const [categoryNote, setCategoryNote] = useState("");

  const [retirementDate, setRetirementDate] = useState("");
  const [tracks, setTracks] = useState([]);
  const [trackKey, setTrackKey] = useState("");
  const [revision, setRevision] = useState("");
  const [optionsError, setOptionsError] = useState("");
  const [lastPay, setLastPay] = useState("");
  const [stagnationAmount, setStagnationAmount] = useState("");
  const [calculationRows, setCalculationRows] = useState([]);
  const [pensionSummary, setPensionSummary] = useState(null);
  const [equivalentScales, setEquivalentScales] = useState(null);
  const [savedScale, setSavedScale] = useState("");
  const [printMaster, setPrintMaster] = useState(null);
  const [dateOfBirth, setDateOfBirth] = useState("");
  const [oldageBenefit, setOldageBenefit] = useState(null);

  const selectedTrack = tracks.find((item) => item.key === trackKey) || null;
  const payStages = selectedTrack?.pay_stages || [];

  const effectivePay = (() => {
    const base = Number(lastPay);
    if (!lastPay || Number.isNaN(base)) return "";
    const stag = Number(stagnationAmount);
    const stagVal = Number.isNaN(stag) ? 0 : stag;
    return String(base + stagVal);
  })();

  const loadTracks = useCallback(async (date) => {
    if (!date) {
      setTracks([]);
      setRevision("");
      setOptionsError("");
      return;
    }
    try {
      const res = await API.get(
        `m2-oldage-arrear/macp/options/?retirement_date=${date}`
      );
      setTracks(res.data.tracks || []);
      setRevision(res.data.revision || "");
      setOptionsError("");
    } catch (err) {
      setTracks([]);
      setRevision("");
      setOptionsError(
        err.response?.data?.error || "MACP scales are not available for this date."
      );
    }
  }, []);

  useEffect(() => {
    loadTracks(retirementDate);
  }, [retirementDate, loadTracks]);

  useEffect(() => {
    if (!selectedTrack) {
      setEquivalentScales(null);
      return;
    }
    setEquivalentScales(selectedTrack.equivalent_scales || null);
    setSavedScale(`MACP ${selectedTrack.key}`);
  }, [selectedTrack]);

  const runCalculation = useCallback(async () => {
    if (!retirementDate || !trackKey || !effectivePay) return;
    try {
      const res = await API.post("m2-oldage-arrear/macp/calculate/", {
        retirement_date: retirementDate,
        track: trackKey,
        last_pay: effectivePay,
        tqs_yr: printMaster?.tqs_yr,
        tqs_month: printMaster?.tqs_month,
        tqs_days: printMaster?.tqs_days,
      });
      setCalculationRows(res.data.rows || []);
      setPensionSummary(res.data.pension || null);
      setEquivalentScales(res.data.equivalent_scales || null);
      if (res.data.scale) setSavedScale(res.data.scale);
      if (res.data.start_revision) setRevision(res.data.start_revision);
    } catch (err) {
      console.error(err);
      alert(err.response?.data?.error || "MACP calculation failed. Check inputs.");
    }
  }, [retirementDate, trackKey, effectivePay, printMaster]);

  useEffect(() => {
    if (retirementDate && trackKey && effectivePay) {
      runCalculation();
    }
  }, [retirementDate, trackKey, effectivePay, runCalculation]);

  const recalculateOldAge = useCallback(async () => {
    if (!dateOfBirth || !pensionSummary) {
      setOldageBenefit(null);
      return;
    }
    const pen = pensionSummary;
    const isEmp = printMaster?.is_employee_pension !== false;
    const m2_359 = isEmp ? pen.pension_359_cpi : pen.family_pension_359_cpi;
    const m2_277 = isEmp ? pen.pension_277_cpi : pen.family_pension_277_cpi;
    try {
      const res = await API.post("m2-oldage-arrear/oldage/calculate/", {
        emp_id: empId || undefined,
        dob: dateOfBirth,
        date_of_birth: dateOfBirth,
        category: "3",
        is_employee_pension: isEmp,
        date_of_death: printMaster?.date_of_death || null,
        double_fpension_upto: printMaster?.double_fpension_upto || null,
        pensioner_name: printMaster?.pensioner_name || null,
        family_pensioner_dob: printMaster?.family_pensioner_dob || null,
        m2_pension_359: pen.pension_359_cpi ?? null,
        m2_pension_277: pen.pension_277_cpi ?? null,
        m2_family_pension_359: pen.family_pension_359_cpi ?? null,
        m2_family_pension_277: pen.family_pension_277_cpi ?? null,
        pension_359: m2_359,
        pension_277: m2_277,
        m1_pension_359: printMaster?.m1_family_pension_359 ?? null,
        m1_pension_277: printMaster?.m1_family_pension_277 ?? null,
      });
      setOldageBenefit(res.data);
    } catch (err) {
      console.error(err);
      setOldageBenefit({
        error: err.response?.data?.error || "Old-age calculation failed",
        milestones: [],
      });
    }
  }, [dateOfBirth, pensionSummary, empId, printMaster]);

  useEffect(() => {
    recalculateOldAge();
  }, [recalculateOldAge]);

  const loadEmployeeById = async (code) => {
    const trimmed = String(code || "").trim();
    if (!trimmed) return;
    setLoadingEmployee(true);
    setCalculationRows([]);
    setPensionSummary(null);
    setOldageBenefit(null);
    setCategoryNote("");
    try {
      const res = await API.get(`m2-oldage-arrear/employee/${trimmed}/`);
      const data = res.data;
      setEmployeeName(data.name || "");
      setEmpId(data.emp_id || trimmed);
      setDateOfBirth(data.date_of_birth || data.dob || "");
      setPrintMaster({
        emp_cd: data.emp_id,
        name: data.name || "",
        case_no: data.case_no || "",
        roll_no: data.roll_no || "",
        designation: data.designation || "",
        tqs: data.tqs || "",
        tqs_yr: data.tqs_yr,
        tqs_month: data.tqs_month,
        tqs_days: data.tqs_days,
        retirement_date: data.separation_date || null,
        retirement_type: data.retirement_type || "",
        date_of_death: data.date_of_death || null,
        family_pensioner_dob: data.family_pensioner_dob || null,
        double_fpension_upto: data.double_fpension_upto || null,
        enhanced_family_pension: !!data.enhanced_family_pension,
        category: "3",
        pensioner_name: data.pensioner_name || "",
        is_employee_pension: data.is_employee_pension || false,
        m1_family_pension_277: data.m1_family_pension_277 ?? null,
        m1_family_pension_359: data.m1_family_pension_359 ?? null,
        date_of_birth: data.date_of_birth || data.dob || null,
      });
      if (data.category && String(data.category) !== "3") {
        setCategoryNote(
          `Employee master category is ${data.category}. This screen still calculates as Class 3 MACP.`
        );
      }
      if (data.separation_date) {
        setRetirementDate(data.separation_date);
        setTrackKey("");
        setLastPay("");
      }
      if (data.warning) alert(data.warning);
    } catch (err) {
      console.error(err);
      alert(err.response?.data?.error || "Could not load employee.");
    } finally {
      setLoadingEmployee(false);
    }
  };

  return (
    <div className="container-fluid mt-3 mt-md-4 px-2 px-md-3">
      <div className="row justify-content-center">
        <div className="col-12 col-xl-10">
          <div className="card shadow">
            <div className="card-header bg-dark text-white">
              <h4 className="mb-0">MACP cases (Class 3)</h4>
            </div>
            <div className="card-body smpk-form">
              <p className="small text-muted">
                Class 3 employees who moved into an Officers&apos; scale under
                MACP. Category stays 3. Fitment follows the staff wage-revision
                orders. 2012 uses the highest Class 3 scale, 23600-56300, for
                every track. Pay matrix is not applied.
              </p>

              <div className="row g-3 mb-3">
                <div className="col-12 col-lg-6">
                  <label className="form-label">Employee ID</label>
                  <div className="input-group">
                    <input
                      type="text"
                      className="form-control"
                      placeholder="Enter emp code and press Enter"
                      value={empId}
                      onChange={(e) => setEmpId(e.target.value)}
                      onKeyDown={(e) => {
                        if (e.key === "Enter") {
                          e.preventDefault();
                          loadEmployeeById(empId);
                        }
                      }}
                      disabled={loadingEmployee}
                    />
                    <button
                      type="button"
                      className="btn btn-outline-primary"
                      onClick={() => loadEmployeeById(empId)}
                      disabled={loadingEmployee || !empId.trim()}
                    >
                      {loadingEmployee ? "Loading..." : "Load"}
                    </button>
                  </div>
                  {employeeName ? (
                    <small className="text-muted d-block mt-1">{employeeName}</small>
                  ) : null}
                  {categoryNote ? (
                    <small className="text-warning d-block mt-1">{categoryNote}</small>
                  ) : null}
                </div>
              </div>

              <div className="row g-2 g-lg-3 align-items-end">
                <div className="col-12 col-md-4 col-xl-3">
                  <label className="form-label">Retirement / Separation Date</label>
                  <input
                    type="date"
                    className="form-control"
                    value={retirementDate}
                    onChange={(e) => {
                      setRetirementDate(e.target.value);
                      setTrackKey("");
                      setLastPay("");
                      setCalculationRows([]);
                      setPensionSummary(null);
                    }}
                  />
                </div>

                <div className="col-12 col-md-8 col-xl-5">
                  <label className="form-label">MACP scale track</label>
                  <select
                    className="form-select"
                    value={trackKey}
                    disabled={!retirementDate || !tracks.length}
                    onChange={(e) => {
                      setTrackKey(e.target.value);
                      setLastPay("");
                      setCalculationRows([]);
                      setPensionSummary(null);
                    }}
                  >
                    <option value="">
                      {retirementDate
                        ? tracks.length
                          ? "Select scale"
                          : "No MACP scale for this date"
                        : "Enter separation date first"}
                    </option>
                    {tracks.map((item) => (
                      <option key={item.key} value={item.key}>
                        {item.label}
                      </option>
                    ))}
                  </select>
                  {selectedTrack ? (
                    <small className="text-muted d-block mt-1">
                      Scale at retirement: {selectedTrack.scale_at_retirement}
                    </small>
                  ) : null}
                </div>

                <div className="col-6 col-md-4 col-xl-2">
                  <label className="form-label">Last Pay</label>
                  {payStages.length ? (
                    <select
                      className="form-select"
                      value={lastPay}
                      disabled={!trackKey}
                      onChange={(e) => setLastPay(e.target.value)}
                    >
                      <option value="">Select Last Pay</option>
                      {payStages.map((item) => (
                        <option key={item} value={item}>
                          {item}
                        </option>
                      ))}
                    </select>
                  ) : (
                    <input
                      type="number"
                      className="form-control"
                      min="0"
                      step="1"
                      placeholder="Last basic"
                      value={lastPay}
                      disabled={!trackKey}
                      onChange={(e) => setLastPay(e.target.value)}
                    />
                  )}
                </div>

                <div className="col-6 col-md-4 col-xl-2">
                  <label className="form-label">Stagnation Amount</label>
                  <input
                    type="number"
                    className="form-control"
                    min="0"
                    step="1"
                    placeholder="0"
                    value={stagnationAmount}
                    disabled={!trackKey}
                    onChange={(e) => setStagnationAmount(e.target.value)}
                  />
                </div>
              </div>

              {optionsError ? (
                <div className="alert alert-warning py-2 px-3 mt-3 mb-0 small">
                  {optionsError}
                </div>
              ) : null}
            </div>
          </div>
        </div>
      </div>

      {equivalentScales ? (
        <div className="row justify-content-center mt-4">
          <div className="col-12 col-xl-10">
            <div className="card shadow">
              <div className="card-header bg-success text-white">
                <h5 className="mb-0">Equivalent Scales</h5>
              </div>
              <div className="card-body">
                <SmpkDataTable
                  tableKey={Object.keys(equivalentScales).join("-")}
                  className="table table-striped table-bordered mb-0 w-100 smpk-datatable"
                  options={{
                    paging: false,
                    searching: false,
                    info: false,
                    lengthChange: false,
                    order: [[0, "asc"]],
                  }}
                >
                  <thead>
                    <tr>
                      <th>Revision</th>
                      <th>Scale</th>
                    </tr>
                  </thead>
                  <tbody>
                    {Object.entries(equivalentScales).map(([key, value]) => (
                      <tr key={key}>
                        <td>{key}</td>
                        <td>{value}</td>
                      </tr>
                    ))}
                  </tbody>
                </SmpkDataTable>
              </div>
            </div>
          </div>
        </div>
      ) : null}

      <Methodology2PensionSummary
        pensionSummary={pensionSummary}
        retirementDate={retirementDate}
        scale={savedScale}
        lastPay={lastPay}
        stagnationAmount={stagnationAmount}
        effectivePay={effectivePay || lastPay}
        empId={empId}
        employeeName={employeeName}
        category="3"
        startRevision={revision}
        calculationRows={calculationRows}
        equivalentScales={equivalentScales}
        printMaster={printMaster}
        dateOfBirth={dateOfBirth}
        oldageBenefit={oldageBenefit}
      />
    </div>
  );
}
