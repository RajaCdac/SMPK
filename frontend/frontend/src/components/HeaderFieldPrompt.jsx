import { useEffect, useRef, useState } from "react";

const HEADER_FIELDS = [
  { key: "name", label: "Pensioner name", type: "text" },
  { key: "case_no", label: "Case No", type: "text" },
  { key: "roll_no", label: "Roll No", type: "text" },
  { key: "tqs", label: "TQS", type: "tqs" },
  { key: "designation", label: "Designation", type: "text" },
  { key: "date_of_birth", label: "Date of birth", type: "date" },
  { key: "retirement_type", label: "Type of retirement", type: "text" },
];

const FAMILY_FIELDS = [
  { key: "date_of_death", label: "Date of death", type: "date" },
  {
    key: "family_pensioner_name",
    label: "Name of family pensioner",
    type: "text",
  },
  {
    key: "family_pensioner_dob",
    label: "Date of birth of family pensioner",
    type: "date",
  },
];

function isBlank(value) {
  return value == null || String(value).trim() === "";
}

function hasTqs(master) {
  if (!isBlank(master?.tqs)) return true;
  return [master?.tqs_yr, master?.tqs_month, master?.tqs_days].some(
    (part) => part !== null && part !== undefined && part !== ""
  );
}

export function missingConsolidationHeaderFields(master, answered) {
  const done = answered || new Set();
  const family =
    master?.is_employee_pension === false || !isBlank(master?.date_of_death);
  const specs = family ? [...HEADER_FIELDS, ...FAMILY_FIELDS] : HEADER_FIELDS;
  return specs.filter((spec) => {
    if (done.has(spec.key)) return false;
    if (spec.key === "tqs") return !hasTqs(master);
    if (spec.key === "family_pensioner_name") {
      return (
        isBlank(master?.pensioner_name) && isBlank(master?.family_pensioner_name)
      );
    }
    return isBlank(master?.[spec.key]);
  });
}

function patchFromAnswers(overrides) {
  const patch = {};
  Object.entries(overrides || {}).forEach(([key, value]) => {
    if (key === "tqs") {
      if (value == null) {
        patch.tqs = "";
        patch.tqs_yr = null;
        patch.tqs_month = null;
        patch.tqs_days = null;
      } else {
        patch.tqs_yr = value.tqs_yr;
        patch.tqs_month = value.tqs_month;
        patch.tqs_days = value.tqs_days;
        patch.tqs = `${value.tqs_yr}Y ${value.tqs_month}M ${value.tqs_days}D`;
      }
      return;
    }
    if (key === "family_pensioner_name") {
      patch.pensioner_name = value || "";
      patch.family_pensioner_name = value || "";
      return;
    }
    patch[key] = value == null ? "" : value;
  });
  return patch;
}

export function useConsolidationHeaderPrompt({ active, master, onFilled }) {
  const [prompt, setPrompt] = useState(null);
  const answeredRef = useRef(new Set());
  const empRef = useRef("");
  const onFilledRef = useRef(onFilled);
  onFilledRef.current = onFilled;

  useEffect(() => {
    const emp = String(master?.emp_cd || "").trim();
    if (emp === empRef.current) return;
    empRef.current = emp;
    answeredRef.current = new Set();
    setPrompt(null);
  }, [master?.emp_cd]);

  useEffect(() => {
    if (!active || !master?.emp_cd || prompt) return;
    const fields = missingConsolidationHeaderFields(
      master,
      answeredRef.current
    );
    if (!fields.length) return;
    setPrompt({
      fields,
      step: 0,
      empCd: master.emp_cd,
      name: master.name || "",
      overrides: {},
      keys: [],
      draft: "",
      tqsYr: "",
      tqsMonth: "",
      tqsDays: "",
      error: "",
    });
  }, [active, master, prompt]);

  const submitHeaderValue = (useNull) => {
    if (!prompt) return;
    const field = prompt.fields[prompt.step];
    if (!field) return;
    let stored = null;
    if (!useNull) {
      if (field.type === "tqs") {
        const years = prompt.tqsYr.trim();
        const months = prompt.tqsMonth.trim();
        const days = prompt.tqsDays.trim();
        if (years === "" || months === "" || days === "") {
          setPrompt((prev) => ({
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
          setPrompt((prev) => ({
            ...prev,
            error: "TQS must be 0–80 years, 0–11 months and 0–30 days.",
          }));
          return;
        }
        stored = { tqs_yr: y, tqs_month: m, tqs_days: d };
      } else if (field.type === "date") {
        if (!prompt.draft) {
          setPrompt((prev) => ({
            ...prev,
            error: "Choose a date, or choose Null.",
          }));
          return;
        }
        stored = prompt.draft;
      } else if (!prompt.draft.trim()) {
        setPrompt((prev) => ({
          ...prev,
          error: "Enter a value, or choose Null.",
        }));
        return;
      } else {
        stored = prompt.draft.trim();
      }
    }
    const overrides = { ...prompt.overrides, [field.key]: stored };
    const keys = [...prompt.keys, field.key];
    const next = prompt.step + 1;
    if (next < prompt.fields.length) {
      setPrompt({
        ...prompt,
        step: next,
        overrides,
        keys,
        draft: "",
        tqsYr: "",
        tqsMonth: "",
        tqsDays: "",
        error: "",
      });
      return;
    }
    keys.forEach((key) => answeredRef.current.add(key));
    setPrompt(null);
    onFilledRef.current(patchFromAnswers(overrides));
  };

  return { prompt, setPrompt, submitHeaderValue };
}

export default function HeaderFieldPrompt({ prompt, onChange, onSave, onNull }) {
  const field = prompt?.fields?.[prompt.step];
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
              {prompt.name ? ` — ${prompt.name}` : ""}. This header value is
              not in the database. Enter it, or choose Null.
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
                type="text"
                className="form-control"
                value={prompt.draft}
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
