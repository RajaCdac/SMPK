import "../styles/AuditLogs.css";

function formatValue(value) {
  if (value === null || value === undefined || value === "") {
    return "—";
  }
  if (typeof value === "object") {
    return JSON.stringify(value, null, 2);
  }
  return String(value);
}

export default function AuditLogDetailModal({ detail, loading, onClose }) {
  if (!detail && !loading) return null;

  const changes = detail?.changes || [];
  const changedCount = changes.filter((c) => c.changed).length;

  return (
    <div className="audit-modal-backdrop" onClick={onClose} role="presentation">
      <div
        className="audit-modal"
        onClick={(e) => e.stopPropagation()}
        role="dialog"
        aria-labelledby="audit-modal-title"
      >
        <div className="audit-modal-header">
          <div>
            <h2 id="audit-modal-title">Audit record #{detail?.record_id}</h2>
            {detail && (
              <p className="audit-modal-subtitle">
                {detail.table_name} · {detail.action} · {detail.module}
                {changedCount > 0 && (
                  <span className="audit-changes-badge">
                    {changedCount} field{changedCount !== 1 ? "s" : ""} changed
                  </span>
                )}
              </p>
            )}
          </div>
          <button type="button" className="audit-modal-close" onClick={onClose}>
            ×
          </button>
        </div>

        {loading && (
          <div className="audit-modal-loading">Loading from database…</div>
        )}

        {!loading && detail && (
          <>
            <div className="audit-modal-meta">
              <span>
                <strong>User:</strong> {detail.changed_by || "—"}
              </span>
              <span>
                <strong>When:</strong>{" "}
                {new Date(detail.timestamp).toLocaleString("en-IN")}
              </span>
              <span>
                <strong>IP:</strong> {detail.ip_address || "—"}
              </span>
            </div>

            {changes.length === 0 ? (
              <p className="audit-modal-empty">
                No field-level data stored for this entry.
              </p>
            ) : (
              <div className="audit-diff-table-wrap">
                <table className="audit-diff-table">
                  <thead>
                    <tr>
                      <th>Field</th>
                      <th>Old value</th>
                      <th>New value</th>
                    </tr>
                  </thead>
                  <tbody>
                    {changes.map((row) => (
                      <tr
                        key={row.field}
                        className={row.changed ? "audit-diff-row-changed" : ""}
                      >
                        <td className="audit-diff-field">{row.field}</td>
                        <td
                          className={
                            row.changed ? "audit-diff-value-changed" : ""
                          }
                        >
                          <pre>{formatValue(row.old_value)}</pre>
                        </td>
                        <td
                          className={
                            row.changed ? "audit-diff-value-changed" : ""
                          }
                        >
                          <pre>{formatValue(row.new_value)}</pre>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}
