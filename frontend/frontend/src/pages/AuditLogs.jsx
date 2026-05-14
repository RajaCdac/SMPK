import React, { useEffect, useState } from "react";
import API from "../services/Api";
import "../styles/AuditLogs.css";
export default function AuditLogs() {
const [logs, setLogs] = useState([]);
useEffect(() => {
API.get("audit/audit-logs/")
      .then((res) => {
        setLogs(res.data);
      })
      .catch((err) => console.error(err));
}, []);
return (

    <div className="audit-page">

      <div className="audit-header">

        <h1>Audit Logs</h1>

        <p>
          System activity and tracking details
        </p>

      </div>

      <div className="audit-table-container">

        <table className="audit-table">

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

            {logs.length > 0 ? (

              logs.map((log) => (

                <tr key={log.id}>

                  <td>{log.changed_by}</td>

                  <td>{log.table_name}</td>

                  <td>{log.record_id}</td>

                  <td>{log.module}</td>

                  <td>
                    <span className={`status ${log.action?.toLowerCase()}`}>
                      {log.action}
                    </span>
                  </td>

                  <td>
                    {new Date(log.timestamp).toLocaleString("en-IN")}
                  </td>

                  <td>{log.ip_address}</td>

                </tr>

              ))

            ) : (

              <tr>

                <td colSpan="7" className="no-data">
                  No Audit Logs Found
                </td>

              </tr>

            )}

          </tbody>

        </table>

      </div>

    </div>

  );

}