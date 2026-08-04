import { useEffect, useState } from "react";
import API from "../services/Api";
import PensionCalculationSheet from "./PensionCalculationSheet";
import "../styles/PensionPrint.css";

export default function PensionReportModal({ caseId, onClose }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!caseId) return undefined;

    let cancelled = false;
    setLoading(true);
    setError("");
    setData(null);

    API.get(`first-pension/report/${caseId}/`)
      .then((res) => {
        if (!cancelled) setData(res.data);
      })
      .catch((err) => {
        console.error(err);
        if (!cancelled) setError("Could not load pension report.");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [caseId]);

  useEffect(() => {
    const onKeyDown = (e) => {
      if (e.key === "Escape") onClose();
    };
    document.addEventListener("keydown", onKeyDown);
    document.body.style.overflow = "hidden";
    return () => {
      document.removeEventListener("keydown", onKeyDown);
      document.body.style.overflow = "";
    };
  }, [onClose]);

  if (!caseId) return null;

  const handlePrint = () => window.print();

  return (
    <div
      className="pension-report-modal-backdrop no-print"
      onClick={onClose}
      role="presentation"
    >
      <div
        className="pension-report-modal"
        onClick={(e) => e.stopPropagation()}
        role="dialog"
        aria-modal="true"
        aria-labelledby="pension-report-modal-title"
      >
        <div className="pension-report-modal-toolbar no-print">
          <h2 id="pension-report-modal-title">
            Pension calculation — {data?.name || "Case"}
          </h2>
          <div className="pension-report-modal-actions">
            <button
              type="button"
              className="pension-report-print-btn"
              onClick={handlePrint}
              disabled={!data}
            >
              Print report
            </button>
            <button
              type="button"
              className="pension-report-close-btn"
              onClick={onClose}
              aria-label="Close"
            >
              ×
            </button>
          </div>
        </div>

        <div className="pension-report-modal-body" id="pension-report-print-root">
          {loading && (
            <div className="pension-report-modal-loading">Loading report…</div>
          )}
          {error && !loading && (
            <div className="pension-report-modal-error">{error}</div>
          )}
          {!loading && !error && data && <PensionCalculationSheet data={data} />}
        </div>
      </div>
    </div>
  );
}
