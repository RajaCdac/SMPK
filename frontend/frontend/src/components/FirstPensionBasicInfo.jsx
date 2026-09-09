import { useEffect, useState } from "react";
import API from "../services/Api";
import "../styles/EsrPersonal.css";
import "../styles/FamilyPensionDashboard.css";

const PANELS = [
  { id: "personal", label: "Personal", path: "family-pension/esr/personal/" },
  { id: "admin", label: "Admin", path: "family-pension/esr/admin/" },
  { id: "finance", label: "Finance", path: "family-pension/esr/finance/" },
  { id: "salary", label: "Salary", path: "family-pension/esr/salary/" },
];

function dash(value) {
  if (value == null || value === "") return "—";
  return String(value);
}

function fmtAmt(value) {
  if (value == null || value === "") return "—";
  const n = Number(value);
  if (Number.isNaN(n)) return "—";
  return n.toLocaleString("en-IN", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
}

function fmtRate(line) {
  if (line?.rate == null || line.rate === "") return "—";
  const n = Number(line.rate);
  if (Number.isNaN(n)) return "—";
  const base = n.toLocaleString("en-IN", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
  return line.rate_pct_flg ? `${base} %` : base;
}

function apiErrorMessage(err, fallback) {
  const data = err?.response?.data;
  if (!data) return err?.message || fallback;
  if (typeof data === "string") return data.slice(0, 400);
  if (data.error) return String(data.error);
  return fallback;
}

function EsrSections({ result }) {
  if (!result?.found) {
    return (
      <p className="text-muted mb-0">
        {result?.error || "No record found for this employee."}
      </p>
    );
  }
  const sections = result.sections || [];
  if (!sections.length) {
    return <p className="text-muted mb-0">No fields to display.</p>;
  }
  return (
    <div className="esr-sections">
      {sections.map((sec) => (
        <section
          key={sec.id}
          className={`esr-card${sec.id === "identity" ? " esr-card-identity" : ""}`}
        >
          <h3 className="esr-card-title">{sec.title}</h3>
          <dl
            className={`esr-field-grid${
              sec.id === "identity" ? " esr-field-grid-row" : ""
            }`}
          >
            {(sec.fields || []).map((f) => (
              <div key={f.key} className="esr-field">
                <dt>{f.label}</dt>
                <dd title={String(f.value)}>{f.value}</dd>
              </div>
            ))}
          </dl>
        </section>
      ))}
    </div>
  );
}

function SalaryPanel({ result }) {
  const months = result?.months || [];
  const firstKey = months.length ? `${months[0].sal_yr}-${months[0].sal_mth}` : "";
  const [selectedKey, setSelectedKey] = useState(firstKey);

  useEffect(() => {
    setSelectedKey(firstKey);
  }, [firstKey]);

  if (!result?.found) {
    return (
      <p className="text-muted mb-0">
        {result?.error || "No salary record found for this employee."}
      </p>
    );
  }

  const selectedMonth =
    months.find((m) => `${m.sal_yr}-${m.sal_mth}` === selectedKey) ||
    months[0] ||
    null;

  return (
    <div className="fp-dashboard">
      {result.latest_month ? (
        <p className="text-muted small mb-2">
          Latest paid month: <strong>{result.latest_month}</strong>
          {result.status ? ` · ${result.status}` : ""}
        </p>
      ) : null}
      <section className="esr-card esr-salary-card">
        <h3 className="esr-card-title">Salary months</h3>
        <div className="esr-salary-table-wrap">
          <table className="esr-salary-table esr-salary-table--hdr">
            <thead>
              <tr>
                <th>Month</th>
                <th>Year</th>
                <th className="num">Basic Rate</th>
                <th>Scale Desc</th>
                <th className="num">Gross Earn Amt</th>
                <th className="num">Net Earn Amt</th>
                <th className="num">Gross Dedn Amt</th>
                <th>Wg St Dt</th>
                <th>Wg End Dt</th>
              </tr>
            </thead>
            <tbody>
              {months.length ? (
                months.map((m) => {
                  const key = `${m.sal_yr}-${m.sal_mth}`;
                  const active = key === selectedKey;
                  return (
                    <tr
                      key={key}
                      className={active ? "is-selected" : ""}
                      onClick={() => setSelectedKey(key)}
                      tabIndex={0}
                      role="button"
                      onKeyDown={(e) => {
                        if (e.key === "Enter" || e.key === " ") {
                          e.preventDefault();
                          setSelectedKey(key);
                        }
                      }}
                    >
                      <td>{m.sal_mth}</td>
                      <td>{m.sal_yr}</td>
                      <td className="num">{fmtAmt(m.basic_rate ?? m.basic)}</td>
                      <td className="name-cell">{dash(m.scale_desc)}</td>
                      <td className="num">{fmtAmt(m.gross_earn_amt ?? m.earning)}</td>
                      <td className="num">{fmtAmt(m.net_earn_amt ?? m.net)}</td>
                      <td className="num">
                        {fmtAmt(m.gross_dedn_amt ?? m.deduction)}
                      </td>
                      <td>{dash(m.wg_st_dt)}</td>
                      <td>{dash(m.wg_end_dt)}</td>
                    </tr>
                  );
                })
              ) : (
                <tr>
                  <td colSpan={9} className="esr-salary-empty">
                    No salary months
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
        <p className="esr-salary-hint">
          Click a month to view earning / deduction details.
        </p>
      </section>
      <section className="esr-card esr-salary-card">
        <h3 className="esr-card-title">
          Earning / Deduction Details
          {selectedMonth
            ? ` — ${
                selectedMonth.month_label ||
                `${selectedMonth.sal_mth}/${selectedMonth.sal_yr}`
              }`
            : ""}
        </h3>
        <div className="esr-salary-table-wrap">
          <table className="esr-salary-table esr-salary-table--dtl">
            <thead>
              <tr>
                <th>Code</th>
                <th>Description</th>
                <th>Type</th>
                <th className="num">No Of Units</th>
                <th className="num">Rate</th>
                <th className="num">Actual</th>
                <th className="num">Adjusted</th>
                <th className="num">Arrear</th>
              </tr>
            </thead>
            <tbody>
              {(selectedMonth?.lines || []).length ? (
                selectedMonth.lines.map((line) => (
                  <tr key={`${line.code}-${line.type_cd}`}>
                    <td>
                      <strong>{line.code}</strong>
                    </td>
                    <td className="name-cell">{dash(line.desc)}</td>
                    <td>{dash(line.type)}</td>
                    <td className="num">{fmtAmt(line.no_of_units)}</td>
                    <td className="num">{fmtRate(line)}</td>
                    <td className="num">{fmtAmt(line.actual)}</td>
                    <td className="num">{fmtAmt(line.adjusted)}</td>
                    <td className="num">{fmtAmt(line.arrear)}</td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td colSpan={8} className="esr-salary-empty">
                    No earning / deduction lines for this month
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}

export default function FirstPensionBasicInfo({
  employee,
  onNext,
  nextLabel = "Next — Pension processing",
}) {
  const empCd = String(employee?.emp_id || employee?.emp_cd || "").trim();
  const [openId, setOpenId] = useState("personal");
  const [cache, setCache] = useState({});
  const [loadingId, setLoadingId] = useState("");
  const [errors, setErrors] = useState({});

  useEffect(() => {
    setCache({});
    setErrors({});
    setOpenId("personal");
    setLoadingId("");
  }, [empCd]);

  useEffect(() => {
    if (!empCd || !openId) return undefined;
    const panel = PANELS.find((p) => p.id === openId);
    if (!panel) return undefined;
    let cancelled = false;
    setLoadingId(openId);
    API.get(panel.path, { params: { emp_cd: empCd } })
      .then(({ data }) => {
        if (cancelled) return;
        setCache((prev) => ({ ...prev, [openId]: data }));
      })
      .catch((err) => {
        if (cancelled) return;
        setErrors((prev) => ({
          ...prev,
          [openId]: apiErrorMessage(err, `Could not load ${panel.label}`),
        }));
      })
      .finally(() => {
        if (!cancelled) setLoadingId("");
      });
    return () => {
      cancelled = true;
    };
  }, [empCd, openId]);

  const toggle = (id) => {
    setOpenId((prev) => (prev === id ? "" : id));
  };

  return (
    <div className="first-pension-basic">
      <p className="text-muted small mb-3">
        Review ESR for this employee, then continue to pension processing
        (separation type and date).
      </p>

      <div className="fp-basic-accordions">
        {PANELS.map((panel) => {
          const open = openId === panel.id;
          const data = cache[panel.id];
          const err = errors[panel.id];
          const loading = loadingId === panel.id;
          return (
            <div
              key={panel.id}
              className={`fp-basic-acc${open ? " is-open" : ""}`}
            >
              <button
                type="button"
                className="fp-basic-acc__head"
                onClick={() => toggle(panel.id)}
                aria-expanded={open}
              >
                <span>{panel.label}</span>
                <span className="fp-basic-acc__chevron" aria-hidden="true">
                  {open ? "▾" : "▸"}
                </span>
              </button>
              {open ? (
                <div className="fp-basic-acc__body">
                  {loading ? (
                    <p className="text-muted mb-0">Loading {panel.label}…</p>
                  ) : err ? (
                    <p className="text-danger mb-0">{err}</p>
                  ) : panel.id === "salary" ? (
                    <SalaryPanel result={data} />
                  ) : (
                    <EsrSections result={data} />
                  )}
                </div>
              ) : null}
            </div>
          );
        })}
      </div>

      <div className="smpk-form-actions process-intake-actions mt-3">
        <button type="button" className="btn btn-primary" onClick={() => onNext?.()}>
          {nextLabel}
        </button>
      </div>
    </div>
  );
}
