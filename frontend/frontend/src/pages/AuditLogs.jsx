import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import API from "../services/Api";

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
        <div>
            <h2>Audit Logs</h2>
            <table border="1" width="100%">
                <thead>
                    <tr>
                        <th>User</th>
                        <th>Table Name</th>
                        <th>Record Id</th>
                        <th>Module</th>
                        <th>Action</th>
                        <th>Timestamp</th>
                        <th>IP</th>
                        
                    </tr>
                </thead>
                <tbody>
                    {logs.map((log) => (
                        <tr key={log.id}>
                            <td>{log.changed_by}</td>
                            <td>{log.table_name}</td>
                            <td>{log.record_id}</td>
                            <td>{log.module}</td>
                            <td>{log.action}</td>
                            <td> {new Date(log.timestamp).toLocaleString("en-IN")}</td>                      
                            <td>{log.ip_address}</td>
                        </tr>   
                    ))}
                </tbody>
            </table>
        </div>
    );      
}