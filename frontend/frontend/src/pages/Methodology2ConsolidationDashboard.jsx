import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { Link } from "react-router-dom";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { faEye } from "@fortawesome/free-solid-svg-icons";
import API from "../services/Api";
import SmpkDataTable from "../components/DataTable/SmpkDataTable";
import Methodology2ConsolidationPrint from "../components/Methodology2ConsolidationPrint";
import { printMethodology2Consolidation } from "../utils/methodology2Print";
import "../styles/Dashboard.css";

function todayIso() {
  const d = new Date();
  const m = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  return `${d.getFullYear()}-${m}-${day}`;
}

function oabAmount(r) {
  if (!r?.oldage_benefit) return null;
  if (r.oa_359 != null && r.oa_359 !== "") return r.oa_359;
  if (r.oa_277 != null && r.oa_277 !== "") return r.oa_277;
  return null;
}

function benefitDiff(m2, m1) {
  const a = amountNumber(m2);
  const b = amountNumber(m1);
  if (a == null || b == null) return null;
  return a - b;
}

function amountNumber(v) {
  if (v == null || v === "") return null;
  const n = Number(String(v).replace(/,/g, ""));
  return Number.isNaN(n) ? null : n;
}

function fmtAmt(v) {
  if (v == null || v === "") return "—";
  const n = Number(v);
  if (Number.isNaN(n)) return "—";
  return n.toLocaleString("en-IN", { maximumFractionDigits: 2 });
}

function fmtDiff(v) {
  if (v == null || v === "") return "—";
  const n = Number(v);
  if (Number.isNaN(n)) return "—";
  return n.toLocaleString("en-IN", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
}

function rowKey(source, emp) {
  return `${String(source || "").toLowerCase()}|${String(emp || "").trim()}`;
}

const EMPTY_SUMMARY = {
  total: 0,
  employee_pension: 0,
  family_pension: 0,
  class_12: 0,
  class_34: 0,
  today: 0,
  this_week: 0,
  this_month: 0,
  oa_count: 0,
  enhanced_count: 0,
  payment_done: 0,
  payment_pending: 0,
  total_matched: 0,
  limit: 100,
};

function StatCard({ label, value, hint, tone = "primary" }) {
  return (
    <div className="col-2">
      <div
        className={`card border-0 shadow-sm h-100 border-start border-4 border-${tone}`}
      >
        <div className="card-body py-3">
          <div className="text-muted small text-uppercase fw-semibold mb-1">
            {label}
          </div>
          <div className="fs-3 fw-bold lh-1">{value ?? 0}</div>
          {hint ? <div className="small text-muted mt-2">{hint}</div> : null}
        </div>
      </div>
    </div>
  );
}

export default function Methodology2ConsolidationDashboard() {
  const [fromDate, setFromDate] = useState("");
  const [toDate, setToDate] = useState(todayIso);
  const [source, setSource] = useState("all");
  const [category, setCategory] = useState("all");
  const [payment, setPayment] = useState("all");
  const [loading, setLoading] = useState(false);
  const [actionBusy, setActionBusy] = useState("");
  const [error, setError] = useState("");
  const [summary, setSummary] = useState(EMPTY_SUMMARY);
  const [rows, setRows] = useState([]);
  const [viewOpen, setViewOpen] = useState(false);
  const [viewLoading, setViewLoading] = useState(false);
  const [viewError, setViewError] = useState("");
  const [viewSnapshot, setViewSnapshot] = useState(null);
  const [viewMeta, setViewMeta] = useState(null);
  const [lastRefreshedAt, setLastRefreshedAt] = useState(null);
  const rowsRef = useRef(rows);
  const tableWrapRef = useRef(null);
  const selectedRef = useRef(new Set());
  const [selectedCount, setSelectedCount] = useState(0);
  const loadRef = useRef(null);
  const loadingRef = useRef(false);
  const viewOpenRef = useRef(false);

  useEffect(() => {
    rowsRef.current = rows;
  }, [rows]);

  useEffect(() => {
    viewOpenRef.current = viewOpen;
  }, [viewOpen]);

  const load = useCallback(
    async ({ silent = false } = {}) => {
      if (loadingRef.current && silent) return;
      loadingRef.current = true;
      if (!silent) {
        setLoading(true);
        setError("");
      }
      try {
        const params = new URLSearchParams();
        if (fromDate) params.set("from_date", fromDate);
        if (toDate) params.set("to_date", toDate);
        if (source) params.set("source", source);
        if (category) params.set("category", category);
        if (payment) params.set("payment", payment);
        const res = await API.get(
          `m2-oldage-arrear/dashboard/?${params.toString()}`
        );
        setSummary(res.data?.summary || EMPTY_SUMMARY);
        setRows(Array.isArray(res.data?.rows) ? res.data.rows : []);
        setLastRefreshedAt(new Date());
        if (silent) setError("");
      } catch (err) {
        if (!silent) {
          setSummary(EMPTY_SUMMARY);
          setRows([]);
        }
        setError(
          err?.response?.data?.error ||
            err?.message ||
            "Failed to load consolidation dashboard"
        );
      } finally {
        loadingRef.current = false;
        if (!silent) setLoading(false);
      }
    },
    [fromDate, toDate, source, category, payment]
  );

  useEffect(() => {
    loadRef.current = load;
  }, [load]);

  useEffect(() => {
    load();
  }, [load]);

  // Refresh when user returns to this browser tab / window (no polling).
  useEffect(() => {
    const refreshIfVisible = () => {
      if (document.visibilityState !== "visible") return;
      // Keep an open print/report modal stable; list refreshes after it closes.
      if (viewOpenRef.current) return;
      loadRef.current?.({ silent: true });
    };
    const onVisibility = () => {
      if (document.visibilityState === "visible") refreshIfVisible();
    };
    document.addEventListener("visibilitychange", onVisibility);
    window.addEventListener("focus", refreshIfVisible);
    return () => {
      document.removeEventListener("visibilitychange", onVisibility);
      window.removeEventListener("focus", refreshIfVisible);
    };
  }, []);

  const openFullReport = useCallback(async (row) => {
    const emp = String(row?.emp_cd || "").trim();
    if (!emp) {
      setViewOpen(true);
      setViewLoading(false);
      setViewSnapshot(null);
      setViewMeta(null);
      setViewError("Employee code missing on this row");
      return;
    }
    const src =
      String(row?.source || "").toLowerCase() === "met2" ? "met2" : "oa";
    const url =
      src === "met2"
        ? `methodology2/consolidation/${emp}/`
        : `m2-oldage-arrear/consolidation/${emp}/`;

    setViewOpen(true);
    setViewLoading(true);
    setViewError("");
    setViewSnapshot(null);
    setViewMeta({
      emp_cd: emp,
      source: src,
      name: row?.name || row?.pensioner_name || "",
    });

    try {
      const res = await API.get(url);
      setViewSnapshot(res.data || null);
      if (!res.data) {
        setViewError(`No saved consolidation for ${emp}`);
      }
    } catch (err) {
      setViewSnapshot(null);
      setViewError(
        err?.response?.data?.error ||
          err?.message ||
          `No saved consolidation for ${emp}`
      );
    } finally {
      setViewLoading(false);
    }
  }, []);

  const closeFullReport = useCallback(() => {
    setViewOpen(false);
    setViewLoading(false);
    setViewSnapshot(null);
    setViewMeta(null);
    setViewError("");
  }, []);

  const syncSelectionChecks = useCallback(() => {
    const wrap = tableWrapRef.current;
    if (!wrap) return;
    wrap.querySelectorAll("[data-row-select]").forEach((el) => {
      const key = el.getAttribute("data-row-key") || "";
      el.checked = selectedRef.current.has(key);
    });
    const all = wrap.querySelector("[data-select-all-listed]");
    if (all) {
      const total = rowsRef.current.length;
      const n = selectedRef.current.size;
      all.checked = total > 0 && n === total;
      all.indeterminate = n > 0 && n < total;
    }
  }, []);

  const setSelectedKeys = useCallback(
    (keys) => {
      selectedRef.current = new Set(keys);
      setSelectedCount(selectedRef.current.size);
      syncSelectionChecks();
    },
    [syncSelectionChecks]
  );

  const selectedItems = useCallback(() => {
    return rowsRef.current
      .filter((r) => selectedRef.current.has(rowKey(r.source, r.emp_cd)))
      .map((r) => ({
        emp_cd: r.emp_cd,
        source: r.source,
        payment_done: !!r.payment_done,
      }));
  }, []);

  const runBulk = useCallback(
    async (kind) => {
      const items = selectedItems();
      if (!items.length) {
        setError("Select one or more rows first.");
        return;
      }
      if (kind === "delete") {
        const paid = items.filter((r) => r.payment_done);
        const deletable = items.filter((r) => !r.payment_done);
        if (!deletable.length) {
          setError(
            "Selected rows are marked paid. Unmark them before delete."
          );
          return;
        }
        const skipNote = paid.length
          ? `\n${paid.length} paid row(s) will be skipped until unmarked.`
          : "";
        const ok = window.confirm(
          `Delete ${deletable.length} consolidation(s) from m2* only?` +
            `${skipNote}\n\nfi_* tables are not touched.`
        );
        if (!ok) return;
      }
      setActionBusy("bulk");
      setError("");
      try {
        const path =
          kind === "delete"
            ? "m2-oldage-arrear/dashboard/delete-many/"
            : "m2-oldage-arrear/dashboard/payment-many/";
        const payload =
          kind === "delete"
            ? {
                items: items
                  .filter((r) => !r.payment_done)
                  .map(({ emp_cd, source }) => ({ emp_cd, source })),
              }
            : {
                payment_done: kind === "paid",
                items: items.map(({ emp_cd, source }) => ({ emp_cd, source })),
              };
        const res = await API.post(path, payload);
        const data = res.data || {};
        const errors = Array.isArray(data.errors) ? data.errors : [];
        if (errors.length) {
          const sample = errors
            .slice(0, 3)
            .map((e) => `${e.emp_cd || ""}: ${e.error || "failed"}`)
            .join("; ");
          setError(
            `${data.ok_count || 0} updated, ${errors.length} failed. ${sample}`
          );
        }
        setSelectedKeys([]);
        await load();
      } catch (err) {
        setError(
          err?.response?.data?.error ||
            err?.message ||
            "Bulk action failed"
        );
      } finally {
        setActionBusy("");
      }
    },
    [load, selectedItems, setSelectedKeys]
  );

  const tableKey = useMemo(
    () =>
      `${source}|${category}|${payment}|${fromDate}|${toDate}|${rows.length}|${
        rows[0]?.emp_cd || ""
      }|${rows[0]?.updated_at || ""}|${rows[0]?.payment_done ? 1 : 0}|diff`,
    [source, category, payment, fromDate, toDate, rows]
  );

  // DataTables moves/clones row DOM — React onClick on buttons often dies.
  // Delegate from the wrap so actions always work after DT init / remount.
  useEffect(() => {
    const wrap = tableWrapRef.current;
    if (!wrap) return undefined;

    const onClick = (e) => {
      const viewBtn = e.target.closest("[data-view-report]");
      if (!viewBtn || !wrap.contains(viewBtn)) return;
      e.preventDefault();
      e.stopPropagation();

      const emp = String(viewBtn.getAttribute("data-emp-cd") || "").trim();
      const src = String(viewBtn.getAttribute("data-source") || "").trim();
      const updated = String(viewBtn.getAttribute("data-updated") || "");
      const match =
        rowsRef.current.find(
          (r) =>
            String(r.emp_cd) === emp &&
            String(r.source) === src &&
            String(r.updated_at || "") === updated
        ) ||
        rowsRef.current.find(
          (r) => String(r.emp_cd) === emp && String(r.source) === src
        ) ||
        { emp_cd: emp, source: src };
      openFullReport(match);
    };

    const onChange = (e) => {
      const box = e.target.closest("[data-row-select], [data-select-all-listed]");
      if (!box || !wrap.contains(box)) return;
      if (box.hasAttribute("data-select-all-listed")) {
        if (box.checked) {
          setSelectedKeys(
            rowsRef.current.map((r) => rowKey(r.source, r.emp_cd))
          );
        } else {
          setSelectedKeys([]);
        }
        return;
      }
      const key = box.getAttribute("data-row-key") || "";
      const next = new Set(selectedRef.current);
      if (box.checked) next.add(key);
      else next.delete(key);
      setSelectedKeys(next);
    };

    wrap.addEventListener("click", onClick);
    wrap.addEventListener("change", onChange);
    const table = wrap.querySelector("table");
    const onDraw = () => syncSelectionChecks();
    table?.addEventListener("draw.dt", onDraw);
    syncSelectionChecks();
    return () => {
      wrap.removeEventListener("click", onClick);
      wrap.removeEventListener("change", onChange);
      table?.removeEventListener("draw.dt", onDraw);
    };
  }, [
    openFullReport,
    tableKey,
    setSelectedKeys,
    syncSelectionChecks,
  ]);

  const reportModal =
    viewOpen &&
    createPortal(
      <div className="modal-overlay no-print" role="dialog" aria-modal="true">
        <div
          className="modal-box modal-box-wide"
          style={{ width: "min(100%, 980px)" }}
        >
          <div className="modal-header d-flex justify-content-between align-items-start gap-2">
            <h2>
              Full consolidation report
              {viewMeta?.emp_cd
                ? ` — ${viewMeta.emp_cd}${
                    viewMeta.name ? ` (${viewMeta.name})` : ""
                  }`
                : ""}
              {viewMeta?.source
                ? ` · ${viewMeta.source === "oa" ? "Old Age" : "Met2"}`
                : ""}
            </h2>
            <button
              type="button"
              className="btn-close"
              aria-label="Close"
              onClick={closeFullReport}
            />
          </div>
          <div className="modal-body">
            {viewLoading ? (
              <div className="text-muted py-4 text-center">
                Loading saved consolidation…
              </div>
            ) : null}
            {viewError ? (
              <div className="alert alert-danger mb-0">{viewError}</div>
            ) : null}
            {!viewLoading && viewSnapshot ? (
              <div
                className="border rounded bg-white p-2"
                style={{ overflow: "auto", maxHeight: "65vh" }}
              >
                <style>{`
                  #methodology2-consolidation-print.m2-consol-print-wrap {
                    position: static !important;
                    left: auto !important;
                    width: 100% !important;
                    max-width: 210mm;
                    margin: 0 auto;
                  }
                `}</style>
                <Methodology2ConsolidationPrint snapshot={viewSnapshot} />
              </div>
            ) : null}
          </div>
          <div className="modal-footer p-3 d-flex justify-content-end gap-2">
            <button
              type="button"
              className="btn btn-outline-secondary"
              onClick={closeFullReport}
            >
              Close
            </button>
            {viewSnapshot && !viewLoading ? (
              <button
                type="button"
                className="btn btn-primary"
                onClick={() =>
                  printMethodology2Consolidation(viewSnapshot?.case_no)
                }
              >
                Print / Save PDF
              </button>
            ) : null}
          </div>
        </div>
      </div>,
      document.body
    );

  return (
    <div className="container-fluid py-3">
      <div className="d-flex flex-wrap justify-content-between align-items-start gap-2 mb-3">
        <div>
          <h4 className="mb-1">Consolidation Dashboard</h4>
          <p className="text-muted mb-0 small">
            Newest consolidations first. Mark payment done, or delete
            m2* snapshot only (fi_* untouched). Paid rows cannot be deleted —
            unmark paid first. List refreshes when you return to this tab.
            {lastRefreshedAt ? (
              <>
                {" "}
                Last refreshed{" "}
                {lastRefreshedAt.toLocaleTimeString("en-IN", {
                  hour: "2-digit",
                  minute: "2-digit",
                  second: "2-digit",
                })}
                .
              </>
            ) : null}
          </p>
        </div>
        <div className="d-flex flex-wrap gap-2">
          <Link
            className="btn btn-outline-secondary btn-sm"
            to="/dashboard/methodology2-oldage-arrear"
          >
            Methodology 2 Consolidation
          </Link>
        </div>
      </div>

      <div className="card shadow-sm mb-3">
        <div className="card-body">
          <div className="row g-2 align-items-end">
            <div className="col-6 col-md-3 col-lg-2">
              <label className="form-label small mb-1">From date</label>
              <input
                type="date"
                className="form-control form-control-sm"
                value={fromDate}
                onChange={(e) => setFromDate(e.target.value)}
              />
            </div>
            <div className="col-6 col-md-3 col-lg-2">
              <label className="form-label small mb-1">To date</label>
              <input
                type="date"
                className="form-control form-control-sm"
                value={toDate}
                onChange={(e) => setToDate(e.target.value)}
              />
            </div>
            <div className="col-6 col-md-3 col-lg-2">
              <label className="form-label small mb-1">Benefit</label>
              <select
                className="form-select form-select-sm"
                value={source}
                onChange={(e) => setSource(e.target.value)}
              >
                <option value="all">All</option>
                <option value="oldage">Old age only</option>
                <option value="without_oldage">Without old age</option>
                <option value="enhanced">Enhanced benefit</option>
              </select>
            </div>
            <div className="col-6 col-md-3 col-lg-2">
              <label className="form-label small mb-1">Category</label>
              <select
                className="form-select form-select-sm"
                value={category}
                onChange={(e) => setCategory(e.target.value)}
              >
                <option value="all">All</option>
                <option value="12">1 &amp; 2</option>
                <option value="34">3 &amp; 4</option>
              </select>
            </div>
            <div className="col-6 col-md-3 col-lg-2">
              <label className="form-label small mb-1">Payment</label>
              <select
                className="form-select form-select-sm"
                value={payment}
                onChange={(e) => setPayment(e.target.value)}
              >
                <option value="all">All</option>
                <option value="pending">Pending</option>
                <option value="done">Paid</option>
              </select>
            </div>
            <div className="col-auto">
              <button
                type="button"
                className="btn btn-primary btn-sm"
                onClick={() => load()}
                disabled={loading}
              >
                {loading ? "Loading…" : "Search"}
              </button>
            </div>
            <div className="col-auto">
              <button
                type="button"
                className="btn btn-outline-secondary btn-sm"
                onClick={() => {
                  setFromDate("");
                  setToDate("");
                  setSource("all");
                  setCategory("all");
                  setPayment("all");
                }}
                disabled={loading}
              >
                Clear filters
              </button>
            </div>
          </div>
          {error ? (
            <div className="alert alert-danger py-2 mt-3 mb-0">{error}</div>
          ) : null}
        </div>
      </div>

      <div className="row g-3 mb-3">
        <StatCard
          label="Showing"
          value={summary.total}
          hint="In selected filter"
          tone="primary"
        />
        <StatCard
          label="Payment pending"
          value={summary.payment_pending}
          hint="In shown rows"
          tone="warning"
        />
        <StatCard
          label="Payment done"
          value={summary.payment_done}
          hint="In shown rows"
          tone="success"
        />
        <StatCard
          label="Today"
          value={summary.today}
          hint="Updated today"
          tone="success"
        />
        <StatCard
          label="This week"
          value={summary.this_week}
          hint="Mon–today"
          tone="info"
        />
        <StatCard
          label="This month"
          value={summary.this_month}
          hint="From 1st of month"
          tone="warning"
        />
        <StatCard
          label="Employee pension"
          value={summary.employee_pension}
          tone="primary"
        />
        <StatCard
          label="Family pension"
          value={summary.family_pension}
          tone="secondary"
        />
        <StatCard label="Class 1 / 2" value={summary.class_12} tone="dark" />
        <StatCard label="Class 3 / 4" value={summary.class_34} tone="dark" />
        <StatCard
          label="Old Age Benefit"
          value={summary.oa_count}
          tone="success"
        />
        <StatCard
          label="Enhanced benefit"
          value={summary.enhanced_count}
          hint="In shown rows"
          tone="info"
        />
      </div>

      <div className="card shadow-sm">
        <div className="card-header bg-light d-flex flex-wrap justify-content-between align-items-center gap-2">
          <div className="d-flex align-items-center gap-2">
            <h5 className="mb-0">Consolidations (newest first)</h5>
            <span className="badge text-bg-secondary">{rows.length} rows</span>
            <span className="badge text-bg-primary">{selectedCount} selected</span>
          </div>
          <div className="d-flex flex-wrap gap-2">
            <button
              type="button"
              className="btn btn-success btn-sm"
              disabled={!selectedCount || actionBusy === "bulk" || loading}
              onClick={() => runBulk("paid")}
            >
              Mark selected paid
            </button>
            <button
              type="button"
              className="btn btn-outline-secondary btn-sm"
              disabled={!selectedCount || actionBusy === "bulk" || loading}
              onClick={() => runBulk("unpaid")}
            >
              Unmark selected
            </button>
            <button
              type="button"
              className="btn btn-outline-danger btn-sm"
              disabled={!selectedCount || actionBusy === "bulk" || loading}
              onClick={() => runBulk("delete")}
            >
              Delete selected
            </button>
          </div>
        </div>
        <div className="card-body" ref={tableWrapRef}>
          <SmpkDataTable
            tableKey={tableKey}
            ready={!loading}
            options={{
              responsive: false,
              scrollX: false,
              order: [],
              pageLength: 25,
              columnDefs: [
                {
                  orderable: false,
                  targets: [0],
                  className: "all",
                  responsivePriority: 1,
                },
                { responsivePriority: 1, targets: 1, className: "all" },
                { responsivePriority: 2, targets: 2 },
                {
                  targets: [6, 7, 9, 10],
                  width: "4.75rem",
                  className: "col-amt text-end",
                },
                {
                  targets: [8, 11, 12],
                  width: "5.5rem",
                  className: "col-ben text-end",
                },
                {
                  targets: 5,
                  width: "2.5rem",
                  className: "col-cat text-center",
                },
                {
                  targets: 13,
                  className: "all text-nowrap",
                  responsivePriority: 1,
                },
                { responsivePriority: 3, targets: 14 },
                { responsivePriority: 3, targets: 15 },
              ],
            }}
          >
            <thead>
              <tr>
                <th className="all">
                  <input
                    type="checkbox"
                    data-select-all-listed="1"
                    title="Select all listed rows"
                    aria-label="Select all listed rows"
                  />
                </th>
                <th className="all">Emp CD</th>
                <th>Name</th>
                <th>Case No</th>
                <th>Roll No</th>
                <th className="col-cat text-center">Category</th>
                <th className="col-amt text-end">M2@277</th>
                <th className="col-amt text-end">M1@277</th>
                <th className="col-ben text-end">Benefit@277</th>
                <th className="col-amt text-end">M2@359</th>
                <th className="col-amt text-end">M1@359</th>
                <th className="col-ben text-end">Benefit@359</th>
                <th className="col-ben text-end">OAB</th>
                <th className="all text-nowrap">Enh Benefit</th>
                <th>Consolidated by</th>
                <th>Payment</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((r) => {
                const benefit277 = benefitDiff(r.m2_277, r.m1_277);
                const benefit359 = benefitDiff(r.m2_359, r.m1_359);
                return (
                <tr
                  key={`${r.source}-${r.emp_cd}-${r.updated_at}`}
                  className={r.payment_done ? "table-success" : undefined}
                >
                  <td className="all">
                    <input
                      type="checkbox"
                      data-row-select="1"
                      data-row-key={rowKey(r.source, r.emp_cd)}
                      aria-label={`Select ${r.emp_cd}`}
                    />
                  </td>
                  <td className="all text-nowrap" data-order={r.emp_cd || ""}>
                    <button
                      type="button"
                      className="btn btn-link btn-sm p-0 me-2 align-baseline"
                      data-view-report="1"
                      data-emp-cd={r.emp_cd || ""}
                      data-source={r.source || ""}
                      data-updated={r.updated_at || ""}
                      title="View report"
                      aria-label={`View report ${r.emp_cd}`}
                    >
                      <FontAwesomeIcon icon={faEye} />
                    </button>
                    {r.emp_cd}
                  </td>
                  <td>{r.name || r.pensioner_name || "—"}</td>
                  <td>{r.case_no || "—"}</td>
                  <td>{r.roll_no || "—"}</td>
                  <td className="col-cat text-center text-nowrap">{r.category || "—"}</td>
                  <td className="col-amt text-end text-nowrap" data-order={r.m2_277 ?? ""}>
                    {fmtAmt(r.m2_277)}
                  </td>
                  <td className="col-amt text-end text-nowrap" data-order={r.m1_277 ?? ""}>
                    {fmtAmt(r.m1_277)}
                  </td>
                  <td className="col-ben text-end text-nowrap" data-order={benefit277 ?? ""}>
                    {fmtDiff(benefit277)}
                  </td>
                  <td className="col-amt text-end text-nowrap" data-order={r.m2_359 ?? ""}>
                    {fmtAmt(r.m2_359)}
                  </td>
                  <td className="col-amt text-end text-nowrap" data-order={r.m1_359 ?? ""}>
                    {fmtAmt(r.m1_359)}
                  </td>
                  <td className="col-ben text-end text-nowrap" data-order={benefit359 ?? ""}>
                    {fmtDiff(benefit359)}
                  </td>
                  <td className="col-ben text-end text-nowrap" data-order={oabAmount(r) ?? ""}>
                    {fmtAmt(oabAmount(r))}
                  </td>
                  <td className="all text-nowrap" data-order={r.enhanced_benefit ? 1 : 0}>
                    {r.enhanced_benefit ? "Yes" : "—"}
                  </td>
                  <td className="text-nowrap" data-order={r.consolidated_by || ""}>
                    {r.consolidated_by || "—"}
                  </td>
                  <td data-order={r.payment_done ? 1 : 0}>
                    {r.payment_done ? (
                      <span className="badge text-bg-success">Paid</span>
                    ) : (
                      <span className="badge text-bg-secondary">Pending</span>
                    )}
                  </td>
                </tr>
                );
              })}
            </tbody>
          </SmpkDataTable>
        </div>
      </div>

      {reportModal}
    </div>
  );
}
