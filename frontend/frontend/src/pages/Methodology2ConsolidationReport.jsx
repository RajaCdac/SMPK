import { useState } from "react";
import API from "../services/Api";

/**
 * Upload EMP_CD Excel and download the same Report.xlsx a bulk batch produces.
 * Reads saved consolidations. Does not recalculate.
 */
export default function Methodology2ConsolidationReport() {
  const [file, setFile] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [note, setNote] = useState("");

  const onSubmit = async (e) => {
    e.preventDefault();
    setError("");
    setNote("");
    if (!file) {
      setError("Choose an Excel file with an EMP_CD column.");
      return;
    }
    setBusy(true);
    try {
      const body = new FormData();
      body.append("file", file);
      const res = await API.post("m2-oldage-arrear/report/excel/", body, {
        responseType: "blob",
        timeout: 0,
        headers: { "Content-Type": "multipart/form-data" },
      });
      const blob = new Blob([res.data], {
        type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
      });
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      const cd = res.headers["content-disposition"] || "";
      const match = cd.match(/filename="?([^"]+)"?/);
      link.download = match ? match[1] : "Report.xlsx";
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
      const requested = Number(res.headers["x-report-requested"] || 0);
      const found = Number(res.headers["x-report-found"] || 0);
      const missing = Number(res.headers["x-report-missing"] || 0);
      if (requested) {
        setNote(
          missing
            ? `Report.xlsx downloaded. ${found} of ${requested} employees had a saved consolidation. ${missing} are listed with blank amounts.`
            : `Report.xlsx downloaded for ${found} employees.`
        );
      } else {
        setNote("Report.xlsx downloaded.");
      }
    } catch (err) {
      let message = err?.message || "Report generation failed";
      if (err?.response?.data instanceof Blob) {
        try {
          const text = await err.response.data.text();
          const json = JSON.parse(text);
          message = json.error || message;
        } catch {
          message = "Report generation failed";
        }
      } else if (err?.response?.data?.error) {
        message = err.response.data.error;
      }
      setError(String(message));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="container-fluid mt-3 mt-md-4 px-2 px-md-3">
      <div className="row justify-content-center">
        <div className="col-12 col-lg-8 col-xl-6">
          <div className="card shadow">
            <div className="card-header bg-dark text-white">
              <h5 className="mb-0">Consolidation report</h5>
            </div>
            <div className="card-body">
              <p className="text-muted small mb-3">
                Upload an Excel file with an <strong>EMP_CD</strong> column.
                The download is the same <code>Report.xlsx</code> a bulk batch
                produces, taken from the saved consolidation. It does not
                recalculate.
              </p>
              <form onSubmit={onSubmit} className="row g-2 align-items-end">
                <div className="col-12">
                  <label className="form-label">Excel file</label>
                  <input
                    type="file"
                    accept=".xlsx,.xls"
                    className="form-control"
                    onChange={(ev) => setFile(ev.target.files?.[0] || null)}
                    disabled={busy}
                  />
                </div>
                <div className="col-12">
                  <button
                    type="submit"
                    className="btn btn-primary w-100"
                    disabled={busy}
                  >
                    {busy ? "Preparing…" : "Download Report.xlsx"}
                  </button>
                </div>
              </form>
              {error ? (
                <div className="alert alert-danger mt-3 mb-0 py-2 small">
                  {error}
                </div>
              ) : null}
              {note ? (
                <div className="alert alert-success mt-3 mb-0 py-2 small">
                  {note}
                </div>
              ) : null}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
