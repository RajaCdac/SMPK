import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import API from "../services/Api";
import FinanceSmpkSync from "../components/Admin/FinanceSmpkSync";
import "../styles/FinanceTransfer.css";

const PRESETS = [
  { id: "all", label: "All prefixes", prefixes: "" },
  { id: "pn", label: "FI_PN*", prefixes: "FI_PN" },
  { id: "core", label: "FI_PN + FI_XX + FI_LA + FI_PR", prefixes: "FI_PN,FI_XX,FI_LA,FI_PR" },
  { id: "xx", label: "FI_XX*", prefixes: "FI_XX" },
  { id: "ma", label: "FI_MA*", prefixes: "FI_MA" },
  { id: "pr", label: "FI_PR*", prefixes: "FI_PR" },
];

const LS_KEY = "smpk_oracle_transfer_mysql";

const DEFAULT_MYSQL = {
  host: "localhost",
  port: "3307",
  user: "root",
  password: "root123",
  database: "finance",
};

function formatNum(n) {
  if (n == null || n === "") return "—";
  return Number(n).toLocaleString();
}

function loadSavedMysql() {
  try {
    const raw = localStorage.getItem(LS_KEY);
    if (!raw) return { ...DEFAULT_MYSQL };
    return { ...DEFAULT_MYSQL, ...JSON.parse(raw) };
  } catch {
    return { ...DEFAULT_MYSQL };
  }
}

function saveMysql(cfg) {
  try {
    localStorage.setItem(
      LS_KEY,
      JSON.stringify({
        host: cfg.host,
        port: cfg.port,
        user: cfg.user,
        password: cfg.password,
        database: cfg.database,
      })
    );
  } catch {
    /* ignore */
  }
}

export default function FinanceTransfer() {
  const [activeTab, setActiveTab] = useState("oracle");
  const [tables, setTables] = useState([]);
  const [meta, setMeta] = useState(null);
  const [prefix, setPrefix] = useState("FI_PN");
  const [filter, setFilter] = useState("");
  const [selected, setSelected] = useState(() => new Set());
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [job, setJob] = useState(null);

  const [mysql, setMysql] = useState(loadSavedMysql);
  const [mysqlOk, setMysqlOk] = useState("");
  const [testingMysql, setTestingMysql] = useState(false);

  const [drop, setDrop] = useState(true);
  const [skipFk, setSkipFk] = useState(true);
  const [batchSize, setBatchSize] = useState(2000);
  const [stopOnError, setStopOnError] = useState(false);
  const [transferMsg, setTransferMsg] = useState("");

  const mysqlPayload = useMemo(
    () => ({
      host: String(mysql.host || "").trim(),
      port: Number(mysql.port) || 3306,
      user: String(mysql.user || "").trim(),
      password: mysql.password ?? "",
      database: String(mysql.database || "").trim(),
    }),
    [mysql]
  );
  const mysqlRef = useRef(mysqlPayload);
  mysqlRef.current = mysqlPayload;

  const mysqlTargetLabel = useMemo(
    () =>
      `${mysqlPayload.user}@${mysqlPayload.host}:${mysqlPayload.port}/${mysqlPayload.database}`,
    [mysqlPayload]
  );

  const setMysqlField = (key, value) => {
    setMysql((prev) => {
      const next = { ...prev, [key]: value };
      saveMysql(next);
      return next;
    });
    setMysqlOk("");
  };

  const loadTables = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const res = await API.post("finance-transfer/tables/", {
        prefix: prefix || "",
        mysql: mysqlRef.current,
      });
      setTables(res.data.tables || []);
      setMeta({
        oracle_schema: res.data.oracle_schema,
        mysql: res.data.mysql,
        count: res.data.count,
      });
      setSelected(new Set());
    } catch (err) {
      setError(
        err.response?.data?.error ||
          err.message ||
          "Could not list Oracle tables."
      );
      setTables([]);
    } finally {
      setLoading(false);
    }
  }, [prefix]);

  const loadStatus = useCallback(async () => {
    try {
      const res = await API.get("finance-transfer/status/");
      setJob(res.data);
    } catch {
      /* ignore */
    }
  }, []);

  useEffect(() => {
    API.get("finance-transfer/defaults/")
      .then((res) => {
        const d = res.data?.mysql_defaults;
        if (!d || localStorage.getItem(LS_KEY)) return;
        setMysql((prev) => ({
          ...prev,
          host: d.host ?? prev.host,
          port: String(d.port ?? prev.port),
          user: d.user ?? prev.user,
          database: d.database ?? prev.database,
        }));
      })
      .catch(() => {});
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
    const q = filter.trim().toUpperCase();
    if (!q) return tables;
    return tables.filter((t) => t.name.includes(q));
  }, [tables, filter]);

  const toggle = (name) => {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(name)) next.delete(name);
      else next.add(name);
      return next;
    });
  };

  const selectVisible = () => {
    setSelected((prev) => {
      const next = new Set(prev);
      visible.forEach((t) => next.add(t.name));
      return next;
    });
  };

  const clearSelection = () => setSelected(new Set());

  const selectMissing = () => {
    setSelected(
      new Set(visible.filter((t) => !t.in_mysql).map((t) => t.name))
    );
  };

  const testMysql = async () => {
    setTestingMysql(true);
    setError("");
    setMysqlOk("");
    try {
      const res = await API.post("finance-transfer/test-mysql/", {
        mysql: mysqlPayload,
      });
      setMysqlOk(res.data.message || "MySQL connection OK.");
      saveMysql(mysql);
    } catch (err) {
      setError(err.response?.data?.error || err.message || "MySQL test failed.");
    } finally {
      setTestingMysql(false);
    }
  };

  const startTransfer = async () => {
    if (!selected.size) {
      setTransferMsg("Select at least one table.");
      return;
    }
    if (
      !window.confirm(
        `Transfer ${selected.size} table(s) to MySQL\n${mysqlTargetLabel}?\n` +
          `Drop existing: ${drop ? "yes" : "no"}\n` +
          `Defer FKs: ${skipFk ? "yes (recommended for bulk)" : "no"}`
      )
    ) {
      return;
    }
    setTransferMsg("");
    setError("");
    saveMysql(mysql);
    try {
      const res = await API.post("finance-transfer/start/", {
        tables: Array.from(selected),
        drop,
        skip_foreign_keys: skipFk,
        batch_size: Number(batchSize) || 2000,
        stop_on_error: stopOnError,
        mysql: mysqlPayload,
      });
      setJob(res.data);
      setTransferMsg(res.data.message || "Transfer started.");
    } catch (err) {
      setError(err.response?.data?.error || err.message || "Start failed.");
    }
  };

  const applyFks = async () => {
    setTransferMsg("");
    setError("");
    try {
      const res = await API.post("finance-transfer/apply-pending-fks/", {
        mysql: mysqlPayload,
      });
      setTransferMsg(res.data.message || "Pending FKs processed.");
      loadStatus();
    } catch (err) {
      setError(err.response?.data?.error || err.message || "FK apply failed.");
    }
  };

  const running = job?.status === "running";
  const progress =
    job?.total > 0
      ? Math.round(
          ((job.completed?.length || 0) +
            (job.failed ? Object.keys(job.failed).length : 0)) /
            job.total *
            100
        )
      : 0;

  return (
    <div className="finance-transfer-page">
      <header className="finance-transfer__header">
        <div>
          <h1>Database transfer &amp; update</h1>
          <p className="text-muted mb-0">
            Admin tools to load Oracle FINANCE into MySQL, and to update{" "}
            <strong>smpk_pension</strong> from the finance mirror.
          </p>
        </div>
      </header>

      <div className="finance-transfer__tabs" role="tablist">
        <button
          type="button"
          role="tab"
          className={`finance-transfer__tab${activeTab === "oracle" ? " is-active" : ""}`}
          onClick={() => setActiveTab("oracle")}
        >
          Oracle → MySQL (finance)
        </button>
        <button
          type="button"
          role="tab"
          className={`finance-transfer__tab${activeTab === "smpk" ? " is-active" : ""}`}
          onClick={() => setActiveTab("smpk")}
        >
          Finance → smpk_pension
        </button>
      </div>

      {activeTab === "smpk" ? (
        <section className="finance-transfer__panel">
          <FinanceSmpkSync />
        </section>
      ) : (
        <>
      <section className="finance-transfer__panel">
        <h2 className="finance-transfer__section-title">Oracle → MySQL (finance dump)</h2>
        <p className="text-muted">
          Copy Oracle <strong>{meta?.oracle_schema || "FINANCE"}</strong> tables into MySQL finance
          (structure, data, PK; FKs deferred by default).
        </p>
        <div className="finance-transfer__mysql-grid">
          <label>
            Host
            <input
              value={mysql.host}
              onChange={(e) => setMysqlField("host", e.target.value)}
              disabled={running}
              placeholder="localhost or IP"
              autoComplete="off"
            />
          </label>
          <label>
            Port
            <input
              type="number"
              value={mysql.port}
              onChange={(e) => setMysqlField("port", e.target.value)}
              disabled={running}
              min={1}
              max={65535}
            />
          </label>
          <label>
            User
            <input
              value={mysql.user}
              onChange={(e) => setMysqlField("user", e.target.value)}
              disabled={running}
              autoComplete="off"
            />
          </label>
          <label>
            Password
            <input
              type="password"
              value={mysql.password}
              onChange={(e) => setMysqlField("password", e.target.value)}
              disabled={running}
              autoComplete="new-password"
            />
          </label>
          <label>
            Database
            <input
              value={mysql.database}
              onChange={(e) => setMysqlField("database", e.target.value)}
              disabled={running}
              placeholder="finance"
            />
          </label>
          <div className="finance-transfer__mysql-actions">
            <button
              type="button"
              className="btn btn-outline-secondary"
              onClick={testMysql}
              disabled={running || testingMysql}
            >
              {testingMysql ? "Testing…" : "Test connection"}
            </button>
            <span className="finance-transfer__mysql-target">
              Target: <code>{mysqlTargetLabel}</code>
            </span>
          </div>
        </div>
        {mysqlOk ? <div className="alert alert-success py-2 mb-2">{mysqlOk}</div> : null}

        <div className="finance-transfer__toolbar">
          <label>
            Prefix filter
            <select
              value={prefix}
              onChange={(e) => setPrefix(e.target.value)}
              disabled={loading || running}
            >
              {PRESETS.map((p) => (
                <option key={p.id} value={p.prefixes}>
                  {p.label}
                </option>
              ))}
            </select>
          </label>
          <label>
            Search name
            <input
              type="search"
              value={filter}
              onChange={(e) => setFilter(e.target.value)}
              placeholder="e.g. PENSION_BILL"
            />
          </label>
          <button
            type="button"
            className="btn btn-outline-primary"
            onClick={loadTables}
            disabled={loading || running}
          >
            {loading ? "Loading…" : "Refresh list"}
          </button>
        </div>

        <div className="finance-transfer__options">
          <label className="finance-transfer__check">
            <input
              type="checkbox"
              checked={drop}
              onChange={(e) => setDrop(e.target.checked)}
              disabled={running}
            />
            Drop &amp; recreate MySQL table before load
          </label>
          <label className="finance-transfer__check">
            <input
              type="checkbox"
              checked={skipFk}
              onChange={(e) => setSkipFk(e.target.checked)}
              disabled={running}
            />
            Defer foreign keys (recommended; apply later)
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
          <button
            type="button"
            className="btn btn-sm btn-outline-secondary"
            onClick={selectVisible}
            disabled={running}
          >
            Select visible ({visible.length})
          </button>
          <button
            type="button"
            className="btn btn-sm btn-outline-secondary"
            onClick={selectMissing}
            disabled={running}
          >
            Select missing in MySQL
          </button>
          <button
            type="button"
            className="btn btn-sm btn-outline-secondary"
            onClick={clearSelection}
            disabled={running}
          >
            Clear selection
          </button>
          <span className="finance-transfer__sel-count">
            Selected: <strong>{selected.size}</strong>
            {meta?.count != null ? ` · Listed: ${meta.count}` : null}
          </span>
          <button
            type="button"
            className="btn btn-primary"
            onClick={startTransfer}
            disabled={running || !selected.size}
          >
            {running ? "Transfer running…" : "Transfer selected"}
          </button>
          <button
            type="button"
            className="btn btn-outline-primary"
            onClick={applyFks}
            disabled={running}
          >
            Apply pending FKs
          </button>
        </div>

        {error ? <div className="alert alert-danger py-2">{error}</div> : null}
        {transferMsg ? <div className="alert alert-info py-2">{transferMsg}</div> : null}

        {job && job.status !== "idle" ? (
          <div className="finance-transfer__job">
            <div className="finance-transfer__job-meta">
              <span>
                Job: <code>{job.job_id || "—"}</code> · Status:{" "}
                <strong>{job.status}</strong>
                {job.mysql ? (
                  <>
                    {" "}
                    · MySQL{" "}
                    <code>
                      {job.mysql.user}@{job.mysql.host}:{job.mysql.port}/
                      {job.mysql.database}
                    </code>
                  </>
                ) : null}
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
              <pre className="finance-transfer__log">
                {job.log.slice(-40).join("\n")}
              </pre>
            ) : null}
          </div>
        ) : null}
      </section>

      <section className="finance-transfer__table-wrap">
        <table className="table table-sm table-hover finance-transfer__table">
          <thead>
            <tr>
              <th style={{ width: 36 }} />
              <th>Table</th>
              <th className="text-end">Oracle rows (approx)</th>
              <th>In MySQL</th>
              <th className="text-end">MySQL rows (approx)</th>
            </tr>
          </thead>
          <tbody>
            {loading && !tables.length ? (
              <tr>
                <td colSpan={5} className="text-center text-muted py-4">
                  Loading Oracle tables…
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
                <td className="text-end">{formatNum(t.oracle_num_rows)}</td>
                <td>
                  {t.in_mysql ? (
                    <span className="badge text-bg-success">Yes</span>
                  ) : (
                    <span className="badge text-bg-secondary">No</span>
                  )}
                </td>
                <td className="text-end">
                  {t.in_mysql ? formatNum(t.mysql_row_count) : "—"}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>

      <p className="finance-transfer__cli text-muted small">
        CLI:{" "}
        <code>
          python oracle_table_to_mysql.py TABLE --drop --mysql-host HOST
          --mysql-port 3306 --mysql-user root --mysql-password *** --mysql-database
          finance
        </code>
      </p>
        </>
      )}
    </div>
  );
}
