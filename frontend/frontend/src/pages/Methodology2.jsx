import { useCallback, useEffect, useRef, useState } from "react";
import API from "../services/Api";
import RevisionCalculationCards from "../components/RevisionCalculationCards";
import MethodologyClass12Result from "../components/MethodologyClass12Result";
import Methodology2PensionSummary from "../components/Methodology2PensionSummary";
import SmpkDataTable from "../components/DataTable/SmpkDataTable";

export default function Methodology2() {
  const [empId, setEmpId] = useState("");
  const [employeeName, setEmployeeName] = useState("");
  const [loadingEmployee, setLoadingEmployee] = useState(false);
  const skipCategoryResetRef = useRef(false);

  const [bulkFile, setBulkFile] = useState(null);
  const [bulkBusy, setBulkBusy] = useState(false);
  const [bulkSummary, setBulkSummary] = useState(null);
  const [bulkError, setBulkError] = useState("");

  const [retirementDate, setRetirementDate] = useState("");
  const [scale, setScale] = useState("");
  const [lastPay, setLastPay] = useState("");
  const [sda, setSda] = useState("");
  const [sdaOptions, setSdaOptions] = useState([]);
  const [category, setCategory] = useState("3");
  const [payStages, setPayStages] = useState([]);
  const [equivalentScales, setEquivalentScales] = useState(null);
  const [calculationRows, setCalculationRows] = useState([]);
  const [pensionSummary, setPensionSummary] = useState(null);
  const [isStageBased, setIsStageBased] = useState(true);
  const [startRevision, setStartRevision] = useState("");
  const [scales, setScales] = useState([]);
  const [class12Result, setClass12Result] = useState(null);
  const [printMaster, setPrintMaster] = useState(null);

  const isClass12 = category === "1" || category === "2";
  const isCategory34 = category === "3" || category === "4";

  const getScaleOptionValue = (item) =>
    item && typeof item === "object" ? item.grade : item;

  const getScaleOptionLabel = (item) => {
    if (item && typeof item === "object") {
      return item.label || item.pay_band || item.scale || item.grade;
    }
    return item;
  };

  const runCalculation = useCallback(
    async (date, scaleValue, pay, sdaValue, categoryValue) => {
      if (!date || !scaleValue || !pay) return;

      try {
        const res = await API.post("methodology2/calculate-revision/", {
          retirement_date: date,
          scale: scaleValue,
          last_pay: pay,
          sda: sdaValue || 0,
          category: categoryValue,
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
    },
    []
  );

  const runClass12Calculation = useCallback(async (date, grade, pay) => {
    if (!date || !grade || !pay) return;

    try {
      const res = await API.post("methodology2/calculate-class12/", {
        separation_date: date,
        scale: grade,
        last_pay: pay,
      });
      setClass12Result(res.data);
    } catch (err) {
      console.error(err);
      alert(err.response?.data?.error || "Calculation failed. Check inputs.");
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
    setClass12Result(null);
    setEquivalentScales(null);

    try {
      const res = await API.get(`methodology2/employee/${trimmed}/`);
      const data = res.data;

      const empCategory = data.category || category;
      if (data.category && String(data.category) !== String(category)) {
        const nextIs12 = data.category === "1" || data.category === "2";
        const curIs12 = category === "1" || category === "2";
        if (nextIs12 !== curIs12) {
          skipCategoryResetRef.current = true;
        }
        setCategory(String(data.category));
      }

      setEmployeeName(data.name || "");
      setEmpId(data.emp_id);
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
        category: empCategory,
        pensioner_name: data.pensioner_name || "",
        is_employee_pension: data.is_employee_pension || false,
        m1_family_pension_277: data.m1_family_pension_277 ?? null,
        m1_family_pension_359: data.m1_family_pension_359 ?? null,
      });

      const sepDate = data.separation_date;
      const scaleValue = data.scale;
      const pay = String(data.last_pay);

      const isEmpClass12 = empCategory === "1" || empCategory === "2";

      if (isEmpClass12) {
        const scalesRes = await API.get(
          `methodology2/get-scales-class12/?separation_date=${sepDate}`
        );
        setScales(scalesRes.data || []);
        setIsStageBased(true);
        setStartRevision("");
        setRetirementDate(sepDate);
        // Class 1/2 uses executive grade (E-n); mirror scale may be a pay band.
        // Keep autofilled last pay; leave scale for user to pick if not a grade.
        const looksLikeGrade = /^E-?\d+/i.test(String(scaleValue || "").trim());
        setScale(looksLikeGrade ? scaleValue : "");
        setLastPay(pay);
      } else {
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
      }
    } catch (err) {
      console.error(err);
      const msg =
        err.response?.data?.error ||
        err.response?.data?.message ||
        "Could not load employee.";
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
    if (isClass12) {
      if (!retirementDate) {
        setScales([]);
        return;
      }
      API.get(
        `methodology2/get-scales-class12/?separation_date=${retirementDate}`
      )
        .then((res) => setScales(res.data || []))
        .catch(console.error);
      setIsStageBased(true);
      return;
    }

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
  }, [retirementDate, isClass12]);

  useEffect(() => {
    API.get("methodology2/get-special-da-options/")
      .then((res) => setSdaOptions(res.data || []))
      .catch(console.error);
  }, []);

  useEffect(() => {
    if (isClass12) {
      if (!retirementDate || !scale) {
        setPayStages([]);
        return;
      }
      API.get(
        `methodology2/get-pay-stages-class12/?separation_date=${retirementDate}&scale=${encodeURIComponent(scale)}`
      )
        .then((res) => setPayStages(res.data || []))
        .catch(console.error);
      return;
    }
    loadPayStages(scale);
  }, [scale, retirementDate, isClass12, loadPayStages]);

  useEffect(() => {
    if (isClass12) {
      setEquivalentScales(null);
      return;
    }
    loadEquivalentScales(retirementDate, scale);
  }, [retirementDate, scale, isClass12, loadEquivalentScales]);

  const resetScaleAndPay = useCallback(() => {
    setScale("");
    setLastPay("");
    setClass12Result(null);
    setCalculationRows([]);
    setPensionSummary(null);
    setEquivalentScales(null);
    setPayStages([]);
  }, []);

  // Only reset when category type changes — not when emp load sets retirementDate
  // (that used to wipe autofilled scale / last pay).
  useEffect(() => {
    if (skipCategoryResetRef.current) {
      skipCategoryResetRef.current = false;
      return;
    }
    resetScaleAndPay();
  }, [isClass12, resetScaleAndPay]);

  useEffect(() => {
    if (isClass12) {
      if (retirementDate && scale && lastPay) {
        runClass12Calculation(retirementDate, scale, lastPay);
      } else {
        setClass12Result(null);
      }
      return;
    }

    if (retirementDate && scale && lastPay) {
      const sdaValue = isCategory34 ? sda : 0;
      runCalculation(retirementDate, scale, lastPay, sdaValue, category);
    }
  }, [
    retirementDate,
    scale,
    lastPay,
    sda,
    category,
    isCategory34,
    isClass12,
    runCalculation,
    runClass12Calculation,
  ]);

  const runBulkUpload = async (e) => {
    e.preventDefault();
    setBulkError("");
    setBulkSummary(null);
    if (!bulkFile) {
      setBulkError("Choose an Excel file with column EMP_CD.");
      return;
    }
    const form = new FormData();
    form.append("file", bulkFile);
    setBulkBusy(true);
    try {
      const { data } = await API.post("methodology2/bulk/", form, {
        headers: { "Content-Type": "multipart/form-data" },
        timeout: 0,
      });
      setBulkSummary(data);
    } catch (err) {
      setBulkError(
        String(
          err?.response?.data?.error || err?.message || "Bulk run failed"
        )
      );
    } finally {
      setBulkBusy(false);
    }
  };

  return (
    <div className="container-fluid mt-3 mt-md-4 px-2 px-md-3 methodology-page">
      <div className="row justify-content-center mb-3">
        <div className="col-12 col-xl-10">
          <div className="card shadow">
            <div className="card-header bg-dark text-white">
              <h5 className="mb-0">Bulk upload (Class 1/2 &amp; 3/4)</h5>
            </div>
            <div className="card-body">
              <p className="text-muted small mb-3">
                Upload Excel with column <code>EMP_CD</code> (optional{" "}
                <code>name</code>, <code>roll_no</code>). Each employee is
                calculated, consolidation saved, and PDF written to Desktop{" "}
                <code>M2_YYYY-MM-DD</code> as <code>case_no.pdf</code>.
              </p>
              <form onSubmit={runBulkUpload} className="row g-2 align-items-end">
                <div className="col-12 col-md-8">
                  <label className="form-label">Excel file</label>
                  <input
                    type="file"
                    accept=".xlsx,.xls"
                    className="form-control"
                    onChange={(ev) => setBulkFile(ev.target.files?.[0] || null)}
                  />
                </div>
                <div className="col-12 col-md-4">
                  <button
                    type="submit"
                    className="btn btn-primary w-100"
                    disabled={bulkBusy}
                  >
                    {bulkBusy ? "Running…" : "Run bulk"}
                  </button>
                </div>
              </form>
              {bulkError ? (
                <div className="alert alert-danger mt-3 mb-0">{bulkError}</div>
              ) : null}
              {bulkSummary ? (
                <div className="mt-3">
                  <p className="mb-1">
                    <strong>Folder:</strong> {bulkSummary.output_dir}
                  </p>
                  <p className="mb-2 small">
                    total {bulkSummary.total} · ok {bulkSummary.ok} · skipped{" "}
                    {bulkSummary.skipped} · failed {bulkSummary.failed}
                  </p>
                  <div className="table-responsive">
                    <table className="table table-sm table-bordered mb-0">
                      <thead>
                        <tr>
                          <th>EMP_CD</th>
                          <th>case_no</th>
                          <th>class</th>
                          <th>status</th>
                          <th>reason</th>
                        </tr>
                      </thead>
                      <tbody>
                        {(bulkSummary.results || []).map((r) => (
                          <tr key={r.emp_cd}>
                            <td>{r.emp_cd}</td>
                            <td>{r.case_no || ""}</td>
                            <td>{r.category || ""}</td>
                            <td>{r.status}</td>
                            <td>
                              {r.reason ||
                                (r.pdf ? "pdf" : r.html ? "html" : "")}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              ) : null}
            </div>
          </div>
        </div>
      </div>

      <div className="row justify-content-center">
        <div className="col-12 col-xl-10">
          <div className="card shadow">
            <div className="card-header bg-primary text-white">
              <h4 className="mb-0">Methodology 2</h4>
            </div>
            <div className="card-body smpk-form">
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

              <div className="row g-3">
                <div className="col-12 col-md-6 col-lg-3">
                  <label className="form-label">Retirement / Separation Date</label>
                  <input
                    type="date"
                    className="form-control"
                    value={retirementDate}
                    onChange={(e) => {
                      setRetirementDate(e.target.value);
                      resetScaleAndPay();
                    }}
                  />
                </div>

                <div className="col-12 col-md-6 col-lg-3">
                  <label className="form-label">Category</label>
                  <select
                    className="form-select"
                    value={category}
                    onChange={(e) => setCategory(e.target.value)}
                  >
                    <option value="1">1</option>
                    <option value="2">2</option>
                    <option value="3">3</option>
                    <option value="4">4</option>
                  </select>
                </div>

                <div className="col-12 col-md-6 col-lg-3">
                  <label className="form-label">Scale</label>
                  <select
                    className="form-select"
                    value={scale}
                    onChange={(e) => {
                      setScale(e.target.value);
                      setLastPay("");
                      setCalculationRows([]);
                      setPensionSummary(null);
                      setClass12Result(null);
                    }}
                    disabled={!retirementDate}
                  >
                    <option value="">
                      {retirementDate ? "Select Scale" : "Enter separation date first"}
                    </option>
                    {scales.map((item, index) => (
                      <option
                        key={index}
                        value={getScaleOptionValue(item)}
                      >
                        {getScaleOptionLabel(item)}
                      </option>
                    ))}
                  </select>
                </div>

                <div className="col-12 col-md-6 col-lg-3">
                  <label className="form-label">Last Pay</label>
                  <select
                    className="form-select"
                    value={lastPay}
                    onChange={(e) => setLastPay(e.target.value)}
                    disabled={!scale}
                  >
                    <option value="">Select Last Pay</option>
                    {payStages.map((item, index) => (
                      <option key={index} value={item}>
                        {item}
                      </option>
                    ))}
                  </select>
                </div>

                {isCategory34 && (
                  <div className="col-12 col-md-6 col-lg-3">
                    <label className="form-label">S.D.A (Revision Order)</label>
                    <select
                      className="form-select"
                      value={sda}
                      onChange={(e) => setSda(e.target.value)}
                    >
                      <option value="">Select S.D.A</option>
                      {sdaOptions.map((item, index) => (
                        <option key={index} value={item}>
                          {item}
                        </option>
                      ))}
                    </select>
                  </div>
                )}
              </div>

              {!isClass12 && !isStageBased && (
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
          <div className="col-12 col-xl-10">
            <div className="card shadow">
              <div className="card-header bg-success text-white">
                <h5 className="mb-0">Equivalent Scales</h5>
              </div>
              <div className="card-body">
                <SmpkDataTable
                  tableKey={Object.keys(equivalentScales || {}).join("-")}
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
                    {Object.entries(equivalentScales).map(([key, value]) =>
                      key !== "Scale" ? (
                        <tr key={key}>
                          <td>{key}</td>
                          <td>{value}</td>
                        </tr>
                      ) : null
                    )}
                  </tbody>
                </SmpkDataTable>
              </div>
            </div>
          </div>
        </div>
      )}

      {isClass12 && (
        <MethodologyClass12Result
          category={category}
          class12Result={class12Result}
        />
      )}

      {isClass12 && class12Result && (
        <Methodology2PensionSummary
          class12Result={class12Result}
          retirementDate={retirementDate}
          scale={scale}
          lastPay={lastPay}
          empId={empId}
          employeeName={employeeName}
          category={category}
          startRevision={class12Result.start_revision || startRevision}
          printMaster={printMaster}
        />
      )}

      {!isClass12 && (
        <Methodology2PensionSummary
          pensionSummary={pensionSummary}
          retirementDate={retirementDate}
          scale={scale}
          lastPay={lastPay}
          empId={empId}
          employeeName={employeeName}
          category={category}
          startRevision={startRevision}
          calculationRows={calculationRows}
          equivalentScales={equivalentScales}
          printMaster={printMaster}
        />
      )}

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
