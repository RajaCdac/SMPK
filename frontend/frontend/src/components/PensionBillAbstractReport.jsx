import { useCallback, useEffect, useState } from "react";
import API from "../services/Api";
import PensionBillAbstractReportPrint from "./PensionBillAbstractReportPrint";
import { printPensionReport } from "../utils/pensionReportPrint";
import "../styles/PensionBillAbstractReport.css";

export default function PensionBillAbstractReport({ billNo, employee }) {
  const [report, setReport] = useState(null);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState("");

  const loadReport = useCallback(async () => {
    if (!billNo) {
      setReport(null);
      return;
    }

    setLoading(true);
    setMessage("");

    try {
      const res = await API.get("first-pension/pension-bill/bill-abstract-report/", {
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
        error.response?.data?.error || "Could not load bill abstract report."
      );
    } finally {
      setLoading(false);
    }
  }, [billNo, employee?.emp_id]);

  useEffect(() => {
    loadReport();
  }, [loadReport]);

  if (!billNo) {
    return (
      <p className="text-muted small mb-0">
        Assign a bill before printing the bill abstract.
      </p>
    );
  }

  return (
    <div className="bill-abstract-panel">
      <div className="d-flex flex-wrap align-items-center gap-2 mb-2">
        <button
          type="button"
          className="btn btn-outline-secondary btn-sm"
          onClick={loadReport}
          disabled={loading}
        >
          Refresh abstract
        </button>
        <button
          type="button"
          className="btn btn-outline-primary btn-sm"
          onClick={printPensionReport}
          disabled={!report || loading}
        >
          Print bill abstract
        </button>
        {loading ? <span className="small text-muted">Loading…</span> : null}
      </div>

      {message ? <div className="alert alert-warning py-2 small">{message}</div> : null}

      {report ? (
        <div className="bill-abstract-preview border rounded p-2 bg-white">
          <PensionBillAbstractReportPrint report={report} />
        </div>
      ) : null}
    </div>
  );
}
