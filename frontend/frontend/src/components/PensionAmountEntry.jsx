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

function formatGratuityOptionLine(amountData, optionKey) {
  const optI =
    amountData?.opt_i_gratuity_amount ?? amountData?.dcr_gratuity_amount;
  const optII =
    amountData?.opt_ii_gratuity_amount ?? amountData?.option_gratuity_amount;
  const formula = optionKey === "opt_i" ? optI : optII;
  if (formula == null) return "—";

  const winner = amountData?.gratuity_winning_option;
  const isWinner =
    optionKey === "opt_i"
      ? winner === 0 || amountData?.gratuity_payable_basis === "opt_i"
      : winner === 1 || amountData?.gratuity_payable_basis === "opt_ii";
  const payable = amountData?.gratuity_amount;
  const capped = amountData?.gratuity_capped;

  if (
    isWinner &&
    capped &&
    payable != null &&
    Number(payable) !== Number(formula)
  ) {
    return `Rs. ${formatMoney(payable)} (${formatMoney(formula)})`;
  }
  return `Rs. ${formatMoney(formula)}`;
}

export default function PensionAmountEntry({ employee, idPrefix = "emp" }) {
  const [amountData, setAmountData] = useState(null);
  const [recordExists, setRecordExists] = useState(false);
  const [loading, setLoading] = useState(true);
  const [calculating, setCalculating] = useState(false);
  const [generatingFirstMonth, setGeneratingFirstMonth] = useState(false);
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
      const defaults =
        res.data.amount_defaults || employee.amount_defaults || null;
      const useLegacy =
        (!data || !data.calculated) && defaults && defaults.legacy;

      if (useLegacy) {
        setAmountData(defaults);
        setRecordExists(false);
        setMessage(
          defaults.message ||
            "Showing legacy Oracle amounts (pension / commutation / gratuity). Save no-pay and recalculate to create SMPK amounts."
        );
      } else {
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
        } else if (data?.is_voluntary_retirement) {
          setMessage(
            "Voluntary retirement (VR): calculate pension and gratuity only. Commutation is processed separately after separation."
          );
        }
      }
    } catch (error) {
      console.error(error);
      if (employee.amount_defaults?.legacy) {
        setAmountData(employee.amount_defaults);
        setRecordExists(false);
        setMessage(
          employee.amount_defaults.message ||
            "Showing legacy Oracle amounts."
        );
      } else {
        setMessage("Could not load amount details from database.");
      }
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

      setAmountData({
        ...res.data.amount_data,
        first_month: res.data.amount_data?.first_month,
      });
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

  const handleFirstPensionGenerate = async () => {
    setGeneratingFirstMonth(true);
    setMessage("");

    try {
      const res = await API.post("first-pension/amount/first-month-generate/", {
        emp_code: employee.emp_id,
      });
      await loadFromDb();
      alert(
        res.data.message ||
          `First pension generated. FMPEN_ID = ${res.data.fmpen_id || "N/A"}`
      );
      if (res.data.fmpen_id || res.data.bill_no) {
        setMessage(
          `Posted: FMPEN_ID=${res.data.fmpen_id || "—"}, BILL_NO=${res.data.bill_no || "—"}, ` +
            `Pension month ${res.data.pension_month ?? "—"}/${res.data.pension_year ?? "—"}`
        );
      }
    } catch (error) {
      console.error(error);
      const err =
        error.response?.data?.error ||
        "First pension generation failed. Ensure proposal + amounts are saved.";
      setMessage(err);
      alert(err);
    } finally {
      setGeneratingFirstMonth(false);
    }
  };

  if (!employee) return null;

  if (loading) {
    return <p className="text-muted mb-0">Loading pension amounts...</p>;
  }

  const isVR = Boolean(amountData?.is_voluntary_retirement);
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
    <div className="smpk-form">
      {message && (
        <div
          className={`alert py-2 mb-3 ${isVR ? "alert-info" : "alert-warning"}`}
          role="alert"
        >
          {message}
        </div>
      )}

      {/* <p className="text-muted small mb-3">
        No-pay days and commutation % are read from the database when this tab
        opens and again when you calculate.
      </p> */}

      <div className="row g-3 mb-3">
        <div className="col-12 col-sm-6 col-lg-3">
          <label className="form-label">Employee Code</label>
          <input
            type="text"
            className="form-control"
            value={employee.emp_id}
            readOnly
          />
        </div>
        <div className="col-12 col-sm-6 col-lg-3">
          <label className="form-label">Last Basic Pay (for pension)</label>
          <input
            type="text"
            className="form-control"
            value={
              amountData?.pension_basic != null
                ? `Rs. ${formatMoney(amountData.pension_basic)}`
                : amountData?.emoluments_basic != null
                  ? `Rs. ${formatMoney(amountData.emoluments_basic)}`
                  : amountData?.last_basic != null
                    ? `Rs. ${formatMoney(amountData.last_basic)}`
                    : "—"
            }
            readOnly
          />
        </div>
        <div className="col-12 col-sm-6 col-lg-3">
          <label className="form-label">
            Commutation % {isVR ? "(VR — deferred)" : "(from application)"}
          </label>
          <input
            type="text"
            className="form-control"
            value={
              isVR
                ? "Deferred — separate application after separation"
                : commPct != null
                  ? `${commPct}%`
                  : "—"
            }
            readOnly
          />
        </div>
        <div className="col-12 col-sm-6 col-lg-3">
          <label className="form-label">No Pay / Dies Non Days (from case)</label>
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
        <div className="row g-3 mb-3">
          <div className="col-12 col-md-4">
            <label className="form-label">Total Service</label>
            <input
              type="text"
              className="form-control"
              value={amountData?.total_service || "—"}
              readOnly
            />
          </div>
          <div className="col-12 col-md-4">
            <label className="form-label">TCCS</label>
            <input
              type="text"
              className="form-control"
              value={amountData?.tccs || "—"}
              readOnly
            />
          </div>
          <div className="col-12 col-md-4">
            <label className="form-label">TQS</label>
            <input
              type="text"
              className="form-control"
              value={amountData?.tqs || "—"}
              readOnly
            />
          </div>
        </div>
      )}

      <table className="table table-bordered mb-3 smpk-summary-table">
        <thead className="table-light">
          <tr>
            <th>Pension Amount</th>
            <th>Commutation Amount</th>
            <th>Gratuity Amount</th>
          </tr>
        </thead>
        <tbody>
          <tr>
            <td
              className="fs-5 fw-semibold text-primary"
              data-label="Pension Amount"
            >
              Rs. {formatMoney(amountData?.pension_amount)}
            </td>
            <td
              className="fs-5 fw-semibold text-primary"
              data-label="Commutation Amount"
            >
              {isVR ? (
                <span className="fs-6 text-muted">Deferred (VR)</span>
              ) : (
                <>Rs. {formatMoney(amountData?.commutation_amount)}</>
              )}
            </td>
            <td
              className="fs-5 fw-semibold text-primary"
              data-label="Gratuity Amount"
            >
              <div>
                {formatGratuityOptionLine(amountData, "opt_i")}
                <div className="small fw-normal text-secondary">
                  Retirement Gratuity Opt-I (Gratuity Act 1972)
                </div>
              </div>
              <div className="mt-2">
                {formatGratuityOptionLine(amountData, "opt_ii")}
                <div className="small fw-normal text-secondary">
                  Retirement Gratuity Opt-II (Living General Pensioners)
                </div>
              </div>
            </td>
          </tr>
        </tbody>
      </table>

      {amountData?.first_month?.generated && (
        <div className="alert alert-success py-2 mb-3" role="status">
          First pension posted: FMPEN_ID{" "}
          <strong>{amountData.first_month.fmpen_id}</strong>
          {amountData.first_month.bill_no ? (
            <>
              {" "}
              | Bill <strong>{amountData.first_month.bill_no}</strong>
            </>
          ) : null}
          {amountData.first_month.pension_month != null ? (
            <>
              {" "}
              | Period {amountData.first_month.pension_month}/
              {amountData.first_month.pension_year}
            </>
          ) : null}
        </div>
      )}

      <div className="smpk-form-actions">
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
        <button
          type="button"
          className="btn btn-outline-primary ms-2"
          onClick={handleFirstPensionGenerate}
          disabled={
            !recordExists ||
            generatingFirstMonth ||
            Boolean(amountData?.first_month?.generated)
          }
        >
          {generatingFirstMonth
            ? "Generating..."
            : amountData?.first_month?.generated
              ? "First pension posted"
              : "First pension Generate"}
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
