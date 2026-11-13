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

const CPI_277_START = "2017-01-01";
const CPI_277_END = "2021-12-31";
const CPI_359_START = "2022-01-01";
const HORIZON_END = "2026-12-31";
const M1_KEYS = ["277_50", "277_30", "359_50", "359_30"];

function fmtDate(iso) {
  if (!iso) return "";
  const [y, m, d] = iso.split("-");
  return `${d}.${m}.${y}`;
}

function nextDay(iso) {
  const d = new Date(`${iso}T00:00:00Z`);
  d.setUTCDate(d.getUTCDate() + 1);
  return d.toISOString().slice(0, 10);
}

/** Last day of the 50% rate: enhanced upto when after death, else date of death. */
function rateCutover(values) {
  const dod = values.date_of_death;
  const upto = values.double_fpension_upto;
  if (upto && (!dod || upto > dod)) return upto;
  return dod || "";
}

/**
 * M1 inputs for this case. A CPI period gets a 50% field when the employee or
 * enhanced pension runs into it, and a 30% field when family pension does.
 */
function m1Fields(values) {
  const class34 = values.category === "3" || values.category === "4";
  const cut = rateCutover(values);
  const eras = [
    { cpi: "277", start: CPI_277_START, end: class34 ? CPI_277_END : HORIZON_END },
  ];
  if (class34) eras.push({ cpi: "359", start: CPI_359_START, end: HORIZON_END });
  const fields = [];
  eras.forEach(({ cpi, start, end }) => {
    const has50 = !!cut && cut >= start;
    const has30 = !cut || cut < end;
    if (has50) {
      const to = cut < end ? cut : end;
      fields.push({
        key: `${cpi}_50`,
        label: `M1@${cpi} (50%)`,
        period: `${fmtDate(start)} – ${fmtDate(to)}`,
      });
    }
    if (has30) {
      const from = cut && cut >= start ? nextDay(cut) : start;
      fields.push({
        key: `${cpi}_30`,
        label: `M1@${cpi} (30%)`,
        period: `${fmtDate(from)} – ${fmtDate(end)}`,
      });
    }
  });
  return fields;
}

function valuesFromMaster(master) {
  const m = master || {};
  const cat = String(m.category || "").trim();
  const inputs = m.m1_inputs || m.m1_inputs_db || {};
  const m1 = {};
  M1_KEYS.forEach((key) => {
    m1[`m1_${key}`] = numText(inputs[key]);
  });
  // CR 02-11-2026 (emp 15068): no fallback to m1_family_pension_* here. On a
  // P-only wage row that field is the employee pension, so the 30% box got the
  // 50% amount. A 30% amount missing in the DB stays blank and must be typed.
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
    ...m1,
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
  ["last_pay", "average_pay", ...m1Fields(values).map((f) => `m1_${f.key}`)].forEach((key) => {
    const v = values[key];
    if (!blank(v) && (!Number.isFinite(Number(v)) || Number(v) < 0)) {
      errors[key] = "Enter a valid amount.";
    }
  });
  m1Fields(values).forEach((f) => {
    const key = `m1_${f.key}`;
    if (blank(values[key])) {
      errors[key] = "Not in the database. Enter this amount from the file.";
    }
  });
  // CR 02-11-2026 (emp 15068): family pension (30%) can never equal the
  // employee / enhanced pension (50%) at the same CPI — block the save.
  m1Fields(values).forEach((f) => {
    if (!f.key.endsWith("_30")) return;
    const key30 = `m1_${f.key}`;
    const key50 = `m1_${f.key.replace("_30", "_50")}`;
    if (errors[key30] || !(key50 in values) || blank(values[key50])) return;
    if (!m1Fields(values).some((x) => `m1_${x.key}` === key50)) return;
    if (Number(values[key30]) === Number(values[key50])) {
      const cpi = f.key.split("_")[0];
      errors[key30] =
        `M1@${cpi} (30%) cannot be the same as M1@${cpi} (50%). ` +
        "Enter the family pension amount from the file.";
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
  // Only the M1 fields shown for this case are sent; they override the
  // wage-table M1 on the matching print columns.
  const amount = (key) => {
    const v = values[`m1_${key}`];
    return blank(v) ? null : Number(v);
  };
  const inputs = {};
  m1Fields(values).forEach(({ key }) => {
    inputs[key] = amount(key);
  });
  patch.m1_inputs = inputs;
  patch.rate_cutover = rateCutover(values) || null;
  const pick = (cpi) => {
    if (`${cpi}_30` in inputs) return inputs[`${cpi}_30`];
    if (`${cpi}_50` in inputs) return inputs[`${cpi}_50`];
    return null;
  };
  patch.m1_family_pension_277 = pick("277");
  patch.m1_family_pension_359 = pick("359");
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

  const m1FieldList = m1Fields(values);
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
      {/* CR 06-11-2026 (emp 00334): scale / last pay taken from the family pension claim. */}
      {!blank(master?.scale_note) ? (
        <div className="form-text text-danger">{master.scale_note}</div>
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
              {m1FieldList.map((f) => {
                const key = `m1_${f.key}`;
                // CR 02-11-2026 (emp 15068): the old "Same as the 30%" hint is
                // now a blocking error on the 30% box (see validate).
                return (
                  <div key={key} className="col-6 col-md-3">
                    <label className="form-label small mb-1">{f.label} *</label>
                    <input
                      type="number"
                      min="0"
                      className={cls(key)}
                      value={values[key]}
                      onChange={(e) => set(key, e.target.value)}
                    />
                    <div className="form-text">
                      {f.key.endsWith("_50") ? "Employee / enhanced" : "Family"}:{" "}
                      {f.period}
                    </div>
                    {blank(initial[key]) && !errors[key] ? (
                      <div className="form-text text-danger">
                        Not in the database. Enter this amount from the file.
                      </div>
                    ) : null}
                    {err(key)}
                  </div>
                );
              })}
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
