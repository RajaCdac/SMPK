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

function currentBillPeriod() {
  const now = new Date();
  return {
    bill_month: now.getMonth() + 1,
    bill_year: now.getFullYear(),
  };
}

export default function PensionBillGeneration({
  employee,
  idPrefix = "emp",
  workflowTabPrefix = idPrefix,
  onBillStatusChange,
}) {
  const period = currentBillPeriod();
  const [billMonth, setBillMonth] = useState(period.bill_month);
  const [billYear, setBillYear] = useState(period.bill_year);
  const [billType, setBillType] = useState("N");
  const [status, setStatus] = useState(null);
  const [candidates, setCandidates] = useState([]);
  const [selected, setSelected] = useState(new Set());
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [message, setMessage] = useState("");
  const [includeSameBank, setIncludeSameBank] = useState(false);
  const [mode, setMode] = useState("generate");
  const [monthSetup, setMonthSetup] = useState(null);
  const [reprocessCandidates, setReprocessCandidates] = useState([]);
  const [reprocessSelected, setReprocessSelected] = useState(new Set());
  const [reprocessing, setReprocessing] = useState(false);
  const [closingMonth, setClosingMonth] = useState(false);

  const monthClosed = monthSetup?.bill_close_flg === 1;

  const loadData = useCallback(async () => {
    if (!employee) return;

    setLoading(true);
    setMessage("");

    try {
      const statusRes = await API.get(
        `first-pension/pension-bill/status/employee/${employee.emp_id}/`
      );
      const statusData = statusRes.data;

      let effectiveMonth = Number(billMonth);
      let effectiveYear = Number(billYear);
      if (statusData?.has_first_month) {
        effectiveMonth = Number(statusData.pension_month);
        effectiveYear = Number(statusData.pension_yr);
        if (
          Number(billMonth) !== effectiveMonth ||
          Number(billYear) !== effectiveYear
        ) {
          setBillMonth(effectiveMonth);
          setBillYear(effectiveYear);
        }
      }

      const billParams = {
        bill_month: effectiveMonth,
        bill_year: effectiveYear,
        bill_type: billType,
      };

      const [monthRes, candRes, reproRes] = await Promise.all([
        API.get("first-pension/pension-bill/month-status/", {
          params: billParams,
        }),
        API.get("first-pension/pension-bill/candidates/", {
          params: { ...billParams, emp_code: employee.emp_id },
        }),
        API.get("first-pension/pension-bill/reprocess/candidates/", {
          params: { ...billParams, emp_code: employee.emp_id },
        }),
      ]);

      setStatus(statusData);
      setMonthSetup(monthRes.data);
      const rows = candRes.data.candidates || [];
      setCandidates(rows);

      const reproRows = reproRes.data.candidates || [];
      setReprocessCandidates(reproRows);

      const preselect = new Set(
        rows
          .filter((r) => r.emp_cd === employee.emp_id && r.ready_for_bill)
          .map((r) => r.fmpen_id)
      );
      setSelected(preselect);

      const reproPreselect = new Set(
        reproRows
          .filter((r) => r.emp_cd === employee.emp_id && r.ready_for_reprocess)
          .map((r) => r.fmpen_id)
      );
      setReprocessSelected(reproPreselect);

      if (
        statusData?.has_first_month &&
        !statusData?.bill_no &&
        rows.length === 0
      ) {
        setMessage(
          `No unbilled rows for ${effectiveMonth}/${effectiveYear}. ` +
            `First-month pension exists (${statusData.fmpen_id}).`
        );
      }
    } catch (error) {
      console.error(error);
      setMessage(
        error.response?.data?.error ||
          "Could not load bill generation data."
      );
    } finally {
      setLoading(false);
    }
  }, [employee, billMonth, billYear, billType]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  useEffect(() => {
    const tabEl = document.getElementById(`${workflowTabPrefix}-bill-tab`);
    if (!tabEl) return undefined;

    const onShown = () => loadData();
    tabEl.addEventListener("shown.bs.tab", onShown);
    return () => tabEl.removeEventListener("shown.bs.tab", onShown);
  }, [workflowTabPrefix, loadData]);

  const toggleRow = (fmpenId) => {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(fmpenId)) next.delete(fmpenId);
      else next.add(fmpenId);
      return next;
    });
  };

  const handleGenerate = async () => {
    if (selected.size === 0) {
      alert("Select at least one pensioner for bill generation.");
      return;
    }

    setGenerating(true);
    setMessage("");

    try {
      const res = await API.post("first-pension/pension-bill/generate/", {
        bill_month: Number(billMonth),
        bill_year: Number(billYear),
        bill_type: billType,
        fmpen_ids: Array.from(selected),
        include_same_bank_unselected: includeSameBank,
      });

      const bills = res.data.bills || [];
      const summary = bills
        .map(
          (b) =>
            `${b.bill_no} (${b.pensioner_count} pensioner(s), bank ${b.bank_cd || "—"})`
        )
        .join("; ");

      alert(res.data.message || "Pension bill generated.");
      setMessage(summary || "Bill generated.");
      await loadData();
      onBillStatusChange?.();
    } catch (error) {
      console.error(error);
      const err =
        error.response?.data?.error || "Bill generation failed.";
      setMessage(err);
      alert(err);
    } finally {
      setGenerating(false);
    }
  };

  const toggleReprocessRow = (fmpenId) => {
    setReprocessSelected((prev) => {
      const next = new Set(prev);
      if (next.has(fmpenId)) next.delete(fmpenId);
      else next.add(fmpenId);
      return next;
    });
  };

  const handleReprocess = async () => {
    if (reprocessSelected.size === 0) {
      alert("Select at least one pensioner to reprocess.");
      return;
    }

    setReprocessing(true);
    setMessage("");

    try {
      const res = await API.post("first-pension/pension-bill/reprocess/", {
        bill_month: Number(billMonth),
        bill_year: Number(billYear),
        bill_type: billType,
        fmpen_ids: Array.from(reprocessSelected),
      });

      const bills = res.data.bills || [];
      const summary = bills
        .map(
          (b) =>
            `${b.bill_no} updated (Earn Rs.${formatMoney(b.total_amt_earned)}, Ded Rs.${formatMoney(b.total_amt_deducted)})`
        )
        .join("; ");

      alert(res.data.message || "Bill reprocessed.");
      setMessage(summary || "Bill reprocessed.");
      await loadData();
      onBillStatusChange?.();
    } catch (error) {
      console.error(error);
      const err =
        error.response?.data?.error || "Bill reprocess failed.";
      setMessage(err);
      alert(err);
    } finally {
      setReprocessing(false);
    }
  };

  const handleCloseMonth = async () => {
    if (
      !window.confirm(
        `Close pension bill month ${billMonth}/${billYear}? No further generation or reprocess will be allowed.`
      )
    ) {
      return;
    }

    setClosingMonth(true);
    setMessage("");

    try {
      const res = await API.post("first-pension/pension-bill/close-month/", {
        bill_month: Number(billMonth),
        bill_year: Number(billYear),
        bill_type: billType,
      });
      setMonthSetup(res.data.month_setup);
      alert(res.data.message || "Month closed.");
      await loadData();
      onBillStatusChange?.();
    } catch (error) {
      console.error(error);
      const err = error.response?.data?.error || "Could not close month.";
      setMessage(err);
      alert(err);
    } finally {
      setClosingMonth(false);
    }
  };

  if (loading && !status) {
    return <p className="text-muted">Loading bill generation…</p>;
  }

  return (
    <div className="pension-bill-generation">
      {message && (
        <div className="alert alert-info py-2" role="status">
          {message}
        </div>
      )}

      {status && !status.has_first_month && (
        <div className="alert alert-warning py-2">
          Generate first-month pension on the Amount tab before creating a bill.
        </div>
      )}

      {status?.has_first_month && status.bill_no && (
        <div className="alert alert-success py-2">
          Bill already assigned: <strong>{status.bill_no}</strong>
          {status.pension_bill && (
            <>
              {" "}
              — Earned Rs.{formatMoney(status.pension_bill.total_amt_earned)},
              Deducted Rs.{formatMoney(status.pension_bill.total_amt_deducted)}
            </>
          )}
        </div>
      )}

      {monthClosed && (
        <div className="alert alert-danger py-2">
          Bill month is <strong>closed</strong>. Generation and reprocess are
          disabled.
        </div>
      )}

      <ul className="nav nav-tabs mb-3">
        <li className="nav-item">
          <button
            type="button"
            className={`nav-link${mode === "generate" ? " active" : ""}`}
            onClick={() => setMode("generate")}
          >
            Generate (new PPN)
          </button>
        </li>
        <li className="nav-item">
          <button
            type="button"
            className={`nav-link${mode === "reprocess" ? " active" : ""}`}
            onClick={() => setMode("reprocess")}
          >
            Reprocess
          </button>
        </li>
      </ul>

      <div className="row g-3 mb-3">
        <div className="col-md-2">
          <label className="form-label">Bill month</label>
          <input
            type="number"
            className="form-control"
            min={1}
            max={12}
            value={billMonth}
            onChange={(e) => setBillMonth(e.target.value)}
          />
        </div>
        <div className="col-md-2">
          <label className="form-label">Bill year</label>
          <input
            type="number"
            className="form-control"
            min={2000}
            max={2100}
            value={billYear}
            onChange={(e) => setBillYear(e.target.value)}
          />
        </div>
        <div className="col-md-2">
          <label className="form-label">Bill type</label>
          <select
            className="form-select"
            value={billType}
            onChange={(e) => setBillType(e.target.value)}
          >
            <option value="N">N — Normal</option>
            <option value="F">F — Family</option>
          </select>
        </div>
        <div className="col-md-4 d-flex align-items-end">
          <button
            type="button"
            className="btn btn-outline-secondary"
            onClick={loadData}
            disabled={loading}
          >
            {loading ? "Refreshing…" : "Refresh"}
          </button>
        </div>
      </div>

      {status?.has_first_month && (
        <div className="card mb-3">
          <div className="card-body py-2">
            <div className="row small">
              <div className="col-md-3">
                <span className="text-muted">FMPEN ID</span>
                <div>{status.fmpen_id || "—"}</div>
              </div>
              <div className="col-md-2">
                <span className="text-muted">Pension month</span>
                <div>
                  {status.pension_month}/{status.pension_yr}
                </div>
              </div>
              <div className="col-md-2">
                <span className="text-muted">Bank</span>
                <div>{status.bank_cd || "—"}</div>
              </div>
              <div className="col-md-2">
                <span className="text-muted">LIC bank</span>
                <div>{status.lic_bank_cd || "—"}</div>
              </div>
            </div>
          </div>
        </div>
      )}

      <div className="table-responsive mb-3">
        <table className="table table-sm table-bordered align-middle">
          <thead className="table-light">
            <tr>
              <th style={{ width: 40 }} />
              <th>Emp</th>
              <th>Name</th>
              <th>CA No</th>
              <th>Bank</th>
              <th className="text-end">Earned</th>
              <th className="text-end">Deducted</th>
              {mode === "reprocess" && (
                <>
                  <th className="text-end">Stored Earn</th>
                  <th className="text-end">Stored Ded</th>
                </>
              )}
              <th>Bill No</th>
            </tr>
          </thead>
          <tbody>
            {(mode === "generate" ? candidates : reprocessCandidates).length ===
            0 ? (
              <tr>
                <td
                  colSpan={mode === "reprocess" ? 10 : 8}
                  className="text-center text-muted"
                >
                  {mode === "generate"
                    ? "No unbilled pensioners for this month."
                    : "No billed pensioners for reprocess."}
                </td>
              </tr>
            ) : mode === "generate" ? (
              candidates.map((row) => (
                <tr key={row.fmpen_id}>
                  <td>
                    <input
                      type="checkbox"
                      className="form-check-input"
                      checked={selected.has(row.fmpen_id)}
                      disabled={!row.ready_for_bill || monthClosed}
                      onChange={() => toggleRow(row.fmpen_id)}
                    />
                  </td>
                  <td>{row.emp_cd}</td>
                  <td>{row.emp_name || "—"}</td>
                  <td>{row.ca_no || "—"}</td>
                  <td>{row.bank_cd || "—"}</td>
                  <td className="text-end">{formatMoney(row.earn_sum)}</td>
                  <td className="text-end">{formatMoney(row.dedn_sum)}</td>
                  <td>{row.bill_no || "—"}</td>
                </tr>
              ))
            ) : (
              reprocessCandidates.map((row) => (
                <tr
                  key={row.fmpen_id}
                  className={row.earn_changed ? "table-warning" : ""}
                >
                  <td>
                    <input
                      type="checkbox"
                      className="form-check-input"
                      checked={reprocessSelected.has(row.fmpen_id)}
                      disabled={!row.ready_for_reprocess || monthClosed}
                      onChange={() => toggleReprocessRow(row.fmpen_id)}
                    />
                  </td>
                  <td>{row.emp_cd}</td>
                  <td>{row.emp_name || "—"}</td>
                  <td>{row.ca_no || "—"}</td>
                  <td>{row.bank_cd || "—"}</td>
                  <td className="text-end">{formatMoney(row.earn_sum)}</td>
                  <td className="text-end">{formatMoney(row.dedn_sum)}</td>
                  <td className="text-end">
                    {formatMoney(row.stored_earn_sum)}
                  </td>
                  <td className="text-end">
                    {formatMoney(row.stored_dedn_sum)}
                  </td>
                  <td>{row.bill_no || "—"}</td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {mode === "generate" && (
        <>
          <div className="form-check mb-3">
            <input
              className="form-check-input"
              type="checkbox"
              id={`${idPrefix}-include-same-bank`}
              checked={includeSameBank}
              onChange={(e) => setIncludeSameBank(e.target.checked)}
            />
            <label
              className="form-check-label"
              htmlFor={`${idPrefix}-include-same-bank`}
            >
              Include other unbilled pensioners with the same bank
            </label>
          </div>

          <button
            type="button"
            className="btn btn-primary me-2"
            onClick={handleGenerate}
            disabled={
              generating ||
              monthClosed ||
              !status?.has_first_month ||
              Boolean(status?.bill_no) ||
              selected.size === 0
            }
          >
            {generating ? "Generating…" : "Generate PPN Bill"}
          </button>
        </>
      )}

      {mode === "reprocess" && (
        <button
          type="button"
          className="btn btn-warning me-2"
          onClick={handleReprocess}
          disabled={
            reprocessing || monthClosed || reprocessSelected.size === 0
          }
        >
          {reprocessing ? "Reprocessing…" : "Reprocess Selected Bills"}
        </button>
      )}

      <button
        type="button"
        className="btn btn-outline-danger"
        onClick={handleCloseMonth}
        disabled={closingMonth || monthClosed}
      >
        {closingMonth ? "Closing…" : "Close Bill Month"}
      </button>
    </div>
  );
}
