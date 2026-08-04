import { useCallback, useEffect, useState } from "react";
import API from "../services/Api";
import PensionLicReportPrint from "./PensionLicReportPrint";
import { printPensionReport } from "../utils/pensionReportPrint";
import { useEmployeeBillContext } from "../hooks/useEmployeeBillContext";
import "../styles/PensionLicReport.css";

function currentBillPeriod() {
  const now = new Date();
  return {
    bill_month: now.getMonth() + 1,
    bill_year: now.getFullYear(),
  };
}

function billPeriodFromStatus(status) {
  if (status?.has_first_month) {
    return {
      bill_month: Number(status.pension_month),
      bill_year: Number(status.pension_yr),
      bill_no: status.bill_no || "",
    };
  }
  return { ...currentBillPeriod(), bill_no: "" };
}

export default function PensionLicReport({ employee, idPrefix = "emp" }) {
  const { billContext, loading: contextLoading, reload } =
    useEmployeeBillContext(employee);
  const [billMonth, setBillMonth] = useState("");
  const [billYear, setBillYear] = useState("");
  const [ppnBills, setPpnBills] = useState([]);
  const [billNo, setBillNo] = useState("");
  const [report, setReport] = useState(null);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState("");
  const [periodReady, setPeriodReady] = useState(false);

  const loadPpnList = useCallback(async () => {
    if (billMonth === "" || billYear === "") return;

    try {
      const res = await API.get("first-pension/pension-bill/ppn/", {
        params: {
          bill_month: billMonth,
          bill_year: billYear,
        },
      });
      setPpnBills(res.data.bills || []);
    } catch (error) {
      console.error(error);
      setMessage(
        error.response?.data?.error || "Could not load PPN bill list."
      );
    }
  }, [billMonth, billYear]);

  const loadReport = useCallback(async () => {
    if (!billNo) {
      setReport(null);
      return;
    }

    setLoading(true);
    setMessage("");

    try {
      const res = await API.get("first-pension/pension-bill/lic-report/", {
        params: {
          bill_no: billNo,
          emp_code: employee?.emp_id,
        },
      });
      setReport(res.data);
    } catch (error) {
      console.error(error);
      setReport(null);
      setMessage(
        error.response?.data?.error || "Could not load LIC report."
      );
    } finally {
      setLoading(false);
    }
  }, [billNo, employee]);

  useEffect(() => {
    if (!employee?.emp_id) {
      const period = currentBillPeriod();
      setBillMonth(period.bill_month);
      setBillYear(period.bill_year);
      setBillNo("");
      setPeriodReady(true);
      return;
    }

    if (contextLoading) {
      setPeriodReady(false);
      return;
    }

    const period = billPeriodFromStatus(billContext?.status);
    setBillMonth(period.bill_month);
    setBillYear(period.bill_year);
    if (period.bill_no) {
      setBillNo(period.bill_no);
    }
    setPeriodReady(true);
  }, [employee?.emp_id, billContext?.status, contextLoading]);

  useEffect(() => {
    if (!periodReady) return;
    loadPpnList();
  }, [periodReady, billMonth, billYear, loadPpnList]);

  useEffect(() => {
    if (billNo) loadReport();
  }, [billNo, loadReport]);

  useEffect(() => {
    const rootPrefix = idPrefix.replace(/-reports$/, "");
    const tabIds = [`${idPrefix}-lic-tab`, `${rootPrefix}-reports-tab`];

    const onShown = async () => {
      if (employee?.emp_id) {
        await reload();
      } else if (periodReady) {
        loadPpnList();
      }
      if (billNo) loadReport();
    };

    const elements = tabIds
      .map((id) => document.getElementById(id))
      .filter(Boolean);

    elements.forEach((el) => el.addEventListener("shown.bs.tab", onShown));
    return () =>
      elements.forEach((el) => el.removeEventListener("shown.bs.tab", onShown));
  }, [
    idPrefix,
    employee?.emp_id,
    billNo,
    periodReady,
    reload,
    loadPpnList,
    loadReport,
  ]);

  return (
    <div className="pension-lic-report">
      {message && (
        <div className="alert alert-warning py-2 no-print" role="status">
          {message}
        </div>
      )}

      <div className="row g-3 mb-3 no-print">
        <div className="col-md-2">
          <label className="form-label">Bill month</label>
          <input
            type="number"
            className="form-control"
            min={1}
            max={12}
            value={billMonth}
            onChange={(e) => setBillMonth(e.target.value)}
            disabled={!periodReady}
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
            disabled={!periodReady}
          />
        </div>
        <div className="col-md-4">
          <label className="form-label">PPN Bill No</label>
          <select
            className="form-select"
            value={billNo}
            onChange={(e) => setBillNo(e.target.value)}
            disabled={!periodReady}
          >
            <option value="">— Select bill —</option>
            {ppnBills.map((b) => (
              <option key={b.bill_no} value={b.bill_no}>
                {b.bill_no} — Bank {b.bank_cd || "—"} (LIC:{" "}
                {b.gen_lic_tag === "G" ? "Yes" : "No"})
              </option>
            ))}
          </select>
        </div>
        <div className="col-md-4 d-flex align-items-end gap-2">
          <button
            type="button"
            className="btn btn-outline-secondary"
            onClick={() => {
              loadPpnList();
              loadReport();
            }}
            disabled={loading || !periodReady}
          >
            Refresh
          </button>
          <button
            type="button"
            className="btn btn-outline-primary"
            onClick={printPensionReport}
            disabled={!report?.pages?.length}
          >
            Print
          </button>
        </div>
      </div>

      {(contextLoading || !periodReady) && (
        <p className="text-muted no-print">Loading bill period…</p>
      )}

      {loading && periodReady && (
        <p className="text-muted no-print">Loading LIC report…</p>
      )}

      {report && report.row_count === 0 && !loading && (
        <div className="alert alert-info py-2 no-print">
          No LIC pensioners on this bill
          {employee ? ` for employee ${employee.emp_id}` : ""}.
        </div>
      )}

      <PensionLicReportPrint report={report} />
    </div>
  );
}
