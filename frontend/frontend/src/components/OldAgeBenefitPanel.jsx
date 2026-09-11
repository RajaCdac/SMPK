import React from "react";

function fmt(n) {
  if (n == null || n === "") return "—";
  const num = Number(n);
  if (Number.isNaN(num)) return String(n);
  return num.toLocaleString("en-IN", {
    minimumFractionDigits: 0,
    maximumFractionDigits: 2,
  });
}

function fmtDate(iso) {
  if (!iso) return "—";
  const [y, m] = String(iso).slice(0, 10).split("-");
  if (!y || !m) return iso;
  const months = [
    "Jan",
    "Feb",
    "Mar",
    "Apr",
    "May",
    "Jun",
    "Jul",
    "Aug",
    "Sep",
    "Oct",
    "Nov",
    "Dec",
  ];
  const mi = Number(m) - 1;
  if (mi < 0 || mi > 11) return iso;
  return `${months[mi]} ${y}`;
}

function lastMonthLabel(oldage) {
  const periods = oldage?.periods || [];
  const lastTo =
    periods.length > 0
      ? periods[periods.length - 1]?.period_to
      : oldage?.as_on_date;
  return fmtDate(lastTo);
}

/**
 * Old-age panel: period-wise (M2−M1)×age-% + DA on enhancement, to Dec-2026.
 */
export default function OldAgeBenefitPanel({
  dob,
  onDobChange,
  oldage,
  loading,
  onRecalculate,
}) {
  if (!oldage && !dob) {
    return (
      <div className="row justify-content-center mt-4 no-print">
        <div className="col-12 col-xl-10">
          <div className="card shadow border-warning">
            <div className="card-header bg-warning">
              <h5 className="mb-0">Old Age Benefit</h5>
            </div>
            <div className="card-body">
              <p className="mb-2 text-muted small">
                Enter Date of Birth (or Load employee) and run Met2 calculation to
                see period-wise old-age benefit + DA.
              </p>
              <div className="row g-2 align-items-end">
                <div className="col-auto">
                  <label className="form-label">Date of Birth</label>
                  <input
                    type="date"
                    className="form-control"
                    value={dob || ""}
                    onChange={(e) => onDobChange?.(e.target.value)}
                  />
                </div>
                <div className="col-auto">
                  <button
                    type="button"
                    className="btn btn-outline-primary"
                    disabled={!dob || loading}
                    onClick={onRecalculate}
                  >
                    {loading ? "Calculating…" : "Calculate old age"}
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    );
  }

  const periods = oldage?.periods || [];
  const uptoLabel = lastMonthLabel(oldage);

  return (
    <div className="row justify-content-center mt-4 no-print">
      <div className="col-12 col-xl-10">
        <div className="card shadow border-warning">
          <div className="card-header bg-warning d-flex justify-content-between align-items-center flex-wrap gap-2">
            <h5 className="mb-0">Old Age Benefit</h5>
            <button
              type="button"
              className="btn btn-sm btn-dark"
              disabled={!dob || loading}
              onClick={onRecalculate}
            >
              {loading ? "Calculating…" : "Recalculate"}
            </button>
          </div>
          <div className="card-body">
            <div className="row g-3 mb-3">
              <div className="col-6 col-md-3">
                <label className="form-label">Date of Birth</label>
                <input
                  type="date"
                  className="form-control"
                  value={dob || ""}
                  onChange={(e) => onDobChange?.(e.target.value)}
                />
              </div>
              <div className="col-6 col-md-3">
                <label className="form-label">Age / current %</label>
                <input
                  className="form-control"
                  readOnly
                  value={
                    oldage?.age_completed != null
                      ? `${oldage.age_completed} yrs · ${oldage.applicable_percent ?? 0}%`
                      : ""
                  }
                />
              </div>
              <div className="col-6 col-md-3">
                <label className="form-label">Current DA%</label>
                <input
                  className="form-control fw-semibold"
                  readOnly
                  value={
                    oldage?.da_pct != null ? `${oldage.da_pct}%` : "—"
                  }
                />
              </div>
              <div className="col-6 col-md-3">
                <label className="form-label">Monthly total (enh+DA)</label>
                <input
                  className="form-control fw-semibold text-primary"
                  readOnly
                  value={
                    oldage?.monthly_total != null
                      ? `Rs. ${fmt(oldage.monthly_total)}`
                      : "—"
                  }
                />
              </div>
            </div>

            <div className="row g-3 mb-3">
              <div className="col-6 col-md-3">
                <label className="form-label">Benefit @ 277</label>
                <input
                  className="form-control"
                  readOnly
                  value={fmt(oldage?.benefit_277)}
                />
              </div>
              <div className="col-6 col-md-3">
                <label className="form-label">Benefit @ 359</label>
                <input
                  className="form-control"
                  readOnly
                  value={fmt(oldage?.benefit_359)}
                />
              </div>
              <div className="col-6 col-md-3">
                <label className="form-label">Enhancement / DA (now)</label>
                <input
                  className="form-control"
                  readOnly
                  value={
                    oldage?.additional_pension != null
                      ? `${fmt(oldage.additional_pension)} + ${fmt(
                          oldage.monthly_da
                        )}`
                      : "—"
                  }
                />
              </div>
              <div className="col-6 col-md-3">
                <label className="form-label">Total arrear (enh+DA)</label>
                <input
                  className="form-control fw-semibold"
                  readOnly
                  value={
                    oldage?.total_arrear != null
                      ? `Rs. ${fmt(oldage.total_arrear)}`
                      : "—"
                  }
                />
              </div>
            </div>

            {oldage?.error && (
              <div className="alert alert-warning py-2">{oldage.error}</div>
            )}

            <p className="small text-muted mb-2">
              {oldage?.note ||
                "Enhancement + DA on enhancement for each period (DA from fi_pr_mh_calc_da)."}
              {uptoLabel !== "—" && <> Schedule upto {uptoLabel}.</>}
              {oldage?.total_arrear_basic != null && (
                <>
                  {" "}
                  Basic arrear {fmt(oldage.total_arrear_basic)} + DA arrear{" "}
                  {fmt(oldage.total_arrear_da)}.
                </>
              )}
            </p>

            <h6 className="mb-2">
              Old Age Benefit Period-wise
              {uptoLabel !== "—" ? ` (upto ${uptoLabel})` : ""}
            </h6>
            <div className="table-responsive">
              <table className="table table-sm table-bordered mb-0">
                <thead className="table-light">
                  <tr>
                    <th>From</th>
                    <th>To</th>
                    <th className="text-end">Mo</th>
                    <th>CPI</th>
                    <th>Age</th>
                    <th>%</th>
                    <th className="text-end">Benefit</th>
                    <th className="text-end">Enh/mo</th>
                    <th className="text-end">DA%</th>
                    <th className="text-end">DA/mo</th>
                    <th className="text-end">Total/mo</th>
                    <th className="text-end">Period arrear</th>
                  </tr>
                </thead>
                <tbody>
                  {periods.map((p) => (
                    <tr key={`${p.period_from}-${p.period_to}`}>
                      <td>{fmtDate(p.period_from)}</td>
                      <td>{fmtDate(p.period_to)}</td>
                      <td className="text-end">{p.months ?? "—"}</td>
                      <td>{p.cpi_period || "—"}</td>
                      <td>{p.age_slab != null ? `${p.age_slab}+` : "—"}</td>
                      <td>{p.percent != null ? `${p.percent}%` : "—"}</td>
                      <td className="text-end">{fmt(p.benefit_base)}</td>
                      <td className="text-end">{fmt(p.monthly_additional)}</td>
                      <td className="text-end">
                        {p.da_pct != null ? `${p.da_pct}%` : "—"}
                      </td>
                      <td className="text-end">{fmt(p.monthly_da)}</td>
                      <td className="text-end">{fmt(p.monthly_total)}</td>
                      <td className="text-end">{fmt(p.period_arrear)}</td>
                    </tr>
                  ))}
                  {!periods.length && (
                    <tr>
                      <td colSpan={12} className="text-muted text-center">
                        No old-age periods in range.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>

            <div className="mt-3 small">
              <strong>Rule:</strong> each period = enhancement (age-% × M2−M1 at
              CPI) + DA on that enhancement at the DA% then in force. Also splits
              when DA% changes. Chart 80→20%, 85→30%, 90→40%, 95→50%, 100→100%.
              No years after the as-on month (capped at Dec 2026).
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
