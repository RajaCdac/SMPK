import { useState } from "react";
import API from "../services/Api";

/**
 * Family Pension report: family pension consolidations only.
 * Pick cases by an EMP_CD Excel, or by the date the consolidation was saved.
 * Payment block is May 2026 – Oct 2026 (same as the Arrear sheet).
 */
export default function Methodology2FamilyPensionReport() {
  const [mode, setMode] = useState("excel");
  const [file, setFile] = useState(null);
  const [fromDate, setFromDate] = useState("");
  const [toDate, setToDate] = useState("");
  const [phase, setPhase] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [note, setNote] = useState("");

  const onSubmit = async (e) => {
    e.preventDefault();
    setError("");
    setNote("");
    if (mode === "excel" && !file) {
      setError("Choose an Excel file with an EMP_CD column.");
      return;
    }
    if (mode === "date" && (!fromDate || !toDate)) {
      setError("Choose both a From date and a To date.");
      return;
    }
    setBusy(true);
    try {
      const body = new FormData();
      if (mode === "excel") {
        body.append("file", file);
      } else {
        body.append("from_date", fromDate);
        body.append("to_date", toDate);
      }
      body.append("phase", phase);
      const res = await API.post("m2-oldage-arrear/family-report/", body, {
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
      link.download = match ? match[1] : "Family_Pension_Report.xlsx";
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);

      const found = Number(res.headers["x-report-found"] || 0);
      const notSaved = String(res.headers["x-report-not-saved"] || "").split(",").filter(Boolean);
      const notFamily = String(res.headers["x-report-not-family"] || "").split(",").filter(Boolean);
      const parts = [`Report downloaded for ${found} family pension case(s).`];
      if (notFamily.length) {
        parts.push(`Skipped (not family pension): ${notFamily.join(", ")}.`);
      }
      if (notSaved.length) {
        parts.push(`Skipped (no saved consolidation): ${notSaved.join(", ")}.`);
      }
      setNote(parts.join(" "));
    } catch (err) {
      let message = err?.message || "Report generation failed";
      if (err?.response?.data instanceof Blob) {
        try {
          const json = JSON.parse(await err.response.data.text());
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
              <h5 className="mb-0">Family Pension Report</h5>
            </div>
            <div className="card-body">
              <p className="text-muted small mb-3">
                Lists family pension consolidations only, from the saved
                consolidation (no recalculation). The payment columns are for
                May 2026 – Oct 2026, the same as the Arrear sheet.
              </p>
              <form onSubmit={onSubmit} className="row g-2 align-items-end">
                <div className="col-12">
                  <div className="btn-group w-100" role="group">
                    <button
                      type="button"
                      className={`btn btn-sm ${mode === "excel" ? "btn-primary" : "btn-outline-primary"}`}
                      onClick={() => setMode("excel")}
                      disabled={busy}
                    >
                      Upload EMP_CD Excel
                    </button>
                    <button
                      type="button"
                      className={`btn btn-sm ${mode === "date" ? "btn-primary" : "btn-outline-primary"}`}
                      onClick={() => setMode("date")}
                      disabled={busy}
                    >
                      From – To saved date
                    </button>
                  </div>
                </div>
                {mode === "excel" ? (
                  <div className="col-12">
                    <label className="form-label">Excel file (EMP_CD column)</label>
                    <input
                      type="file"
                      accept=".xlsx,.xls"
                      className="form-control"
                      onChange={(ev) => setFile(ev.target.files?.[0] || null)}
                      disabled={busy}
                    />
                  </div>
                ) : (
                  <>
                    <div className="col-6">
                      <label className="form-label">From date</label>
                      <input
                        type="date"
                        className="form-control"
                        value={fromDate}
                        onChange={(ev) => setFromDate(ev.target.value)}
                        disabled={busy}
                      />
                    </div>
                    <div className="col-6">
                      <label className="form-label">To date</label>
                      <input
                        type="date"
                        className="form-control"
                        value={toDate}
                        onChange={(ev) => setToDate(ev.target.value)}
                        disabled={busy}
                      />
                    </div>
                  </>
                )}
                <div className="col-12">
                  <label className="form-label">Phase</label>
                  <input
                    type="text"
                    className="form-control"
                    placeholder="e.g. Phase-1"
                    value={phase}
                    onChange={(ev) => setPhase(ev.target.value)}
                    disabled={busy}
                  />
                </div>
                <div className="col-12">
                  <button type="submit" className="btn btn-success w-100" disabled={busy}>
                    {busy ? "Preparing…" : "Download Family Pension Report"}
                  </button>
                </div>
              </form>
              {error ? (
                <div className="alert alert-danger mt-3 mb-0 py-2 small">{error}</div>
              ) : null}
              {note ? (
                <div className="alert alert-success mt-3 mb-0 py-2 small">{note}</div>
              ) : null}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
