import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import API from "../../services/Api";

const SMPK_LS_KEY = "smpk_finance_smpk_sync";

const SMPK_PREFIX_PRESETS = [
  { id: "pn", label: "FI_PN*", prefix: "fi_pn" },
  { id: "core", label: "FI_PN + FI_XX + FI_LA + FI_PR", prefix: "fi_pn,fi_xx,fi_la,fi_pr" },
  { id: "pm", label: "FI_PM*", prefix: "fi_pm" },
  { id: "pr", label: "FI_PR*", prefix: "fi_pr" },
  { id: "xx", label: "FI_XX*", prefix: "fi_xx" },
];

function formatNum(n) {
  if (n == null || n === "") return "—";
  return Number(n).toLocaleString();
}

function loadSavedPair() {
  try {
    const raw = localStorage.getItem(SMPK_LS_KEY);
    if (!raw) return null;
    return JSON.parse(raw);
  } catch {
    return null;
  }
}

function savePair(source, target) {
  try {
    localStorage.setItem(
      SMPK_LS_KEY,
      JSON.stringify({
        source: {
          host: source.host,
          port: source.port,
          user: source.user,
          password: source.password,
          database: source.database,
        },
        target: {
          host: target.host,
          port: target.port,
          user: target.user,
          password: target.password,
          database: target.database,
        },
      })
    );
  } catch {
    /* ignore */
  }
}

function mysqlPayload(cfg) {
  return {
    host: String(cfg.host || "").trim(),
    port: Number(cfg.port) || 3306,
    user: String(cfg.user || "").trim(),
    password: cfg.password ?? "",
    database: String(cfg.database || "").trim(),
  };
}

export default function FinanceSmpkSync() {
  const [defaults, setDefaults] = useState(null);
  const [source, setSource] = useState({
    host: "localhost",
    port: "3307",
    user: "root",
    password: "root123",
    database: "finance",
  });
  const [target, setTarget] = useState({
    host: "localhost",
    port: "3306",
    user: "root",
    password: "root123",
    database: "smpk_pension",
  });
  const [tables, setTables] = useState([]);
  const [meta, setMeta] = useState(null);
  const [prefix, setPrefix] = useState("fi_pn,fi_xx,fi_la,fi_pr");
  const [filter, setFilter] = useState("");
  const [selected, setSelected] = useState(() => new Set());
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [job, setJob] = useState(null);
  const [syncMode, setSyncMode] = useState("insert_ignore");
  const [includePayroll, setIncludePayroll] = useState(false);
  const [batchSize, setBatchSize] = useState(2000);
  const [stopOnError, setStopOnError] = useState(false);
  const [syncMsg, setSyncMsg] = useState("");
  const [testMsg, setTestMsg] = useState("");

  const sourceRef = useRef(source);
  const targetRef = useRef(target);
  sourceRef.current = source;
  targetRef.current = target;

  const syncModes = defaults?.sync_modes || [];
  const selectedMode = syncModes.find((m) => m.id === syncMode);

  const sourceLabel = useMemo(
    () =>
      `${mysqlPayload(source).user}@${mysqlPayload(source).host}:${mysqlPayload(source).port}/${mysqlPayload(source).database}`,
    [source]
  );
  const targetLabel = useMemo(
    () =>
      `${mysqlPayload(target).user}@${mysqlPayload(target).host}:${mysqlPayload(target).port}/${mysqlPayload(target).database}`,
    [target]
  );

  useEffect(() => {
    API.get("finance-transfer/smpk-sync/defaults/")
      .then((res) => {
        setDefaults(res.data);
        const saved = loadSavedPair();
        if (saved?.source) setSource((p) => ({ ...p, ...saved.source, port: String(saved.source.port ?? p.port) }));
        if (saved?.target) setTarget((p) => ({ ...p, ...saved.target, port: String(saved.target.port ?? p.port) }));
        if (!saved && res.data?.source_defaults) {
          setSource((p) => ({
            ...p,
            ...res.data.source_defaults,
            port: String(res.data.source_defaults.port ?? p.port),
            password: p.password,
          }));
        }
        if (!saved && res.data?.target_defaults) {
          setTarget((p) => ({
            ...p,
            ...res.data.target_defaults,
            port: String(res.data.target_defaults.port ?? p.port),
            password: p.password,
          }));
        }
      })
      .catch(() => {});
  }, []);

  const loadTables = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const res = await API.post("finance-transfer/smpk-sync/tables/", {
        prefix,
        include_payroll: includePayroll,
        source: mysqlPayload(sourceRef.current),
        target: mysqlPayload(targetRef.current),
      });
      setTables(res.data.tables || []);
      setMeta({ source: res.data.source, target: res.data.target, count: res.data.count });
      setSelected(new Set());
    } catch (err) {
      setError(err.response?.data?.error || err.message || "Could not list tables.");
      setTables([]);
    } finally {
      setLoading(false);
    }
  }, [prefix, includePayroll]);

  const loadStatus = useCallback(async () => {
    try {
      const res = await API.get("finance-transfer/smpk-sync/status/");
      setJob(res.data);
    } catch {
      /* ignore */
    }
  }, []);

  useEffect(() => {
    loadTables();
  }, [loadTables]);

  useEffect(() => {
    loadStatus();
  }, [loadStatus]);

  useEffect(() => {
    if (job?.status !== "running") return undefined;
    const id = setInterval(loadStatus, 2000);
    return () => clearInterval(id);
  }, [job?.status, loadStatus]);

  const visible = useMemo(() => {
    const q = filter.trim().toLowerCase();
    if (!q) return tables;
    return tables.filter((t) => t.name.includes(q));
  }, [tables, filter]);

  const setConnField = (which, key, value) => {
    if (which === "source") {
      setSource((prev) => {
        const next = { ...prev, [key]: value };
        savePair(next, targetRef.current);
        return next;
      });
    } else {
      setTarget((prev) => {
        const next = { ...prev, [key]: value };
        savePair(sourceRef.current, next);
        return next;
      });
    }
    setTestMsg("");
  };

  const toggle = (name) => {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(name)) next.delete(name);
      else next.add(name);
      return next;
    });
  };

  const selectVisible = () => {
    setSelected(new Set(visible.map((t) => t.name)));
  };

  const selectMissing = () => {
    setSelected(new Set(visible.filter((t) => !t.in_smpk).map((t) => t.name)));
  };

  const selectSalaryPreset = () => {
    const names = defaults?.salary_tables || [];
    setSelected(new Set(names.filter((n) => tables.some((t) => t.name === n))));
  };

  const testConn = async (role) => {
    setTestMsg("");
    setError("");
    try {
      const res = await API.post("finance-transfer/smpk-sync/test-mysql/", {
        role,
        mysql: mysqlPayload(role === "source" ? source : target),
      });
      setTestMsg(res.data.message || `${role} MySQL OK`);
      savePair(source, target);
    } catch (err) {
      setError(err.response?.data?.error || err.message || "Connection test failed.");
    }
  };

  const startSync = async (preset = "") => {
    const modeInfo = selectedMode;
    const countLabel = preset === "all" ? "all overlapping tables" : `${selected.size} selected table(s)`;

    let confirmText =
      `Sync ${countLabel}\n` +
      `From: ${sourceLabel}\n` +
      `To:   ${targetLabel}\n` +
      `Mode: ${modeInfo?.label || syncMode}`;

    if (modeInfo?.destructive) {
      confirmText += "\n\nWARNING: This mode replaces data in selected smpk_pension tables.";
    } else if (syncMode === "insert_ignore") {
      confirmText += "\n\nOnly new PKs will be inserted. Existing smpk_pension rows stay unchanged.";
    }

    if (!window.confirm(confirmText)) return;

    setSyncMsg("");
    setError("");
    savePair(source, target);

    const payload = {
      mode: syncMode,
      include_payroll: includePayroll,
      batch_size: Number(batchSize) || 2000,
      stop_on_error: stopOnError,
      source: mysqlPayload(source),
      target: mysqlPayload(target),
    };
    if (preset === "salary") payload.preset = "salary";
    else if (preset === "all") payload.preset = "all";
    else payload.tables = Array.from(selected);

    try {
      const res = await API.post("finance-transfer/smpk-sync/start/", payload);
      setJob(res.data);
      setSyncMsg(res.data.message || "Sync started.");
    } catch (err) {
      setError(err.response?.data?.error || err.message || "Start failed.");
    }
  };

  const running = job?.status === "running";
  const progress =
    job?.total > 0
      ? Math.round(
          ((job.completed?.length || 0) + Object.keys(job.failed || {}).length) /
            job.total *
            100
        )
      : 0;

  const renderConn = (which, cfg) => (
    <div className="finance-transfer__mysql-grid finance-transfer__mysql-grid--half">
      <label>
        Host
        <input value={cfg.host} onChange={(e) => setConnField(which, "host", e.target.value)} disabled={running} />
      </label>
      <label>
        Port
        <input
          type="number"
          value={cfg.port}
          onChange={(e) => setConnField(which, "port", e.target.value)}
          disabled={running}
        />
      </label>
      <label>
        User
        <input value={cfg.user} onChange={(e) => setConnField(which, "user", e.target.value)} disabled={running} />
      </label>
      <label>
        Password
        <input
          type="password"
          value={cfg.password}
          onChange={(e) => setConnField(which, "password", e.target.value)}
          disabled={running}
        />
      </label>
      <label>
        Database
        <input
          value={cfg.database}
          onChange={(e) => setConnField(which, "database", e.target.value)}
          disabled={running}
        />
      </label>
      <div className="finance-transfer__mysql-actions">
        <button
          type="button"
          className="btn btn-outline-secondary btn-sm"
          onClick={() => testConn(which)}
          disabled={running}
        >
          Test
        </button>
      </div>
    </div>
  );

  return (
    <>
      <p className="text-muted mb-3">
        Copy rows from MySQL <strong>finance</strong> (source dump, usually port 3307) into{" "}
        <strong>smpk_pension</strong> (app DB). SMPK-only tables are never touched.
      </p>

      <div className="finance-transfer__dual-db">
        <div>
          <h3 className="finance-transfer__section-title">Source — finance</h3>
          {renderConn("source", source)}
          <p className="small text-muted mb-0">
            <code>{sourceLabel}</code>
          </p>
        </div>
        <div>
          <h3 className="finance-transfer__section-title">Target — smpk_pension</h3>
          {renderConn("target", target)}
          <p className="small text-muted mb-0">
            <code>{targetLabel}</code>
          </p>
        </div>
      </div>

      {testMsg ? <div className="alert alert-success py-2 mb-2">{testMsg}</div> : null}

      <div className="finance-transfer__toolbar">
        <label>
          Update mode
          <select value={syncMode} onChange={(e) => setSyncMode(e.target.value)} disabled={running}>
            {syncModes.map((m) => (
              <option key={m.id} value={m.id}>
                {m.label}
              </option>
            ))}
          </select>
        </label>
        <label>
          Prefix filter
          <select value={prefix} onChange={(e) => setPrefix(e.target.value)} disabled={loading || running}>
            {SMPK_PREFIX_PRESETS.map((p) => (
              <option key={p.id} value={p.prefix}>
                {p.label}
              </option>
            ))}
          </select>
        </label>
        <label>
          Search name
          <input type="search" value={filter} onChange={(e) => setFilter(e.target.value)} />
        </label>
        <button type="button" className="btn btn-outline-primary" onClick={loadTables} disabled={loading || running}>
          {loading ? "Loading…" : "Refresh list"}
        </button>
      </div>

      {selectedMode?.description ? (
        <p className="finance-transfer__mode-hint small text-muted">{selectedMode.description}</p>
      ) : null}

      <div className="finance-transfer__options">
        <label className="finance-transfer__check">
          <input
            type="checkbox"
            checked={includePayroll}
            onChange={(e) => setIncludePayroll(e.target.checked)}
            disabled={running}
          />
          Include huge payroll tables (FI_PR_*_SALOUT)
        </label>
        <label className="finance-transfer__check">
          <input
            type="checkbox"
            checked={stopOnError}
            onChange={(e) => setStopOnError(e.target.checked)}
            disabled={running}
          />
          Stop on first error
        </label>
        <label>
          Batch size
          <input
            type="number"
            min={100}
            step={100}
            value={batchSize}
            onChange={(e) => setBatchSize(e.target.value)}
            disabled={running}
            className="finance-transfer__batch"
          />
        </label>
      </div>

      <div className="finance-transfer__actions">
        <button type="button" className="btn btn-sm btn-outline-secondary" onClick={selectVisible} disabled={running}>
          Select visible ({visible.length})
        </button>
        <button type="button" className="btn btn-sm btn-outline-secondary" onClick={selectMissing} disabled={running}>
          Select missing in smpk
        </button>
        <button type="button" className="btn btn-sm btn-outline-secondary" onClick={selectSalaryPreset} disabled={running}>
          Select salary tables
        </button>
        <button
          type="button"
          className="btn btn-sm btn-outline-secondary"
          onClick={() => setSelected(new Set())}
          disabled={running}
        >
          Clear
        </button>
        <span className="finance-transfer__sel-count">
          Selected: <strong>{selected.size}</strong>
          {meta?.count != null ? ` · Listed: ${meta.count}` : null}
        </span>
        <button
          type="button"
          className="btn btn-primary"
          onClick={() => startSync("")}
          disabled={running || !selected.size}
        >
          {running ? "Sync running…" : "Update selected"}
        </button>
        <button type="button" className="btn btn-outline-primary" onClick={() => startSync("salary")} disabled={running}>
          Update salary preset
        </button>
        <button type="button" className="btn btn-outline-primary" onClick={() => startSync("all")} disabled={running}>
          Update all listed
        </button>
      </div>

      {error ? <div className="alert alert-danger py-2">{error}</div> : null}
      {syncMsg ? <div className="alert alert-info py-2">{syncMsg}</div> : null}

      {job && job.status !== "idle" ? (
        <div className="finance-transfer__job">
          <div className="finance-transfer__job-meta">
            <span>
              Job: <code>{job.job_id || "—"}</code> · Status: <strong>{job.status}</strong>
              {job.options?.mode ? <> · Mode: <code>{job.options.mode}</code></> : null}
            </span>
            {job.total ? (
              <span>
                Progress: {job.current_index || 0}/{job.total}
                {job.current_table ? ` · ${job.current_table}` : ""}
              </span>
            ) : null}
          </div>
          <div className="finance-transfer__progress-bar">
            <div style={{ width: `${Math.min(100, progress)}%` }} />
          </div>
          <p className="mb-1 small">{job.message}</p>
          {job.failed && Object.keys(job.failed).length > 0 ? (
            <details className="small">
              <summary>Failed tables ({Object.keys(job.failed).length})</summary>
              <ul>
                {Object.entries(job.failed).map(([name, msg]) => (
                  <li key={name}>
                    <code>{name}</code>: {msg}
                  </li>
                ))}
              </ul>
            </details>
          ) : null}
          {job.log?.length ? (
            <pre className="finance-transfer__log">{job.log.slice(-40).join("\n")}</pre>
          ) : null}
        </div>
      ) : null}

      <section className="finance-transfer__table-wrap">
        <table className="table table-sm table-hover finance-transfer__table">
          <thead>
            <tr>
              <th style={{ width: 36 }} />
              <th>Table</th>
              <th className="text-end">Finance rows (approx)</th>
              <th>In smpk</th>
              <th className="text-end">smpk rows (approx)</th>
            </tr>
          </thead>
          <tbody>
            {loading && !tables.length ? (
              <tr>
                <td colSpan={5} className="text-center text-muted py-4">
                  Loading tables…
                </td>
              </tr>
            ) : null}
            {!loading && !visible.length ? (
              <tr>
                <td colSpan={5} className="text-center text-muted py-4">
                  No tables match.
                </td>
              </tr>
            ) : null}
            {visible.map((t) => (
              <tr
                key={t.name}
                className={selected.has(t.name) ? "table-active" : ""}
                onClick={() => !running && toggle(t.name)}
                style={{ cursor: running ? "default" : "pointer" }}
              >
                <td onClick={(e) => e.stopPropagation()}>
                  <input
                    type="checkbox"
                    checked={selected.has(t.name)}
                    disabled={running}
                    onChange={() => toggle(t.name)}
                  />
                </td>
                <td>
                  <code>{t.name}</code>
                </td>
                <td className="text-end">{formatNum(t.finance_row_count)}</td>
                <td>
                  {t.in_smpk ? (
                    <span className="badge text-bg-success">Yes</span>
                  ) : (
                    <span className="badge text-bg-secondary">No</span>
                  )}
                </td>
                <td className="text-end">{t.in_smpk ? formatNum(t.smpk_row_count) : "—"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>
    </>
  );
}
