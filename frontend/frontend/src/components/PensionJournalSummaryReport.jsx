import { useCallback, useEffect, useState } from "react";
import API from "../services/Api";
import PensionJournalSummaryPrint from "./PensionJournalSummaryPrint";
import { printPensionReport } from "../utils/pensionReportPrint";
import "../styles/PensionJournalSummary.css";

export default function PensionJournalSummaryReport({
  billNo,
  jvYear,
  jvMonth,
}) {
  const [report, setReport] = useState(null);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState("");

  const loadReport = useCallback(async () => {
    if (!billNo || !jvYear || !jvMonth) {
      setReport(null);
      return;
    }

    setLoading(true);
    setMessage("");
    try {
      const res = await API.get("first-pension/pension-bill/journal-summary-report/", {
        params: {
          yr: jvYear,
          mth: jvMonth,
          bill_no: billNo,
        },
      });
      setReport(res.data);
    } catch (error) {
      console.error(error);
      setReport(null);
      setMessage(
        error.response?.data?.error ||
          "Could not load Summary of Journal report."
      );
    } finally {
      setLoading(false);
    }
  }, [billNo, jvYear, jvMonth]);

  useEffect(() => {
    loadReport();
  }, [loadReport]);

  if (!billNo) {
    return (
      <p className="text-muted small mb-0">
        Save or generate a journal voucher before printing the summary.
      </p>
    );
  }

  return (
    <div className="journal-summary-panel">
      <p className="text-muted small mb-2">
        Oracle report <strong>FI_PN_TD_JV_RPT</strong> — Summary of Journal for
        bill {billNo} (year {jvYear}, month {jvMonth}).
      </p>

      <div className="d-flex flex-wrap align-items-center gap-2 mb-2">
        <button
          type="button"
          className="btn btn-outline-secondary btn-sm"
          onClick={loadReport}
          disabled={loading}
        >
          Refresh summary
        </button>
        <button
          type="button"
          className="btn btn-outline-primary btn-sm"
          onClick={printPensionReport}
          disabled={!report || loading}
        >
          Print summary of journal
        </button>
        {loading ? <span className="small text-muted">Loading…</span> : null}
      </div>

      {message ? (
        <div className="alert alert-warning py-2 small">{message}</div>
      ) : null}

      {report ? (
        <div className="journal-summary-preview border rounded p-2 bg-white">
          {report.report_kind ? (
            <p className="small text-muted mb-2">
              Format:{" "}
              {report.report_kind === "pfn_bill" && "PFN bill (Family Pension JV)"}
              {report.report_kind === "bank_lic" && "Bank bill — LIC (Manual JV)"}
              {report.report_kind === "bank_non_lic" && "Bank bill — non-LIC (Manual JV)"}
              {report.report_kind === "ppn_bill" && "PPN bill (Pension JV)"}
              {report.report_kind === "other" && "Journal voucher"}
            </p>
          ) : null}
          <PensionJournalSummaryPrint report={report} />
        </div>
      ) : null}
    </div>
  );
}
