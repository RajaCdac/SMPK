import { useCallback, useEffect, useState } from "react";
import API from "../services/Api";
import PensionProposalSanctionPrint from "./PensionProposalSanctionPrint";
import { printPensionReport } from "../utils/pensionReportPrint";
import "../styles/PensionLicReport.css";
import "../styles/PensionProposalSanctionReport.css";

export default function PensionProposalSanctionReport({
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
      const res = await API.get(
        "first-pension/pension-bill/proposal-sanction-report/",
        {
          params: {
            emp_code: employee.emp_id,
          },
        }
      );
      setReport(res.data);
    } catch (error) {
      console.error(error);
      setReport(null);
      setMessage(
        error.response?.data?.error ||
          "Could not load recommendation & sanction report."
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
    const tabIds = [`${idPrefix}-sanction-tab`, `${rootPrefix}-reports-tab`];

    const onShown = () => loadReport();

    const elements = tabIds
      .map((id) => document.getElementById(id))
      .filter(Boolean);

    elements.forEach((el) => el.addEventListener("shown.bs.tab", onShown));
    return () =>
      elements.forEach((el) => el.removeEventListener("shown.bs.tab", onShown));
  }, [idPrefix, loadReport]);

  return (
    <div className="pension-proposal-sanction-report">
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
        <p className="text-muted no-print">Loading recommendation report…</p>
      )}

      <PensionProposalSanctionPrint report={report} />
    </div>
  );
}
