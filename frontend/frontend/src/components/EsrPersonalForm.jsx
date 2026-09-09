import "../styles/FamilyPensionClaim.css";
import "../styles/EsrPersonal.css";

/**
 * Oracle FI_XX_MH_EMP_PER_E — Personal Information entry (read-only, prefilled).
 */
export default function EsrPersonalForm({ form, loading, onClose }) {
  if (!form && !loading) return null;

  const groups = form?.groups || [];

  return (
    <div
      className="esr-form-overlay"
      role="presentation"
      onClick={onClose}
      onKeyDown={(e) => {
        if (e.key === "Escape") onClose?.();
      }}
    >
      <div
        className="esr-form-window"
        role="dialog"
        aria-modal="true"
        aria-labelledby="esr-personal-form-title"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="fpc-title-bar" id="esr-personal-form-title">
          {form?.title || "Personal Information"}
        </div>

        <div className="esr-form-toolbar">
          <span className="esr-form-toolbar-meta">
            {form?.emp_cd ? (
              <>
                Employee <strong>{form.emp_cd}</strong>
              </>
            ) : (
              "Loading…"
            )}
          </span>
          <button
            type="button"
            className="btn btn-sm btn-light"
            onClick={onClose}
          >
            Close
          </button>
        </div>

        <div className="fpc-panel esr-form-panel">
          {loading ? (
            <p className="esr-form-loading">Loading personal record…</p>
          ) : null}

          {!loading && groups.length === 0 ? (
            <p className="text-muted mb-0">No personal fields to display.</p>
          ) : null}

          {!loading
            ? groups.map((group) => (
                <fieldset key={group.id} className="fpc-group">
                  <legend>{group.legend}</legend>
                  {(group.rows || []).map((row, rowIdx) => (
                    <div key={`${group.id}-${rowIdx}`} className="fpc-row">
                      {(row || []).map((field) => (
                        <div
                          key={field.key}
                          className={`fpc-field fpc-w-${field.width || "md"}`}
                        >
                          <label className="fpc-label" htmlFor={`esr-${field.key}`}>
                            {field.label}
                          </label>
                          <input
                            id={`esr-${field.key}`}
                            className="form-control"
                            readOnly
                            value={field.value ?? ""}
                            tabIndex={-1}
                          />
                        </div>
                      ))}
                    </div>
                  ))}
                </fieldset>
              ))
            : null}
        </div>
      </div>
    </div>
  );
}
