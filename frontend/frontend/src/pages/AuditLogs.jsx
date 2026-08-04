import { useEffect, useState } from "react";
import API from "../services/Api";
import AuditLogDetailModal from "../components/AuditLogDetailModal";
import SmpkDataTable from "../components/DataTable/SmpkDataTable";
import "../styles/AuditLogs.css";

export default function AuditLogs() {
  const [logs, setLogs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [detail, setDetail] = useState(null);
  const [loadingDetail, setLoadingDetail] = useState(false);

  useEffect(() => {
    setLoading(true);
    API.get("audit/audit-logs/")
      .then((res) => setLogs(Array.isArray(res.data) ? res.data : []))
      .catch((err) => console.error(err))
      .finally(() => setLoading(false));
  }, []);

  const openRecordDetail = async (logId) => {
    setLoadingDetail(true);
    setDetail(null);
    try {
      const res = await API.get(`audit/audit-logs/${logId}/`);
      setDetail(res.data);
    } catch (err) {
      console.error(err);
      alert("Could not load audit details.");
    } finally {
      setLoadingDetail(false);
    }
  };

  const closeDetail = () => {
    setDetail(null);
    setLoadingDetail(false);
  };

  return (
    <div className="audit-page">
      <div className="audit-header">
        <h1>Audit Logs</h1>
        <p>System activity and tracking details. Click a record ID to view changes.</p>
      </div>

      <div className="audit-table-container">
        <SmpkDataTable
          ready={!loading}
          tableKey={logs.map((l) => l.id).join("-") || "empty"}
          className="table table-striped table-hover w-100 audit-table smpk-datatable"
          options={{
            order: [[5, "desc"]],
            columnDefs: [
              { targets: [2, 4], orderable: false },
            ],
          }}
        >
          <thead>
            <tr>
              <th>User</th>
              <th>Table Name</th>
              <th>Record ID</th>
              <th>Module</th>
              <th>Action</th>
              <th>Timestamp</th>
              <th>IP Address</th>
            </tr>
          </thead>
          <tbody>
            {logs.map((log) => (
              <tr key={log.id}>
                <td>{log.changed_by || "—"}</td>
                <td>{log.table_name}</td>
                <td>
                  <button
                    type="button"
                    className="audit-record-link"
                    onClick={() => openRecordDetail(log.id)}
                    title="View old vs new data"
                  >
                    {log.record_id}
                  </button>
                </td>
                <td>{log.module}</td>
                <td>
                  <span className={`status ${log.action?.toLowerCase()}`}>
                    {log.action}
                  </span>
                </td>
                <td data-order={log.timestamp}>
                  {new Date(log.timestamp).toLocaleString("en-IN")}
                </td>
                <td>{log.ip_address || "—"}</td>
              </tr>
            ))}
          </tbody>
        </SmpkDataTable>
      </div>

      {(detail || loadingDetail) && (
        <AuditLogDetailModal
          detail={detail}
          loading={loadingDetail}
          onClose={closeDetail}
        />
      )}
    </div>
  );
}
