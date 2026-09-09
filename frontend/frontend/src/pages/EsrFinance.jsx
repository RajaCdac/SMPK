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

const EMPTY_STATS = {
  total_rows: null,
  class_1: null,
  class_2: null,
  class_3: null,
  class_4: null,
  class_other: null,
  with_bank: null,
  suspended: null,
  quarter_flag: null,
};

export default function EsrFinance() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [listError, setListError] = useState("");
  const [result, setResult] = useState(null);
  const [stats, setStats] = useState(EMPTY_STATS);

  useEffect(() => {
    let cancelled = false;
    API.get("family-pension/esr/finance/", { params: { summary: 1 } })
      .then(({ data }) => {
        if (cancelled || !data || data.error) return;
        setStats({
          total_rows: data.total_rows,
          class_1: data.class_1,
          class_2: data.class_2,
          class_3: data.class_3,
          class_4: data.class_4,
          class_other: data.class_other,
          with_bank: data.with_bank,
          suspended: data.suspended,
          quarter_flag: data.quarter_flag,
        });
      })
      .catch(() => {});
    return () => {
      cancelled = true;
    };
  }, []);

  const loadFinance = useCallback(async (code) => {
    const cleaned = String(code || "").trim();
    if (!cleaned) return;
    setLoading(true);
    setError("");
    setResult(null);
    try {
      const { data } = await API.get("family-pension/esr/finance/", {
        params: { emp_cd: cleaned },
      });
      if (data?.error && !data?.found) {
        setError(data.error);
        return;
      }
      setResult(data);
      requestAnimationFrame(() => {
        document
          .getElementById("esr-finance-detail")
          ?.scrollIntoView({ behavior: "smooth", block: "start" });
      });
    } catch (err) {
      setError(apiErrorMessage(err, "Could not load finance record"));
    } finally {
      setLoading(false);
    }
  }, []);

  const handleListClick = (e) => {
    const pick = e.target.closest("[data-emp-cd]");
    if (!pick) return;
    const code = pick.getAttribute("data-emp-cd");
    if (code) loadFinance(code);
  };

  const options = useMemo(
    () => ({
      serverSide: true,
      processing: true,
      searching: true,
      ordering: true,
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
        { data: "emp_class", render: (d) => dash(d) },
        { data: "bank_cd", render: (d) => dash(d) },
        { data: "paymode_cd", render: (d) => dash(d) },
        { data: "bank_ac_no", render: (d) => dash(d) },
        { data: "scale_sl", render: (d) => dash(d) },
        { data: "scale_wef_dt", render: (d) => dash(d) },
        { data: "suspend_flg", render: (d) => dash(d) },
        { data: "final_stlmt_status", render: (d) => dash(d) },
      ],
      ajax: (dtReq, callback) => {
        const params = {
          draw: dtReq.draw,
          start: dtReq.start,
          length: dtReq.length,
          "search[value]": dtReq.search?.value || "",
          "order[0][column]": dtReq.order?.[0]?.column ?? 0,
          "order[0][dir]": dtReq.order?.[0]?.dir || "asc",
        };
        API.get("family-pension/esr/finance/", { params })
          .then(({ data }) => {
            setListError("");
            callback({
              draw: data.draw,
              recordsTotal: data.recordsTotal,
              recordsFiltered: data.recordsFiltered,
              data: Array.isArray(data.data) ? data.data : [],
            });
          })
          .catch((err) => {
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
      },
      language: {
        emptyTable: "No employees found",
        processing: "Loading…",
      },
    }),
    []
  );

  const cards = [
    {
      key: "total",
      label: "Total employees",
      value: fmtCount(stats.total_rows),
      hint: "Finance master",
    },
    {
      key: "c1",
      label: "Class I",
      value: fmtCount(stats.class_1),
      hint: "EMP_CLASS 1",
    },
    {
      key: "c2",
      label: "Class II",
      value: fmtCount(stats.class_2),
      hint: "EMP_CLASS 2",
    },
    {
      key: "c3",
      label: "Class III",
      value: fmtCount(stats.class_3),
      hint: "EMP_CLASS 3",
    },
    {
      key: "c4",
      label: "Class IV",
      value: fmtCount(stats.class_4),
      hint: "EMP_CLASS 4",
    },
    {
      key: "coth",
      label: "Class other",
      value: fmtCount(stats.class_other),
      hint: "Blank / other",
    },
    {
      key: "bank",
      label: "With bank",
      value: fmtCount(stats.with_bank),
      hint: "Bank code set",
    },
    {
      key: "susp",
      label: "Suspended",
      value: fmtCount(stats.suspended),
      hint: "Suspend flag",
    },
    {
      key: "qtr",
      label: "Quarter",
      value: fmtCount(stats.quarter_flag),
      hint: "QTR flag",
    },
  ];

  return (
    <div className="fp-dashboard">
      <header className="fp-dashboard__hero">
        <h1 className="fp-dashboard__title">Finance</h1>
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

      {result?.found ? (
        <div id="esr-finance-detail" className="esr-result esr-result-dash">
          <button
            type="button"
            className="esr-detail-close"
            onClick={() => {
              setResult(null);
              setError("");
            }}
            aria-label="Close employee details"
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
                {result.fields?.EMP_CLASS &&
                result.fields.EMP_CLASS !== "—" ? (
                  <>
                    {" · Class "}
                    {result.fields.EMP_CLASS}
                  </>
                ) : null}
                {result.fields?.BANK_CD && result.fields.BANK_CD !== "—" ? (
                  <>
                    {" · "}
                    {result.fields.BANK_CD}
                  </>
                ) : null}
              </p>
            </div>
          </div>

          <div className="esr-sections">
            {(result.sections || []).map((sec) => (
              <section
                key={sec.id}
                className={`esr-card${
                  sec.id === "identity" ? " esr-card-identity" : ""
                }`}
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
              ? "Loading record…"
              : "Click Emp Code to open finance record"}
          </p>
        </div>
        <div className="fp-dashboard__panel-body">
          <SmpkDataTable
            ready
            tableKey="esr-finance-server"
            className="table table-striped table-hover table-sm w-100 smpk-datatable"
            options={options}
          >
            <thead>
              <tr>
                <th>Emp Code</th>
                <th>Name</th>
                <th>Class</th>
                <th>Bank</th>
                <th>Pay mode</th>
                <th>A/C No</th>
                <th>Scale</th>
                <th>Scale WEF</th>
                <th>Suspend</th>
                <th>Final stlmt</th>
              </tr>
            </thead>
          </SmpkDataTable>
        </div>
      </section>
    </div>
  );
}
