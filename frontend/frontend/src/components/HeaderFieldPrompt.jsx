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

const FAMILY_AMOUNT_FIELDS = [
  { key: "m1_277", label: "M1@277", type: "number" },
  { key: "m1_359", label: "M1@359", type: "number" },
];

const CLASS_OPTIONS = [
  { value: "1", label: "Class 1" },
  { value: "2", label: "Class 2" },
  { value: "3", label: "Class 3" },
  { value: "4", label: "Class 4" },
];

/** Family consolidation menu: confirm every header from the database. */
const FAMILY_CONFIRM_FIELDS = [
  { key: "name", label: "Employee name", type: "text" },
  { key: "category", label: "Class of employee", type: "category" },
  {
    key: "family_pensioner_name",
    label: "Name of family pensioner",
    type: "text",
  },
  { key: "case_no", label: "Case No", type: "text" },
  { key: "roll_no", label: "Roll No", type: "text" },
  { key: "designation", label: "Designation", type: "text" },
  { key: "tqs", label: "TQS", type: "tqs" },
  { key: "retirement_type", label: "Type of retirement", type: "text" },
  {
    key: "retirement_date",
    label: "Date of retirement / separation",
    type: "date",
  },
  { key: "date_of_death", label: "Date of death", type: "date" },
  {
    key: "date_of_birth",
    label: "Date of birth of employee",
    type: "date",
  },
  {
    key: "family_pensioner_dob",
    label: "Date of birth of family pensioner",
    type: "date",
  },
  {
    key: "double_fpension_upto",
    label: "Enhanced family pension upto",
    type: "date",
  },
  { key: "scale", label: "Pay scale", type: "scale" },
  { key: "last_pay", label: "Last pay", type: "pay" },
  { key: "m1_277", label: "M1@277", type: "number" },
  { key: "m1_359", label: "M1@359", type: "number" },
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

function isFamilyMaster(master) {
  return (
    master?.is_employee_pension === false || !isBlank(master?.date_of_death)
  );
}

function amountMissing(master, key) {
  if (key === "m1_277") return isBlank(master?.m1_family_pension_277);
  if (key === "m1_359") return isBlank(master?.m1_family_pension_359);
  return false;
}

function isoDate(value) {
  if (isBlank(value)) return "";
  const text = String(value).trim();
  if (/^\d{4}-\d{2}-\d{2}/.test(text)) return text.slice(0, 10);
  return text;
}

function numberDraft(value) {
  if (isBlank(value)) return "";
  return String(value).replace(/,/g, "");
}

function resolvedCategory(master, amounts) {
  // Prefer master (confirmed / DB) over form default (often "3").
  return String(master?.category || amounts?.category || "").trim();
}

export function missingConsolidationHeaderFields(master, answered, amounts) {
  const done = answered || new Set();
  const family = isFamilyMaster(master);
  const specs = family ? [...HEADER_FIELDS, ...FAMILY_FIELDS] : [...HEADER_FIELDS];
  if (family) {
    const category = resolvedCategory(master, amounts);
    if (isBlank(category) && !done.has("category")) {
      specs.splice(1, 0, {
        key: "category",
        label: "Class of employee",
        type: "category",
      });
    }
    FAMILY_AMOUNT_FIELDS.forEach((spec) => {
      if (spec.key.endsWith("359") && category !== "3" && category !== "4") {
        return;
      }
      specs.push(spec);
    });
  }
  return specs.filter((spec) => {
    if (done.has(spec.key)) return false;
    if (spec.key === "tqs") return !hasTqs(master);
    if (spec.key === "family_pensioner_name") {
      return (
        isBlank(master?.pensioner_name) && isBlank(master?.family_pensioner_name)
      );
    }
    if (spec.key === "category") {
      return isBlank(master?.category);
    }
    if (spec.key === "m1_277" || spec.key === "m1_359") {
      return amountMissing(master, spec.key);
    }
    return isBlank(master?.[spec.key]);
  });
}

export function familyConfirmHeaderFields(master, amounts) {
  const category = resolvedCategory(master, amounts);
  return FAMILY_CONFIRM_FIELDS.filter((spec) => {
    // M1@359 only for class 3/4 — never while class is unknown/defaulted.
    if (spec.key === "m1_359" && category !== "3" && category !== "4") {
      return false;
    }
    return true;
  });
}

function draftStateForField(master, field) {
  if (field.type === "tqs") {
    return {
      draft: "",
      tqsYr:
        master?.tqs_yr != null && master?.tqs_yr !== ""
          ? String(master.tqs_yr)
          : "",
      tqsMonth:
        master?.tqs_month != null && master?.tqs_month !== ""
          ? String(master.tqs_month)
          : "",
      tqsDays:
        master?.tqs_days != null && master?.tqs_days !== ""
          ? String(master.tqs_days)
          : "",
    };
  }
  if (field.key === "family_pensioner_name") {
    return {
      draft:
        master?.family_pensioner_name || master?.pensioner_name || "",
      tqsYr: "",
      tqsMonth: "",
      tqsDays: "",
    };
  }
  if (field.key === "category" || field.type === "category") {
    const cat = String(master?.category || "").trim();
    return {
      draft: ["1", "2", "3", "4"].includes(cat) ? cat : "",
      tqsYr: "",
      tqsMonth: "",
      tqsDays: "",
    };
  }
  if (field.key === "m1_277") {
    return {
      draft: numberDraft(master?.m1_family_pension_277),
      tqsYr: "",
      tqsMonth: "",
      tqsDays: "",
    };
  }
  if (field.key === "m1_359") {
    return {
      draft: numberDraft(master?.m1_family_pension_359),
      tqsYr: "",
      tqsMonth: "",
      tqsDays: "",
    };
  }
  if (field.key === "last_pay" || field.type === "pay") {
    const stages = Array.isArray(master?.pay_stages) ? master.pay_stages : [];
    const raw = numberDraft(master?.last_pay);
    let draft = "";
    if (raw) {
      const match = stages.find((item) => String(item) === String(raw));
      draft = match != null ? String(match) : stages.length ? "" : raw;
    }
    return {
      draft,
      tqsYr: "",
      tqsMonth: "",
      tqsDays: "",
    };
  }
  if (field.key === "scale" || field.type === "scale") {
    const options = Array.isArray(master?.scale_options)
      ? master.scale_options
      : [];
    const rawScale = !isBlank(master?.scale) ? String(master.scale).trim() : "";
    const rawDisplay = !isBlank(master?.scale_display)
      ? String(master.scale_display).trim()
      : "";
    const canon = (text) =>
      String(text || "")
        .trim()
        .toLowerCase()
        .replace(/\s+/g, "")
        .replace(/–|—/g, "-");
    let draft = "";
    for (const item of options) {
      const value = scaleOptionValue(item);
      const label = scaleOptionLabel(item);
      if (
        (rawScale &&
          (canon(value) === canon(rawScale) ||
            canon(label) === canon(rawScale))) ||
        (rawDisplay &&
          (canon(value) === canon(rawDisplay) ||
            canon(label) === canon(rawDisplay)))
      ) {
        draft = value;
        break;
      }
    }
    // If a class-specific list is loaded, do not keep a non-matching value
    // (e.g. class 3/4 pay band after user chose class 1/2).
    if (!draft) draft = options.length ? "" : rawScale || "";
    return {
      draft,
      tqsYr: "",
      tqsMonth: "",
      tqsDays: "",
    };
  }
  if (field.type === "date") {
    return {
      draft: isoDate(master?.[field.key]),
      tqsYr: "",
      tqsMonth: "",
      tqsDays: "",
    };
  }
  return {
    draft: isBlank(master?.[field.key]) ? "" : String(master[field.key]),
    tqsYr: "",
    tqsMonth: "",
    tqsDays: "",
  };
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
    if (key === "m1_277") {
      patch.m1_family_pension_277 = value == null ? null : value;
      return;
    }
    if (key === "m1_359") {
      patch.m1_family_pension_359 = value == null ? null : value;
      return;
    }
    if (key === "last_pay") {
      patch.last_pay = value == null ? "" : value;
      return;
    }
    patch[key] = value == null ? "" : value;
  });
  return patch;
}

export function scaleOptionValue(item) {
  if (item && typeof item === "object") {
    // Same as the form Scale dropdown: grade for class 1/2.
    return String(item.grade || item.label || item.pay_band || item.scale || "");
  }
  return item == null ? "" : String(item);
}

export function scaleOptionLabel(item) {
  if (item && typeof item === "object") {
    const label = String(item.label || item.pay_band || item.scale || "").trim();
    const grade = String(item.grade || "").trim();
    if (label && grade && label !== grade) return `${label} (${grade})`;
    return label || grade;
  }
  return item == null ? "" : String(item);
}

function buildPromptState(
  master,
  fields,
  step = 0,
  overrides = {},
  keys = [],
  scaleOptionsOverride = null,
  payStagesOverride = null
) {
  const options = Array.isArray(scaleOptionsOverride)
    ? scaleOptionsOverride
    : Array.isArray(master?.scale_options)
      ? master.scale_options
      : [];
  const payStages = Array.isArray(payStagesOverride)
    ? payStagesOverride
    : Array.isArray(master?.pay_stages)
      ? master.pay_stages
      : [];
  const patchedMaster = {
    ...(master || {}),
    ...patchFromAnswers(overrides),
    scale_options: options,
    pay_stages: payStages,
  };
  const field = fields[step];
  const draft = draftStateForField(patchedMaster, field);
  return {
    fields,
    step,
    empCd: master.emp_cd,
    name: master.name || "",
    overrides,
    keys,
    mode: "confirm",
    scaleOptions: options,
    payStages,
    error: "",
    ...draft,
  };
}

function parseStoredValue(prompt, field, useNull) {
  if (useNull) return { ok: true, stored: null };
  if (field.type === "tqs") {
    const years = prompt.tqsYr.trim();
    const months = prompt.tqsMonth.trim();
    const days = prompt.tqsDays.trim();
    if (years === "" || months === "" || days === "") {
      return {
        ok: false,
        error: "Enter years, months and days, or choose Null.",
      };
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
      return {
        ok: false,
        error: "TQS must be 0–80 years, 0–11 months and 0–30 days.",
      };
    }
    return { ok: true, stored: { tqs_yr: y, tqs_month: m, tqs_days: d } };
  }
  if (field.type === "date") {
    if (!prompt.draft) {
      return { ok: false, error: "Choose a date, or choose Null." };
    }
    return { ok: true, stored: prompt.draft };
  }
  if (field.type === "scale") {
    if (!prompt.draft.trim()) {
      return { ok: false, error: "Choose a pay scale, or choose Null." };
    }
    return { ok: true, stored: prompt.draft.trim() };
  }
  if (field.type === "category" || field.key === "category") {
    const cat = prompt.draft.trim();
    if (!["1", "2", "3", "4"].includes(cat)) {
      return { ok: false, error: "Choose class 1, 2, 3 or 4." };
    }
    return { ok: true, stored: cat };
  }
  if (field.type === "pay" || field.key === "last_pay") {
    const stages = Array.isArray(prompt.payStages) ? prompt.payStages : [];
    const text = prompt.draft.trim().replace(/,/g, "");
    if (!text) {
      return {
        ok: false,
        error: stages.length
          ? "Choose last pay from the list, or choose Null."
          : "Enter last pay, or choose Null.",
      };
    }
    const amount = Number(text);
    if (!Number.isFinite(amount) || amount < 0) {
      return { ok: false, error: "Enter a valid last pay, or choose Null." };
    }
    if (
      stages.length &&
      !stages.some((item) => String(item) === String(text))
    ) {
      return {
        ok: false,
        error: "Last pay must be one of the pay stages for this scale.",
      };
    }
    return { ok: true, stored: amount };
  }
  if (field.type === "number") {
    const text = prompt.draft.trim().replace(/,/g, "");
    const amount = Number(text);
    if (!text || !Number.isFinite(amount) || amount < 0) {
      return { ok: false, error: "Enter an amount, or choose Null." };
    }
    return { ok: true, stored: amount };
  }
  if (!prompt.draft.trim()) {
    return { ok: false, error: "Enter a value, or choose Null." };
  }
  // Header text (name, designation, case/roll, retirement type, …) always CAPS.
  return { ok: true, stored: prompt.draft.trim().toUpperCase() };
}

export function useConsolidationHeaderPrompt({
  active,
  master,
  onFilled,
  amounts,
  confirmAll = false,
  loadScaleOptions = null,
  loadPayStages = null,
}) {
  const [prompt, setPrompt] = useState(null);
  const answeredRef = useRef(new Set());
  const empRef = useRef("");
  const startedRef = useRef("");
  const onFilledRef = useRef(onFilled);
  const loadScaleOptionsRef = useRef(loadScaleOptions);
  const loadPayStagesRef = useRef(loadPayStages);
  onFilledRef.current = onFilled;
  loadScaleOptionsRef.current = loadScaleOptions;
  loadPayStagesRef.current = loadPayStages;

  useEffect(() => {
    const emp = String(master?.emp_cd || "").trim();
    if (emp === empRef.current) return;
    empRef.current = emp;
    answeredRef.current = new Set();
    startedRef.current = "";
    setPrompt(null);
  }, [master?.emp_cd]);

  useEffect(() => {
    if (!active || !master?.emp_cd || prompt) return;
    if (confirmAll) {
      const token = `${master.emp_cd}|confirm`;
      if (startedRef.current === token) return;
      const fields = familyConfirmHeaderFields(master, amounts);
      if (!fields.length) return;
      startedRef.current = token;
      setPrompt(buildPromptState(master, fields, 0, {}, []));
      return;
    }
    const fields = missingConsolidationHeaderFields(
      master,
      answeredRef.current,
      amounts
    );
    if (!fields.length) return;
    setPrompt({
      fields,
      step: 0,
      empCd: master.emp_cd,
      name: master.name || "",
      overrides: {},
      keys: [],
      mode: "missing",
      draft: "",
      tqsYr: "",
      tqsMonth: "",
      tqsDays: "",
      payStages: [],
      scaleOptions: [],
      error: "",
    });
  }, [active, master, prompt, amounts, confirmAll]);

  const openConfirmStep = async (fields, step, overrides, keys) => {
    const nextField = fields[step];
    let scaleOptions = null;
    let payStages = null;
    const patched = {
      ...(master || {}),
      ...patchFromAnswers(overrides),
    };
    const date = patched.retirement_date || "";
    const cat = String(
      patched.category || master?.category || amounts?.category || ""
    ).trim();
    if (
      nextField &&
      (nextField.type === "scale" || nextField.key === "scale") &&
      typeof loadScaleOptionsRef.current === "function"
    ) {
      try {
        scaleOptions = await loadScaleOptionsRef.current(date, cat);
      } catch (err) {
        console.error(err);
        scaleOptions = [];
      }
    }
    if (
      nextField &&
      (nextField.type === "pay" || nextField.key === "last_pay") &&
      typeof loadPayStagesRef.current === "function"
    ) {
      try {
        payStages = await loadPayStagesRef.current(
          patched.scale || "",
          date,
          cat
        );
      } catch (err) {
        console.error(err);
        payStages = [];
      }
    }
    setPrompt(
      buildPromptState(
        master,
        fields,
        step,
        overrides,
        keys,
        scaleOptions,
        payStages
      )
    );
  };

  const submitHeaderValue = async (useNull) => {
    if (!prompt) return;
    const field = prompt.fields[prompt.step];
    if (!field) return;
    // Class must be chosen — Null is not allowed for category.
    if (
      useNull &&
      (field.type === "category" || field.key === "category")
    ) {
      setPrompt((prev) => ({
        ...prev,
        error: "Choose class 1, 2, 3 or 4.",
      }));
      return;
    }
    const parsed = parseStoredValue(prompt, field, useNull);
    if (!parsed.ok) {
      setPrompt((prev) => ({ ...prev, error: parsed.error }));
      return;
    }
    const overrides = { ...prompt.overrides, [field.key]: parsed.stored };
    // Class / scale change invalidates dependent answers.
    if (field.key === "category") {
      delete overrides.scale;
      delete overrides.last_pay;
    }
    if (field.key === "scale") {
      delete overrides.last_pay;
    }
    const keys = [...prompt.keys, field.key].filter((key) => {
      if (field.key === "category" && (key === "scale" || key === "last_pay")) {
        return false;
      }
      if (field.key === "scale" && key === "last_pay") return false;
      return true;
    });

    // After class is set, rebuild remaining prompts so M1@359 appears only
    // for class 3/4 (and scale list follows class 1/2 vs 3/4).
    if (prompt.mode === "confirm") {
      const patchedMaster = {
        ...(master || {}),
        ...patchFromAnswers(overrides),
        ...(field.key === "category"
          ? { scale: "", scale_display: "", last_pay: "" }
          : {}),
        ...(field.key === "scale" ? { last_pay: "" } : {}),
      };
      const fields =
        field.key === "category"
          ? familyConfirmHeaderFields(patchedMaster, {
              ...(amounts || {}),
              category: overrides.category,
            })
          : prompt.fields;
      const nextStep = fields.findIndex((f) => !keys.includes(f.key));
      if (nextStep < 0) {
        keys.forEach((key) => answeredRef.current.add(key));
        setPrompt(null);
        onFilledRef.current(patchFromAnswers(overrides));
        return;
      }
      await openConfirmStep(fields, nextStep, overrides, keys);
      return;
    }

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

  const goBackHeaderValue = async () => {
    if (!prompt || prompt.step <= 0) return;
    const keys = [...(prompt.keys || [])];
    const prevKey = keys.pop();
    const overrides = { ...prompt.overrides };
    if (prevKey) delete overrides[prevKey];

    if (prompt.mode === "confirm") {
      // Rebuild field list (e.g. after backing past class, M1@359 may drop).
      const patchedMaster = {
        ...(master || {}),
        ...patchFromAnswers(overrides),
      };
      const fields = familyConfirmHeaderFields(patchedMaster, {
        ...(amounts || {}),
        category: overrides.category ?? patchedMaster.category,
      });
      const idx =
        prevKey != null ? fields.findIndex((f) => f.key === prevKey) : -1;
      const step =
        idx >= 0 ? idx : Math.max(0, Math.min(prompt.step - 1, fields.length - 1));
      await openConfirmStep(fields, step, overrides, keys);
      return;
    }

    const step = Math.max(0, prompt.step - 1);
    const field = prompt.fields[step];
    const draft = draftStateForField(
      { ...(master || {}), ...patchFromAnswers(overrides) },
      field
    );
    setPrompt({
      ...prompt,
      step,
      overrides,
      keys,
      error: "",
      ...draft,
    });
  };

  return { prompt, setPrompt, submitHeaderValue, goBackHeaderValue };
}

function headerFieldHint(fieldKey, mode, prompt) {
  if (mode === "confirm") {
    if (fieldKey === "category") {
      return "Choose class 1, 2, 3 or 4. Class 1/2 uses M1@277 only; class 3/4 also asks M1@359.";
    }
    if (fieldKey === "scale") {
      if (prompt?.scaleOptions?.length) {
        return isBlank(prompt.draft)
          ? "No pay scale in the database. Choose one for this retirement date."
          : "Pay scale for this retirement date. Press OK to keep it, or choose another.";
      }
      return "Confirm the retirement date first so the scale list can load, or type the scale.";
    }
    if (fieldKey === "last_pay") {
      if (prompt?.payStages?.length) {
        return "Choose last pay from the stages for this scale (same list as on the form).";
      }
      return "Confirm pay scale first so pay stages can load, or enter last pay.";
    }
    return "Value from the database. Press OK to keep it, or change it first. Use Back to fix an earlier field.";
  }
  if (fieldKey === "category") {
    return "Class is needed so the correct M1 amount(s) are asked. Choose 1, 2, 3 or 4.";
  }
  if (fieldKey === "last_pay") {
    return "Choose last pay from the pay stages for the selected scale.";
  }
  if (fieldKey === "m1_277" || fieldKey === "m1_359") {
    return "This amount is not in the database. Enter it, or choose Null to leave it blank.";
  }
  return "This header value is not in the database. Enter it, or choose Null.";
}

export default function HeaderFieldPrompt({
  prompt,
  onChange,
  onSave,
  onNull,
  onBack,
}) {
  const field = prompt?.fields?.[prompt.step];
  if (!field) return null;
  const setDraft = (draft) => onChange({ ...prompt, draft, error: "" });
  const confirm = prompt.mode === "confirm";
  const canBack = typeof onBack === "function" && prompt.step > 0;
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
              {prompt.name ? ` — ${prompt.name}` : ""}.{" "}
              {headerFieldHint(field.key, prompt.mode, prompt)}
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
            ) : field.type === "category" || field.key === "category" ? (
              <select
                className="form-select"
                value={prompt.draft}
                onChange={(e) => setDraft(e.target.value)}
              >
                <option value="">Select class</option>
                {CLASS_OPTIONS.map((item) => (
                  <option key={item.value} value={item.value}>
                    {item.label}
                  </option>
                ))}
              </select>
            ) : field.type === "scale" ? (
              prompt.scaleOptions?.length ? (
                <select
                  className="form-select"
                  value={prompt.draft}
                  onChange={(e) => setDraft(e.target.value)}
                >
                  <option value="">Select Scale</option>
                  {prompt.scaleOptions.map((item, index) => {
                    const value = scaleOptionValue(item);
                    const label = scaleOptionLabel(item);
                    return (
                      <option key={`${value}-${index}`} value={value}>
                        {label}
                      </option>
                    );
                  })}
                </select>
              ) : (
                <input
                  type="text"
                  className="form-control"
                  value={prompt.draft}
                  placeholder="Select retirement date first, or type the scale"
                  onChange={(e) => setDraft(e.target.value)}
                />
              )
            ) : field.type === "pay" || field.key === "last_pay" ? (
              prompt.payStages?.length ? (
                <select
                  className="form-select"
                  value={prompt.draft}
                  onChange={(e) => setDraft(e.target.value)}
                >
                  <option value="">Select Last Pay</option>
                  {prompt.payStages.map((item, index) => (
                    <option key={`${item}-${index}`} value={item}>
                      {item}
                    </option>
                  ))}
                </select>
              ) : (
                <input
                  type="number"
                  className="form-control"
                  value={prompt.draft}
                  min="0"
                  placeholder="Confirm scale first, or enter last pay"
                  onChange={(e) => setDraft(e.target.value)}
                />
              )
            ) : (
              <input
                type={field.type === "number" ? "number" : "text"}
                className="form-control"
                value={prompt.draft}
                min={field.type === "number" ? "0" : undefined}
                onChange={(e) => setDraft(e.target.value)}
              />
            )}
            {prompt.error ? (
              <div className="text-danger small mt-2">{prompt.error}</div>
            ) : null}
          </div>
          <div className="modal-footer">
            {canBack ? (
              <button
                type="button"
                className="btn btn-outline-primary me-auto"
                onClick={onBack}
              >
                Back
              </button>
            ) : null}
            <button type="button" className="btn btn-outline-secondary" onClick={onNull}>
              Null
            </button>
            <button type="button" className="btn btn-primary" onClick={onSave}>
              {confirm ? "OK" : "Save"}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
