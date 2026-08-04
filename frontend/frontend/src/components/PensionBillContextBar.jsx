export default function PensionBillContextBar({
  billContext,
  loading,
  onRefresh,
}) {
  const status = billContext?.status;

  return (
    <div className="card mb-3 border-primary-subtle pension-bill-context">
      <div className="card-body py-2">
        <div className="d-flex flex-wrap align-items-center justify-content-between gap-2">
          <div className="d-flex flex-wrap gap-3 small">
            <span>
              <span className="text-muted">Pension month: </span>
              <strong>
                {status?.pension_month && status?.pension_yr
                  ? `${status.pension_month}/${status.pension_yr}`
                  : "—"}
              </strong>
            </span>
            <span>
              <span className="text-muted">Bill No: </span>
              <strong>{billContext?.billNo || "—"}</strong>
            </span>
            <span>
              <span className="text-muted">Voucher: </span>
              <strong>{billContext?.voucherNo || "—"}</strong>
            </span>
          </div>
          <button
            type="button"
            className="btn btn-outline-secondary btn-sm"
            onClick={onRefresh}
            disabled={loading}
          >
            {loading ? "Refreshing…" : "Refresh"}
          </button>
        </div>
      </div>
    </div>
  );
}
