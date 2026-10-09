import { Fragment, useMemo, useState } from "react";
import API from "../services/Api";

const MONTHS = [
  { v: 1, l: "Jan" },
  { v: 2, l: "Feb" },
  { v: 3, l: "Mar" },
  { v: 4, l: "Apr" },
  { v: 5, l: "May" },
  { v: 6, l: "Jun" },
  { v: 7, l: "Jul" },
  { v: 8, l: "Aug" },
  { v: 9, l: "Sep" },
  { v: 10, l: "Oct" },
  { v: 11, l: "Nov" },
  { v: 12, l: "Dec" },
];

function years() {
  const now = new Date().getFullYear();
  const list = [];
  for (let y = now + 1; y >= 2017; y -= 1) list.push(y);
  return list;
}

function money(value) {
  if (value == null || value === "") return "—";
  const n = Number(value);
  if (Number.isNaN(n)) return String(value);
  return n.toLocaleString("en-IN", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
}

function periodLabel(line) {
  if (!line) return "";
  if (line.from_label === line.to_label) return line.from_label;
  return `${line.from_label} – ${line.to_label}`;
}

async function readBlobError(err) {
  let message = err?.message || "Request failed";
  if (err?.response?.data instanceof Blob) {
    try {
      const text = await err.response.data.text();
      const json = JSON.parse(text);
      message = json.error || message;
    } catch {
      message = "Request failed";
    }
  } else if (err?.response?.data?.error) {
    message = err.response.data.error;
  }
  return String(message);
}

export default function Methodology2Arrear() {
  const now = new Date();
  const [file, setFile] = useState(null);
  const [fromMonth, setFromMonth] = useState(5);
  const [fromYear, setFromYear] = useState(now.getFullYear());
  const [toMonth, setToMonth] = useState(9);
  const [toYear, setToYear] = useState(now.getFullYear());
  const [phase, setPhase] = useState("");
  const [busy, setBusy] = useState(false);
  const [exporting, setExporting] = useState(false);
  const [error, setError] = useState("");
  const [batch, setBatch] = useState(null);
  const [selected, setSelected] = useState(() => new Set());
  const [openEmp, setOpenEmp] = useState("");

  const rows = batch?.rows || [];
  const okRows = useMemo(() => rows.filter((row) => row.ok), [rows]);
  const allOkSelected =
    okRows.length > 0 && okRows.every((row) => selected.has(row.emp_cd));

  const toggleAll = () => {
    if (allOkSelected) {
      setSelected(new Set());
      return;
    }
    setSelected(new Set(okRows.map((row) => row.emp_cd)));
  };

  const toggleOne = (emp) => {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(emp)) next.delete(emp);
      else next.add(emp);
      return next;
    });
  };

  const calculate = async () => {
    setError("");
    setBatch(null);
    setSelected(new Set());
    setOpenEmp("");
    if (!file) {
      setError("Choose an Excel file with an EMP_CD column.");
      return;
    }
    setBusy(true);
    try {
      const body = new FormData();
      body.append("file", file);
      body.append("from_month", String(fromMonth));
      body.append("from_year", String(fromYear));
      body.append("to_month", String(toMonth));
      body.append("to_year", String(toYear));
      const res = await API.post("m2-oldage-arrear/arrear/batch/", body, {
        timeout: 0,
      });
      const data = res.data || {};
      setBatch(data);
      const ready = (data.rows || []).filter((row) => row.ok).map((row) => row.emp_cd);
      setSelected(new Set(ready));
    } catch (err) {
      setError(await readBlobError(err));
    } finally {
      setBusy(false);
    }
  };

  const exportSheet = async () => {
    const empCds = okRows
      .filter((row) => selected.has(row.emp_cd))
      .map((row) => row.emp_cd);
    if (!empCds.length) {
      setError("Select at least one calculated employee.");
      return;
    }
    setExporting(true);
    setError("");
    try {
      const res = await API.post(
        "m2-oldage-arrear/arrear/export/",
        {
          emp_cds: empCds,
          from_month: fromMonth,
          from_year: fromYear,
          to_month: toMonth,
          to_year: toYear,
          phase,
        },
        { responseType: "blob", timeout: 0 }
      );
      const blob = new Blob([res.data], {
        type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
      });
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      const cd = res.headers["content-disposition"] || "";
      const match = cd.match(/filename="?([^"]+)"?/);
      link.download = match ? match[1] : "Arrear.xlsx";
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
    } catch (err) {
      setError(await readBlobError(err));
    } finally {
      setExporting(false);
    }
  };

  return (
    <div className="container-fluid mt-3 mt-md-4 px-2 px-md-3">
      <div className="card shadow">
        <div className="card-header bg-dark text-white">
          <h4 className="mb-0">Arrear Calculation</h4>
        </div>
        <div className="card-body">
          <p className="small text-muted mb-3">
            Upload employee codes, choose the months to pay, and review the
            breakup from the saved consolidation. Tick the rows that are
            correct and export the Pay &amp; Cash sheet. Export does not mark
            the consolidation as paid. Amounts use the 277 CPI difference
            through December 2021, and from January 2022 Class 3 and 4 use
            359 CPI. Class 1 and 2 stay on 277. Old-age benefit is added to
            that difference, then dearness relief is worked on the combined
            monthly amount. The payable difference starts in January 2017.
          </p>

          <div className="row g-2 align-items-end">
            <div className="col-12 col-lg-4">
              <label className="form-label">Employee Excel</label>
              <input
                type="file"
                className="form-control"
                accept=".xlsx,.xls"
                onChange={(e) => setFile(e.target.files?.[0] || null)}
              />
              <div className="form-text">One column named EMP_CD.</div>
            </div>
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
                {years().map((y) => (
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
                {years().map((y) => (
                  <option key={y} value={y}>
                    {y}
                  </option>
                ))}
              </select>
            </div>
          </div>

          <div className="row g-2 align-items-end mt-2">
            <div className="col-12 col-md-3">
              <label className="form-label">Phase</label>
              <input
                type="text"
                className="form-control"
                value={phase}
                placeholder="Optional, printed on the sheet"
                onChange={(e) => setPhase(e.target.value)}
              />
            </div>
            <div className="col-12 col-md-3">
              <button
                type="button"
                className="btn btn-primary"
                disabled={busy || !file}
                onClick={calculate}
              >
                {busy ? "Calculating..." : "Calculate"}
              </button>
            </div>
          </div>

          {error ? (
            <div className="alert alert-danger py-2 px-3 mt-3 mb-0 small">
              {error}
            </div>
          ) : null}
        </div>
      </div>

      {batch ? (
        <div className="card shadow mt-4">
          <div className="card-header d-flex flex-wrap justify-content-between align-items-center gap-2">
            <div>
              <h5 className="mb-0">
                {batch.from_label} to {batch.to_label}
              </h5>
              <div className="small text-muted">
                {batch.ok_count} calculated
                {batch.failed_count
                  ? `, ${batch.failed_count} could not be calculated`
                  : ""}
                . Arrear to be paid upto {batch.paid_upto}. {selected.size}{" "}
                selected.
              </div>
            </div>
            <button
              type="button"
              className="btn btn-success"
              disabled={exporting || selected.size === 0}
              onClick={exportSheet}
            >
              {exporting ? "Exporting..." : "Export"}
            </button>
          </div>
          <div className="card-body">
            <div className="table-responsive">
              <table className="table table-sm table-bordered align-middle mb-0">
                <thead>
                  <tr>
                    <th style={{ width: 36 }}>
                      <input
                        type="checkbox"
                        className="form-check-input"
                        checked={allOkSelected}
                        onChange={toggleAll}
                        disabled={!okRows.length}
                        aria-label="Select all calculated employees"
                      />
                    </th>
                    <th>Employee</th>
                    <th>Name</th>
                    <th>Class</th>
                    <th className="text-end">M-I</th>
                    <th className="text-end">M-II</th>
                    <th>Beneficial</th>
                    <th className="text-end">Benefit</th>
                    <th className="text-end">Pension arrear</th>
                    <th className="text-end">DA relief</th>
                    <th className="text-end">Total</th>
                  </tr>
                </thead>
                <tbody>
                  {rows.map((row) => {
                    const open = openEmp === row.emp_cd;
                    const pair = row.pair || {};
                    return (
                      <Fragment key={row.emp_cd}>
                        <tr className={row.ok ? "" : "table-warning"}>
                          <td>
                            <input
                              type="checkbox"
                              className="form-check-input"
                              checked={selected.has(row.emp_cd)}
                              disabled={!row.ok}
                              onChange={() => toggleOne(row.emp_cd)}
                              aria-label={`Select ${row.emp_cd}`}
                            />
                          </td>
                          <td>
                            <button
                              type="button"
                              className="btn btn-link btn-sm p-0"
                              onClick={() =>
                                setOpenEmp(open ? "" : row.emp_cd)
                              }
                            >
                              {row.emp_cd}
                            </button>
                          </td>
                          <td>{row.name || "—"}</td>
                          <td>{row.class_label || "—"}</td>
                          <td className="text-end">{money(pair.m1)}</td>
                          <td className="text-end">{money(pair.m2)}</td>
                          <td>{pair.beneficial || "—"}</td>
                          <td className="text-end">{money(pair.benefit)}</td>
                          <td className="text-end">{money(row.pension_arrear)}</td>
                          <td className="text-end">{money(row.da_relief)}</td>
                          <td className="text-end">{money(row.total)}</td>
                        </tr>
                        {open ? (
                          <tr key={`${row.emp_cd}-detail`}>
                            <td colSpan={11} className="bg-light">
                              {row.error ? (
                                <div className="small text-danger">{row.error}</div>
                              ) : (
                                <div>
                                  <div className="small mb-2">
                                    {row.designation || "—"}
                                    {row.retirement_date
                                      ? ` · Retired ${row.retirement_date}`
                                      : ""}
                                    {row.last_pay != null
                                      ? ` · Pay ${money(row.last_pay)}`
                                      : ""}
                                    {row.scale ? ` · ${row.scale}` : ""}
                                  </div>
                                  <table className="table table-sm table-bordered mb-0 bg-white">
                                    <thead>
                                      <tr>
                                        <th>Period</th>
                                        <th>Pension</th>
                                        <th>Months</th>
                                        <th>CPI</th>
                                        <th className="text-end">M-I</th>
                                        <th className="text-end">M-II</th>
                                        <th className="text-end">Pension diff</th>
                                        <th className="text-end">Old age %</th>
                                        <th className="text-end">Old age</th>
                                        <th className="text-end">DA %</th>
                                        <th className="text-end">Pension arrear</th>
                                        <th className="text-end">DA relief</th>
                                        <th className="text-end">Total</th>
                                      </tr>
                                    </thead>
                                    <tbody>
                                      {(row.lines || []).map((line) => (
                                        <tr
                                          key={`${row.emp_cd}-${line.from_iso}-${line.pension_kind}-${line.da_pct}`}
                                        >
                                          <td>{periodLabel(line)}</td>
                                          <td>{line.pension_label || "—"}</td>
                                          <td>{line.months}</td>
                                          <td>{line.cpi}</td>
                                          <td className="text-end">{money(line.m1)}</td>
                                          <td className="text-end">{money(line.m2)}</td>
                                          <td className="text-end">
                                            {money(line.pension_diff)}
                                          </td>
                                          <td className="text-end">
                                            {`${line.oldage_percent || 0}%`}
                                          </td>
                                          <td className="text-end">
                                            {money(line.oldage_benefit || 0)}
                                          </td>
                                          <td className="text-end">{line.da_pct}</td>
                                          <td className="text-end">
                                            {money(line.pension_arrear)}
                                          </td>
                                          <td className="text-end">
                                            {money(line.da_relief)}
                                          </td>
                                          <td className="text-end">{money(line.total)}</td>
                                        </tr>
                                      ))}
                                    </tbody>
                                  </table>
                                </div>
                              )}
                            </td>
                          </tr>
                        ) : null}
                      </Fragment>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      ) : null}
    </div>
  );
}
