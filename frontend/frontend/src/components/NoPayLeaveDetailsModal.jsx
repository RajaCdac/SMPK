import { useEffect, useState } from "react";
import API from "../services/Api";
import "../styles/NoPayLeaveDetails.css";

export default function NoPayLeaveDetailsModal({ empId, open, onClose }) {
  const [payload, setPayload] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!open || !empId) return undefined;

    let cancelled = false;
    setLoading(true);
    setError("");
    setPayload(null);

    API.get(`first-pension/no-pay/leave-details/employee/${empId}/`)
      .then((res) => {
        if (!cancelled) setPayload(res.data);
      })
      .catch((err) => {
        console.error(err);
        if (!cancelled) {
          setError(
            err.response?.data?.error ||
              "Could not load no-pay leave details."
          );
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [open, empId]);

  useEffect(() => {
    if (!open) return undefined;
    const onKeyDown = (e) => {
      if (e.key === "Escape") onClose();
    };
    document.addEventListener("keydown", onKeyDown);
    document.body.style.overflow = "hidden";
    return () => {
      document.removeEventListener("keydown", onKeyDown);
      document.body.style.overflow = "";
    };
  }, [open, onClose]);

  if (!open) return null;

  const details = payload?.details || [];

  return (
    <div
      className="nopay-leave-backdrop"
      onClick={onClose}
      role="presentation"
    >
      <div
        className="nopay-leave-modal"
        onClick={(e) => e.stopPropagation()}
        role="dialog"
        aria-modal="true"
        aria-labelledby="nopay-leave-title"
      >
        <div className="nopay-leave-header">
          <div>
            <h6 id="nopay-leave-title" className="mb-0">
              No-pay leave details
            </h6>
            <p className="nopay-leave-sub text-muted mb-0">
              Employee {empId}
              {payload
                ? ` · ${payload.total_applications ?? details.length} application(s) · total ${payload.total_no_pay_days ?? 0} day(s)`
                : ""}
            </p>
          </div>
          <button
            type="button"
            className="btn btn-sm btn-outline-secondary"
            onClick={onClose}
          >
            Close
          </button>
        </div>

        {loading ? (
          <p className="text-muted mb-0">Loading leave details…</p>
        ) : null}

        {error ? (
          <div className="alert alert-warning py-2 mb-0">{error}</div>
        ) : null}

        {!loading && !error ? (
          details.length === 0 ? (
            <p className="text-muted mb-0">No NPL leave records found.</p>
          ) : (
            <div className="nopay-leave-table-wrap">
              <table className="table table-sm table-striped nopay-leave-table mb-0">
                <thead>
                  <tr>
                    <th>Appl No</th>
                    <th>Type</th>
                    <th>From</th>
                    <th>To</th>
                    <th className="text-end">Days</th>
                    <th>Reason</th>
                  </tr>
                </thead>
                <tbody>
                  {details.map((row, index) => (
                    <tr key={`${row.appl_no || "row"}-${index}`}>
                      <td>{row.appl_no || "—"}</td>
                      <td>{row.attend_desc || "—"}</td>
                      <td>{row.from_date || "—"}</td>
                      <td>{row.to_date || "—"}</td>
                      <td className="text-end">{row.no_pay_days ?? "—"}</td>
                      <td>{row.reason || "—"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )
        ) : null}
      </div>
    </div>
  );
}
