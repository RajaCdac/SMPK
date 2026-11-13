import { useEffect, useState } from "react";
import API from "../services/Api";
import { generatePayStages } from "../utils/scaleParser";

// CR 06-11-2026: M2 "M1 calculation" — Methodology-1 employee pension (50%)
// and family pension (30%) at 277 / 359 CPI. Class 3/4 runs the M1 chain on the
// full last pay (no starting 30% / 607 slab); class 1/2 uses the class 1/2 engine.

const CPI_1030_REVISION = "1993(1030 CPI)";
const PRE_1988_REVISIONS = ["1979(REVISED PAY SCALE)", "1984(REVISED PAY SCALE)"];

function money(value) {
  if (value == null || value === "") return "—";
  const n = Number(value);
  return Number.isNaN(n) ? String(value) : n.toLocaleString("en-IN", { maximumFractionDigits: 2 });
}

function scaleLabel(item) {
  if (item && typeof item === "object") {
    if (item.label) return item.label;
    const stages = generatePayStages(item.scale || "");
    return stages.length >= 2 ? `${stages[0]} - ${stages[stages.length - 1]}` : item.scale;
  }
  return String(item || "");
}

function scaleValue(item, class12) {
  if (item && typeof item === "object") return class12 ? item.grade : item.scale || "";
  return String(item || "");
}

export default function Methodology2M1Calculation() {
  const [empId, setEmpId] = useState("");
  const [employeeName, setEmployeeName] = useState("");
  const [loading, setLoading] = useState(false);
  const [separationDate, setSeparationDate] = useState("");
  const [category, setCategory] = useState("3");
  const [scale, setScale] = useState("");
  const [lastPay, setLastPay] = useState("");
  const [equivPay, setEquivPay] = useState("");
  const [scaleRevision, setScaleRevision] = useState("");
  const [scaleOptions, setScaleOptions] = useState([]);
  const [payStages, setPayStages] = useState([]);
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const isClass12 = category === "1" || category === "2";
  const needsScale34 =
    !isClass12 &&
    (scaleRevision === CPI_1030_REVISION || PRE_1988_REVISIONS.includes(scaleRevision));
  const showScale = isClass12 || needsScale34;

  useEffect(() => {
    setResult(null);
    setError("");
    if (!separationDate) {
      setScaleRevision("");
      return;
    }
    API.get(`methodology1/get-scale-type/?retirement_date=${separationDate}`)
      .then((res) => setScaleRevision(res.data?.scale_revision || ""))
      .catch(() => setScaleRevision(""));
  }, [separationDate]);

  useEffect(() => {
    if (!separationDate || !showScale) {
      setScaleOptions([]);
      return;
    }
    const url = isClass12
      ? `methodology2/get-scales-class12/?separation_date=${separationDate}`
      : `methodology1/get-scales/?retirement_date=${separationDate}`;
    API.get(url)
      .then((res) => setScaleOptions(res.data || []))
      .catch(() => setScaleOptions([]));
  }, [separationDate, showScale, isClass12]);

  useEffect(() => {
    if (!scale || !separationDate) {
      setPayStages([]);
      return;
    }
    const url = isClass12
      ? `methodology2/get-pay-stages-class12/?separation_date=${separationDate}&scale=${encodeURIComponent(scale)}`
      : `methodology1/get-pay-stages/?scale=${encodeURIComponent(scale)}&retirement_date=${separationDate}`;
    API.get(url)
      .then((res) => setPayStages(res.data || []))
      .catch(() => setPayStages([]));
  }, [scale, separationDate, isClass12]);

  const loadEmployee = async () => {
    const code = empId.trim();
    if (!code) return;
    setLoading(true);
    setError("");
    setResult(null);
    try {
      const { data } = await API.get(`methodology1/employee/${code}/`);
      setEmployeeName(data.name || "");
      setSeparationDate(data.separation_date || "");
      if (data.category) setCategory(String(data.category));
      setScale(data.scale || "");
      setLastPay(data.last_pay != null ? String(data.last_pay) : "");
    } catch (err) {
      setEmployeeName("");
      setError(err.response?.data?.error || "Could not load employee.");
    } finally {
      setLoading(false);
    }
  };

  const calculate = async () => {
    setBusy(true);
    setError("");
    setResult(null);
    try {
      const { data } = await API.post("methodology1/m1-calculation/", {
        separation_date: separationDate,
        category,
        pay: lastPay || null,
        scale: showScale ? scale || null : null,
        equiv_pay_at_base_cpi: equivPay || null,
      });
      setResult(data);
    } catch (err) {
      setError(err.response?.data?.error || "Calculation failed. Check the inputs.");
    } finally {
      setBusy(false);
    }
  };

  const canCalculate =
    separationDate && (Number(lastPay) > 0 || Number(equivPay) > 0) && (!isClass12 || scale);

  return (
    <div className="container-fluid mt-3 px-2 px-md-3">
      <div className="card shadow">
        <div className="card-header bg-primary text-white">
          <h5 className="mb-0">M1 calculation — Employee pension &amp; Family pension</h5>
        </div>
        <div className="card-body smpk-form">
          <div className="row g-2 mb-3">
            <div className="col-12 col-md-5">
              <label className="form-label small mb-1">Employee code (optional)</label>
              <div className="input-group input-group-sm">
                <input
                  className="form-control"
                  value={empId}
                  onChange={(e) => setEmpId(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && loadEmployee()}
                  placeholder="Enter emp code and press Enter"
                />
                <button className="btn btn-outline-primary" onClick={loadEmployee} disabled={loading || !empId.trim()}>
                  {loading ? "Loading..." : "Load"}
                </button>
              </div>
              {employeeName ? <div className="form-text">{employeeName}</div> : null}
            </div>
          </div>

          <div className="row g-2">
            <div className="col-6 col-md-2">
              <label className="form-label small mb-1">Separation date</label>
              <input
                type="date"
                className="form-control form-control-sm"
                value={separationDate}
                onChange={(e) => {
                  setSeparationDate(e.target.value);
                  setScale("");
                }}
              />
            </div>
            <div className="col-6 col-md-1">
              <label className="form-label small mb-1">Class</label>
              <select
                className="form-select form-select-sm"
                value={category}
                onChange={(e) => {
                  setCategory(e.target.value);
                  setScale("");
                  setResult(null);
                }}
              >
                {["1", "2", "3", "4"].map((c) => (
                  <option key={c} value={c}>{c}</option>
                ))}
              </select>
            </div>
            {showScale ? (
              <div className="col-12 col-md-3">
                <label className="form-label small mb-1">
                  {isClass12 ? "Scale (executive grade)" : needsScale34 && scaleRevision === CPI_1030_REVISION ? "Scale (1030 CPI)" : "Scale (pre-1988)"}
                </label>
                <select
                  className="form-select form-select-sm"
                  value={scale}
                  onChange={(e) => setScale(e.target.value)}
                  disabled={!separationDate}
                >
                  <option value="">{separationDate ? "Select scale" : "Enter separation date first"}</option>
                  {scaleOptions.map((item, i) => (
                    <option key={i} value={scaleValue(item, isClass12)}>{scaleLabel(item)}</option>
                  ))}
                </select>
              </div>
            ) : null}
            <div className="col-6 col-md-2">
              <label className="form-label small mb-1">Last pay</label>
              <input
                type="number"
                min="1"
                className="form-control form-control-sm"
                list="m1calc-pay-stages"
                value={lastPay}
                onChange={(e) => setLastPay(e.target.value)}
              />
              <datalist id="m1calc-pay-stages">
                {payStages.map((p) => (
                  <option key={p} value={p} />
                ))}
              </datalist>
            </div>
            {!isClass12 ? (
              <div className="col-6 col-md-2">
                <label className="form-label small mb-1">Base CPI pay (if scale not matched)</label>
                <input
                  type="number"
                  min="1"
                  className="form-control form-control-sm"
                  value={equivPay}
                  onChange={(e) => setEquivPay(e.target.value)}
                />
              </div>
            ) : null}
            <div className="col-12 col-md-2 d-flex align-items-end">
              <button className="btn btn-primary btn-sm w-100" onClick={calculate} disabled={!canCalculate || busy}>
                {busy ? "Calculating..." : "Calculate"}
              </button>
            </div>
          </div>
          {scaleRevision ? (
            <div className="form-text mt-2">Scale at separation: {scaleRevision}</div>
          ) : null}
          {error ? <div className="alert alert-danger py-2 small mt-3 mb-0">{error}</div> : null}
        </div>
      </div>

      {result ? (
        <div className="card shadow-sm mt-3">
          <div className="card-body">
            <h6 className="text-primary">Result</h6>
            <div className="table-responsive">
              <table className="table table-sm table-bordered align-middle text-center mb-2">
                <thead className="table-light">
                  <tr>
                    <th>CPI</th>
                    <th>Notional (full pay chain)</th>
                    <th>Employee pension (50%)</th>
                    <th>Family pension (30%)</th>
                  </tr>
                </thead>
                <tbody>
                  <tr>
                    <td>2017 (277 CPI)</td>
                    <td>{money(result.notional_277)}</td>
                    <td className="fw-semibold">{money(result.EP_277_cpi)}</td>
                    <td className="fw-semibold">{money(result.FP_277_cpi)}</td>
                  </tr>
                  <tr>
                    <td>2022 (359 CPI)</td>
                    <td>{money(result.notional_359)}</td>
                    <td className="fw-semibold">{money(result.EP_359_cpi)}</td>
                    <td className="fw-semibold">{money(result.FP_359_cpi)}</td>
                  </tr>
                </tbody>
              </table>
            </div>
            <div className="small text-muted mb-3">{result.note}</div>

            {result.steps?.length ? (
              <>
                <h6 className="text-primary">Working</h6>
                <div className="table-responsive">
                  <table className="table table-sm table-bordered align-middle mb-0">
                    <thead className="table-light">
                      <tr>
                        <th>Stage</th>
                        {result.category_group === "3/4" ? (
                          <>
                            <th className="text-end">Pay</th>
                            <th className="text-end">DA</th>
                            <th className="text-end">Fitment</th>
                          </>
                        ) : null}
                        <th className="text-end">{result.category_group === "3/4" ? "Notional" : "Amount"}</th>
                      </tr>
                    </thead>
                    <tbody>
                      {result.steps.map((s, i) => (
                        <tr key={i}>
                          <td>{s.stage}</td>
                          {result.category_group === "3/4" ? (
                            <>
                              <td className="text-end">{money(s.pay)}</td>
                              <td className="text-end">{money(s.da)}</td>
                              <td className="text-end">{money(s.fitment)}</td>
                            </>
                          ) : null}
                          <td className="text-end">{money(s.notional)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </>
            ) : null}
          </div>
        </div>
      ) : null}
    </div>
  );
}
