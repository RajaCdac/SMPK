import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
import API from "../services/Api";

/**
 * M2-manual entry — Excel upload only.
 * Output: Desktop/m2-manual-YYYY-MM-DD_HHMM (PDFs when Generate PDF on;
 * Report.xlsx only when PDF is off). Excel also via batch download from DB.
 * Each run creates a batch; Excel-by-batch exports from DB.
 */
export default function Methodology2OldAgeManualEntry() {
  const [file, setFile] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [summary, setSummary] = useState(null);
  const [progress, setProgress] = useState(null);
  const [generatePdf, setGeneratePdf] = useState(true);
  const [batches, setBatches] = useState([]);
  const [batchId, setBatchId] = useState("");
  const [batchBusy, setBatchBusy] = useState(false);
  const [batchError, setBatchError] = useState("");
  const [headerPrompt, setHeaderPrompt] = useState(null);
  const headerAnswersRef = useRef(null);
  const headerResolverRef = useRef(null);

  const askHeaderFields = (fields, empCd, name) =>
    new Promise((resolve) => {
      headerResolverRef.current = resolve;
      setHeaderPrompt({
        fields,
        step: 0,
        empCd: empCd || "",
        name: name || "",
        overrides: {},
        keys: [],
        draft: "",
        tqsYr: "",
        tqsMonth: "",
        tqsDays: "",
        error: "",
      });
    });

  const closeHeaderPrompt = (payload) => {
    const resolve = headerResolverRef.current;
    headerResolverRef.current = null;
    setHeaderPrompt(null);
    if (resolve) resolve(payload);
  };

  const submitHeaderValue = (useNull) => {
    if (!headerPrompt) return;
    const field = headerPrompt.fields[headerPrompt.step];
    if (!field) return;
    let stored = null;
    if (!useNull) {
      if (field.type === "tqs") {
        const years = headerPrompt.tqsYr.trim();
        const months = headerPrompt.tqsMonth.trim();
        const days = headerPrompt.tqsDays.trim();
        if (years === "" || months === "" || days === "") {
          setHeaderPrompt((prev) => ({
            ...prev,
            error: "Enter years, months and days, or choose Null.",
          }));
          return;
        }
        const y = Number(years);
        const m = Number(months);
        const d = Number(days);
        if (
          !Number.isInteger(y) ||
          !Number.isInteger(m) ||
          !Number.isInteger(d) ||
          y < 0 ||
          y > 80 ||
          m < 0 ||
          m > 11 ||
          d < 0 ||
          d > 30
        ) {
          setHeaderPrompt((prev) => ({
            ...prev,
            error: "TQS must be 0–80 years, 0–11 months and 0–30 days.",
          }));
          return;
        }
        stored = { tqs_yr: y, tqs_month: m, tqs_days: d };
      } else if (field.type === "date") {
        if (!headerPrompt.draft) {
          setHeaderPrompt((prev) => ({
            ...prev,
            error: "Choose a date, or choose Null.",
          }));
          return;
        }
        stored = headerPrompt.draft;
      } else if (field.type === "number") {
        const amount = Number(String(headerPrompt.draft).replace(/,/g, ""));
        if (headerPrompt.draft.trim() === "" || Number.isNaN(amount) || amount < 0) {
          setHeaderPrompt((prev) => ({
            ...prev,
            error: "Enter a number, or choose Null.",
          }));
          return;
        }
        stored = amount;
      } else if (!headerPrompt.draft.trim()) {
        setHeaderPrompt((prev) => ({
          ...prev,
          error: "Enter a value, or choose Null.",
        }));
        return;
      } else {
        stored = headerPrompt.draft.trim();
      }
    }
    const overrides = { ...headerPrompt.overrides, [field.key]: stored };
    const keys = [...headerPrompt.keys, field.key];
    const next = headerPrompt.step + 1;
    if (next >= headerPrompt.fields.length) {
      closeHeaderPrompt({ overrides, keys });
      return;
    }
    setHeaderPrompt({
      ...headerPrompt,
      step: next,
      overrides,
      keys,
      draft: "",
      tqsYr: "",
      tqsMonth: "",
      tqsDays: "",
      error: "",
    });
  };

  const progressPct = useMemo(() => {
    if (!progress?.total) return 0;
    return Math.min(
      100,
      Math.round((progress.current / progress.total) * 100)
    );
  }, [progress]);

  const loadBatches = useCallback(async () => {
    setBatchError("");
    try {
      const { data } = await API.get("m2-oldage-arrear/batches/", {
        params: { source: "manual", limit: 50 },
      });
      const rows = data?.batches || [];
      setBatches(rows);
      setBatchId((prev) => prev || (rows[0]?.batch_id ?? ""));
    } catch (err) {
      setBatchError(
        String(
          err?.response?.data?.error || err?.message || "Failed to load batches"
        )
      );
    }
  }, []);

  useEffect(() => {
    loadBatches();
  }, [loadBatches]);

  const onSubmit = async (e) => {
    e.preventDefault();
    setError("");
    setSummary(null);
    setProgress(null);
    if (!file) {
      setError("Choose an Excel file (M2_BULK style).");
      return;
    }
    const form = new FormData();
    form.append("file", file);
    form.append("generate_pdf", generatePdf ? "1" : "0");
    setBusy(true);
    headerAnswersRef.current = null;
    try {
      const { data: prep } = await API.post(
        "m2-oldage-arrear/manual/prepare/",
        form,
        {
          headers: { "Content-Type": "multipart/form-data" },
          timeout: 120000,
        }
      );

      const { session_id: sessionId, total, output_dir: outputDir } = prep;
      if (!sessionId || !total) {
        throw new Error("Prepare step did not return session_id / total.");
      }

      setProgress({ current: 0, total, emp_cd: "", status: "starting" });

      let index = 0;
      while (index < total) {
        const answers = headerAnswersRef.current;
        const { data: rowEvt } = await API.post(
          "m2-oldage-arrear/manual/row/",
          {
            session_id: sessionId,
            index,
            output_dir: outputDir,
            header_overrides: answers?.overrides || null,
            header_answered: answers?.keys || null,
          },
          { timeout: 0 }
        );
        if (rowEvt.status === "needs_header") {
          if (!rowEvt.fields?.length) {
            throw new Error(
              "A header value is missing, but no field was returned to enter."
            );
          }
          setProgress({
            current: index + 1,
            total: rowEvt.total ?? total,
            emp_cd: rowEvt.emp_cd ?? "",
            status: "header",
          });
          const filled = await askHeaderFields(
            rowEvt.fields || [],
            rowEvt.emp_cd,
            rowEvt.name
          );
          const prev = headerAnswersRef.current;
          headerAnswersRef.current = {
            overrides: { ...(prev?.overrides || {}), ...filled.overrides },
            keys: [...new Set([...(prev?.keys || []), ...filled.keys])],
          };
          continue;
        }
        headerAnswersRef.current = null;
        index += 1;
        setProgress({
          current: rowEvt.current ?? index,
          total: rowEvt.total ?? total,
          emp_cd: rowEvt.emp_cd ?? "",
          status: rowEvt.status ?? "",
        });
      }

      const { data: doneSummary } = await API.post(
        "m2-oldage-arrear/manual/finish/",
        {
          session_id: sessionId,
          output_dir: outputDir,
        },
        { timeout: 120000 }
      );

      setSummary(doneSummary);
      setProgress({
        current: total,
        total,
        emp_cd: "",
        status: "complete",
      });
      if (doneSummary?.batch_id) {
        setBatchId(doneSummary.batch_id);
      }
      await loadBatches();
    } catch (err) {
      setError(
        String(
          err?.response?.data?.error || err?.message || "Manual upload failed"
        )
      );
    } finally {
      setBusy(false);
    }
  };

  const downloadBatchExcel = async () => {
    setBatchError("");
    if (!batchId) {
      setBatchError("Select a batch first.");
      return;
    }
    setBatchBusy(true);
    try {
      const res = await API.get(
        `m2-oldage-arrear/batches/${encodeURIComponent(batchId)}/report/`,
        { responseType: "blob", timeout: 0 }
      );
      const blob = new Blob([res.data], {
        type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
      });
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      const cd = res.headers["content-disposition"] || "";
      const match = cd.match(/filename="?([^"]+)"?/);
      link.download = match ? match[1] : `Report_${batchId}.xlsx`;
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
    } catch (err) {
      if (err?.response?.data instanceof Blob) {
        try {
          const text = await err.response.data.text();
          const json = JSON.parse(text);
          setBatchError(json.error || "Batch Excel download failed");
        } catch {
          setBatchError("Batch Excel download failed");
        }
      } else {
        setBatchError(
          String(
            err?.response?.data?.error ||
              err?.message ||
              "Batch Excel download failed"
          )
        );
      }
    } finally {
      setBatchBusy(false);
    }
  };

  return (
    <div className="container-fluid mt-3 mt-md-4 px-2 px-md-3">
      <div className="row justify-content-center">
        <div className="col-12 col-lg-8 col-xl-6">
          <div className="card shadow">
            <div className="card-header bg-dark text-white">
              <h5 className="mb-0">M2-manual entry</h5>
            </div>
            <div className="card-body">
              <p className="text-muted small mb-3">
                Upload Excel with employee details (emp_cd, name, TQS, retirement
                date, class, scale, last pay, DOB, M-I 277 / 359). For a family
                pensioner also include date of death, name of family pensioner,
                and DOB of family pensioner. If M1@277 is not in the Excel, it is
                asked before that employee is calculated. Other header values
                missing from the Excel and the database are asked one field at
                a time. Enter the value, or Null when you do not have it. Each run
                creates a <strong>batch</strong> (IST stamp + case count). Output
                folder: <code>m2-manual-YYYY-MM-DD_HHMM</code>. With{" "}
                <strong>Generate PDF</strong> on: PDFs only; with PDF off:{" "}
                <code>Report.xlsx</code>. Prefer{" "}
                <strong>Excel by batch</strong> (from DB) after the run.
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
                  <div className="form-check">
                    <input
                      className="form-check-input"
                      type="checkbox"
                      id="oaManualGeneratePdf"
                      checked={generatePdf}
                      onChange={(e) => setGeneratePdf(e.target.checked)}
                      disabled={busy}
                    />
                    <label
                      className="form-check-label"
                      htmlFor="oaManualGeneratePdf"
                    >
                      Generate PDF
                    </label>
                  </div>
                </div>
                <div className="col-12">
                  <button
                    type="submit"
                    className="btn btn-primary w-100"
                    disabled={busy}
                  >
                    {busy ? "Processing…" : "Upload"}
                  </button>
                </div>
              </form>

              <div className="border rounded p-3 mt-3 bg-light">
                <div className="d-flex flex-wrap justify-content-between align-items-center gap-2 mb-2">
                  <strong className="small mb-0">Excel by batch (from DB)</strong>
                  <button
                    type="button"
                    className="btn btn-sm btn-outline-secondary"
                    onClick={loadBatches}
                    disabled={batchBusy || busy}
                  >
                    Refresh
                  </button>
                </div>
                <div className="row g-2 align-items-end">
                  <div className="col-12 col-md-8">
                    <label className="form-label small mb-1">Batch</label>
                    <select
                      className="form-select form-select-sm"
                      value={batchId}
                      onChange={(e) => setBatchId(e.target.value)}
                      disabled={batchBusy || busy || !batches.length}
                    >
                      {!batches.length ? (
                        <option value="">No batches yet</option>
                      ) : (
                        batches.map((b) => (
                          <option key={b.batch_id} value={b.batch_id}>
                            {b.label || b.batch_id}
                          </option>
                        ))
                      )}
                    </select>
                  </div>
                  <div className="col-12 col-md-4">
                    <button
                      type="button"
                      className="btn btn-sm btn-success w-100"
                      onClick={downloadBatchExcel}
                      disabled={batchBusy || busy || !batchId}
                    >
                      {batchBusy ? "Preparing…" : "Download Excel"}
                    </button>
                  </div>
                </div>
                {batchError ? (
                  <div className="alert alert-warning mt-2 mb-0 py-2 small">
                    {batchError}
                  </div>
                ) : null}
              </div>

              {busy && progress?.total ? (
                <div className="mt-3">
                  <div className="d-flex justify-content-between small mb-1">
                    <span>
                      Processing employee{" "}
                      <strong>{progress.current}</strong> of{" "}
                      <strong>{progress.total}</strong>
                      {progress.emp_cd ? (
                        <>
                          {" "}
                          — <code>{progress.emp_cd}</code>
                          {progress.status === "header"
                            ? " (enter missing header)"
                            : progress.status
                              ? ` (${progress.status})`
                              : ""}
                        </>
                      ) : progress.status === "starting" ? (
                        " — preparing…"
                      ) : null}
                    </span>
                    <span>{progressPct}%</span>
                  </div>
                  <div
                    className="progress"
                    role="progressbar"
                    aria-valuenow={progressPct}
                    aria-valuemin={0}
                    aria-valuemax={100}
                  >
                    <div
                      className="progress-bar progress-bar-striped progress-bar-animated"
                      style={{ width: `${Math.max(progressPct, 2)}%` }}
                    />
                  </div>
                  <p className="text-muted small mb-0 mt-2">
                    {generatePdf
                      ? "PDFs only (no Report.xlsx in folder). Large files may take several minutes."
                      : "PDF off — consolidating to DB; Report.xlsx written to folder."}
                  </p>
                </div>
              ) : busy ? (
                <div className="mt-3 text-muted small">Starting manual run…</div>
              ) : null}

              {error ? (
                <div className="alert alert-danger mt-3 mb-0">{error}</div>
              ) : null}
              {summary ? (
                <div className="mt-3">
                  <p className="mb-1">
                    <strong>Folder:</strong> {summary.output_dir}
                  </p>
                  {summary.batch_id ? (
                    <p className="mb-1 small">
                      <strong>Batch:</strong> <code>{summary.batch_id}</code>
                      {summary.stamp ? ` · stamp ${summary.stamp}` : ""}
                      {summary.case_count != null
                        ? ` · ${summary.case_count} cases`
                        : ""}
                    </p>
                  ) : null}
                  <p className="mb-2 text-muted small">
                    total {summary.total} · ok {summary.ok} · skipped{" "}
                    {summary.skipped} · failed {summary.failed}
                  </p>
                  {(summary.results || []).filter(
                    (r) => r.status !== "ok"
                  ).length > 0 ? (
                    <div className="table-responsive">
                      <table className="table table-sm table-bordered mb-0">
                        <thead>
                          <tr>
                            <th>EMP</th>
                            <th>Status</th>
                            <th>Reason</th>
                          </tr>
                        </thead>
                        <tbody>
                          {(summary.results || [])
                            .filter((r) => r.status !== "ok")
                            .map((r) => (
                              <tr key={`${r.emp_cd}-${r.status}`}>
                                <td>{r.emp_cd}</td>
                                <td>{r.status}</td>
                                <td>{r.reason}</td>
                              </tr>
                            ))}
                        </tbody>
                      </table>
                    </div>
                  ) : (
                    <div className="alert alert-success mb-0">
                      All rows processed successfully.
                    </div>
                  )}
                </div>
              ) : null}
            </div>
          </div>
        </div>
      </div>
      {headerPrompt ? (
        <HeaderPrompt
          prompt={headerPrompt}
          onChange={setHeaderPrompt}
          onSave={() => submitHeaderValue(false)}
          onNull={() => submitHeaderValue(true)}
        />
      ) : null}
    </div>
  );
}

function HeaderPrompt({ prompt, onChange, onSave, onNull }) {
  const field = prompt.fields[prompt.step];
  if (!field) return null;
  const setDraft = (draft) => onChange({ ...prompt, draft, error: "" });
  return (
    <div
      className="modal fade show d-block"
      style={{ background: "rgba(0,0,0,0.45)" }}
      role="dialog"
      aria-modal="true"
    >
      <div className="modal-dialog modal-dialog-centered">
        <div className="modal-content">
          <div className="modal-header">
            <h5 className="modal-title">
              {field.label}
              <span className="text-muted small ms-2">
                {prompt.step + 1} of {prompt.fields.length}
              </span>
            </h5>
          </div>
          <div className="modal-body">
            <p className="small text-muted mb-2">
              Employee <strong>{prompt.empCd}</strong>
              {prompt.name ? ` — ${prompt.name}` : ""}.{" "}
              {field.key === "m1_277"
                ? "M1@277 is not in the Excel. Enter the amount, or choose Null to leave the database figure."
                : "This header value is not in the Excel or the database. Enter it, or choose Null."}
              {["retirement_date", "last_pay", "scale"].includes(field.key)
                ? " Null on retirement date, last pay or pay scale skips this employee, because the calculation needs those three."
                : ""}
            </p>
            {field.type === "tqs" ? (
              <div className="row g-2">
                <div className="col-4">
                  <label className="form-label small">Years</label>
                  <input
                    className="form-control"
                    inputMode="numeric"
                    value={prompt.tqsYr}
                    onChange={(e) =>
                      onChange({ ...prompt, tqsYr: e.target.value, error: "" })
                    }
                  />
                </div>
                <div className="col-4">
                  <label className="form-label small">Months (0–11)</label>
                  <input
                    className="form-control"
                    inputMode="numeric"
                    value={prompt.tqsMonth}
                    onChange={(e) =>
                      onChange({
                        ...prompt,
                        tqsMonth: e.target.value,
                        error: "",
                      })
                    }
                  />
                </div>
                <div className="col-4">
                  <label className="form-label small">Days (0–30)</label>
                  <input
                    className="form-control"
                    inputMode="numeric"
                    value={prompt.tqsDays}
                    onChange={(e) =>
                      onChange({
                        ...prompt,
                        tqsDays: e.target.value,
                        error: "",
                      })
                    }
                  />
                </div>
              </div>
            ) : field.type === "date" ? (
              <input
                type="date"
                className="form-control"
                value={prompt.draft}
                onChange={(e) => setDraft(e.target.value)}
              />
            ) : (
              <input
                type={field.type === "number" ? "number" : "text"}
                className="form-control"
                value={prompt.draft}
                min={field.type === "number" ? "0" : undefined}
                onChange={(e) => setDraft(e.target.value)}
              />
            )}
            {prompt.error ? (
              <div className="text-danger small mt-2">{prompt.error}</div>
            ) : null}
          </div>
          <div className="modal-footer">
            <button type="button" className="btn btn-outline-secondary" onClick={onNull}>
              Null
            </button>
            <button type="button" className="btn btn-primary" onClick={onSave}>
              Save
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
