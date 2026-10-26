import { useCallback, useEffect, useState } from "react";
import API from "../services/Api";
import SmpkDataTable from "../components/DataTable/SmpkDataTable";
import "../styles/AuditLogs.css";

function cell(value) {
  const text = String(value ?? "").trim();
  return text || "—";
}

export default function AdminConsolidationByUser() {
  const [users, setUsers] = useState([]);
  const [dates, setDates] = useState([]);
  const [rows, setRows] = useState([]);
  const [username, setUsername] = useState("");
  const [fromDate, setFromDate] = useState("");
  const [toDate, setToDate] = useState("");
  const [query, setQuery] = useState("");
  const [activeQuery, setActiveQuery] = useState("");
  const [activeUser, setActiveUser] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const load = useCallback(async (params) => {
    setLoading(true);
    setError("");
    try {
      const { data } = await API.get("methodology2/admin/consolidation-by-user/", {
        params,
      });
      setUsers(Array.isArray(data.users) ? data.users : []);
      setDates(Array.isArray(data.dates) ? data.dates : []);
      setRows(Array.isArray(data.rows) ? data.rows : []);
      setActiveQuery(String(data.q || ""));
      setActiveUser(String(data.username || ""));
    } catch (err) {
      const detail = err?.response?.data?.error || err?.response?.data?.detail;
      setError(detail || "Could not load the consolidation report.");
      setDates([]);
      setRows([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load({});
  }, [load]);

  const showUser = (event) => {
    event.preventDefault();
    setQuery("");
    load({
      username,
      from_date: fromDate,
      to_date: toDate,
    });
  };

  const findCreator = (event) => {
    event.preventDefault();
    const q = query.trim();
    if (!q) {
      setError("Enter an employee code, case number, or name.");
      return;
    }
    load({
      q,
      from_date: fromDate,
      to_date: toDate,
    });
  };

  const userKey = users.map((row) => `${row.username}:${row.total}`).join("|");
  const dateKey = dates.map((row) => `${row.date_iso}:${row.total}`).join("|");
  const rowKey = rows
    .map((row) => `${row.source}:${row.emp_cd}:${row.saved_at}`)
    .join("|");

  return (
    <div className="audit-page">
      <div className="audit-header">
        <h1>Consolidation by user</h1>
        <p>
          Choose a user to see how many consolidations they saved, date by date.
          Search an employee or case number to see who created it.
        </p>
      </div>

      <form
        className="card border-0 shadow-sm mb-3"
        onSubmit={showUser}
      >
        <div className="card-body row g-3 align-items-end">
          <div className="col-12 col-md-4">
            <label className="form-label" htmlFor="consol-user">
              User
            </label>
            <select
              id="consol-user"
              className="form-select"
              value={username}
              onChange={(event) => setUsername(event.target.value)}
            >
              <option value="">All users</option>
              {users.map((row) => (
                <option key={row.filter_key || row.username} value={row.filter_key || row.username}>
                  {row.username}
                  {row.total ? ` (${row.total})` : ""}
                </option>
              ))}
            </select>
          </div>
          <div className="col-6 col-md-2">
            <label className="form-label" htmlFor="consol-from">
              From
            </label>
            <input
              id="consol-from"
              type="date"
              className="form-control"
              value={fromDate}
              onChange={(event) => setFromDate(event.target.value)}
            />
          </div>
          <div className="col-6 col-md-2">
            <label className="form-label" htmlFor="consol-to">
              To
            </label>
            <input
              id="consol-to"
              type="date"
              className="form-control"
              value={toDate}
              onChange={(event) => setToDate(event.target.value)}
            />
          </div>
          <div className="col-12 col-md-2">
            <button type="submit" className="btn btn-primary w-100" disabled={loading}>
              Show
            </button>
          </div>
        </div>
      </form>

      <form className="card border-0 shadow-sm mb-4" onSubmit={findCreator}>
        <div className="card-body row g-3 align-items-end">
          <div className="col-12 col-md-6">
            <label className="form-label" htmlFor="consol-find">
              Find who created a consolidation
            </label>
            <input
              id="consol-find"
              className="form-control"
              placeholder="Employee code, case number, or name"
              value={query}
              onChange={(event) => setQuery(event.target.value)}
            />
          </div>
          <div className="col-12 col-md-2">
            <button type="submit" className="btn btn-outline-primary w-100" disabled={loading}>
              Search
            </button>
          </div>
        </div>
      </form>

      {error ? <div className="alert alert-danger">{error}</div> : null}

      {!activeUser && !activeQuery ? (
        <div className="audit-table-container mb-4">
          <h2 className="h5 mb-3">How much each user has saved</h2>
          <SmpkDataTable
            tableKey={`users-${userKey}`}
            ready={!loading}
            options={{ order: [[3, "desc"]] }}
          >
            <thead>
              <tr>
                <th>User</th>
                <th className="text-end">Methodology-2</th>
                <th className="text-end">Old age</th>
                <th className="text-end">Total</th>
                <th>Last saved</th>
              </tr>
            </thead>
            <tbody>
              {users.map((row) => (
                <tr key={row.filter_key || row.username}>
                  <td>{cell(row.username)}</td>
                  <td className="text-end" data-order={row.methodology2}>
                    {row.methodology2}
                  </td>
                  <td className="text-end" data-order={row.old_age}>
                    {row.old_age}
                  </td>
                  <td className="text-end" data-order={row.total}>
                    {row.total}
                  </td>
                  <td data-order={row.last_iso || ""}>{cell(row.last_date)}</td>
                </tr>
              ))}
            </tbody>
          </SmpkDataTable>
        </div>
      ) : null}

      {activeUser && !activeQuery ? (
        <div className="audit-table-container mb-4">
          <h2 className="h5 mb-3">
            {activeUser === "__none__" ? "Not recorded" : activeUser} — by date
          </h2>
          <SmpkDataTable
            tableKey={`dates-${activeUser}-${dateKey}`}
            ready={!loading}
            options={{ order: [[0, "desc"]] }}
          >
            <thead>
              <tr>
                <th>Date</th>
                <th className="text-end">Methodology-2</th>
                <th className="text-end">Old age</th>
                <th className="text-end">Total</th>
              </tr>
            </thead>
            <tbody>
              {dates.map((row) => (
                <tr key={row.date_iso || row.date}>
                  <td data-order={row.date_iso || ""}>{cell(row.date)}</td>
                  <td className="text-end" data-order={row.methodology2}>
                    {row.methodology2}
                  </td>
                  <td className="text-end" data-order={row.old_age}>
                    {row.old_age}
                  </td>
                  <td className="text-end" data-order={row.total}>
                    {row.total}
                  </td>
                </tr>
              ))}
            </tbody>
          </SmpkDataTable>
        </div>
      ) : null}

      {activeUser || activeQuery ? (
        <div className="audit-table-container">
          <h2 className="h5 mb-3">
            {activeQuery
              ? `Who created “${activeQuery}”`
              : `${activeUser === "__none__" ? "Not recorded" : activeUser} — consolidations`}
          </h2>
          <SmpkDataTable
            tableKey={`rows-${activeUser}-${activeQuery}-${rowKey}`}
            ready={!loading}
            options={{ order: [[0, "desc"]] }}
          >
            <thead>
              <tr>
                <th>Saved at</th>
                <th>Emp CD</th>
                <th>Name</th>
                <th>Case No</th>
                <th>Roll No</th>
                <th>Category</th>
                <th>Type</th>
                <th>Created by</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((row) => (
                <tr key={`${row.source}-${row.emp_cd}-${row.saved_at}`}>
                  <td className="text-nowrap" data-order={row.saved_at || ""}>
                    {cell(row.saved_at)}
                  </td>
                  <td>{cell(row.emp_cd)}</td>
                  <td>{cell(row.name)}</td>
                  <td>{cell(row.case_no)}</td>
                  <td>{cell(row.roll_no)}</td>
                  <td>{cell(row.category)}</td>
                  <td>{cell(row.source)}</td>
                  <td>{cell(row.consolidated_by)}</td>
                </tr>
              ))}
            </tbody>
          </SmpkDataTable>
        </div>
      ) : null}
    </div>
  );
}
