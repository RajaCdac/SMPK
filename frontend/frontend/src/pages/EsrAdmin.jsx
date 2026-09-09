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
  in_service: null,
  separated: null,
  retired: null,
  death: null,
  voluntary_ret: null,
  terminated: null,
  hindi_known: null,
};

export default function EsrAdmin() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [listError, setListError] = useState("");
  const [result, setResult] = useState(null);
  const [stats, setStats] = useState(EMPTY_STATS);

  useEffect(() => {
    let cancelled = false;
    API.get("family-pension/esr/admin/", { params: { summary: 1 } })
      .then(({ data }) => {
        if (cancelled || !data || data.error) return;
        setStats({
          total_rows: data.total_rows,
          in_service: data.in_service,
          separated: data.separated,
          retired: data.retired,
          death: data.death,
          voluntary_ret: data.voluntary_ret,
          terminated: data.terminated,
          hindi_known: data.hindi_known,
        });
      })
      .catch(() => {});
    return () => {
      cancelled = true;
    };
  }, []);

  const loadAdmin = useCallback(async (code) => {
    const cleaned = String(code || "").trim();
    if (!cleaned) return;
    setLoading(true);
    setError("");
    setResult(null);
    try {
      const { data } = await API.get("family-pension/esr/admin/", {
        params: { emp_cd: cleaned },
      });
      if (data?.error && !data?.found) {
        setError(data.error);
        return;
      }
      setResult(data);
      requestAnimationFrame(() => {
        document
          .getElementById("esr-admin-detail")
          ?.scrollIntoView({ behavior: "smooth", block: "start" });
      });
    } catch (err) {
      setError(apiErrorMessage(err, "Could not load admin record"));
    } finally {
      setLoading(false);
    }
  }, []);

  const handleListClick = (e) => {
    const pick = e.target.closest("[data-emp-cd]");
    if (!pick) return;
    const code = pick.getAttribute("data-emp-cd");
    if (code) loadAdmin(code);
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
        { data: "desig_cd", render: (d) => dash(d) },
        { data: "join_dt", render: (d) => dash(d) },
        { data: "confirm_dt", render: (d) => dash(d) },
        { data: "separation_type", render: (d) => dash(d) },
        { data: "separation_dt", render: (d) => dash(d) },
        { data: "exp_ret_dt", render: (d) => dash(d) },
        { data: "pf_type", render: (d) => dash(d) },
        { data: "pan_no", render: (d) => dash(d) },
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
        API.get("family-pension/esr/admin/", { params })
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
      hint: "Admin master",
    },
    {
      key: "service",
      label: "In service",
      value: fmtCount(stats.in_service),
      hint: "No sep. date",
    },
    {
      key: "sep",
      label: "Separated",
      value: fmtCount(stats.separated),
      hint: "Has sep. date",
    },
    {
      key: "rt",
      label: "Retirement",
      value: fmtCount(stats.retired),
      hint: "Type RT",
    },
    {
      key: "dt",
      label: "Death",
      value: fmtCount(stats.death),
      hint: "Type DT",
    },
    {
      key: "vr",
      label: "Voluntary ret.",
      value: fmtCount(stats.voluntary_ret),
      hint: "Type VR",
    },
    {
      key: "tn",
      label: "Terminated",
      value: fmtCount(stats.terminated),
      hint: "Type TN",
    },
    {
      key: "hi",
      label: "Hindi known",
      value: fmtCount(stats.hindi_known),
      hint: "Hindi flag",
    },
  ];

  return (
    <div className="fp-dashboard">
      <header className="fp-dashboard__hero">
        <h1 className="fp-dashboard__title">Admin</h1>
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
        <div id="esr-admin-detail" className="esr-result esr-result-dash">
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
                {result.fields?.DESIG_CD && result.fields.DESIG_CD !== "—" ? (
                  <>
                    {" · "}
                    {result.fields.DESIG_CD}
                  </>
                ) : null}
                {result.fields?.JOIN_DT && result.fields.JOIN_DT !== "—" ? (
                  <>
                    {" · Joined "}
                    {result.fields.JOIN_DT}
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
              : "Click Emp Code to open admin record"}
          </p>
        </div>
        <div className="fp-dashboard__panel-body">
          <SmpkDataTable
            ready
            tableKey="esr-admin-server"
            className="table table-striped table-hover table-sm w-100 smpk-datatable"
            options={options}
          >
            <thead>
              <tr>
                <th>Emp Code</th>
                <th>Name</th>
                <th>Desig</th>
                <th>Join Date</th>
                <th>Confirm Date</th>
                <th>Sep. Type</th>
                <th>Sep. Date</th>
                <th>Exp. Ret.</th>
                <th>PF Type</th>
                <th>PAN</th>
              </tr>
            </thead>
          </SmpkDataTable>
        </div>
      </section>
    </div>
  );
}
