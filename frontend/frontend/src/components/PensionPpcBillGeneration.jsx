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

export default function PensionPpcBillGeneration({
  employee,
  idPrefix = "emp",
  workflowTabPrefix = idPrefix,
  onBillStatusChange,
}) {
  const [billMonth, setBillMonth] = useState(1);
  const [billYear, setBillYear] = useState(new Date().getFullYear());
  const [status, setStatus] = useState(null);
  const [candidates, setCandidates] = useState([]);
  const [selected, setSelected] = useState(new Set());
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [message, setMessage] = useState("");
  const [includeSameBank, setIncludeSameBank] = useState(false);
  const [monthSetup, setMonthSetup] = useState(null);

  const monthClosed = monthSetup?.bill_close_flg === 1;

  const loadData = useCallback(async () => {
    if (!employee) return;

    setLoading(true);
    setMessage("");

    try {
      const statusRes = await API.get(
        `first-pension/pension-bill/ppc/status/employee/${employee.emp_id}/`
      );
      const statusData = statusRes.data;

      let effectiveMonth = Number(billMonth);
      let effectiveYear = Number(billYear);
      if (statusData?.sepcom_month || statusData?.commutation_month) {
        effectiveMonth = Number(
          statusData.sepcom_month ?? statusData.commutation_month
        );
        effectiveYear = Number(
          statusData.sepcom_year ?? statusData.commutation_year
        );
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
        bill_type: "C",
      };

      const [monthRes, candRes] = await Promise.all([
        API.get("first-pension/pension-bill/month-status/", {
          params: billParams,
        }),
        API.get("first-pension/pension-bill/ppc/candidates/", {
          params: {
            bill_month: effectiveMonth,
            bill_year: effectiveYear,
            emp_code: employee.emp_id,
          },
        }),
      ]);

      setStatus(statusData);
      setMonthSetup(monthRes.data);
      const rows = candRes.data.candidates || [];
      setCandidates(rows);

      const preselect = new Set(
        rows
          .filter((r) => r.emp_cd === employee.emp_id && r.ready_for_bill)
          .map((r) => r.emp_cd)
      );
      setSelected(preselect);

      if (statusData?.bill_no) {
        setMessage(`PPC bill posted: ${statusData.bill_no}`);
      } else if (
        statusData?.has_commutation_application &&
        !statusData?.ready_for_ppc &&
        statusData?.block_reason
      ) {
        setMessage(statusData.block_reason);
      }
    } catch (error) {
      console.error(error);
      setMessage(
        error.response?.data?.error || "Could not load PPC bill data."
      );
    } finally {
      setLoading(false);
    }
  }, [employee, billMonth, billYear]);

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

  const toggleRow = (empCd) => {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(empCd)) next.delete(empCd);
      else next.add(empCd);
      return next;
    });
  };

  const handleGenerate = async () => {
    if (selected.size === 0) {
      alert("Select at least one pensioner for PPC bill generation.");
      return;
    }

    setGenerating(true);
    setMessage("");

    try {
      const res = await API.post("first-pension/pension-bill/ppc/generate/", {
        bill_month: Number(billMonth),
        bill_year: Number(billYear),
        emp_cds: Array.from(selected),
        include_same_bank_unselected: includeSameBank,
      });

      const bills = res.data.bills || [];
      const summary = bills
        .map(
          (b) =>
            `${b.bill_no} (${b.pensioner_count} case(s), bank ${b.bank_cd || "—"}, Rs.${formatMoney(b.total_amt_earned)})`
        )
        .join("; ");

      alert(res.data.message || "PPC bill generated.");
      setMessage(summary || "PPC bill generated.");
      await loadData();
      onBillStatusChange?.();
    } catch (error) {
      console.error(error);
      const err = error.response?.data?.error || "PPC bill generation failed.";
      setMessage(err);
      alert(err);
    } finally {
      setGenerating(false);
    }
  };

  if (loading && !status) {
    return <p className="text-muted">Loading PPC bill generation…</p>;
  }

  return (
    <div className="pension-bill-generation pension-ppc-bill-generation">
      <p className="text-muted small mb-3">
        Oracle form <strong>FI_PN_TH_Commutation_Bill_Gen</strong> (step 3):
        creates PPC bill from generated SEPCOM rows. Run SEPCOM generation on
        the Commutation tab first.
      </p>

      {!status?.sepcom_generated && (
        <div className="alert alert-warning py-2">
          Generate SEPCOM on the Commutation tab before PPC bill.
        </div>
      )}

      {message && (
        <div
          className={`alert py-2 ${status?.bill_no ? "alert-success" : "alert-info"}`}
          role="status"
        >
          {message}
        </div>
      )}

      {!status?.has_commutation_application && (
        <div className="alert alert-warning py-2">
          Save the commutation application (COM) on the Commutation tab first.
        </div>
      )}

      {status?.bill_no && status?.ppc_bill && (
        <div className="alert alert-success py-2">
          PPC bill: <strong>{status.bill_no}</strong> — Rs.{" "}
          {formatMoney(status.ppc_bill.total_amt_earned)} (bank{" "}
          {status.ppc_bill.bank_cd || "—"})
        </div>
      )}

      {monthClosed && (
        <div className="alert alert-danger py-2">
          Commutation bill month is <strong>closed</strong>.
        </div>
      )}

      <div className="row g-3 mb-3">
        <div className="col-md-2">
          <label className="form-label">Bill month</label>
          <input
            type="number"
            min={1}
            max={12}
            className="form-control"
            value={billMonth}
            onChange={(e) => setBillMonth(e.target.value)}
          />
        </div>
        <div className="col-md-2">
          <label className="form-label">Bill year</label>
          <input
            type="number"
            className="form-control"
            value={billYear}
            onChange={(e) => setBillYear(e.target.value)}
          />
        </div>
        <div className="col-md-3 d-flex align-items-end">
          <button
            type="button"
            className="btn btn-outline-secondary"
            onClick={loadData}
            disabled={loading}
          >
            Refresh
          </button>
        </div>
      </div>

      {candidates.length > 0 ? (
        <div className="table-responsive mb-3">
          <table className="table table-sm table-bordered">
            <thead className="table-light">
              <tr>
                <th />
                <th>Emp</th>
                <th>Name</th>
                <th>Bank</th>
                <th>Comm %</th>
                <th>Lump sum</th>
                <th>Ref no</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {candidates.map((row) => (
                <tr key={row.emp_cd}>
                  <td>
                    <input
                      type="checkbox"
                      checked={selected.has(row.emp_cd)}
                      disabled={!row.ready_for_bill || monthClosed || !!row.bill_no}
                      onChange={() => toggleRow(row.emp_cd)}
                    />
                  </td>
                  <td>{row.emp_cd}</td>
                  <td>{row.emp_name}</td>
                  <td>{row.bank_cd}</td>
                  <td>{row.commutation_per}%</td>
                  <td>Rs. {formatMoney(row.commutation_lump_sum)}</td>
                  <td>{row.ref_no || "—"}</td>
                  <td>
                    {row.bill_no ? (
                      <span className="text-success">Billed {row.bill_no}</span>
                    ) : row.ready_for_bill ? (
                      <span className="text-primary">Ready</span>
                    ) : (
                      <span className="text-muted small">
                        {row.block_reason || "Not ready"}
                      </span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : status?.bill_no ? (
        <p className="text-muted">
          PPC bill <strong>{status.bill_no}</strong> is already posted for this
          employee. No further PPC generation is required.
        </p>
      ) : (
        <p className="text-muted">
          No separate commutation candidates for {billMonth}/{billYear}.
        </p>
      )}

      <div className="d-flex flex-wrap align-items-center gap-3">
        <label className="form-check mb-0">
          <input
            type="checkbox"
            className="form-check-input me-2"
            checked={includeSameBank}
            onChange={(e) => setIncludeSameBank(e.target.checked)}
          />
          Include other ready cases at same bank
        </label>
        <button
          type="button"
          className="btn btn-primary"
          onClick={handleGenerate}
          disabled={
            generating ||
            monthClosed ||
            selected.size === 0 ||
            Boolean(status?.bill_no)
          }
        >
          {generating ? "Generating…" : "Generate PPC bill"}
        </button>
      </div>
    </div>
  );
}
