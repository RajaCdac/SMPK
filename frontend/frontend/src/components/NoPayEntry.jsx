import { useState, useEffect } from "react";
import API from "../services/Api";

const emptyForm = {
  id: null,
  emp_code: "",
  no_pay_days: "",
  dies_non_days: "",
  no_pay_more_than_240_days: "",
  suspension_days: "",
};

function applyNoPayData(setForm, data, empId) {
  setForm({
    id: data.id,
    emp_code: data.emp_code || empId,
    no_pay_days: data.no_pay_days ?? 0,
    dies_non_days: data.dies_non_days ?? 0,
    no_pay_more_than_240_days: data.no_pay_more_than_240_days ?? 0,
    suspension_days: data.suspension_days ?? 0,
  });
}

export default function NoPayEntry({ employee }) {
  const [form, setForm] = useState(emptyForm);
  const [recordExists, setRecordExists] = useState(false);
  const [isEditing, setIsEditing] = useState(false);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!employee) return;

    const loadFromDb = async () => {
      setLoading(true);

      let data = null;
      let exists = false;

      if (employee.no_pay_exists && employee.no_pay_data) {
        exists = true;
        data = employee.no_pay_data;
      } else {
        try {
          const res = await API.get(
            `first-pension/no-pay/employee/${employee.emp_id}/`
          );
          exists = res.data.exists;
          data = res.data.no_pay_data;
        } catch (error) {
          console.error(error);
        }
      }

      if (exists && data) {
        applyNoPayData(setForm, data, employee.emp_id);
        setRecordExists(true);
        setIsEditing(false);
      } else {
        setRecordExists(false);
        setIsEditing(true);
        setForm({
          ...emptyForm,
          emp_code: employee.emp_id,
        });
      }

      setLoading(false);
    };

    loadFromDb();
  }, [employee]);

  const handleChange = (e) => {
    const { name, value } = e.target;
    setForm((prev) => ({ ...prev, [name]: value }));
  };

  const buildPayload = () => ({
    emp_code: employee.emp_id,
    name: employee.name,
    class: employee.class,
    birth_date: employee.birth_date,
    joining_date: employee.join_date,
    retirement_date: employee.expected_retirement_date,
    designation: employee.designation,
    scale: employee.scale,
    last_basic: employee.basic_amount,
    no_pay_days: form.no_pay_days || 0,
    dies_non_days: form.dies_non_days || 0,
    no_pay_more_than_240_days: form.no_pay_more_than_240_days || 0,
    suspension_days: form.suspension_days || 0,
  });

  const handleSubmit = async (e) => {
    e.preventDefault();
    const isUpdate = Boolean(form.id);

    const noPayPayload = {
      no_pay_days: form.no_pay_days || 0,
      dies_non_days: form.dies_non_days || 0,
      no_pay_more_than_240_days: form.no_pay_more_than_240_days || 0,
      suspension_days: form.suspension_days || 0,
    };

    try {
      const response = isUpdate
        ? await API.put(`first-pension/no-pay/${form.id}/`, noPayPayload)
        : await API.post("first-pension/no-pay/", buildPayload());

      const message = isUpdate
        ? "No-Pay Entry Updated Successfully"
        : "No-Pay Entry Saved Successfully";

      alert(message);

      if (response.data.no_pay_data) {
        applyNoPayData(setForm, response.data.no_pay_data, employee.emp_id);
      }

      setRecordExists(true);
      setIsEditing(false);
    } catch (error) {
      console.error(error);
      alert(error.response?.data?.error || "Save Failed");
    }
  };

  const handleEdit = () => {
    setIsEditing(true);
  };

  if (!employee) return null;

  if (loading) {
    return (
      <p className="text-muted mb-0">Loading no-pay details...</p>
    );
  }

  const fieldsDisabled = recordExists && !isEditing;
  const saveDisabled = recordExists && !isEditing;

  return (
    <form onSubmit={handleSubmit}>
      <div className="row">
        <div className="col-md-3 mb-3">
          <label className="form-label fw-bold">Employee Code</label>
          <input
            type="text"
            className="form-control"
            name="emp_code"
            value={form.emp_code}
            readOnly
          />
        </div>
        <div className="col-md-3 mb-3">
          <label className="form-label fw-bold">No Pay Days</label>
          <input
            type="number"
            min="0"
            className="form-control"
            name="no_pay_days"
            placeholder="Enter No Pay Days"
            value={form.no_pay_days}
            onChange={handleChange}
            disabled={fieldsDisabled}
          />
        </div>
        <div className="col-md-3 mb-3">
          <label className="form-label fw-bold">Dies Non Days</label>
          <input
            type="number"
            min="0"
            className="form-control"
            name="dies_non_days"
            placeholder="Enter Dies Non Days"
            value={form.dies_non_days}
            onChange={handleChange}
            disabled={fieldsDisabled}
          />
        </div>
        <div className="col-md-3 mb-3">
          <label className="form-label fw-bold">No Pay More Than 240 Days</label>
          <input
            type="number"
            min="0"
            className="form-control"
            name="no_pay_more_than_240_days"
            placeholder="Enter days"
            value={form.no_pay_more_than_240_days}
            onChange={handleChange}
            disabled={fieldsDisabled}
          />
        </div>
        <div className="col-md-3 mb-3">
          <label className="form-label fw-bold">Suspension Days</label>
          <input
            type="number"
            min="0"
            className="form-control"
            name="suspension_days"
            placeholder="Enter Suspension Days"
            value={form.suspension_days}
            onChange={handleChange}
            disabled={fieldsDisabled}
          />
        </div>
      </div>
      <div className="text-end">
        {recordExists && (
          <button
            type="button"
            className="btn btn-secondary me-2"
            onClick={handleEdit}
            disabled={isEditing}
          >
            Edit
          </button>
        )}
        <button
          type="submit"
          className="btn btn-success"
          disabled={saveDisabled}
        >
          Save
        </button>
      </div>
    </form>
  );
}
