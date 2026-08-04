import { useEffect, useState } from "react";
import API from "../services/Api";
import PensionReportModal from "../components/PensionReportModal";
import SmpkDataTable from "../components/DataTable/SmpkDataTable";
import "../styles/PensionCaseList.css";

export default function PensionCaseList() {
  const [cases, setCases] = useState([]);
  const [loading, setLoading] = useState(true);
  const [reportCaseId, setReportCaseId] = useState(null);

  useEffect(() => {
    setLoading(true);
    API.get("first-pension/cases/")
      .then((res) => setCases(Array.isArray(res.data) ? res.data : []))
      .catch((err) => console.error(err))
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="case-page">
      <div className="case-header">
        <div>
          <h1>Pension Cases</h1>
          <p>View and manage all processed pension cases</p>
        </div>
        <div className="case-count">
          <span>Total Cases</span>
          <h2>{cases.length}</h2>
        </div>
      </div>

      <SmpkDataTable
          ready={!loading}
          tableKey={cases.map((c) => c.id).join("-") || "empty"}
          className="table table-striped table-hover w-100 case-table smpk-datatable"
          options={{
            order: [[3, "desc"]],
            columnDefs: [{ targets: 6, orderable: false, searchable: false }],
            language: { emptyTable: "No pension cases found" },
          }}
        >
          <thead>
            <tr>
              <th>Emp Code</th>
              <th>Name</th>
              <th>Designation</th>
              <th>Retirement Date</th>
              <th>Status</th>
              <th>Last Basic</th>
              <th>Action</th>
            </tr>
          </thead>
          <tbody>
            {cases.map((c) => (
              <tr key={c.id}>
                <td>{c.emp_code}</td>
                <td>{c.name}</td>
                <td>{c.designation}</td>
                <td>{c.retirement_date}</td>
                <td>
                  <span className="status-badge">{c.status}</span>
                </td>
                <td data-order={c.last_basic}>₹ {c.last_basic}</td>
                <td>
                  <button
                    type="button"
                    className="details-btn"
                    onClick={() => setReportCaseId(c.id)}
                  >
                    View Details
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </SmpkDataTable>

      {reportCaseId && (
        <PensionReportModal
          caseId={reportCaseId}
          onClose={() => setReportCaseId(null)}
        />
      )}
    </div>
  );
}
