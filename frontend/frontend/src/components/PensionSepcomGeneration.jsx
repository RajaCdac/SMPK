import { useCallback, useEffect, useState } from "react";
import API from "../services/Api";

function formatMoney(value) {
  if (value === null || value === undefined || value === "") return "—";
  const n = Number(value);
  if (Number.isNaN(n)) return "—";
  return n.toLocaleString("en-PK", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
}

export default function PensionSepcomGeneration({ employee, onSepcomChange }) {
  const [billMonth, setBillMonth] = useState(1);
  const [billYear, setBillYear] = useState(new Date().getFullYear());
  const [status, setStatus] = useState(null);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [message, setMessage] = useState("");

  const loadStatus = useCallback(async () => {
    if (!employee?.emp_id) return;
    setLoading(true);
    setMessage("");
    try {
      const res = await API.get(
        `first-pension/pension-bill/sepcom/status/employee/${employee.emp_id}/`
      );
      const data = res.data;
      setStatus(data);
      if (data.sepcom_month) setBillMonth(Number(data.sepcom_month));
      if (data.sepcom_year) setBillYear(Number(data.sepcom_year));
      if (data.sepcom_id) {
        setMessage(`SEPCOM generated: ${data.sepcom_id}`);
      } else if (data.block_reason) {
        setMessage(data.block_reason);
      }
    } catch (error) {
      setMessage(error.response?.data?.error || "Could not load SEPCOM status.");
    } finally {
      setLoading(false);
    }
  }, [employee]);

  useEffect(() => {
    loadStatus();
  }, [loadStatus]);

  const handleGenerate = async () => {
    setGenerating(true);
    setMessage("");
    try {
      const res = await API.post("first-pension/pension-bill/sepcom/generate/", {
        bill_month: Number(billMonth),
        bill_year: Number(billYear),
        emp_cds: [employee.emp_id],
      });
      const rec = res.data.sepcom_records?.[0];
      alert(
        res.data.message ||
          `SEPCOM ${rec?.sepcom_id || ""} generated. Amount Rs.${formatMoney(rec?.original_com_amt)}`
      );
      await loadStatus();
      onSepcomChange?.();
    } catch (error) {
      const err = error.response?.data?.error || "SEPCOM generation failed.";
      setMessage(err);
      alert(err);
    } finally {
      setGenerating(false);
    }
  };

  if (!employee) return null;

  return (
    <section className="pension-sepcom-generation border rounded p-3 mb-3">
      <h6 className="mb-2">Step 2 — Commutation Generation (SEPCOM)</h6>
      <p className="text-muted small mb-3">
        Oracle form <strong>FI_PN_COMUTATION_GENERATION</strong>: calculates
        commutation and posts <code>FI_PN_TH_SEPCOM</code> /{" "}
        <code>FI_PN_TD_SEPCOM</code> before PPC bill.
      </p>

      {message && (
        <div
          className={`alert py-2 ${status?.sepcom_generated ? "alert-success" : "alert-warning"}`}
          role="status"
        >
          {message}
        </div>
      )}

      <div className="row g-3 align-items-end mb-3">
        <div className="col-md-2">
          <label className="form-label">Month</label>
          <input
            type="number"
            min={1}
            max={12}
            className="form-control"
            value={billMonth}
            onChange={(e) => setBillMonth(e.target.value)}
            disabled={status?.sepcom_generated}
          />
        </div>
        <div className="col-md-2">
          <label className="form-label">Year</label>
          <input
            type="number"
            className="form-control"
            value={billYear}
            onChange={(e) => setBillYear(e.target.value)}
            disabled={status?.sepcom_generated}
          />
        </div>
        <div className="col-md-4">
          <button
            type="button"
            className="btn btn-primary me-2"
            onClick={handleGenerate}
            disabled={
              generating ||
              loading ||
              status?.sepcom_generated ||
              !status?.ready_for_sepcom_generation
            }
          >
            {generating ? "Generating…" : "Generate SEPCOM"}
          </button>
          <button
            type="button"
            className="btn btn-outline-secondary"
            onClick={loadStatus}
            disabled={loading}
          >
            Refresh
          </button>
        </div>
      </div>

      {status?.sepcom_generated && (
        <p className="small mb-0 text-success">
          SEPCOM ID <strong>{status.sepcom_id}</strong>
          {status.original_com_amt != null && (
            <> — Rs. {formatMoney(status.original_com_amt)}</>
          )}
          {status.bill_no && (
            <> | PPC bill <strong>{status.bill_no}</strong></>
          )}
        </p>
      )}
    </section>
  );
}
