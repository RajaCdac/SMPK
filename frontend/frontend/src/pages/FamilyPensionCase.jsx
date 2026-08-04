import { useMemo, useState } from "react";
import API from "../services/Api";
import SmpkDataTable from "../components/DataTable/SmpkDataTable";
import "../styles/Dashboard.css";

function fmtAmt(value) {
  if (value == null || value === "") return "—";
  const n = Number(value);
  if (Number.isNaN(n)) return String(value);
  return n.toLocaleString("en-IN", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
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

export default function FamilyPensionCase() {
  const [error, setError] = useState("");
  const [totalHint, setTotalHint] = useState(null);

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
            if (typeof data?.recordsTotal === "number") {
              setTotalHint(data.recordsTotal);
            }
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

  return (
    <div className="container-fluid mt-3 mt-md-4 px-2 px-md-3">
      <div className="d-flex flex-wrap align-items-center justify-content-between gap-2 mb-3">
        <div>
          <h4 className="mb-1">Dashboard</h4>
          <p className="text-muted mb-0 small">
            Family pensioners · Source:{" "}
            <code>smpk_pension.fi_pn_mh_familypensioner</code>
            {totalHint != null
              ? ` · ${totalHint.toLocaleString("en-IN")} records`
              : ""}
            {" · server-side paging"}
          </p>
        </div>
      </div>

      {error ? <div className="alert alert-danger">{error}</div> : null}

      <div className="card shadow-sm">
        <div className="card-body">
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
      </div>
    </div>
  );
}
