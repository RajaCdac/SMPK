import { useEffect, useState } from "react";
import API from "../services/Api";

const emptyForm = {
  separation_type: "",
  separation_date: "",
  remarks: "",
};

function toInputDate(value) {
  if (!value) return "";
  if (/^\d{4}-\d{2}-\d{2}/.test(String(value))) return String(value).slice(0, 10);
  const parts = String(value).split("-");
  if (parts.length === 3 && parts[0].length <= 2) {
    return `${parts[2]}-${parts[1]}-${parts[0]}`;
  }
  return value;
}

function hasSavedIntake(data, completed) {
  return Boolean(
    completed ||
      (data?.separation_type && data?.separation_date)
  );
}

export default function ProcessIntakeForm({
  employee,
  onComplete,
  onContinue,
  onBack,
  backLabel = "Back to ESR Check",
  continueLabel = "Next — No-pay entry",
}) {
  const [form, setForm] = useState(emptyForm);
  const [savedForm, setSavedForm] = useState(emptyForm);
  const [recordExists, setRecordExists] = useState(false);
  const [isEditing, setIsEditing] = useState(false);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!employee) return undefined;

    let cancelled = false;

    const load = async () => {
      setLoading(true);
      setError("");

      let data = employee.process_intake_data;
      let completed = employee.process_intake_completed;

      if (data === undefined && completed === undefined) {
        try {
          const res = await API.get(
            `first-pension/process-intake/employee/${employee.emp_id}/`
          );
          completed = res.data.completed;
          data = res.data.intake_data;
        } catch (err) {
          console.error(err);
          if (!cancelled) {
            setError("Could not load process intake details.");
            setLoading(false);
          }
          return;
        }
      }

      if (cancelled) return;

      const exists = hasSavedIntake(data, completed);
      const loaded = {
        separation_type: data?.separation_type || "",
        separation_date: toInputDate(data?.separation_date) || "",
        remarks: data?.remarks || "",
      };

      setForm(loaded);
      setSavedForm(loaded);
      setRecordExists(exists);
      setIsEditing(!exists);
      setLoading(false);
    };

    load();

    return () => {
      cancelled = true;
    };
  }, [employee]);

  const handleChange = (e) => {
    const { name, value } = e.target;
    setForm((prev) => ({ ...prev, [name]: value }));
  };

  const handleEdit = () => {
    setIsEditing(true);
    setError("");
  };

  const handleCancelEdit = () => {
    setForm(savedForm);
    setIsEditing(false);
    setError("");
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setSubmitting(true);
    setError("");

    try {
      const res = await API.post("first-pension/process-intake/", {
        emp_code: employee.emp_id,
        name: employee.name,
        class: employee.class,
        birth_date: employee.birth_date,
        joining_date: employee.join_date,
        retirement_date: employee.expected_retirement_date,
        designation: employee.designation,
        scale: employee.scale,
        last_basic: employee.basic_amount,
        separation_type: form.separation_type,
        separation_date: form.separation_date,
        remarks: form.remarks,
      });

      const saved = {
        separation_type: res.data.intake_data?.separation_type || form.separation_type,
        separation_date: toInputDate(
          res.data.intake_data?.separation_date || form.separation_date
        ),
        remarks: res.data.intake_data?.remarks ?? form.remarks,
      };

      setForm(saved);
      setSavedForm(saved);
      setRecordExists(true);
      setIsEditing(false);
      if (res.data.oracle_warning) {
        alert(res.data.oracle_warning);
      }
      onComplete?.(res.data);
    } catch (err) {
      console.error(err);
      setError(
        err.response?.data?.error || "Failed to save process intake."
      );
    } finally {
      setSubmitting(false);
    }
  };

  if (!employee) return null;

  if (loading) {
    return (
      <p className="text-muted text-center">Loading process details...</p>
    );
  }

  const fieldsDisabled = recordExists && !isEditing;
  const showSubmit = !recordExists || isEditing;

  return (
    <form onSubmit={handleSubmit} className="process-intake-form smpk-form">
      <p className="text-muted small mb-3">
        {recordExists && !isEditing
          ? "Separation details are saved. Click Edit to change, or continue to No-pay."
          : "Enter separation details before continuing. Separation date is not the same as retirement date."}
      </p>

      <div className="row g-3 process-intake-fields">
        {employee.expected_retirement_date && (
          <div className="col-12 col-md-6 col-lg-4">
            <label className="form-label">Retirement Date (reference)</label>
            <input
              type="text"
              className="form-control"
              value={employee.expected_retirement_date}
              readOnly
            />
          </div>
        )}

        <div className="col-12 col-md-6 col-lg-4">
          <label className="form-label">Separation Type</label>
          <select
            className="form-select"
            name="separation_type"
            value={form.separation_type}
            onChange={handleChange}
            disabled={fieldsDisabled}
            required={showSubmit}
          >
            <option value="">Select</option>
            <option value="RT">Superannuation</option>
            <option value="DT">Death</option>
            <option value="VR">Voluntary Retirement</option>
          </select>
        </div>

        <div className="col-12 col-md-6 col-lg-4">
          <label className="form-label">Separation Date</label>
          <input
            type="date"
            className="form-control"
            name="separation_date"
            value={form.separation_date}
            onChange={handleChange}
            disabled={fieldsDisabled}
            required={showSubmit}
          />
        </div>

        <div className="col-12">
          <label className="form-label">Remarks</label>
          <textarea
            className="form-control"
            name="remarks"
            rows={4}
            placeholder="Enter remarks (optional)"
            value={form.remarks}
            onChange={handleChange}
            disabled={fieldsDisabled}
          />
        </div>
      </div>

      {error && (
        <p className="text-danger mt-3 mb-0" role="alert">
          {error}
        </p>
      )}

      <div className="smpk-form-actions process-intake-actions">
        {onBack ? (
          <button
            type="button"
            className="btn btn-outline-secondary"
            onClick={onBack}
            disabled={submitting}
          >
            {backLabel}
          </button>
        ) : null}
        {showSubmit && (
          <>
            <button
              type="submit"
              className="btn btn-primary"
              disabled={submitting}
            >
              {submitting
                ? "Saving..."
                : recordExists
                  ? "Update"
                  : "Submit"}
            </button>
            {recordExists && isEditing && (
              <button
                type="button"
                className="btn btn-outline-secondary"
                onClick={handleCancelEdit}
                disabled={submitting}
              >
                Cancel
              </button>
            )}
          </>
        )}

        {recordExists && !isEditing && (
          <>
            <button
              type="button"
              className="btn btn-outline-primary"
              onClick={handleEdit}
            >
              Edit
            </button>
            <button
              type="button"
              className="btn btn-primary"
              onClick={() => onContinue?.()}
            >
              {continueLabel}
            </button>
          </>
        )}
      </div>
    </form>
  );
}
