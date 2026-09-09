import { useEffect, useMemo, useState } from "react";
import API from "../services/Api";
import SmpkDataTable from "../components/DataTable/SmpkDataTable";
import "../styles/Dashboard.css";
import "../styles/FamilyPensionDashboard.css";

function fmtAmt(value) {
  if (value == null || value === "") return "—";
  const n = Number(value);
  if (Number.isNaN(n)) return String(value);
  return n.toLocaleString("en-IN", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
}

function fmtCount(value) {
  if (value == null || value === "") return "—";
  const n = Number(value);
  if (Number.isNaN(n)) return "—";
  return n.toLocaleString("en-IN");
}

function fmtCpi(value) {
  if (value == null || value === "") return "—";
  const n = Number(value);
  if (Number.isNaN(n)) return String(value);
  return Number.isInteger(n) ? String(n) : n.toFixed(2);
}

function dash(value) {
  if (value == null || value === "") return "—";
  return String(value);
}

const EMPTY_STATS = {
  total_rows: null,
  unique_emps: null,
  from_eform: null,
  from_proposal: null,
  class_1_2: null,
  class_3_4: null,
  class_other: null,
};

export default function FamilyPensionCase() {
  const [error, setError] = useState("");
  const [stats, setStats] = useState(EMPTY_STATS);

  useEffect(() => {
    let cancelled = false;
    API.get("family-pension/pensioners/", { params: { summary: 1 } })
      .then(({ data }) => {
        if (cancelled || !data || data.error) return;
        setStats({
          total_rows: data.total_rows,
          unique_emps: data.unique_emps,
          from_eform: data.from_eform,
          from_proposal: data.from_proposal,
          class_1_2: data.class_1_2,
          class_3_4: data.class_3_4,
          class_other: data.class_other,
        });
      })
      .catch(() => {
        /* table load has its own error path; cards stay as — */
      });
    return () => {
      cancelled = true;
    };
  }, []);

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
        { data: "emp_cd", render: (d) => dash(d) },
        { data: "roll_no", render: (d) => dash(d) },
        { data: "claim_id", render: (d) => dash(d) },
        { data: "ca_number", render: (d) => dash(d) },
        {
          data: "original_single_pension_amt",
          className: "text-end",
          render: (d) => fmtAmt(d),
        },
        {
          data: "original_double_pension_amt",
          className: "text-end",
          render: (d) => fmtAmt(d),
        },
        {
          data: "base_cpi",
          className: "text-end",
          render: (d) => fmtCpi(d),
        },
        { data: "app_class", render: (d) => dash(d) },
        { data: "emp_ret_dt", render: (d) => dash(d) },
        { data: "wef_dt", render: (d) => dash(d) },
        { data: "double_pension_upto", render: (d) => dash(d) },
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
        API.get("family-pension/pensioners/", { params })
          .then(({ data }) => {
            setError("");
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
              "Failed to load family pensioners";
            setError(String(msg));
            callback({
              draw: dtReq.draw,
              recordsTotal: 0,
              recordsFiltered: 0,
              data: [],
            });
          });
      },
      language: {
        emptyTable: "No family pensioners found",
        processing: "Loading…",
      },
    }),
    []
  );

  const cards = [
    {
      key: "records",
      label: "Total records",
      value: fmtCount(stats.total_rows),
      hint: "Master rows",
    },
    {
      key: "emps",
      label: "Employees",
      value: fmtCount(stats.unique_emps),
      hint: "Distinct Emp ID",
    },
    {
      key: "eform",
      label: "From E-Form",
      value: fmtCount(stats.from_eform),
      hint: "Master rows · CM",
    },
    {
      key: "proposal",
      label: "From Proposal",
      value: fmtCount(stats.from_proposal),
      hint: "Master rows · CA",
    },
    {
      key: "c12",
      label: "Class I–II",
      value: fmtCount(stats.class_1_2),
      hint: "Employees",
    },
    {
      key: "c34",
      label: "Class III–IV",
      value: fmtCount(stats.class_3_4),
      hint: "Employees",
    },
    {
      key: "coth",
      label: "Class other",
      value: fmtCount(stats.class_other),
      hint: "Blank / not 1–4",
    },
  ];

  return (
    <div className="fp-dashboard">
      <header className="fp-dashboard__hero">
        <h1 className="fp-dashboard__title">Dashboard</h1>
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

      {error ? <div className="fp-dashboard__alert">{error}</div> : null}

      <section className="fp-dashboard__panel">
        <div className="fp-dashboard__panel-head">
          <h2 className="fp-dashboard__panel-title">Family pensioners</h2>
          <p className="fp-dashboard__panel-hint">
            Search tip: type <code>cm</code> or <code>ca</code> for claim source
            (E-Form / Proposal); other text searches Emp / Roll / Claim / CA no
          </p>
        </div>
        <div className="fp-dashboard__panel-body">
          <SmpkDataTable
            ready
            tableKey="fp-server-side"
            className="table table-striped table-hover table-sm w-100 smpk-datatable"
            options={options}
          >
            <thead>
              <tr>
                <th>Emp ID</th>
                <th>Roll No</th>
                <th>Claim ID</th>
                <th>CA Number</th>
                <th>Original Single</th>
                <th>Original Double</th>
                <th>Base CPI</th>
                <th>Class</th>
                <th>Emp Ret Date</th>
                <th>WEF Date</th>
                <th>Double Upto</th>
              </tr>
            </thead>
          </SmpkDataTable>
        </div>
      </section>
    </div>
  );
}
