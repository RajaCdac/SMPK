import { useEffect, useState } from "react";
import API from "../services/Api";
import AuditLogDetailModal from "../components/AuditLogDetailModal";
import SmpkDataTable from "../components/DataTable/SmpkDataTable";
import "../styles/AuditLogs.css";

/** Show audit time as plain local string; avoid UTC/IST browser re-parse. */
function formatAuditTime(value) {
  if (value == null || value === "") return "—";
  const text = String(value).trim();
  // Already formatted by API: DD-MM-YYYY HH:MM:SS
  if (/^\d{2}-\d{2}-\d{4} \d{2}:\d{2}:\d{2}$/.test(text)) {
    return text;
  }
  // Fallback ISO / other
  const d = new Date(text);
  if (Number.isNaN(d.getTime())) return text;
  const pad = (n) => String(n).padStart(2, "0");
  return (
    `${pad(d.getDate())}-${pad(d.getMonth() + 1)}-${d.getFullYear()} ` +
    `${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`
  );
}

/** Sort key for DataTables from DD-MM-YYYY HH:MM:SS or ISO. */
function auditTimeOrder(value) {
  if (value == null || value === "") return 0;
  const text = String(value).trim();
  const m = text.match(
    /^(\d{2})-(\d{2})-(\d{4}) (\d{2}):(\d{2}):(\d{2})$/
  );
  if (m) {
    const [, dd, mm, yyyy, hh, mi, ss] = m;
    return Date.UTC(+yyyy, +mm - 1, +dd, +hh, +mi, +ss);
  }
  const d = new Date(text);
  return Number.isNaN(d.getTime()) ? 0 : d.getTime();
}

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
        <p>
          System activity (login, logout, save, generate). Time shown as local
          date/time (DD-MM-YYYY HH:MM:SS). Click a record ID for details.
        </p>
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
                <td
                  data-order={auditTimeOrder(
                    log.timestamp_local || log.timestamp
                  )}
                >
                  {formatAuditTime(log.timestamp_local || log.timestamp)}
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
