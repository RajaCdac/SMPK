import { useCallback, useEffect, useMemo, useState } from "react";
import API from "../services/Api";
import Methodology2PensionSummary from "../components/Methodology2OldAgePensionSummary";
import HeaderFieldPrompt, {
  useConsolidationHeaderPrompt,
} from "../components/HeaderFieldPrompt";

const CLASS_OPTIONS = ["1", "2", "3", "4"];

function scaleValue(item) {
  return item && typeof item === "object" ? String(item.grade || "") : String(item);
}

function scaleLabel(item) {
  if (item && typeof item === "object") {
    return item.label || item.pay_band || item.scale || item.grade;
  }
  return String(item);
}

function toNumber(value) {
  const n = Number(String(value ?? "").replace(/,/g, ""));
  return Number.isFinite(n) ? n : null;
}

/**
 * Doctor Consolidation: last pay = basic + NPA, each revised separately so the
 * revision blocks show Pay | NPA | Total. Saved to m2_doctor_consolidation.
 */
export default function Methodology2DoctorConsolidation() {
  const [empInput, setEmpInput] = useState("");
  const [empId, setEmpId] = useState("");
  const [employeeName, setEmployeeName] = useState("");
  const [loading, setLoading] = useState(false);
  const [master, setMaster] = useState(null);
  const [dateOfBirth, setDateOfBirth] = useState("");

  const [category, setCategory] = useState("");
  const [retirementDate, setRetirementDate] = useState("");
  const [scale, setScale] = useState("");
  const [scales, setScales] = useState([]);
  const [payStages, setPayStages] = useState([]);
  const [basic, setBasic] = useState("");
  const [npa, setNpa] = useState("");
  const [includeBunching, setIncludeBunching] = useState(false);

  const [result, setResult] = useState(null);
  const [calcError, setCalcError] = useState("");
  const [oldageBenefit, setOldageBenefit] = useState(null);
  const [blockedMsg, setBlockedMsg] = useState("");

  const isClass12 = category === "1" || category === "2";
  const totalPay = useMemo(() => {
    const b = toNumber(basic);
    if (b == null || b <= 0) return "";
    return String(b + (toNumber(npa) || 0));
  }, [basic, npa]);

  const loadEmployee = async () => {
    const code = empInput.trim();
    if (!code) return;
    setLoading(true);
    setResult(null);
    setCalcError("");
    setOldageBenefit(null);
    setMaster(null);
    setBlockedMsg("");
    try {
      const { data } = await API.get(`m2-doctor/employee/${code}/`);
      const cat = String(data.category || "");
      const sep = data.separation_date || "";
      setEmpId(data.emp_id || code);
      setEmployeeName(data.name || "");
      setCategory(CLASS_OPTIONS.includes(cat) ? cat : "");
      setRetirementDate(sep);
      setScale(data.scale || "");
      setBasic(data.last_basic != null ? String(data.last_basic) : "");
      setNpa(data.last_npa != null ? String(data.last_npa) : "");
      setIncludeBunching(false);
      setDateOfBirth(data.date_of_birth || data.dob || "");
      if (data.warning) alert(data.warning);
      setMaster({
        emp_cd: data.emp_id || code,
        name: data.name || "",
        case_no: data.case_no || "",
        roll_no: data.roll_no || "",
        designation: data.designation || "",
        tqs: data.tqs || "",
        tqs_yr: data.tqs_yr,
        tqs_month: data.tqs_month,
        tqs_days: data.tqs_days,
        retirement_date: sep || null,
        retirement_type: data.retirement_type || "",
        date_of_death: data.date_of_death || null,
        family_pensioner_dob: data.family_pensioner_dob || null,
        family_pensioner_name: data.pensioner_name || "",
        double_fpension_upto: data.double_fpension_upto || null,
        enhanced_family_pension: !!data.enhanced_family_pension,
        category: cat,
        pensioner_name: data.pensioner_name || "",
        is_employee_pension:
          data.is_employee_pension === false || data.date_of_death
            ? false
            : !!data.is_employee_pension,
        m1_family_pension_277: data.m1_family_pension_277 ?? null,
        m1_family_pension_359: data.m1_family_pension_359 ?? null,
        m1_bunching: data.m1_bunching || null,
        // CR 12-11-2026 (emp 46913): family (30%) M1 missing in the DB — asked.
        family_m1_missing: data.family_m1_missing || [],
        date_of_birth: data.date_of_birth || data.dob || null,
        scale: data.scale || "",
        last_pay: data.last_pay ?? "",
      });
    } catch (err) {
      console.error(err);
      const msg = err.response?.data?.error || "Could not load employee.";
      if (err.response?.data?.compulsory_retirement) {
        setBlockedMsg(`Employee ${code}: ${msg}`);
        setEmpId("");
        setEmployeeName("");
        setRetirementDate("");
        setScale("");
        setBasic("");
        setNpa("");
      } else {
        alert(msg);
      }
    } finally {
      setLoading(false);
    }
  };

  // Scale list for the class and separation date.
  useEffect(() => {
    if (!category || !retirementDate) {
      setScales([]);
      return;
    }
    const url = isClass12
      ? `m2-oldage-arrear/get-scales-class12/?separation_date=${retirementDate}`
      : `m2-oldage-arrear/get-scales/?retirement_date=${retirementDate}`;
    API.get(url)
      .then((res) => setScales(res.data || []))
      .catch(() => setScales([]));
  }, [category, retirementDate, isClass12]);

  // Pay stages for the chosen scale (suggestions; salary basic may differ).
  useEffect(() => {
    if (!scale || !retirementDate) {
      setPayStages([]);
      return;
    }
    const url = isClass12
      ? `m2-oldage-arrear/get-pay-stages-class12/?separation_date=${retirementDate}&scale=${encodeURIComponent(scale)}`
      : `m2-oldage-arrear/get-pay-stages/?scale=${encodeURIComponent(scale)}`;
    API.get(url)
      .then((res) => setPayStages(res.data || []))
      .catch(() => setPayStages([]));
  }, [scale, retirementDate, isClass12]);

  // Recalculate when the inputs change.
  useEffect(() => {
    if (!category || !retirementDate || !scale || !toNumber(basic)) {
      setResult(null);
      return undefined;
    }
    const timer = setTimeout(async () => {
      try {
        const { data } = await API.post("m2-doctor/calculate/", {
          category,
          separation_date: retirementDate,
          scale,
          basic,
          npa: npa || 0,
          tqs_yr: master?.tqs_yr,
          tqs_month: master?.tqs_month,
          tqs_days: master?.tqs_days,
          // CR 10-11-2026 (emp 45654): death in harness → TQS/10, not cut off.
          retirement_type: master?.retirement_type,
        });
        setResult(data);
        setCalcError("");
      } catch (err) {
        setResult(null);
        setCalcError(err.response?.data?.error || "Calculation failed. Check inputs.");
      }
    }, 300);
    return () => clearTimeout(timer);
  }, [category, retirementDate, scale, basic, npa, master?.tqs_yr, master?.tqs_month, master?.tqs_days, master?.retirement_type]);

  const class12Result = isClass12 ? result : null;
  const pensionSummary = !isClass12 && result ? result.pension || null : null;

  const recalculateOldAge = useCallback(async () => {
    const isFamily = master?.is_employee_pension === false;
    if (!result || (!isFamily && !dateOfBirth)) {
      setOldageBenefit(null);
      return;
    }
    const pen = pensionSummary || {
      pension_277_cpi: class12Result?.pension,
      family_pension_277_cpi: class12Result?.family_pension,
    };
    const isEmp = !isFamily;
    const m2_277 = isEmp ? pen.pension_277_cpi : pen.family_pension_277_cpi;
    const m2_359 = isEmp ? pen.pension_359_cpi : pen.family_pension_359_cpi;
    try {
      const { data } = await API.post("m2-oldage-arrear/oldage/calculate/", {
        emp_id: empId || undefined,
        dob: dateOfBirth,
        date_of_birth: dateOfBirth,
        category: category || undefined,
        is_employee_pension: isEmp,
        date_of_death: master?.date_of_death || null,
        double_fpension_upto: master?.double_fpension_upto || null,
        pensioner_name: master?.pensioner_name || null,
        family_pensioner_dob: master?.family_pensioner_dob || null,
        m2_pension_277: pen.pension_277_cpi ?? null,
        m2_pension_359: pen.pension_359_cpi ?? null,
        m2_family_pension_277: pen.family_pension_277_cpi ?? null,
        m2_family_pension_359: pen.family_pension_359_cpi ?? null,
        pension_277: m2_277 ?? null,
        pension_359: m2_359 ?? null,
        m1_pension_277: master?.m1_family_pension_277 ?? null,
        m1_pension_359: master?.m1_family_pension_359 ?? null,
      });
      setOldageBenefit(data);
    } catch (err) {
      setOldageBenefit({
        error: err.response?.data?.error || "Old-age calculation failed",
        milestones: [],
      });
    }
  }, [result, pensionSummary, class12Result, master, dateOfBirth, empId, category]);

  useEffect(() => {
    recalculateOldAge();
  }, [recalculateOldAge]);

  const headerAmounts = useMemo(
    () => ({
      ready: !!result,
      category,
      m2_277: isClass12 ? result?.family_pension ?? null : pensionSummary?.family_pension_277_cpi ?? null,
      m2_359: isClass12 ? null : pensionSummary?.family_pension_359_cpi ?? null,
    }),
    [result, category, isClass12, pensionSummary]
  );

  const {
    prompt: headerPrompt,
    setPrompt: setHeaderPrompt,
    submitHeaderValue,
    goBackHeaderValue,
  } = useConsolidationHeaderPrompt({
    active: !loading && !!master?.emp_cd && !!scale && !!toNumber(basic),
    master,
    amounts: headerAmounts,
    onFilled: async (patch) => {
      setMaster((prev) => ({ ...(prev || {}), ...patch }));
      if (patch.name) setEmployeeName(patch.name);
      if (Object.prototype.hasOwnProperty.call(patch, "date_of_birth")) {
        setDateOfBirth(patch.date_of_birth || "");
      }
    },
  });

  const printMaster = useMemo(
    () =>
      master
        ? { ...master, category, retirement_date: retirementDate || null, scale, last_pay: totalPay }
        : null,
    [master, category, retirementDate, scale, totalPay]
  );
  const hasBunch = !!master?.m1_bunching?.bunch_basic;

  return (
    <div className="container-fluid mt-3 mt-md-4 px-2 px-md-3 methodology-page">
      <div className="row justify-content-center">
        <div className="col-12 col-xl-10">
          <div className="card shadow">
            <div className="card-header bg-primary text-white">
              <h4 className="mb-0">Doctor Consolidation</h4>
            </div>
            <div className="card-body smpk-form">
              <div className="row g-3 mb-3">
                <div className="col-12 col-lg-6">
                  <label className="form-label">Employee ID</label>
                  <div className="input-group">
                    <input
                      type="text"
                      className="form-control"
                      placeholder="Enter doctor's emp code and press Enter"
                      value={empInput}
                      onChange={(e) => setEmpInput(e.target.value)}
                      onKeyDown={(e) => {
                        if (e.key === "Enter") {
                          e.preventDefault();
                          loadEmployee();
                        }
                      }}
                      disabled={loading}
                    />
                    <button
                      type="button"
                      className="btn btn-outline-primary"
                      onClick={loadEmployee}
                      disabled={loading || !empInput.trim()}
                    >
                      {loading ? "Loading..." : "Load"}
                    </button>
                  </div>
                  {blockedMsg ? (
                    <div className="alert alert-danger fw-semibold py-2 mt-2 mb-0" role="alert">
                      {blockedMsg}
                    </div>
                  ) : null}
                  {employeeName ? (
                    <small className="text-muted d-block mt-1">
                      {empId} — {employeeName}
                    </small>
                  ) : null}
                  <small className="text-muted d-block mt-1">
                    Last pay is basic + NPA from the salary. Basic and NPA are each
                    revised with the same DA and fitment, so every revision line shows
                    Pay, NPA and Total. M2 pension is on the total.
                  </small>
                </div>
              </div>

              <div className="row g-2 g-lg-3 align-items-end">
                <div className="col-6 col-md-4 col-xl-2">
                  <label className="form-label">Retirement / Separation Date</label>
                  <input
                    type="date"
                    className="form-control"
                    value={retirementDate}
                    onChange={(e) => setRetirementDate(e.target.value)}
                  />
                </div>
                <div className="col-6 col-md-4 col-xl-2">
                  <label className="form-label">Class</label>
                  <select
                    className="form-select"
                    value={category}
                    onChange={(e) => {
                      setCategory(e.target.value);
                      setScale("");
                    }}
                  >
                    <option value="">Select class</option>
                    {CLASS_OPTIONS.map((c) => (
                      <option key={c} value={c}>
                        Class {c}
                      </option>
                    ))}
                  </select>
                </div>
                <div className="col-12 col-md-4 col-xl-3">
                  <label className="form-label">Scale</label>
                  <select
                    className="form-select"
                    value={scale}
                    onChange={(e) => setScale(e.target.value)}
                    disabled={!scales.length}
                  >
                    <option value="">
                      {!category
                        ? "Choose class first"
                        : !retirementDate
                          ? "Enter separation date first"
                          : "Select Scale"}
                    </option>
                    {scales.map((item, index) => (
                      <option key={`${scaleValue(item)}-${index}`} value={scaleValue(item)}>
                        {scaleLabel(item)}
                      </option>
                    ))}
                  </select>
                </div>
                <div className="col-6 col-md-4 col-xl-2">
                  <label className="form-label">Basic pay</label>
                  <select
                    className="form-select"
                    value={basic}
                    onChange={(e) => setBasic(e.target.value)}
                    disabled={!scale}
                  >
                    <option value="">{scale ? "Select Basic Pay" : "Choose scale first"}</option>
                    {(basic && !payStages.some((s) => Number(s) === Number(basic))
                      ? [...payStages, basic]
                      : payStages
                    ).map((s, i) => (
                      <option key={`${s}-${i}`} value={String(s)}>
                        {payStages.some((p) => Number(p) === Number(s))
                          ? s
                          : `${s} (salary basic, not a pay stage)`}
                      </option>
                    ))}
                  </select>
                </div>
                <div className="col-6 col-md-4 col-xl-1">
                  <label className="form-label">NPA</label>
                  <input
                    type="number"
                    min="0"
                    className="form-control"
                    value={npa}
                    onChange={(e) => setNpa(e.target.value)}
                  />
                </div>
                <div className="col-6 col-md-4 col-xl-2">
                  <label className="form-label">Last pay (basic + NPA)</label>
                  <input className="form-control" value={totalPay} readOnly />
                </div>
              </div>

              {hasBunch ? (
                <div className="form-check mt-3">
                  <input
                    id="doctor-bunching"
                    type="checkbox"
                    className="form-check-input"
                    checked={includeBunching}
                    onChange={(e) => setIncludeBunching(e.target.checked)}
                  />
                  <label className="form-check-label" htmlFor="doctor-bunching">
                    Include LIC bunching ({master.m1_bunching.bunch_basic}) in M1@277
                  </label>
                </div>
              ) : null}

              {calcError ? (
                <div className="alert alert-danger py-2 mt-3 mb-0 small">{calcError}</div>
              ) : null}
              {result?.note ? (
                <div className="alert alert-warning py-2 mt-3 mb-0 small">{result.note}</div>
              ) : null}
            </div>
          </div>
        </div>
      </div>

      {result ? (
        <Methodology2PensionSummary
          pensionSummary={pensionSummary}
          class12Result={class12Result}
          retirementDate={retirementDate}
          scale={scale}
          lastPay={totalPay}
          npaAmount={npa || ""}
          includeBunching={includeBunching}
          isDoctor
          effectivePay={totalPay}
          empId={empId}
          employeeName={employeeName}
          category={category}
          startRevision={result.start_revision || ""}
          calculationRows={isClass12 ? [] : result.rows || []}
          equivalentScales={result.equivalent_scales || null}
          printMaster={printMaster}
          dateOfBirth={dateOfBirth}
          oldageBenefit={oldageBenefit}
          saveUrl="m2-doctor/consolidation/"
        />
      ) : null}

      {headerPrompt ? (
        <HeaderFieldPrompt
          prompt={headerPrompt}
          onChange={setHeaderPrompt}
          onSave={() => submitHeaderValue(false)}
          onNull={() => submitHeaderValue(true)}
          onBack={() => goBackHeaderValue()}
        />
      ) : null}
    </div>
  );
}
