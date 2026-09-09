import { useCallback, useEffect, useMemo, useState } from "react";
import API from "../services/Api";
import SmpkDataTable from "../components/DataTable/SmpkDataTable";
import "../styles/FamilyPensionDashboard.css";
import "../styles/EsrPersonal.css";

function apiErrorMessage(err, fallback = "Request failed") {
  const data = err?.response?.data;
  if (!data) return err?.message || fallback;
  if (typeof data === "string") return data.slice(0, 400);
  if (data.error) return String(data.error);
  return fallback;
}

function dash(value) {
  if (value == null || value === "") return "—";
  return String(value);
}

function fmtCount(value) {
  if (value == null || value === "") return "—";
  const n = Number(value);
  if (Number.isNaN(n)) return "—";
  return n.toLocaleString("en-IN");
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

const MONTH_SHORT = [
  "",
  "Jan",
  "Feb",
  "Mar",
  "Apr",
  "May",
  "Jun",
  "Jul",
  "Aug",
  "Sep",
  "Oct",
  "Nov",
  "Dec",
];

/** Chronologically next calendar month after (yr, mth). */
function nextSalaryYm(salYr, salMth) {
  let y = Number(salYr);
  let m = Number(salMth);
  if (!y || !m || m < 1 || m > 12) return null;
  m += 1;
  if (m > 12) {
    m = 1;
    y += 1;
  }
  return { sal_yr: y, sal_mth: m };
}

function monthLabel(salMth, salYr) {
  const m = Number(salMth);
  const y = Number(salYr);
  const name = MONTH_SHORT[m] || String(m || "");
  return y ? `${name} ${y}` : name;
}

/**
 * Next-month draft: header is basic rate + scale only;
 * earn/dedn lines are only 001 (basic) and 007 (DA) from last paid month.
 */
function buildNextMonthRow(latestMonth) {
  if (!latestMonth) return null;
  const next = nextSalaryYm(latestMonth.sal_yr, latestMonth.sal_mth);
  if (!next) return null;

  const basic = latestMonth.basic_rate ?? latestMonth.basic ?? null;
  const scale = latestMonth.scale_desc || "—";
  const srcLines = Array.isArray(latestMonth.lines) ? latestMonth.lines : [];

  const pickLine = (code, fallback) => {
    const src = srcLines.find((l) => String(l.code || "").trim() === code);
    if (src) {
      return {
        code,
        desc: src.desc || fallback.desc,
        type: src.type || "Earning",
        type_cd: src.type_cd || "E",
        no_of_units: src.no_of_units ?? null,
        rate: src.rate ?? fallback.rate,
        rate_pct_flg: src.rate_pct_flg ?? fallback.rate_pct_flg ?? 0,
        actual: src.actual ?? fallback.actual,
        adjusted: src.adjusted ?? null,
        arrear: src.arrear ?? null,
      };
    }
    return { ...fallback, code };
  };

  const lines = [
    pickLine("001", {
      desc: "BASIC PAY",
      type: "Earning",
      type_cd: "E",
      no_of_units: null,
      rate: basic,
      rate_pct_flg: 0,
      actual: basic,
      adjusted: null,
      arrear: null,
    }),
    pickLine("007", {
      desc: "DEARNESS ALLOWANCE",
      type: "Earning",
      type_cd: "E",
      no_of_units: null,
      rate: null,
      rate_pct_flg: 0,
      actual: null,
      adjusted: null,
      arrear: null,
    }),
  ];

  return {
    sal_yr: next.sal_yr,
    sal_mth: next.sal_mth,
    month_label: monthLabel(next.sal_mth, next.sal_yr),
    fa_no:
      latestMonth.fa_no && latestMonth.fa_no !== "—"
        ? latestMonth.fa_no
        : "",
    sal_bill_no: "",
    basic,
    basic_rate: basic,
    scale_desc: scale === "—" ? "" : scale,
    gross: null,
    gross_earn_amt: null,
    net: null,
    net_earn_amt: null,
    deduction: null,
    gross_dedn_amt: null,
    wg_st_dt: "—",
    wg_end_dt: "—",
    da: lines.find((l) => l.code === "007")?.actual ?? null,
    lines,
    is_added: true,
  };
}

const EMPTY_STATS = {
  total_rows: null,
  total_emp: null,
  distinct_months: null,
  latest_month: null,
  latest_month_emp: null,
};

export default function EsrSalary() {
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [listError, setListError] = useState("");
  const [result, setResult] = useState(null);
  const [selectedKey, setSelectedKey] = useState(null);
  const [stats, setStats] = useState(EMPTY_STATS);

  useEffect(() => {
    let cancelled = false;
    API.get("family-pension/esr/salary/", { params: { summary: 1 } })
      .then(({ data }) => {
        if (cancelled || !data || data.error) return;
        setStats({
          total_rows: data.total_rows,
          total_emp: data.total_emp,
          distinct_months: data.distinct_months,
          latest_month: data.latest_month,
          latest_month_emp: data.latest_month_emp,
        });
      })
      .catch(() => {});
    return () => {
      cancelled = true;
    };
  }, []);

  const loadSalary = useCallback(async (code) => {
    const cleaned = String(code || "").trim();
    if (!cleaned) return;
    setLoading(true);
    setError("");
    setMessage("");
    setResult(null);
    setSelectedKey(null);
    try {
      const { data } = await API.get("family-pension/esr/salary/", {
        params: { emp_cd: cleaned, months: 10 },
      });
      if (data?.error && !data?.found) {
        setError(data.error);
        return;
      }
      setResult(data);
      const months = data?.months || [];
      const pick =
        months.find((m) => (m.lines || []).length > 0) || months[0];
      if (pick) {
        setSelectedKey(`${pick.sal_yr}-${pick.sal_mth}`);
      }
      requestAnimationFrame(() => {
        document
          .getElementById("esr-salary-detail")
          ?.scrollIntoView({ behavior: "smooth", block: "start" });
      });
    } catch (err) {
      setError(apiErrorMessage(err, "Could not load salary records"));
    } finally {
      setLoading(false);
    }
  }, []);

  const handleListClick = (e) => {
    const pick = e.target.closest("[data-emp-cd]");
    if (!pick) return;
    const code = pick.getAttribute("data-emp-cd");
    if (code) loadSalary(code);
  };

  const selectedMonth = useMemo(() => {
    if (!result?.months?.length) return null;
    return (
      result.months.find((m) => `${m.sal_yr}-${m.sal_mth}` === selectedKey) ||
      result.months[0]
    );
  }, [result, selectedKey]);

  /** API returns months newest-first — that row is the seed for “next month”. */
  const latestPaidMonth = useMemo(() => {
    const months = result?.months || [];
    if (!months.length) return null;
    const paid = months.filter((m) => !m.is_added);
    if (!paid.length) return months[0];
    return paid.reduce((best, m) => {
      const a = Number(best.sal_yr) * 100 + Number(best.sal_mth);
      const b = Number(m.sal_yr) * 100 + Number(m.sal_mth);
      return b > a ? m : best;
    }, paid[0]);
  }, [result]);

  const canAddNextMonth = useMemo(() => {
    if (!latestPaidMonth) return false;
    const next = nextSalaryYm(latestPaidMonth.sal_yr, latestPaidMonth.sal_mth);
    if (!next) return false;
    const key = `${next.sal_yr}-${next.sal_mth}`;
    return !(result?.months || []).some(
      (m) => `${m.sal_yr}-${m.sal_mth}` === key
    );
  }, [latestPaidMonth, result]);

  const pendingAddedMonth = useMemo(() => {
    return (result?.months || []).find((m) => m.is_added) || null;
  }, [result]);

  const updateAddedBasic = (key, raw) => {
    const cleaned = String(raw ?? "").replace(/,/g, "");
    const num =
      cleaned === "" || cleaned === "." ? null : Number(cleaned);
    const basic = Number.isFinite(num) ? num : null;
    setResult((prev) => {
      if (!prev) return prev;
      return {
        ...prev,
        months: (prev.months || []).map((m) => {
          if (`${m.sal_yr}-${m.sal_mth}` !== key || !m.is_added) return m;
          const lines = (m.lines || []).map((line) => {
            if (String(line.code) !== "001") return line;
            return {
              ...line,
              rate: basic,
              actual: basic,
            };
          });
          // If 007 is % of basic, recompute actual for display
          const lines2 = lines.map((line) => {
            if (String(line.code) !== "007") return line;
            if (line.rate_pct_flg && line.rate != null && basic != null) {
              const da = Math.round(basic * Number(line.rate) * 100) / 10000;
              return { ...line, actual: da };
            }
            return line;
          });
          return {
            ...m,
            basic,
            basic_rate: basic,
            lines: lines2,
            da: lines2.find((l) => l.code === "007")?.actual ?? m.da,
          };
        }),
      };
    });
  };

  const addNextMonth = () => {
    if (!latestPaidMonth || !canAddNextMonth) return;
    const row = buildNextMonthRow(latestPaidMonth);
    if (!row) return;
    const key = `${row.sal_yr}-${row.sal_mth}`;
    setResult((prev) => {
      if (!prev) return prev;
      return {
        ...prev,
        months: [row, ...(prev.months || [])],
        months_count: (prev.months_count || 0) + 1,
        latest_month: row.month_label,
      };
    });
    setSelectedKey(key);
    setError("");
    setMessage(
      `Draft ${row.month_label} added — edit Basic Rate, then click Save month`
    );
  };

  const saveAddedMonth = async () => {
    if (!result?.emp_cd || !pendingAddedMonth) return;
    const basic = pendingAddedMonth.basic_rate ?? pendingAddedMonth.basic;
    if (basic == null || basic === "") {
      setError("Enter basic rate before saving");
      return;
    }
    setSaving(true);
    setError("");
    setMessage("");
    try {
      const { data } = await API.post("family-pension/esr/salary/", {
        emp_cd: result.emp_cd,
        sal_yr: pendingAddedMonth.sal_yr,
        sal_mth: pendingAddedMonth.sal_mth,
        basic_rate: basic,
        scale_desc:
          pendingAddedMonth.scale_desc === "—"
            ? ""
            : pendingAddedMonth.scale_desc || "",
        fa_no:
          (pendingAddedMonth.fa_no && pendingAddedMonth.fa_no !== "—"
            ? pendingAddedMonth.fa_no
            : latestPaidMonth?.fa_no && latestPaidMonth.fa_no !== "—"
              ? latestPaidMonth.fa_no
              : "") || "",
        sal_bill_no:
          pendingAddedMonth.sal_bill_no === "—"
            ? ""
            : pendingAddedMonth.sal_bill_no || "",
        lines: (pendingAddedMonth.lines || []).map((line) => ({
          code: line.code,
          type_cd: line.type_cd || "E",
          rate: line.rate,
          rate_pct_flg: line.rate_pct_flg || 0,
          actual: line.actual,
        })),
      });
      setMessage(data?.message || "Salary month saved");
      // Reload from server so the row loses draft/is_added state
      await loadSalary(result.emp_cd);
      if (data?.message) setMessage(data.message);
      const key = `${pendingAddedMonth.sal_yr}-${pendingAddedMonth.sal_mth}`;
      setSelectedKey(key);
    } catch (err) {
      setError(apiErrorMessage(err, "Could not save salary month"));
    } finally {
      setSaving(false);
    }
  };

  const options = useMemo(
    () => ({
      serverSide: true,
      processing: true,
      searching: true,
      ordering: true,
      searchDelay: 400,
      pageLength: 25,
      lengthMenu: [10, 25, 50, 100],
      order: [[0, "asc"]],
      columns: [
        {
          data: "emp_cd",
          render: (d) => {
            const code = dash(d);
            if (code === "—") return code;
            return `<button type="button" class="fp-emp-pick" data-emp-cd="${String(
              d
            ).replace(/"/g, "")}">${code}</button>`;
          },
        },
        { data: "full_name", render: (d) => dash(d) },
        { data: "last_month", render: (d) => dash(d) },
        {
          data: "basic",
          className: "dt-body-right",
          render: (d) => fmtAmt(d),
        },
        {
          data: "gross",
          className: "dt-body-right",
          render: (d) => fmtAmt(d),
        },
        {
          data: "net",
          className: "dt-body-right",
          render: (d) => fmtAmt(d),
        },
        { data: "scale_desc", render: (d) => dash(d) },
      ],
      ajax: (() => {
        let reqSeq = 0;
        return (dtReq, callback) => {
          const params = {
            draw: dtReq.draw,
            start: dtReq.start,
            length: dtReq.length,
            "search[value]": dtReq.search?.value || "",
            "order[0][column]": dtReq.order?.[0]?.column ?? 0,
            "order[0][dir]": dtReq.order?.[0]?.dir || "asc",
          };
          const seq = ++reqSeq;
          API.get("family-pension/esr/salary/", { params })
            .then(({ data }) => {
              if (seq !== reqSeq) return;
              setListError("");
              callback({
                draw: data.draw,
                recordsTotal: data.recordsTotal,
                recordsFiltered: data.recordsFiltered,
                data: Array.isArray(data.data) ? data.data : [],
              });
            })
            .catch((err) => {
              if (seq !== reqSeq) return;
              const msg =
                err?.response?.data?.error ||
                err?.message ||
                "Failed to load employees";
              setListError(String(msg));
              callback({
                draw: dtReq.draw,
                recordsTotal: 0,
                recordsFiltered: 0,
                data: [],
              });
            });
        };
      })(),
      language: {
        emptyTable: "No employees with salary found",
        processing: "Loading…",
        searchPlaceholder: "Emp code or name…",
      },
    }),
    []
  );

  const cards = [
    {
      key: "emp",
      label: "Employees",
      value: fmtCount(stats.total_emp),
      hint: "With salary rows",
    },
    {
      key: "rows",
      label: "Salary rows",
      value: fmtCount(stats.total_rows),
      hint: "All months",
    },
    {
      key: "months",
      label: "Payroll months",
      value: fmtCount(stats.distinct_months),
      hint: "Distinct yr/mth",
    },
    {
      key: "latest",
      label: "Latest month",
      value: dash(stats.latest_month),
      hint: "System-wide",
    },
    {
      key: "latest_emp",
      label: "In latest month",
      value: fmtCount(stats.latest_month_emp),
      hint: "Employees paid",
    },
  ];

  return (
    <div className="fp-dashboard">
      <header className="fp-dashboard__hero">
        <h1 className="fp-dashboard__title">Salary</h1>
        <div className="fp-dashboard__stats">
          {cards.map((card) => (
            <div key={card.key} className="fp-dashboard__stat">
              <span className="fp-dashboard__stat-label">{card.label}</span>
              <span className="fp-dashboard__stat-value">{card.value}</span>
              {card.hint ? (
                <span className="fp-dashboard__stat-hint">{card.hint}</span>
              ) : null}
            </div>
          ))}
        </div>
      </header>

      {listError ? (
        <div className="fp-dashboard__alert" role="alert">
          {listError}
        </div>
      ) : null}

      {error ? (
        <div className="fp-dashboard__alert" role="alert">
          {error}
        </div>
      ) : null}

      {message ? (
        <div className="fp-dashboard__alert fp-dashboard__alert--info" role="status">
          {message}
        </div>
      ) : null}

      {result?.found ? (
        <div id="esr-salary-detail" className="esr-result esr-result-dash">
          <button
            type="button"
            className="esr-detail-close"
            onClick={() => {
              setResult(null);
              setSelectedKey(null);
              setError("");
            }}
            aria-label="Close salary details"
          >
            Close
          </button>
          <div className="esr-profile">
            <div className="esr-avatar" aria-hidden="true">
              {(result.display_name || result.emp_cd || "?")
                .trim()
                .charAt(0)
                .toUpperCase()}
            </div>
            <div>
              <h2 className="esr-name">{result.display_name || "—"}</h2>
              <p className="esr-meta">
                Emp Code <strong>{result.emp_cd}</strong>
                {result.status ? (
                  <>
                    {" · "}
                    {result.status}
                  </>
                ) : null}
                {result.latest_month ? (
                  <>
                    {" · Latest "}
                    {result.latest_month}
                  </>
                ) : null}
              </p>
            </div>
          </div>

          {/* Oracle-style Salary header block */}
          <section className="esr-card esr-salary-card">
            <div className="esr-salary-card-head">
              <h3 className="esr-card-title">Salary</h3>
              <div className="esr-salary-actions">
                <button
                  type="button"
                  className="btn btn-sm btn-success esr-salary-add-btn"
                  onClick={addNextMonth}
                  disabled={!canAddNextMonth || loading || saving}
                  title={
                    canAddNextMonth
                      ? "Add next month with basic rate, scale, and earn codes 001 & 007 only"
                      : "Next month already added (or no salary to extend)"
                  }
                >
                  + Add next month
                </button>
                <button
                  type="button"
                  className="btn btn-sm btn-primary esr-salary-save-btn"
                  onClick={saveAddedMonth}
                  disabled={!pendingAddedMonth || saving || loading}
                  title="Save draft month (basic + 001/007) to salary tables"
                >
                  {saving ? "Saving…" : "Save month"}
                </button>
              </div>
            </div>
            <div className="esr-salary-table-wrap">
              <table className="esr-salary-table esr-salary-table--hdr">
                <thead>
                  <tr>
                    <th>Month</th>
                    <th>Year</th>
                    <th>Emp Cd</th>
                    <th>Emp Name</th>
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
                  {(result.months || []).map((m) => {
                    const key = `${m.sal_yr}-${m.sal_mth}`;
                    const active = key === (selectedKey || `${result.months[0]?.sal_yr}-${result.months[0]?.sal_mth}`);
                    return (
                      <tr
                        key={key}
                        className={[
                          active ? "is-selected" : "",
                          m.is_added ? "is-added" : "",
                        ]
                          .filter(Boolean)
                          .join(" ")}
                        onClick={() => setSelectedKey(key)}
                        onKeyDown={(e) => {
                          if (e.key === "Enter" || e.key === " ") {
                            e.preventDefault();
                            setSelectedKey(key);
                          }
                        }}
                        tabIndex={0}
                        role="button"
                        aria-pressed={active}
                      >
                        <td>
                          {m.sal_mth}
                          {m.is_added ? (
                            <span className="esr-salary-added-tag"> new</span>
                          ) : null}
                        </td>
                        <td>{m.sal_yr}</td>
                        <td>{result.emp_cd}</td>
                        <td className="name-cell">
                          {result.display_name || "—"}
                        </td>
                        <td className="num">
                          {m.is_added ? (
                            <input
                              type="number"
                              className="form-control form-control-sm esr-basic-input"
                              value={
                                m.basic_rate ?? m.basic ?? ""
                              }
                              step="0.01"
                              min="0"
                              onClick={(e) => e.stopPropagation()}
                              onFocus={(e) => e.stopPropagation()}
                              onChange={(e) => {
                                e.stopPropagation();
                                updateAddedBasic(key, e.target.value);
                              }}
                              onKeyDown={(e) => e.stopPropagation()}
                              aria-label="Basic rate for new month"
                            />
                          ) : (
                            fmtAmt(m.basic_rate ?? m.basic)
                          )}
                        </td>
                        <td>{dash(m.scale_desc)}</td>
                        <td className="num">
                          {fmtAmt(m.gross_earn_amt ?? m.gross)}
                        </td>
                        <td className="num">
                          {fmtAmt(m.net_earn_amt ?? m.net)}
                        </td>
                        <td className="num">
                          {fmtAmt(m.gross_dedn_amt ?? m.deduction)}
                        </td>
                        <td>{dash(m.wg_st_dt)}</td>
                        <td>{dash(m.wg_end_dt)}</td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
            <p className="esr-salary-hint">
              Click a salary month to view earning / deduction details.{" "}
              <strong>Add next month</strong> creates a draft (basic + scale, details
              001 &amp; 007). Edit <strong>Basic Rate</strong>, then click{" "}
              <strong>Save month</strong> to write it to salary tables.
            </p>
          </section>

          {/* Oracle-style Earning/Deduction detail block */}
          <section className="esr-card esr-salary-card">
            <h3 className="esr-card-title">
              Earning / Deduction Details
              {selectedMonth
                ? ` — ${selectedMonth.month_label || `${selectedMonth.sal_mth}/${selectedMonth.sal_yr}`}`
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
      ) : null}

      <section
        className="fp-dashboard__panel"
        onClick={handleListClick}
        onKeyDown={(e) => {
          if (e.key === "Enter" || e.key === " ") handleListClick(e);
        }}
      >
        <div className="fp-dashboard__panel-head">
          <h2 className="fp-dashboard__panel-title">Employees</h2>
          <p className="fp-dashboard__panel-hint">
            {loading
              ? "Loading salary…"
              : "Click Emp Code to open salary (last months + earn/dedn)"}
          </p>
        </div>
        <div className="fp-dashboard__panel-body">
          <SmpkDataTable
            ready
            tableKey="esr-salary-server"
            className="table table-striped table-hover table-sm w-100 smpk-datatable"
            options={options}
          >
            <thead>
              <tr>
                <th>Emp Code</th>
                <th>Name</th>
                <th>Last month</th>
                <th>Basic</th>
                <th>Gross</th>
                <th>Net</th>
                <th>Scale</th>
              </tr>
            </thead>
          </SmpkDataTable>
        </div>
      </section>
    </div>
  );
}
