import { useState, useEffect, useCallback } from "react";
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

export default function PensionAmountEntry({ employee, idPrefix = "emp" }) {
  const [amountData, setAmountData] = useState(null);
  const [recordExists, setRecordExists] = useState(false);
  const [loading, setLoading] = useState(true);
  const [calculating, setCalculating] = useState(false);
  const [message, setMessage] = useState("");

  const loadFromDb = useCallback(async () => {
    if (!employee) return;

    setLoading(true);
    setMessage("");

    try {
      const res = await API.get(
        `first-pension/amount/employee/${employee.emp_id}/`
      );

      const data = res.data.amount_data;
      setAmountData(data);
      setRecordExists(Boolean(data?.calculated));

      if (!res.data.exists) {
        setMessage(
          res.data.message ||
            "Save no-pay entry before calculating amounts."
        );
      } else if (data && !data.inputs_ready) {
        setMessage(
          "Save commutation application with commutation % before calculating."
        );
      }
    } catch (error) {
      console.error(error);
      setMessage("Could not load amount details from database.");
    } finally {
      setLoading(false);
    }
  }, [employee]);

  useEffect(() => {
    loadFromDb();
  }, [loadFromDb]);

  useEffect(() => {
    const tabEl = document.getElementById(`${idPrefix}-amount-tab`);
    if (!tabEl) return undefined;

    const onShown = () => {
      loadFromDb();
    };

    tabEl.addEventListener("shown.bs.tab", onShown);
    return () => tabEl.removeEventListener("shown.bs.tab", onShown);
  }, [idPrefix, loadFromDb]);

  const handleCalculate = async () => {
    setCalculating(true);
    setMessage("");

    try {
      const res = await API.post("first-pension/amount/calculate/", {
        emp_code: employee.emp_id,
      });

      setAmountData(res.data.amount_data);
      setRecordExists(true);
      alert(res.data.message || "Amounts calculated and saved.");
    } catch (error) {
      console.error(error);
      const err =
        error.response?.data?.error ||
        "Calculation failed. Save commutation and no-pay first.";
      setMessage(err);
      alert(err);
    } finally {
      setCalculating(false);
    }
  };

  if (!employee) return null;

  if (loading) {
    return <p className="text-muted mb-0">Loading pension amounts...</p>;
  }

  const commPct =
    amountData?.commutation_percent_from_app ??
    amountData?.commutation_percent;

  const noPayDays =
    amountData?.no_pay_days !== undefined && amountData?.no_pay_days !== null
      ? amountData.no_pay_days
      : null;
  const diesNonDays =
    amountData?.dies_non_days !== undefined &&
    amountData?.dies_non_days !== null
      ? amountData.dies_non_days
      : null;

  return (
    <div>
      {message && (
        <div className="alert alert-warning py-2 mb-3" role="alert">
          {message}
        </div>
      )}

      {/* <p className="text-muted small mb-3">
        No-pay days and commutation % are read from the database when this tab
        opens and again when you calculate.
      </p> */}

      <div className="row mb-3">
        <div className="col-md-3">
          <label className="form-label fw-bold">Employee Code</label>
          <input
            type="text"
            className="form-control"
            value={employee.emp_id}
            readOnly
          />
        </div>
        <div className="col-md-3">
          <label className="form-label fw-bold">Last Basic Pay (from case)</label>
          <input
            type="text"
            className="form-control"
            value={
              amountData?.last_basic != null
                ? `Rs. ${formatMoney(amountData.last_basic)}`
                : "—"
            }
            readOnly
          />
        </div>
        <div className="col-md-3">
          <label className="form-label fw-bold">
            Commutation % (from application)
          </label>
          <input
            type="text"
            className="form-control"
            value={commPct != null ? `${commPct}%` : "—"}
            readOnly
          />
        </div>
        <div className="col-md-3">
          <label className="form-label fw-bold">No Pay / Dies Non Days (from case)</label>
          <input
            type="text"
            className="form-control"
            value={
              noPayDays !== null && diesNonDays !== null
                ? `${noPayDays} / ${diesNonDays}`
                : "—"
            }
            readOnly
          />
        </div>
      </div>

      {(amountData?.total_service || recordExists) && (
        <div className="row mb-3">
          <div className="col-md-4">
            <label className="form-label fw-bold">Total Service</label>
            <input
              type="text"
              className="form-control"
              value={amountData?.total_service || "—"}
              readOnly
            />
          </div>
          <div className="col-md-4">
            <label className="form-label fw-bold">TCCS</label>
            <input
              type="text"
              className="form-control"
              value={amountData?.tccs || "—"}
              readOnly
            />
          </div>
          <div className="col-md-4">
            <label className="form-label fw-bold">TQS</label>
            <input
              type="text"
              className="form-control"
              value={amountData?.tqs || "—"}
              readOnly
            />
          </div>
        </div>
      )}

      <table className="table table-bordered mb-3">
        <thead className="table-light">
          <tr>
            <th>Pension Amount</th>
            <th>Commutation Amount</th>
            <th>Gratuity Amount</th>
          </tr>
        </thead>
        <tbody>
          <tr>
            <td className="fs-5 fw-semibold text-primary">
              Rs. {formatMoney(amountData?.pension_amount)}
            </td>
            <td className="fs-5 fw-semibold text-primary">
              Rs. {formatMoney(amountData?.commutation_amount)}
            </td>
            <td className="fs-5 fw-semibold text-primary">
              Rs. {formatMoney(amountData?.gratuity_amount)}
            </td>
          </tr>
        </tbody>
      </table>

      <div className="d-flex gap-2">
        <button
          type="button"
          className="btn btn-primary"
          onClick={handleCalculate}
          disabled={calculating || !amountData?.inputs_ready}
        >
          {calculating
            ? "Calculating..."
            : recordExists
              ? "Recalculate"
              : "Calculate & Save"}
        </button>
        {recordExists && (
          <span className="align-self-center text-success small">
            Amounts saved in pension case summary.
          </span>
        )}
      </div>
    </div>
  );
}
