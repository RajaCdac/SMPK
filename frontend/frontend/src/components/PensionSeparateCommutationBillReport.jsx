import { useCallback, useEffect, useState } from "react";
import API from "../services/Api";
import PensionSeparateCommutationBillPrint from "./PensionSeparateCommutationBillPrint";
import { printPensionReport } from "../utils/pensionReportPrint";
import "../styles/PensionSeparateCommutationBillReport.css";

export default function PensionSeparateCommutationBillReport({
  employee,
  idPrefix = "emp",
}) {
  const [report, setReport] = useState(null);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState("");
  const [ppcStatus, setPpcStatus] = useState(null);

  const loadPpcStatus = useCallback(async () => {
    if (!employee?.emp_id) {
      setPpcStatus(null);
      return;
    }
    try {
      const res = await API.get(
        `first-pension/pension-bill/ppc/status/employee/${employee.emp_id}/`
      );
      setPpcStatus(res.data);
    } catch (error) {
      console.error(error);
      setPpcStatus(null);
    }
  }, [employee?.emp_id]);

  const loadReport = useCallback(async () => {
    if (!employee?.emp_id) {
      setReport(null);
      return;
    }

    setLoading(true);
    setMessage("");

    try {
      const res = await API.get(
        "first-pension/pension-bill/separate-commutation-bill-report/",
        { params: { emp_code: employee.emp_id } }
      );
      setReport(res.data);
    } catch (error) {
      console.error(error);
      setReport(null);
      setMessage(
        error.response?.data?.error ||
          "Could not load separate commutation bill report."
      );
    } finally {
      setLoading(false);
    }
  }, [employee]);

  useEffect(() => {
    loadPpcStatus();
  }, [loadPpcStatus]);

  useEffect(() => {
    loadReport();
  }, [loadReport]);

  useEffect(() => {
    const rootPrefix = idPrefix.replace(/-reports$/, "");
    const tabIds = [`${idPrefix}-sepcombill-tab`, `${rootPrefix}-reports-tab`];

    const onShown = () => {
      loadPpcStatus();
      loadReport();
    };

    const elements = tabIds
      .map((id) => document.getElementById(id))
      .filter(Boolean);

    elements.forEach((el) => el.addEventListener("shown.bs.tab", onShown));
    return () =>
      elements.forEach((el) => el.removeEventListener("shown.bs.tab", onShown));
  }, [idPrefix, loadPpcStatus, loadReport]);

  const isSeparateCommutation =
    String(ppcStatus?.impl_fpen_combill || "").toUpperCase() === "COM";

  return (
    <div className="pension-sepcom-bill-report">
      {!isSeparateCommutation && ppcStatus?.has_commutation_application === false ? (
        <p className="text-muted small mb-2">
          Separate commutation bill is available for VR cases with a commutation
          application set to Separate Commutation (COM).
        </p>
      ) : null}

      {ppcStatus?.bill_no ? (
        <p className="small text-muted mb-2">
          PPC Bill No: <strong>{ppcStatus.bill_no}</strong>
          {ppcStatus.sepcom_id ? (
            <>
              {" "}
              · SEPCOM: <strong>{ppcStatus.sepcom_id}</strong>
            </>
          ) : null}
        </p>
      ) : null}

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
        <p className="text-muted no-print">Loading separate commutation bill…</p>
      )}

      <PensionSeparateCommutationBillPrint report={report} />
    </div>
  );
}
