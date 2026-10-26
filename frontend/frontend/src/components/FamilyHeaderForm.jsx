import { useEffect, useMemo, useRef, useState } from "react";
import { scaleOptionLabel, scaleOptionValue } from "./HeaderFieldPrompt";

const CLASS_OPTIONS = ["1", "2", "3", "4"];

const TEXT_KEYS = [
  "name",
  "family_pensioner_name",
  "case_no",
  "roll_no",
  "designation",
  "retirement_type",
];

function blank(value) {
  return value == null || String(value).trim() === "";
}

function isoDate(value) {
  if (blank(value)) return "";
  const text = String(value).trim();
  return /^\d{4}-\d{2}-\d{2}/.test(text) ? text.slice(0, 10) : "";
}

function numText(value) {
  return blank(value) ? "" : String(value).replace(/,/g, "");
}

function canon(text) {
  return String(text || "")
    .trim()
    .toLowerCase()
    .replace(/\s+/g, "")
    .replace(/–|—/g, "-");
}

/** Option value for a database scale (grade or pay band text). */
function matchScale(options, ...candidates) {
  for (const raw of candidates) {
    if (blank(raw)) continue;
    for (const item of options) {
      if (
        canon(scaleOptionValue(item)) === canon(raw) ||
        canon(scaleOptionLabel(item)) === canon(raw)
      ) {
        return scaleOptionValue(item);
      }
    }
  }
  return "";
}

function valuesFromMaster(master) {
  const m = master || {};
  const cat = String(m.category || "").trim();
  return {
    name: m.name || "",
    category: CLASS_OPTIONS.includes(cat) ? cat : "",
    family_pensioner_name: m.family_pensioner_name || m.pensioner_name || "",
    case_no: m.case_no || "",
    roll_no: m.roll_no || "",
    designation: m.designation || "",
    retirement_type: m.retirement_type || "",
    retirement_date: isoDate(m.retirement_date),
    date_of_birth: isoDate(m.date_of_birth),
    tqs_yr: blank(m.tqs_yr) ? "" : String(m.tqs_yr),
    tqs_month: blank(m.tqs_month) ? "" : String(m.tqs_month),
    tqs_days: blank(m.tqs_days) ? "" : String(m.tqs_days),
    date_of_death: isoDate(m.date_of_death),
    family_pensioner_dob: isoDate(m.family_pensioner_dob),
    double_fpension_upto: isoDate(m.double_fpension_upto),
    scale: String(m.scale || "").trim(),
    last_pay: numText(m.last_pay),
    average_pay: numText(m.average_pay),
    m1_277: numText(m.m1_family_pension_277),
    m1_359: numText(m.m1_family_pension_359),
  };
}

function validate(values, payStages) {
  const errors = {};
  if (!CLASS_OPTIONS.includes(values.category)) {
    errors.category = "Choose the class.";
  }
  const tqs = [values.tqs_yr, values.tqs_month, values.tqs_days];
  if (tqs.some((p) => !blank(p))) {
    const [y, m, d] = tqs.map((p) => Number(p));
    if (
      tqs.some((p) => blank(p)) ||
      ![y, m, d].every(Number.isInteger) ||
      y < 0 || y > 80 || m < 0 || m > 11 || d < 0 || d > 30
    ) {
      errors.tqs = "TQS: years 0–80, months 0–11, days 0–30 (fill all three or none).";
    }
  }
  ["last_pay", "average_pay", "m1_277", "m1_359"].forEach((key) => {
    const v = values[key];
    if (!blank(v) && (!Number.isFinite(Number(v)) || Number(v) < 0)) {
      errors[key] = "Enter a valid amount.";
    }
  });
  if (
    !errors.last_pay &&
    !blank(values.last_pay) &&
    payStages.length &&
    !payStages.some((s) => String(s) === String(values.last_pay))
  ) {
    errors.last_pay = "Last pay must be one of the pay stages for this scale.";
  }
  return errors;
}

/** Same shape the one-by-one popup sends to onFilled. */
function patchFromValues(values) {
  const patch = {};
  TEXT_KEYS.forEach((key) => {
    patch[key] = String(values[key] || "").trim().toUpperCase();
  });
  patch.pensioner_name = patch.family_pensioner_name;
  patch.category = values.category;
  [
    "retirement_date",
    "date_of_birth",
    "date_of_death",
    "family_pensioner_dob",
    "double_fpension_upto",
  ].forEach((key) => {
    patch[key] = values[key] || "";
  });
  if (blank(values.tqs_yr)) {
    patch.tqs = "";
    patch.tqs_yr = null;
    patch.tqs_month = null;
    patch.tqs_days = null;
  } else {
    patch.tqs_yr = Number(values.tqs_yr);
    patch.tqs_month = Number(values.tqs_month);
    patch.tqs_days = Number(values.tqs_days);
    patch.tqs = `${patch.tqs_yr}Y ${patch.tqs_month}M ${patch.tqs_days}D`;
  }
  patch.scale = values.scale || "";
  patch.last_pay = blank(values.last_pay) ? "" : Number(values.last_pay);
  patch.average_pay = blank(values.average_pay) ? "" : Number(values.average_pay);
  patch.m1_family_pension_277 = blank(values.m1_277) ? null : Number(values.m1_277);
  const class34 = values.category === "3" || values.category === "4";
  patch.m1_family_pension_359 =
    class34 && !blank(values.m1_359) ? Number(values.m1_359) : null;
  return patch;
}

export default function FamilyHeaderForm({
  master,
  loadScaleOptions,
  loadPayStages,
  onSubmit,
  onClose,
}) {
  const initial = useMemo(() => valuesFromMaster(master), [master]);
  const [values, setValues] = useState(initial);
  const [scaleOptions, setScaleOptions] = useState([]);
  const [payStages, setPayStages] = useState([]);
  const [loadingScales, setLoadingScales] = useState(false);
  const [loadingPay, setLoadingPay] = useState(false);
  const [errors, setErrors] = useState({});
  const [saving, setSaving] = useState(false);
  const scaleReq = useRef(0);
  const payReq = useRef(0);
  const firstScaleLoad = useRef(true);

  useEffect(() => {
    setValues(initial);
    setErrors({});
    firstScaleLoad.current = true;
  }, [initial]);

  const set = (key, value) => {
    setValues((prev) => ({ ...prev, [key]: value }));
    setErrors((prev) => {
      if (!prev[key] && !(key.startsWith("tqs") && prev.tqs)) return prev;
      const next = { ...prev };
      delete next[key];
      if (key.startsWith("tqs")) delete next.tqs;
      return next;
    });
  };

  // Scale list depends on class and retirement date.
  useEffect(() => {
    const id = ++scaleReq.current;
    if (!values.category || !values.retirement_date || !loadScaleOptions) {
      setScaleOptions([]);
      return;
    }
    setLoadingScales(true);
    Promise.resolve(loadScaleOptions(values.retirement_date, values.category))
      .catch(() => [])
      .then((options) => {
        if (id !== scaleReq.current) return;
        const list = Array.isArray(options) ? options : [];
        setScaleOptions(list);
        setLoadingScales(false);
        const first = firstScaleLoad.current;
        firstScaleLoad.current = false;
        setValues((prev) => {
          const keep = matchScale(list, prev.scale);
          const fromDb = first
            ? matchScale(list, master?.scale, master?.scale_display)
            : "";
          const next = keep || fromDb;
          if (next === prev.scale) return prev;
          // A class / date change that drops the scale also drops its last pay.
          return { ...prev, scale: next, last_pay: first ? prev.last_pay : "" };
        });
      });
  }, [values.category, values.retirement_date, loadScaleOptions, master]);

  // Pay stages depend on scale (and class / date for class 1/2).
  useEffect(() => {
    const id = ++payReq.current;
    if (!values.scale || !loadPayStages) {
      setPayStages([]);
      return;
    }
    setLoadingPay(true);
    Promise.resolve(
      loadPayStages(values.scale, values.retirement_date, values.category)
    )
      .catch(() => [])
      .then((stages) => {
        if (id !== payReq.current) return;
        setPayStages(Array.isArray(stages) ? stages : []);
        setLoadingPay(false);
      });
  }, [values.scale, values.retirement_date, values.category, loadPayStages]);

  const class34 = values.category === "3" || values.category === "4";
  const changed = (key) => String(values[key] ?? "") !== String(initial[key] ?? "");
  const cls = (key, base = "form-control form-control-sm") =>
    `${base}${errors[key] ? " is-invalid" : ""}${
      changed(key) ? " border-warning bg-warning-subtle" : ""
    }`;
  const err = (key) =>
    errors[key] ? <div className="invalid-feedback d-block">{errors[key]}</div> : null;

  const text = (key, label, col = "col-12 col-md-4") => (
    <div className={col}>
      <label className="form-label small mb-1">{label}</label>
      <input
        type="text"
        className={cls(key)}
        style={{ textTransform: "uppercase" }}
        value={values[key]}
        onChange={(e) => set(key, e.target.value)}
      />
      {err(key)}
    </div>
  );

  const date = (key, label, col = "col-6 col-md-3") => (
    <div className={col}>
      <label className="form-label small mb-1">{label}</label>
      <input
        type="date"
        className={cls(key)}
        value={values[key]}
        onChange={(e) => set(key, e.target.value)}
      />
      {err(key)}
    </div>
  );

  const amount = (key, label, col = "col-6 col-md-3") => (
    <div className={col}>
      <label className="form-label small mb-1">{label}</label>
      <input
        type="number"
        min="0"
        className={cls(key)}
        value={values[key]}
        onChange={(e) => set(key, e.target.value)}
      />
      {err(key)}
    </div>
  );

  const lastPayInList =
    blank(values.last_pay) ||
    payStages.some((s) => String(s) === String(values.last_pay));

  const classField = (
    <div className="col-6 col-md-2">
      <label className="form-label small mb-1">Class *</label>
      <select
        className={cls("category", "form-select form-select-sm")}
        value={values.category}
        onChange={(e) => set("category", e.target.value)}
      >
        <option value="">Select</option>
        {CLASS_OPTIONS.map((c) => (
          <option key={c} value={c}>
            Class {c}
          </option>
        ))}
      </select>
      {err("category")}
    </div>
  );

  const tqsField = (
    <div className="col-12 col-md-2">
      <label className="form-label small mb-1">TQS (Y / M / D)</label>
      <div className="input-group input-group-sm">
        {["tqs_yr", "tqs_month", "tqs_days"].map((key, i) => (
          <input
            key={key}
            type="number"
            min="0"
            className={`${cls(key)}${errors.tqs ? " is-invalid" : ""} px-1`}
            placeholder={["Y", "M", "D"][i]}
            title={["Years", "Months (0–11)", "Days (0–30)"][i]}
            value={values[key]}
            onChange={(e) => set(key, e.target.value)}
          />
        ))}
      </div>
      {err("tqs")}
    </div>
  );

  const lastPayInput = payStages.length ? (
    <select
      className={cls("last_pay", "form-select form-select-sm")}
      value={values.last_pay}
      onChange={(e) => set("last_pay", e.target.value)}
    >
      <option value="">{loadingPay ? "Loading..." : "Select last pay"}</option>
      {!lastPayInList ? (
        <option value={values.last_pay}>{values.last_pay} (not a pay stage)</option>
      ) : null}
      {payStages.map((s, i) => (
        <option key={`${s}-${i}`} value={s}>
          {s}
        </option>
      ))}
    </select>
  ) : (
    <input
      type="number"
      min="0"
      className={cls("last_pay")}
      placeholder={values.scale ? (loadingPay ? "Loading..." : "") : "Choose scale first"}
      value={values.last_pay}
      onChange={(e) => set("last_pay", e.target.value)}
    />
  );

  const payField = (
    <div className="col-6 col-md-3">
      <label className="form-label small mb-1">Last pay</label>
      {lastPayInput}
      {err("last_pay")}
      <label className="form-label small mb-1 mt-2">Average pay</label>
      <input
        type="number"
        min="0"
        className={cls("average_pay")}
        placeholder="Same as last pay if empty"
        value={values.average_pay}
        onChange={(e) => set("average_pay", e.target.value)}
      />
      {err("average_pay")}
    </div>
  );

  const scaleField = (
    <div className="col-12 col-md-4">
      <label className="form-label small mb-1">Pay scale</label>
      <select
        className={cls("scale", "form-select form-select-sm")}
        value={values.scale}
        onChange={(e) => {
          set("scale", e.target.value);
          set("last_pay", "");
        }}
        disabled={!scaleOptions.length}
      >
        <option value="">
          {!values.category
            ? "Choose class first"
            : !values.retirement_date
              ? "Enter retirement date first"
              : loadingScales
                ? "Loading scales..."
                : "Select scale"}
        </option>
        {scaleOptions.map((item, index) => (
          <option key={`${scaleOptionValue(item)}-${index}`} value={scaleOptionValue(item)}>
            {scaleOptionLabel(item)}
          </option>
        ))}
      </select>
      {!values.scale && !blank(master?.scale_display || master?.scale) ? (
        <div className="form-text">
          Database scale: {master.scale_display || master.scale} (not in list for
          this class / date)
        </div>
      ) : null}
    </div>
  );

  const submit = async () => {
    const found = validate(values, payStages);
    setErrors(found);
    if (Object.keys(found).length) return;
    setSaving(true);
    try {
      await onSubmit(patchFromValues(values));
    } finally {
      setSaving(false);
    }
  };

  return (
    <div
      className="modal fade show d-block"
      style={{ background: "rgba(0,0,0,0.45)" }}
      role="dialog"
      aria-modal="true"
    >
      <div
        className="modal-dialog modal-xl modal-dialog-scrollable"
        style={{ maxWidth: "min(1700px, 96vw)" }}
      >
        <div className="modal-content">
          <div className="modal-header">
            <h5 className="modal-title">
              Family pension header — Emp {master?.emp_cd}
            </h5>
            <button type="button" className="btn-close" onClick={onClose} />
          </div>
          <div className="modal-body">
            <p className="small text-muted mb-3">
              Values are filled from the database. Check them against the physical
              file and change anything that differs; changed fields turn yellow.
              Leave a field empty if it is not available.
            </p>

            <h6 className="border-bottom pb-1">Employee</h6>
            <div className="row g-2 mb-2">
              {text("name", "Employee name", "col-12 col-md-3")}
              {classField}
              {text("designation", "Designation", "col-12 col-md-3")}
              {date("retirement_date", "Date of retirement (DOR)", "col-6 col-md-2")}
              {tqsField}
            </div>
            <div className="row g-2 mb-3 align-items-start">
              {date("double_fpension_upto", "Enhanced pension date upto", "col-6 col-md-3")}
              {payField}
              {scaleField}
              {date("date_of_birth", "Date of birth (DOB)", "col-6 col-md-2")}
            </div>

            <h6 className="border-bottom pb-1">Family pensioner</h6>
            <div className="row g-2 mb-3">
              {text("family_pensioner_name", "Family pensioner name", "col-12 col-md-6")}
              {date("family_pensioner_dob", "DOB of family pensioner")}
              {date("date_of_death", "Date of death of ex-employee")}
            </div>

            <h6 className="border-bottom pb-1">M-I</h6>
            <div className="row g-2 mb-3">
              {amount("m1_277", "277")}
              {class34 ? amount("m1_359", "359") : null}
            </div>

            <h6 className="border-bottom pb-1 text-muted">Other details</h6>
            <div className="row g-2">
              {text("case_no", "Case No", "col-6 col-md-3")}
              {text("roll_no", "Roll No", "col-6 col-md-3")}
              {text("retirement_type", "Type of retirement", "col-12 col-md-6")}
            </div>
          </div>
          <div className="modal-footer">
            <button
              type="button"
              className="btn btn-outline-secondary me-auto"
              onClick={() => {
                setValues(initial);
                setErrors({});
              }}
              disabled={saving}
            >
              Reset to database values
            </button>
            <button
              type="button"
              className="btn btn-outline-secondary"
              onClick={onClose}
              disabled={saving}
            >
              Close
            </button>
            <button
              type="button"
              className="btn btn-primary"
              onClick={submit}
              disabled={saving}
            >
              {saving ? "Applying..." : "Save and continue"}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
