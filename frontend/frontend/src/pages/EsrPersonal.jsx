import { useCallback, useEffect, useMemo, useState } from "react";
import API from "../services/Api";
import SmpkDataTable from "../components/DataTable/SmpkDataTable";
import EsrPersonalForm from "../components/EsrPersonalForm";
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
  male: null,
  female: null,
  regular_emp: null,
  probationary: null,
  trainee: null,
  deputation_wb: null,
  deputation_central: null,
  pensioner: null,
  family_pensioner: null,
  exgratia: null,
  doctor: null,
};

export default function EsrPersonal() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [listError, setListError] = useState("");
  const [result, setResult] = useState(null);
  const [stats, setStats] = useState(EMPTY_STATS);

  useEffect(() => {
    let cancelled = false;
    API.get("family-pension/esr/personal/", { params: { summary: 1 } })
      .then(({ data }) => {
        if (cancelled || !data || data.error) return;
        setStats({
          total_rows: data.total_rows,
          male: data.male,
          female: data.female,
          regular_emp: data.regular_emp,
          probationary: data.probationary,
          trainee: data.trainee,
          deputation_wb: data.deputation_wb,
          deputation_central: data.deputation_central,
          pensioner: data.pensioner,
          family_pensioner: data.family_pensioner,
          exgratia: data.exgratia,
          doctor: data.doctor,
        });
      })
      .catch(() => {});
    return () => {
      cancelled = true;
    };
  }, []);

  const loadPersonal = useCallback(async (code) => {
    const cleaned = String(code || "").trim();
    if (!cleaned) return;
    setLoading(true);
    setError("");
    setResult(null);
    try {
      const { data } = await API.get("family-pension/esr/personal/", {
        params: { emp_cd: cleaned },
      });
      if (data?.error && !data?.found) {
        setError(data.error);
        return;
      }
      setResult(data);
      requestAnimationFrame(() => {
        document.getElementById("esr-personal-form-anchor")?.focus();
      });
    } catch (err) {
      setError(apiErrorMessage(err, "Could not load personal record"));
    } finally {
      setLoading(false);
    }
  }, []);

  const handleListClick = (e) => {
    const pick = e.target.closest("[data-emp-cd]");
    if (!pick) return;
    const code = pick.getAttribute("data-emp-cd");
    if (code) loadPersonal(code);
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
            return `<button type="button" class="esr-emp-pick" data-emp-cd="${String(
              d
            ).replace(/"/g, "")}">${code}</button>`;
          },
        },
        { data: "full_name", render: (d) => dash(d) },
        { data: "sex", render: (d) => dash(d) },
        { data: "birth_dt", render: (d) => dash(d) },
        { data: "category", render: (d) => dash(d) },
        { data: "marital_status", render: (d) => dash(d) },
        { data: "city", render: (d) => dash(d) },
        { data: "contact", render: (d) => dash(d) },
        { data: "status", render: (d) => dash(d) },
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
        API.get("family-pension/esr/personal/", { params })
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
      hint: "Master rows",
    },
    {
      key: "male",
      label: "Male",
      value: fmtCount(stats.male),
      hint: "Sex M",
    },
    {
      key: "female",
      label: "Female",
      value: fmtCount(stats.female),
      hint: "Sex F",
    },
    {
      key: "re",
      label: "Regular Emp",
      value: fmtCount(stats.regular_emp),
      hint: "Status RE",
    },
    {
      key: "pe",
      label: "Probationary",
      value: fmtCount(stats.probationary),
      hint: "Status PE",
    },
    {
      key: "te",
      label: "Trainee",
      value: fmtCount(stats.trainee),
      hint: "Status TE",
    },
    {
      key: "dw",
      label: "Deput. WB",
      value: fmtCount(stats.deputation_wb),
      hint: "Status DW",
    },
    {
      key: "dc",
      label: "Deput. Central",
      value: fmtCount(stats.deputation_central),
      hint: "Status DC",
    },
    {
      key: "pn",
      label: "Pensioner",
      value: fmtCount(stats.pensioner),
      hint: "Status PN",
    },
    {
      key: "fp",
      label: "Family Pensioner",
      value: fmtCount(stats.family_pensioner),
      hint: "Status FP",
    },
    {
      key: "eg",
      label: "Exgratia holder",
      value: fmtCount(stats.exgratia),
      hint: "Status EG",
    },
    {
      key: "doctor",
      label: "Doctor",
      value: fmtCount(stats.doctor),
      hint: "Doctor flag 1",
    },
  ];

  return (
    <div className="fp-dashboard">
      <header className="fp-dashboard__hero">
        <h1 className="fp-dashboard__title">Personal</h1>
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

      {result?.found || loading ? (
        <>
          <span
            id="esr-personal-form-anchor"
            tabIndex={-1}
            className="esr-form-anchor"
            aria-hidden="true"
          />
          <EsrPersonalForm
            form={result?.form}
            loading={loading}
            onClose={() => {
              setResult(null);
              setError("");
            }}
          />
        </>
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
              : "Click Emp Code to open personal record"}
          </p>
        </div>
        <div className="fp-dashboard__panel-body">
          <SmpkDataTable
            ready
            tableKey="esr-personal-server"
            className="table table-striped table-hover table-sm w-100 smpk-datatable"
            options={options}
          >
            <thead>
              <tr>
                <th>Emp Code</th>
                <th>Name</th>
                <th>Sex</th>
                <th>Date of Birth</th>
                <th>Category</th>
                <th>Marital</th>
                <th>City</th>
                <th>Contact</th>
                <th>Status</th>
              </tr>
            </thead>
          </SmpkDataTable>
        </div>
      </section>
    </div>
  );
}
