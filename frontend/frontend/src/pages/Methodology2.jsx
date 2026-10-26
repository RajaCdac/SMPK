import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import API from "../services/Api";
import RevisionCalculationCards from "../components/RevisionCalculationCards";
import Methodology2PensionSummary from "../components/Methodology2PensionSummary";
import HeaderFieldPrompt, {
  useConsolidationHeaderPrompt,
} from "../components/HeaderFieldPrompt";
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
  const [reportBusy, setReportBusy] = useState(false);
  const [reportError, setReportError] = useState("");
  const [reportFrom, setReportFrom] = useState("");
  const [reportTo, setReportTo] = useState("");

  const [retirementDate, setRetirementDate] = useState("");
  const [scale, setScale] = useState("");
  const [lastPay, setLastPay] = useState("");
  const [stagnationAmount, setStagnationAmount] = useState("");
  const [npaAmount, setNpaAmount] = useState("");
  const [doctorPay, setDoctorPay] = useState("");
  const [isDoctor, setIsDoctor] = useState(false);
  const [includeBunching, setIncludeBunching] = useState(false);
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

  /** Doctor: Stagnation/NPA is NPA added to the basic, unless salary already included it. */
  const npaFoldedIn =
    isDoctor && doctorPay !== "" && String(lastPay) === String(doctorPay);
  const effectivePay = (() => {
    const base = Number(lastPay);
    if (!lastPay || Number.isNaN(base)) return "";
    if (isDoctor) {
      if (npaFoldedIn) return String(base);
      const npa = Number(npaAmount);
      return String(base + (Number.isNaN(npa) ? 0 : npa));
    }
    const stag = Number(stagnationAmount);
    const stagVal = Number.isNaN(stag) ? 0 : stag;
    return String(base + stagVal);
  })();
  const headerLastPay =
    isDoctor && !npaFoldedIn && effectivePay ? effectivePay : lastPay;

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
          tqs_yr: printMaster?.tqs_yr,
          tqs_month: printMaster?.tqs_month,
          tqs_days: printMaster?.tqs_days,
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
    [printMaster]
  );

  const runClass12Calculation = useCallback(async (date, grade, pay) => {
    if (!date || !grade || !pay) return;

    try {
      const res = await API.post("methodology2/calculate-class12/", {
        separation_date: date,
        scale: grade,
        last_pay: pay,
        tqs_yr: printMaster?.tqs_yr,
        tqs_month: printMaster?.tqs_month,
        tqs_days: printMaster?.tqs_days,
      });
      setClass12Result(res.data);
    } catch (err) {
      console.error(err);
      alert(err.response?.data?.error || "Calculation failed. Check inputs.");
    }
  }, [printMaster]);

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
    setStagnationAmount("");
    setNpaAmount("");
    setDoctorPay("");
    setIsDoctor(false);
    setIncludeBunching(false);

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
        retirement_type: data.retirement_type || "",
        date_of_birth: data.date_of_birth || data.dob || null,
        date_of_death: data.date_of_death || null,
        family_pensioner_dob: data.family_pensioner_dob || null,
        double_fpension_upto: data.double_fpension_upto || null,
        enhanced_family_pension: !!data.enhanced_family_pension,
        category: empCategory,
        pensioner_name: data.pensioner_name || "",
        is_employee_pension: data.is_employee_pension || false,
        m1_family_pension_277: data.m1_family_pension_277 ?? null,
        m1_family_pension_359: data.m1_family_pension_359 ?? null,
        m1_bunching: data.m1_bunching || null,
      });

      const sepDate = data.separation_date;
      const scaleValue = data.scale || "";
      const pay =
        data.last_pay != null && data.last_pay !== ""
          ? String(data.last_pay)
          : "";
      const doctor =
        Number(data.doctor_flg) === 1 ||
        (data.npa_amount != null && data.npa_amount !== "");
      setIsDoctor(doctor);
      if (data.npa_amount != null && data.npa_amount !== "") {
        setNpaAmount(String(data.npa_amount));
        setDoctorPay(pay);
        setStagnationAmount("");
      } else {
        setNpaAmount("");
        setDoctorPay("");
      }
      if (data.warning) {
        alert(data.warning);
      }
      if (!sepDate || !scaleValue) {
        if (sepDate) setRetirementDate(sepDate);
        setScale("");
        setLastPay("");
        return;
      }

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
    setStagnationAmount("");
    setNpaAmount("");
    setDoctorPay("");
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
      if (retirementDate && scale && effectivePay) {
        runClass12Calculation(retirementDate, scale, effectivePay);
      } else {
        setClass12Result(null);
      }
      return;
    }

    if (retirementDate && scale && effectivePay) {
      const sdaValue = isCategory34 ? sda : 0;
      runCalculation(retirementDate, scale, effectivePay, sdaValue, category);
    }
  }, [
    retirementDate,
    scale,
    effectivePay,
    sda,
    category,
    isCategory34,
    isClass12,
    runCalculation,
    runClass12Calculation,
  ]);

  const headerAmounts = useMemo(() => {
    if (isClass12) {
      return {
        ready: !!class12Result,
        category,
        m2_277: class12Result?.family_pension ?? null,
        m2_359: null,
      };
    }
    return {
      ready: !!pensionSummary,
      category,
      m2_277: pensionSummary?.family_pension_277_cpi ?? null,
      m2_359: pensionSummary?.family_pension_359_cpi ?? null,
    };
  }, [isClass12, class12Result, pensionSummary, category]);

  const { prompt: headerPrompt, setPrompt: setHeaderPrompt, submitHeaderValue } =
    useConsolidationHeaderPrompt({
      active:
        !loadingEmployee &&
        !!printMaster?.emp_cd &&
        !!scale &&
        !!String(lastPay || "").trim(),
      master: printMaster,
      amounts: headerAmounts,
      onFilled: (patch) => {
        setPrintMaster((prev) => ({ ...(prev || {}), ...patch }));
        if (patch.name) setEmployeeName(patch.name);
      },
    });

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

  const downloadReport = async () => {
    setReportError("");
    if (!reportFrom || !reportTo) {
      setReportError(
        "Select Updated From and Updated To dates before downloading the Excel report."
      );
      return;
    }
    if (reportFrom > reportTo) {
      setReportError("Updated From cannot be after Updated To.");
      return;
    }
    setReportBusy(true);
    try {
      const res = await API.get("methodology2/report/", {
        params: { from_date: reportFrom, to_date: reportTo },
        responseType: "blob",
        timeout: 0,
      });
      const blob = new Blob([res.data], {
        type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
      });
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      const cd = res.headers["content-disposition"] || "";
      const match = cd.match(/filename="?([^"]+)"?/);
      link.download = match
        ? match[1]
        : `M2_consolidation_report_${reportFrom}_${reportTo}.xlsx`;
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
    } catch (err) {
      if (err?.response?.data instanceof Blob) {
        try {
          const text = await err.response.data.text();
          const json = JSON.parse(text);
          setReportError(json.error || "Report download failed");
        } catch {
          setReportError("Report download failed");
        }
      } else {
        setReportError(
          String(
            err?.response?.data?.error ||
              err?.message ||
              "Report download failed"
          )
        );
      }
    } finally {
      setReportBusy(false);
    }
  };

  return (
    <div className="container-fluid mt-3 mt-md-4 px-2 px-md-3 methodology-page">
      <div className="row justify-content-center mb-3">
        <div className="col-12 col-xl-10">
          <div className="card shadow">
            <div className="card-header bg-dark text-white d-flex flex-wrap justify-content-between align-items-center gap-2">
              <h5 className="mb-0">Bulk upload (Class 1/2 &amp; 3/4)</h5>
              <div className="d-flex flex-wrap align-items-end gap-2">
                <div>
                  <label className="form-label text-white-50 small mb-1">
                    Updated from
                  </label>
                  <input
                    type="date"
                    className="form-control form-control-sm"
                    value={reportFrom}
                    onChange={(e) => setReportFrom(e.target.value)}
                    disabled={reportBusy || bulkBusy}
                  />
                </div>
                <div>
                  <label className="form-label text-white-50 small mb-1">
                    Updated to
                  </label>
                  <input
                    type="date"
                    className="form-control form-control-sm"
                    value={reportTo}
                    onChange={(e) => setReportTo(e.target.value)}
                    disabled={reportBusy || bulkBusy}
                  />
                </div>
                <button
                  type="button"
                  className="btn btn-sm btn-success"
                  onClick={downloadReport}
                  disabled={reportBusy || bulkBusy}
                  title="Export rows by updated_at date range"
                >
                  {reportBusy ? "Preparing…" : "Report (Excel)"}
                </button>
              </div>
            </div>
            <div className="card-body">
              <p className="text-muted small mb-3">
                Upload Excel with column <code>EMP_CD</code> (optional{" "}
                <code>name</code>, <code>roll_no</code>). Each employee is
                calculated, consolidation saved, and PDF written to Desktop{" "}
                <code>M2_YYYY-MM-DD</code> as <code>case_no.pdf</code>.
                Click <strong>Report (Excel)</strong> with an{" "}
                <strong>Updated from / to</strong> range to export only rows
                whose <code>updated_at</code> falls in that period (not the full
                table).
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
              {reportError ? (
                <div className="alert alert-danger mt-3 mb-0">{reportError}</div>
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
                  {(bulkSummary.results || []).filter(
                    (r) => r.status === "skipped"
                  ).length > 0 ? (
                    <>
                      <p className="mb-2 small fw-semibold">
                        Skipped employees (with reason)
                      </p>
                      <div className="table-responsive">
                        <table className="table table-sm table-bordered mb-0">
                          <thead>
                            <tr>
                              <th>EMP_CD</th>
                              <th>case_no</th>
                              <th>class</th>
                              <th>reason</th>
                            </tr>
                          </thead>
                          <tbody>
                            {(bulkSummary.results || [])
                              .filter((r) => r.status === "skipped")
                              .map((r) => (
                                <tr key={r.emp_cd}>
                                  <td>{r.emp_cd}</td>
                                  <td>{r.case_no || ""}</td>
                                  <td>{r.category || ""}</td>
                                  <td>{r.reason || "—"}</td>
                                </tr>
                              ))}
                          </tbody>
                        </table>
                      </div>
                    </>
                  ) : (
                    <p className="mb-0 small text-muted">
                      No employees were skipped.
                    </p>
                  )}
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
                  <small className="text-muted d-block mt-1">
                    After employee, scale and last pay are entered, any header
                    value still missing from the database is asked one field at
                    a time. Stagnation/NPA stays optional. For a doctor, that
                    amount is NPA.
                  </small>
                </div>
              </div>

              <div className="text-center text-muted small mb-3">— OR —</div>

              <div className="row g-2 g-lg-3 align-items-end">
                <div className="col-6 col-md-4 col-xl-2">
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

                <div className="col-6 col-md-4 col-xl-2">
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

                <div className="col-6 col-md-4 col-xl-2">
                  <label className="form-label">Scale</label>
                  <select
                    className="form-select"
                    value={scale}
                    onChange={(e) => {
                      setScale(e.target.value);
                      setLastPay("");
                      setStagnationAmount("");
                      setNpaAmount("");
                      setDoctorPay("");
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

                <div className="col-6 col-md-4 col-xl-2">
                  <label className="form-label">Last Pay</label>
                  <select
                    className="form-select"
                    value={lastPay}
                    onChange={(e) => {
                      const next = e.target.value;
                      setLastPay(next);
                      if (!isDoctor && String(next) !== String(doctorPay)) {
                        setNpaAmount("");
                      }
                    }}
                    disabled={!scale}
                  >
                    <option value="">Select Last Pay</option>
                    {(payStages.some((item) => String(item) === String(lastPay))
                      ? payStages
                      : lastPay
                        ? [...payStages, lastPay]
                        : payStages
                    ).map((item, index) => (
                      <option key={`${item}-${index}`} value={item}>
                        {isDoctor && npaAmount && String(item) === String(lastPay)
                          ? `${item} (npa ${npaAmount})`
                          : item}
                      </option>
                    ))}
                  </select>
                </div>

                <div className="col-6 col-md-4 col-xl-2">
                  <label className="form-label">Stagnation/NPA</label>
                  <input
                    type="number"
                    className="form-control"
                    min="0"
                    step="1"
                    placeholder={isDoctor ? "NPA" : "0"}
                    value={isDoctor ? npaAmount : stagnationAmount}
                    onChange={(e) => {
                      if (isDoctor) {
                        setNpaAmount(e.target.value);
                        setStagnationAmount("");
                      } else {
                        setStagnationAmount(e.target.value);
                        setNpaAmount("");
                        setDoctorPay("");
                      }
                    }}
                    disabled={!scale}
                  />
                </div>

                <div className="col-6 col-md-4 col-xl-2">
                  <label className="form-label">S.D.A (Revision Order)</label>
                  <select
                    className="form-select"
                    value={isCategory34 ? sda : ""}
                    onChange={(e) => setSda(e.target.value)}
                    disabled={!isCategory34}
                  >
                    <option value="">
                      {isCategory34 ? "Select S.D.A" : "N/A"}
                    </option>
                    {isCategory34 &&
                      sdaOptions.map((item, index) => (
                        <option key={index} value={item}>
                          {item}
                        </option>
                      ))}
                  </select>
                </div>
              </div>

              {!isClass12 && !isStageBased && (
                <p className="small text-muted mt-2 mb-0">
                  Scale type for this date is not stage-based.
                </p>
              )}
              {isDoctor && printMaster?.m1_bunching?.bunch_basic ? (
                <div className="form-check mt-3">
                  <input
                    id="m2-include-bunching"
                    className="form-check-input"
                    type="checkbox"
                    checked={includeBunching}
                    onChange={(e) => setIncludeBunching(e.target.checked)}
                  />
                  <label className="form-check-label" htmlFor="m2-include-bunching">
                    Include bunching ({printMaster.m1_bunching.bunch_basic})
                  </label>
                  <small className="text-muted d-block">
                    Leave this off to keep M1@277 without the LIC bunch. Tick it
                    to add the bunch for this doctor.
                  </small>
                </div>
              ) : null}
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

      {isClass12 && class12Result && (
        <Methodology2PensionSummary
          class12Result={class12Result}
          retirementDate={retirementDate}
          scale={scale}
          lastPay={headerLastPay}
          stagnationAmount={isDoctor ? "" : stagnationAmount}
          npaAmount={npaAmount}
          includeBunching={includeBunching}
          isDoctor={isDoctor}
          effectivePay={effectivePay || lastPay}
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
          lastPay={headerLastPay}
          stagnationAmount={isDoctor ? "" : stagnationAmount}
          npaAmount={npaAmount}
          includeBunching={includeBunching}
          isDoctor={isDoctor}
          effectivePay={effectivePay || lastPay}
          empId={empId}
          employeeName={employeeName}
          category={category}
          startRevision={startRevision}
          calculationRows={calculationRows}
          equivalentScales={equivalentScales}
          printMaster={printMaster}
        />
      )}

      {/*
        BLOCKED (UI only) — Revision Calculation (year-wise)
        Kept for later; consolidation print/snapshot still uses revision_blocks.
        Set SHOW_REVISION_YEARWISE_UI = true to restore the cards below.
      */}
      {false && calculationRows.length > 0 && startRevision && (
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
      {calculationRows.length > 0 && startRevision && (
        <div className="row justify-content-center mt-4 no-print">
          <div className="col-12">
            <div className="alert alert-secondary mb-0" role="status">
              <strong>Revision Calculation (year-wise) — temporarily blocked.</strong>
              <div className="small mt-1 mb-0">
                Year-wise revision cards are hidden on this consolidation screen for
                now. Calculation still runs in the background and is used for
                consolidation / print. This section is not removed and can be
                re-enabled later.
              </div>
            </div>
          </div>
        </div>
      )}
      {headerPrompt ? (
        <HeaderFieldPrompt
          prompt={headerPrompt}
          onChange={setHeaderPrompt}
          onSave={() => submitHeaderValue(false)}
          onNull={() => submitHeaderValue(true)}
        />
      ) : null}
    </div>
  );
}
