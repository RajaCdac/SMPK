import { useCallback, useEffect, useState } from "react";
import API from "../services/Api";
import PensionCommutationBillPrint from "./PensionCommutationBillPrint";
import { printPensionReport } from "../utils/pensionReportPrint";
import "../styles/PensionLicReport.css";
import "../styles/PensionCommutationBillReport.css";

export default function PensionCommutationBillReport({
  employee,
  idPrefix = "emp",
}) {
  const [report, setReport] = useState(null);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState("");

  const loadReport = useCallback(async () => {
    if (!employee?.emp_id) {
      setReport(null);
      return;
    }

    setLoading(true);
    setMessage("");

    try {
      let res;
      try {
        res = await API.get("first-pension/pension-bill/sep-comm-report/", {
          params: { emp_code: employee.emp_id },
        });
      } catch (sepErr) {
        if (sepErr.response?.status !== 400) throw sepErr;
        res = await API.get("first-pension/pension-bill/commutation-report/", {
          params: { emp_code: employee.emp_id },
        });
      }
      setReport(res.data);
    } catch (error) {
      console.error(error);
      setReport(null);
      setMessage(
        error.response?.data?.error ||
          "Could not load commutation sanction report."
      );
    } finally {
      setLoading(false);
    }
  }, [employee]);

  useEffect(() => {
    loadReport();
  }, [loadReport]);

  useEffect(() => {
    const rootPrefix = idPrefix.replace(/-reports$/, "");
    const tabIds = [`${idPrefix}-combill-tab`, `${rootPrefix}-reports-tab`];

    const onShown = () => loadReport();

    const elements = tabIds
      .map((id) => document.getElementById(id))
      .filter(Boolean);

    elements.forEach((el) => el.addEventListener("shown.bs.tab", onShown));
    return () =>
      elements.forEach((el) => el.removeEventListener("shown.bs.tab", onShown));
  }, [idPrefix, loadReport]);

  return (
    <div className="pension-commutation-bill-report">
      {message && (
        <div className="alert alert-warning py-2 no-print" role="status">
          {message}
        </div>
      )}

      <div className="d-flex justify-content-end gap-2 mb-3 no-print">
        <button
          type="button"
          className="btn btn-outline-secondary"
          onClick={loadReport}
          disabled={loading || !employee}
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

      {loading && (
        <p className="text-muted no-print">Loading commutation sanction report…</p>
      )}

      <PensionCommutationBillPrint report={report} />
    </div>
  );
}
