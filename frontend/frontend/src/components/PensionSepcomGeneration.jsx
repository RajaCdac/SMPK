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

function toIsoDate(dateStr) {
  if (!dateStr) return "";
  if (/^\d{4}-\d{2}-\d{2}/.test(dateStr)) return dateStr.slice(0, 10);
  const parts = String(dateStr).split("-");
  if (parts.length === 3 && parts[0].length <= 2) {
    return `${parts[2]}-${parts[1]}-${parts[0]}`;
  }
  return String(dateStr);
}

function periodFromDate(dateStr) {
  const input = toIsoDate(dateStr);
  if (!input || !input.includes("-")) return null;
  const [yearStr, monthStr] = input.split("-");
  const year = Number(yearStr);
  const month = Number(monthStr);
  if (!year || !month) return null;
  return { month, year };
}

function periodFromEmployee(employee) {
  const data = employee?.commutation_data || {};
  const defaults = employee?.commutation_defaults || {};
  return (
    periodFromDate(data.commutation_dt) ||
    periodFromDate(data.appcn_dt) ||
    periodFromDate(defaults.commutation_dt) ||
    periodFromDate(defaults.appcn_dt)
  );
}

export default function PensionSepcomGeneration({
  employee,
  onSepcomChange,
  commutationDt = "",
  appcnDt = "",
}) {
  const fromForm =
    periodFromDate(commutationDt) || periodFromDate(appcnDt) || null;
  const fromEmployee = periodFromEmployee(employee);
  const initial = fromForm || fromEmployee || { month: 1, year: "" };

  const [billMonth, setBillMonth] = useState(initial.month);
  const [billYear, setBillYear] = useState(initial.year);
  const [status, setStatus] = useState(null);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [message, setMessage] = useState("");

  const applyPeriod = useCallback((month, year) => {
    const m = Number(month);
    const y = Number(year);
    if (m >= 1 && m <= 12) setBillMonth(m);
    if (y > 1900) setBillYear(y);
  }, []);

  useEffect(() => {
    const next = fromForm || fromEmployee;
    if (next) applyPeriod(next.month, next.year);
  }, [applyPeriod, fromForm?.month, fromForm?.year, fromEmployee?.month, fromEmployee?.year]);

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
      applyPeriod(data.sepcom_month, data.sepcom_year);
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
  }, [applyPeriod, employee]);

  useEffect(() => {
    loadStatus();
  }, [loadStatus]);

  const handleGenerate = async () => {
    setGenerating(true);
    setMessage("");
    try {
      const res = await API.post("first-pension/pension-bill/sepcom/generate/", {
        bill_month: Number(status?.sepcom_month || billMonth),
        bill_year: Number(status?.sepcom_year || billYear),
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

  const ready = Boolean(status?.ready_for_sepcom_generation);
  const alreadyGenerated = Boolean(status?.sepcom_generated);

  return (
    <section className="pension-sepcom-generation border rounded p-3 mb-3">
      <h6 className="mb-2">Step 2 — Commutation Generation (SEPCOM)</h6>
      <p className="text-muted small mb-3">
        Oracle form <strong>FI_PN_COMUTATION_GENERATION</strong>: calculates
        commutation and posts <code>FI_PN_TH_SEPCOM</code> /{" "}
        <code>FI_PN_TD_SEPCOM</code> before PPC bill. Month/year follow the
        commutation date, not the current calendar period.
      </p>

      {message && (
        <div
          className={`alert py-2 ${alreadyGenerated ? "alert-success" : "alert-warning"}`}
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
            readOnly
          />
        </div>
        <div className="col-md-2">
          <label className="form-label">Year</label>
          <input
            type="number"
            className="form-control"
            value={billYear}
            readOnly
          />
        </div>
        <div className="col-md-6">
          <button
            type="button"
            className="btn btn-primary me-2"
            onClick={handleGenerate}
            disabled={generating || loading || alreadyGenerated || !ready}
            title={
              alreadyGenerated
                ? "SEPCOM already generated"
                : ready
                  ? "Generate SEPCOM for this commutation period"
                  : status?.block_reason || "SEPCOM cannot be generated yet"
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

      {alreadyGenerated && (
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
