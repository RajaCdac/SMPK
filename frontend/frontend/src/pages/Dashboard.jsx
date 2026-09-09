import "../styles/Dashboard.css";
import { memo, useCallback, useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import API from "../services/Api";
import SmpkDataTable from "../components/DataTable/SmpkDataTable";
import DashboardWorkflowStatus from "../components/DashboardWorkflowStatus";

function formatAge(age) {
  if (!age || age.years == null) return "N/A";
  const parts = [`${age.years} yrs`];
  if (age.months != null) parts.push(`${age.months} mn`);
  if (age.days != null) parts.push(`${age.days} days`);
  return parts.join(" ");
}

/**
 * Isolated, memoized retirement table.
 *
 * Kept separate from Dashboard's modal/search-input state so that opening the
 * Process modal (or typing in the search box) does NOT re-render the
 * DataTables-managed table. It only re-renders when `dataVersion` changes
 * (initial load / search / reset), which remounts the grid with fresh rows.
 */
const RetirementTable = memo(function RetirementTable({
  rows,
  ready,
  dataVersion,
}) {
  return (
    <SmpkDataTable
      ready={ready}
      tableKey={`retire-${dataVersion}`}
      className="table table-striped table-hover w-100 employee-table smpk-datatable"
      options={{
        order: [[4, "asc"]],
        columnDefs: [
          {
            targets: 11,
            orderable: false,
            searchable: false,
            responsivePriority: 1,
          },
        ],
        language: { emptyTable: "No employees found" },
      }}
    >
      <thead>
        <tr>
          <th>Emp Code</th>
          <th>Name</th>
          <th>Class</th>
          <th>Joining Date</th>
          <th>Retirement Date</th>
          <th>Birth Date</th>
          <th>Designation</th>
          <th>Scale</th>
          <th>Last Basic</th>
          <th>Age on Appointment</th>
          <th>Age on Retirement</th>
          <th>Action</th>
        </tr>
      </thead>
      <tbody>
        {rows.map((e) => (
          <tr key={e.emp_code}>
            <td>{e.emp_code}</td>
            <td>{e.name}</td>
            <td>{e.class}</td>
            <td>{e.joining_date}</td>
            <td>{e.retirement_date}</td>
            <td>{e.birth_date}</td>
            <td>{e.designation}</td>
            <td>{e.scale}</td>
            <td data-order={e.last_basic}>₹ {e.last_basic}</td>
            <td>{formatAge(e.age_on_appointment)}</td>
            <td>{formatAge(e.age_on_retirement)}</td>
            <td
              className="dashboard-action-cell"
              data-order={e.workflow_status || "not_started"}
            >
              <div className="dashboard-action-cell__inner">
                <button
                  type="button"
                  className="process-btn"
                  data-process-emp={e.emp_code}
                >
                  Process
                </button>
                <DashboardWorkflowStatus row={e} />
              </div>
            </td>
          </tr>
        ))}
      </tbody>
    </SmpkDataTable>
  );
});

export default function Dashboard() {
  const navigate = useNavigate();

  const [data, setData] = useState({
    total_employees: 0,
    retirement_count: 0,
    retirement_list: [],
    prev_month_count: 0,
    next_month_count: 0,
    prev_month_label: "Previous Month",
    this_month_label: "This Month",
    next_month_label: "Next Month",
  });

  const [filteredData, setFilteredData] = useState([]);
  const [dataVersion, setDataVersion] = useState(0);

  const [searchMonth, setSearchMonth] = useState("");
  const [searchYear, setSearchYear] = useState("");

  const [dashboardReady, setDashboardReady] = useState(false);
  const [loadError, setLoadError] = useState("");
  const tableContainerRef = useRef(null);
  const rowsByEmpCodeRef = useRef({});

  useEffect(() => {
    const map = {};
    filteredData.forEach((row) => {
      map[String(row.emp_code)] = row;
    });
    rowsByEmpCodeRef.current = map;
  }, [filteredData]);

  const handleProcess = useCallback(
    (emp) => {
      const code = String(emp?.emp_code || "").trim();
      if (!code) return;
      navigate(
        `/dashboard/firstpensioncases?emp=${encodeURIComponent(code)}`
      );
    },
    [navigate]
  );

  useEffect(() => {
    const root = tableContainerRef.current;
    if (!root) return undefined;

    const onTableClick = (event) => {
      const btn = event.target.closest("[data-process-emp]");
      if (!btn || !root.contains(btn)) return;
      event.preventDefault();
      event.stopPropagation();
      const emp = rowsByEmpCodeRef.current[btn.getAttribute("data-process-emp")];
      if (emp) handleProcess(emp);
    };

    root.addEventListener("click", onTableClick);
    return () => root.removeEventListener("click", onTableClick);
  }, [handleProcess, dashboardReady]);

  useEffect(() => {
    setDashboardReady(false);
    setLoadError("");
    API.get("dashboard/")
      .then((res) => {
        setData(res.data);
        setFilteredData(res.data.retirement_list);
        setDataVersion((v) => v + 1);
      })
      .catch((err) => {
        console.error(err);
        setLoadError(
          err.response?.data?.detail ||
            err.response?.data?.error ||
            "Could not load retirement list. Check backend is running and DB is connected."
        );
      })
      .finally(() => setDashboardReady(true));
  }, []);

  const handleSearch = async () => {
    try {
      setLoadError("");
      const res = await API.get(
        `dashboard/?month=${searchMonth}&year=${searchYear}`
      );
      setData(res.data);
      setFilteredData(res.data.retirement_list);
      setDataVersion((v) => v + 1);
    } catch (err) {
      console.error(err);
      setLoadError(
        err.response?.data?.detail ||
          err.response?.data?.error ||
          "Search failed. Check backend and database connection."
      );
    }
  };

  const handleReset = () => {
    setSearchMonth("");
    setSearchYear("");
    setFilteredData(data.retirement_list);
    setDataVersion((v) => v + 1);
  };

  return (

    <div className="dashboard-page"><div className="dashboard-header">

        <div>

          <h1 className="dashboard-heading" style={{color: "black"}}>
            Pension Dashboard
          </h1>
        </div>

      </div><div className="dashboard-cards dashboard-cards-3">

        <div className="dashboard-card card-prev">

          <div className="card-icon">
            📅
          </div>

          <div>

            <h3>Retired Previous Month</h3>

            <span className="card-subtitle">{data.prev_month_label}</span>

            <h2>
              {data.prev_month_count}
            </h2>

          </div>

        </div>

        <div className="dashboard-card card-current">

          <div className="card-icon">
            📋
          </div>

          <div>

            <h3>Retiring This Month</h3>

            <span className="card-subtitle">{data.this_month_label}</span>

            <h2>
              {data.retirement_count}
            </h2>

          </div>

        </div>

        <div className="dashboard-card card-next">

          <div className="card-icon">
            ⏭️
          </div>

          <div>

            <h3>Retiring Next Month</h3>

            <span className="card-subtitle">{data.next_month_label}</span>

            <h2>
              {data.next_month_count}
            </h2>

          </div>

        </div>

      </div>

      <div className="search-container">

        <h3 className="search-title">
          Search Retirement Employees
        </h3>

        <div className="search-box smpk-form">

          <select
            value={searchMonth}
            className="form-select"
            onChange={(e) =>
              setSearchMonth(e.target.value) 
            }
          >

            <option value="">
              Select Month
            </option>

            <option value="1">January</option>
            <option value="2">February</option>
            <option value="3">March</option>
            <option value="4">April</option>
            <option value="5">May</option>
            <option value="6">June</option>
            <option value="7">July</option>
            <option value="8">August</option>
            <option value="9">September</option>
            <option value="10">October</option>
            <option value="11">November</option>
            <option value="12">December</option>

          </select>

          <input
            type="number"
            className="form-control"
            placeholder="Enter Year"
            value={searchYear}
            onChange={(e) =>
              setSearchYear(e.target.value)
            }
          />

          <button
            className="search-btn"
            onClick={handleSearch}
          >
            Search
          </button>

          <button
            className="reset-btn"
            onClick={handleReset}
          >
            Reset
          </button>

        </div>

      </div><div
        ref={tableContainerRef}
        className="table-container"
        style={{ color: "black" }}
      >

        <h3 className="table-title">
          Employees Retiring This Month
        </h3>

        {loadError ? (
          <div className="alert alert-danger" role="alert">
            {loadError}
          </div>
        ) : null}

        <RetirementTable
          rows={filteredData}
          ready={dashboardReady}
          dataVersion={dataVersion}
        />

      </div>

    </div>

  );

}
