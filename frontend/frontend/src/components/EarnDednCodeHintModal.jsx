import { useEffect, useMemo, useState } from "react";
import API from "../services/Api";
import "../styles/EarnDednCodeHint.css";

let cachedDeductions = null;
let cachePromise = null;

async function loadDeductionList() {
  if (cachedDeductions) return cachedDeductions;
  if (cachePromise) return cachePromise;
  cachePromise = API.get("first-pension/earn-dedn-list/?type=D")
    .then((res) => {
      cachedDeductions = res.data?.items || [];
      return cachedDeductions;
    })
    .finally(() => {
      cachePromise = null;
    });
  return cachePromise;
}

export function clearEarnDednHintCache() {
  cachedDeductions = null;
  cachePromise = null;
}

export default function EarnDednCodeHintModal({
  open,
  onClose,
  onSelect,
  title = "Deduction codes",
}) {
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [filter, setFilter] = useState("");

  useEffect(() => {
    if (!open) return;
    let cancelled = false;
    setFilter("");
    setLoading(true);
    setError("");
    loadDeductionList()
      .then((list) => {
        if (!cancelled) setItems(list);
      })
      .catch((err) => {
        if (!cancelled) {
          setError(err.response?.data?.error || "Could not load deduction codes.");
          setItems([]);
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [open]);

  useEffect(() => {
    if (!open) return undefined;
    const onKey = (e) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, onClose]);

  const filtered = useMemo(() => {
    const q = filter.trim().toLowerCase();
    if (!q) return items;
    return items.filter(
      (row) =>
        String(row.code || "").toLowerCase().includes(q) ||
        String(row.desc || "").toLowerCase().includes(q)
    );
  }, [items, filter]);

  if (!open) return null;

  return (
    <div
      className="earn-dedn-hint-backdrop"
      role="presentation"
      onClick={onClose}
    >
      <div
        className="earn-dedn-hint-modal"
        role="dialog"
        aria-modal="true"
        aria-labelledby="earn-dedn-hint-title"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="earn-dedn-hint-header">
          <h6 id="earn-dedn-hint-title" className="mb-0">
            {title}
          </h6>
          <button
            type="button"
            className="btn-close btn-close-sm"
            aria-label="Close"
            onClick={onClose}
          />
        </div>
        <p className="earn-dedn-hint-sub text-muted mb-2">
          Press F9 on the code field or click a row to select. Oracle LOV:
          FI_PN_MH_EARNDEDN (deductions).
        </p>
        <input
          type="search"
          className="form-control form-control-sm mb-2"
          placeholder="Search code or description…"
          value={filter}
          onChange={(e) => setFilter(e.target.value)}
          autoFocus
        />
        {loading && <p className="text-muted small mb-0">Loading…</p>}
        {error && <p className="text-danger small mb-0">{error}</p>}
        {!loading && !error && (
          <div className="earn-dedn-hint-table-wrap">
            <table className="table table-sm table-hover earn-dedn-hint-table mb-0">
              <thead>
                <tr>
                  <th>Code</th>
                  <th>Description</th>
                </tr>
              </thead>
              <tbody>
                {filtered.length === 0 ? (
                  <tr>
                    <td colSpan={2} className="text-muted text-center">
                      No codes found
                    </td>
                  </tr>
                ) : (
                  filtered.map((row) => (
                    <tr
                      key={row.code}
                      className="earn-dedn-hint-row"
                      onClick={() => onSelect(row)}
                    >
                      <td className="fw-semibold">{row.code}</td>
                      <td>{row.desc}</td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
