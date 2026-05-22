import { useCallback, useEffect, useState } from "react";
import API from "../services/Api";
import RevisionCalculationCards from "../components/RevisionCalculationCards";
import Methodology2PensionSummary from "../components/Methodology2PensionSummary";

export default function Methodology2() {
  const [empId, setEmpId] = useState("");
  const [employeeName, setEmployeeName] = useState("");
  const [loadingEmployee, setLoadingEmployee] = useState(false);

  const [retirementDate, setRetirementDate] = useState("");
  const [scale, setScale] = useState("");
  const [lastPay, setLastPay] = useState("");
  const [payStages, setPayStages] = useState([]);
  const [equivalentScales, setEquivalentScales] = useState(null);
  const [calculationRows, setCalculationRows] = useState([]);
  const [pensionSummary, setPensionSummary] = useState(null);
  const [isStageBased, setIsStageBased] = useState(true);
  const [startRevision, setStartRevision] = useState("");
  const [scales, setScales] = useState([]);

  const runCalculation = useCallback(async (date, scaleValue, pay) => {
    if (!date || !scaleValue || !pay) return;

    try {
      const res = await API.post("methodology2/calculate-revision/", {
        retirement_date: date,
        scale: scaleValue,
        last_pay: pay,
      });
      setCalculationRows(res.data.rows || []);
      setPensionSummary(res.data.pension || null);
      if (res.data.start_revision) {
        setStartRevision(res.data.start_revision);
      }
    } catch (err) {
      console.error(err);
      alert(
        err.response?.data?.error || "Calculation failed. Check inputs."
      );
    }
  }, []);

  const loadPayStages = useCallback(async (scaleValue) => {
    if (!scaleValue) {
      setPayStages([]);
      return;
    }
    const res = await API.get(
      `methodology2/get-pay-stages/?scale=${encodeURIComponent(scaleValue)}`
    );
    setPayStages(res.data);
  }, []);

  const loadEquivalentScales = useCallback(async (date, scaleValue) => {
    if (!date || !scaleValue) {
      setEquivalentScales(null);
      return;
    }
    const res = await API.get(
      `methodology2/get-equivalent-scales/?retirement_date=${date}&scale=${encodeURIComponent(scaleValue)}`
    );
    setEquivalentScales(res.data);
  }, []);

  const loadEmployeeById = async (code) => {
    const trimmed = code.trim();
    if (!trimmed) return;

    setLoadingEmployee(true);
    setCalculationRows([]);
    setPensionSummary(null);
    setEquivalentScales(null);

    try {
      const res = await API.get(`methodology2/employee/${trimmed}/`);
      const data = res.data;

      setEmployeeName(data.name || "");
      setEmpId(data.emp_id);

      const sepDate = data.separation_date;
      const scaleValue = data.scale;
      const pay = String(data.last_pay);

      const scalesRes = await API.get(
        `methodology2/get-scales/?retirement_date=${sepDate}`
      );
      setScales(scalesRes.data);

      const typeRes = await API.get(
        `methodology2/get-scale-type/?retirement_date=${sepDate}`
      );
      setIsStageBased(typeRes.data.is_stage_based);
      setStartRevision(typeRes.data.revision || data.revision || "");

      await loadPayStages(scaleValue);

      setRetirementDate(sepDate);
      setScale(scaleValue);
      setLastPay(pay);

      await loadEquivalentScales(sepDate, scaleValue);
    } catch (err) {
      console.error(err);
      const msg =
        err.response?.data?.error ||
        err.response?.data?.message ||
        "Could not load employee from Oracle.";
      alert(msg);
    } finally {
      setLoadingEmployee(false);
    }
  };

  const handleEmpKeyDown = (e) => {
    if (e.key === "Enter") {
      e.preventDefault();
      loadEmployeeById(empId);
    }
  };

  useEffect(() => {
    if (!retirementDate) {
      setScales([]);
      return;
    }

    API.get(`methodology2/get-scales/?retirement_date=${retirementDate}`)
      .then((res) => setScales(res.data))
      .catch(console.error);

    API.get(`methodology2/get-scale-type/?retirement_date=${retirementDate}`)
      .then((res) => {
        setIsStageBased(res.data.is_stage_based);
        setStartRevision(res.data.revision || "");
      })
      .catch(console.error);
  }, [retirementDate]);

  useEffect(() => {
    loadPayStages(scale);
  }, [scale, loadPayStages]);

  useEffect(() => {
    loadEquivalentScales(retirementDate, scale);
  }, [retirementDate, scale, loadEquivalentScales]);

  useEffect(() => {
    if (retirementDate && scale && lastPay) {
      runCalculation(retirementDate, scale, lastPay);
    }
  }, [retirementDate, scale, lastPay, runCalculation]);

  return (
    <div className="container mt-4">
      <div className="row justify-content-center">
        <div className="col-md-10">
          <div className="card shadow">
            <div className="card-header bg-primary text-white">
              <h4 className="mb-0">Methodology 2</h4>
            </div>
            <div className="card-body">
              <div className="row mb-3">
                <div className="col-md-5">
                  <label className="form-label fw-bold">
                    Employee ID (Oracle)
                  </label>
                  <div className="input-group">
                    <input
                      type="text"
                      className="form-control"
                      placeholder="Enter emp code and press Enter"
                      value={empId}
                      onChange={(e) => setEmpId(e.target.value)}
                      onKeyDown={handleEmpKeyDown}
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
                  {employeeName && (
                    <small className="text-muted d-block mt-1">
                      {employeeName}
                    </small>
                  )}
                </div>
              </div>

              <div className="text-center text-muted small mb-3">— OR —</div>

              <div className="row">
                <div className="col-md-4">
                  <label className="form-label">Retirement / Separation Date</label>
                  <input
                    type="date"
                    className="form-control"
                    value={retirementDate}
                    onChange={(e) => setRetirementDate(e.target.value)}
                  />
                </div>

                <div className="col-md-4">
                  <label className="form-label">Scale</label>
                  <select
                    className="form-select"
                    value={scale}
                    onChange={(e) => setScale(e.target.value)}
                  >
                    <option value="">Select Scale</option>
                    {scales.map((item, index) => (
                      <option key={index} value={item}>
                        {item}
                      </option>
                    ))}
                  </select>
                </div>

                <div className="col-md-4">
                  <label className="form-label">Last Pay</label>
                  <select
                    className="form-select"
                    value={lastPay}
                    onChange={(e) => setLastPay(e.target.value)}
                  >
                    <option value="">Select Last Pay</option>
                    {payStages.map((item, index) => (
                      <option key={index} value={item}>
                        {item}
                      </option>
                    ))}
                  </select>
                </div>
              </div>

              {!isStageBased && (
                <p className="small text-muted mt-2 mb-0">
                  Scale type for this date is not stage-based.
                </p>
              )}
            </div>
          </div>
        </div>
      </div>

      {equivalentScales && (
        <div className="row justify-content-center mt-4">
          <div className="col-md-10">
            <div className="card shadow">
              <div className="card-header bg-success text-white">
                <h5 className="mb-0">Equivalent Scales</h5>
              </div>
              <div className="card-body">
                <table className="table table-bordered mb-0">
                  <thead>
                    <tr>
                      <th>Revision</th>
                      <th>Scale</th>
                    </tr>
                  </thead>
                  <tbody>
                    {Object.entries(equivalentScales).map(([key, value], index) =>
                      key !== "Scale" ? (
                        <tr key={index}>
                          <td>{key}</td>
                          <td>{value}</td>
                        </tr>
                      ) : null
                    )}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        </div>
      )}

      <Methodology2PensionSummary
        pensionSummary={pensionSummary}
        retirementDate={retirementDate}
        scale={scale}
        lastPay={lastPay}
        empId={empId}
        employeeName={employeeName}
      />

      {calculationRows.length > 0 && startRevision && (
        <div className="row justify-content-center mt-4">
          <div className="col-12">
            <div className="card shadow">
              <div className="card-header bg-secondary text-white">
                <h5 className="mb-0">Revision Calculation (year-wise)</h5>
              </div>
              <div className="card-body">
                <RevisionCalculationCards
                  calculationRows={calculationRows}
                  startRevision={startRevision}
                />
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
