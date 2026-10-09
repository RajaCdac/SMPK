import React, { useMemo, useState } from "react";
import API from "../services/Api";
import OldAgeBenefitPanel from "../components/OldAgeBenefitPanel";

const MONTHS = [
  { v: 1, l: "JAN" },
  { v: 2, l: "FEB" },
  { v: 3, l: "MAR" },
  { v: 4, l: "APR" },
  { v: 5, l: "MAY" },
  { v: 6, l: "JUN" },
  { v: 7, l: "JUL" },
  { v: 8, l: "AUG" },
  { v: 9, l: "SEP" },
  { v: 10, l: "OCT" },
  { v: 11, l: "NOV" },
  { v: 12, l: "DEC" },
];

function fmt(n) {
  if (n == null || n === "") return "—";
  const num = Number(n);
  if (Number.isNaN(num)) return String(n);
  return num.toLocaleString("en-IN", {
    minimumFractionDigits: 0,
    maximumFractionDigits: 2,
  });
}

function yearOptions() {
  const y = new Date().getFullYear();
  const list = [];
  for (let i = y + 1; i >= 2010; i -= 1) list.push(i);
  return list;
}

export default function Methodology2OldAgeBenefit() {
  const now = new Date();
  const [empId, setEmpId] = useState("");
  const [empName, setEmpName] = useState("");
  const [dob, setDob] = useState("");
  const [fromMonth, setFromMonth] = useState(1);
  const [fromYear, setFromYear] = useState(2017);
  const [toMonth, setToMonth] = useState(now.getMonth() + 1);
  const [toYear, setToYear] = useState(now.getFullYear());
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  const years = useMemo(() => yearOptions(), []);

  const loadEmp = async () => {
    const trimmed = String(empId || "").trim();
    if (!trimmed) {
      setError("Enter Employee Code");
      return;
    }
    setError("");
    setLoading(true);
    try {
      const res = await API.get(`m2-oldage-arrear/employee/${trimmed}/`);
      const data = res.data || {};
      setEmpName(data.name || data.wage_emp_name || data.pensioner_name || "");
      setDob(
        (data.date_of_birth || data.dob || "").toString().slice(0, 10)
      );
      setResult(null);
    } catch (err) {
      setError(err.response?.data?.error || "Employee not found");
      setEmpName("");
      setDob("");
    } finally {
      setLoading(false);
    }
  };

  const calculate = async ({ save = false } = {}) => {
    const trimmed = String(empId || "").trim();
    if (!trimmed) {
      setError("Enter Employee Code");
      return;
    }
    setError("");
    setLoading(true);
    try {
      const res = await API.post("m2-oldage-arrear/oldage-benefit/calculate/", {
        emp_cd: trimmed,
        from_month: Number(fromMonth),
        from_year: Number(fromYear),
        to_month: Number(toMonth),
        to_year: Number(toYear),
        dob: dob || undefined,
        date_of_birth: dob || undefined,
        name: empName || undefined,
        save: save ? true : undefined,
      });
      setResult(res.data);
      if (res.data?.dob || res.data?.date_of_birth) {
        setDob(String(res.data.dob || res.data.date_of_birth).slice(0, 10));
      }
      if (res.data?.name) setEmpName(res.data.name);
    } catch (err) {
      setResult(null);
      setError(
        err.response?.data?.error || "Old-age benefit calculation failed"
      );
    } finally {
      setLoading(false);
    }
  };

  const save = async () => {
    if (!result || result.error) {
      setError("Calculate first, then save");
      return;
    }
    setSaving(true);
    setError("");
    try {
      const res = await API.post("m2-oldage-arrear/oldage-benefit/save/", result);
      setResult(res.data);
    } catch (err) {
      setError(err.response?.data?.error || "Save failed");
    } finally {
      setSaving(false);
    }
  };

  const months = result?.months || [];

  return (
    <div className="container-fluid py-3">
      <div className="d-flex align-items-center justify-content-between flex-wrap gap-2 mb-3">
        <h4 className="mb-0">M2 Old Age Arrear — Old Age Benefit</h4>
      </div>

      <div className="card shadow-sm mb-3">
        <div className="card-body">
          <div className="row g-3 align-items-end">
            <div className="col-6 col-md-2">
              <label className="form-label">Emp CD</label>
              <input
                className="form-control"
                value={empId}
                maxLength={5}
                onChange={(e) => setEmpId(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter") loadEmp();
                }}
              />
            </div>
            <div className="col-auto">
              <button
                type="button"
                className="btn btn-outline-primary"
                disabled={loading}
                onClick={loadEmp}
              >
                Load
              </button>
            </div>
            <div className="col-md-3">
              <label className="form-label">Name</label>
              <input className="form-control" readOnly value={empName} />
            </div>
            <div className="col-6 col-md-2">
              <label className="form-label">DOB</label>
              <input
                type="date"
                className="form-control"
                value={dob}
                onChange={(e) => setDob(e.target.value)}
              />
            </div>
          </div>

          <div className="row g-3 align-items-end mt-1">
            <div className="col-6 col-md-2">
              <label className="form-label">From month</label>
              <select
                className="form-select"
                value={fromMonth}
                onChange={(e) => setFromMonth(Number(e.target.value))}
              >
                {MONTHS.map((m) => (
                  <option key={m.v} value={m.v}>
                    {m.l}
                  </option>
                ))}
              </select>
            </div>
            <div className="col-6 col-md-2">
              <label className="form-label">From year</label>
              <select
                className="form-select"
                value={fromYear}
                onChange={(e) => setFromYear(Number(e.target.value))}
              >
                {years.map((y) => (
                  <option key={y} value={y}>
                    {y}
                  </option>
                ))}
              </select>
            </div>
            <div className="col-6 col-md-2">
              <label className="form-label">To month</label>
              <select
                className="form-select"
                value={toMonth}
                onChange={(e) => setToMonth(Number(e.target.value))}
              >
                {MONTHS.map((m) => (
                  <option key={m.v} value={m.v}>
                    {m.l}
                  </option>
                ))}
              </select>
            </div>
            <div className="col-6 col-md-2">
              <label className="form-label">To year</label>
              <select
                className="form-select"
                value={toYear}
                onChange={(e) => setToYear(Number(e.target.value))}
              >
                {years.map((y) => (
                  <option key={y} value={y}>
                    {y}
                  </option>
                ))}
              </select>
            </div>
            <div className="col-auto d-flex gap-2">
              <button
                type="button"
                className="btn btn-warning"
                disabled={loading}
                onClick={() => calculate({ save: false })}
              >
                {loading ? "Calculating…" : "Calculate"}
              </button>
              <button
                type="button"
                className="btn btn-success"
                disabled={loading || saving || !result}
                onClick={save}
              >
                {saving ? "Saving…" : "Save month-wise"}
              </button>
            </div>
          </div>

          {error ? (
            <div className="alert alert-danger mt-3 mb-0 py-2">{error}</div>
          ) : null}
          {result?.saved ? (
            <div className="alert alert-success mt-3 mb-0 py-2">
              Saved hdr #{result.hdr_id} · v{result.version_no} ·{" "}
              {result.month_count ?? months.length} month row(s) in{" "}
              <code>m2_oa_td_oldage_benefit_mth</code>
            </div>
          ) : null}
          {result?.bases_source ? (
            <p className="text-muted small mt-2 mb-0">
              Pension bases from <code>{result.bases_source}</code>
            </p>
          ) : null}
        </div>
      </div>

      {result && !result.error ? (
        <>
          <OldAgeBenefitPanel
            dob={dob}
            onDobChange={setDob}
            oldage={result}
            loading={loading}
            onRecalculate={() => calculate({ save: false })}
          />

          <div className="row justify-content-center mt-3">
            <div className="col-12 col-xl-10">
              <div className="card shadow border-secondary">
                <div className="card-header bg-light">
                  <h5 className="mb-0">Month-wise Old Age Benefit</h5>
                </div>
                <div className="card-body p-0">
                  <div className="table-responsive">
                    <table className="table table-sm table-striped mb-0">
                      <thead>
                        <tr>
                          <th>Month</th>
                          <th>Year</th>
                          <th>CPI</th>
                          <th className="text-end">M-I pension</th>
                          <th className="text-end">M-II pension</th>
                          <th className="text-end">Benefit (M-II − M-I)</th>
                          <th>OA %</th>
                          <th className="text-end">OA basic</th>
                          <th className="text-end">DA %</th>
                          <th className="text-end">OA DA</th>
                          <th className="text-end">Month total</th>
                        </tr>
                      </thead>
                      <tbody>
                        {months.length === 0 ? (
                          <tr>
                            <td colSpan={11} className="text-center text-muted py-3">
                              No month rows in this range
                            </td>
                          </tr>
                        ) : (
                          months.map((m) => (
                            <tr key={`${m.bill_year}-${m.bill_month}`}>
                              <td>{m.bill_mth}</td>
                              <td>{m.bill_year}</td>
                              <td>{m.cpi_point ?? "—"}</td>
                              <td className="text-end">{fmt(m.m1_pension)}</td>
                              <td className="text-end">{fmt(m.m2_pension)}</td>
                              <td className="text-end">{fmt(m.benefit_base)}</td>
                              <td>{m.oa_percent ?? 0}</td>
                              <td className="text-end">{fmt(m.oa_basic)}</td>
                              <td className="text-end">{fmt(m.da_pct)}</td>
                              <td className="text-end">{fmt(m.oa_da)}</td>
                              <td className="text-end fw-semibold">
                                {fmt(m.month_total)}
                              </td>
                            </tr>
                          ))
                        )}
                      </tbody>
                      {months.length > 0 ? (
                        <tfoot>
                          <tr className="fw-semibold">
                            <td colSpan={7}>Total (From–To)</td>
                            <td className="text-end">
                              {fmt(result.total_arrear_basic)}
                            </td>
                            <td />
                            <td className="text-end">
                              {fmt(result.total_arrear_da)}
                            </td>
                            <td className="text-end">
                              {fmt(result.total_arrear)}
                            </td>
                          </tr>
                        </tfoot>
                      ) : null}
                    </table>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </>
      ) : null}
    </div>
  );
}
