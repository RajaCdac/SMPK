import { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import API from "../services/Api";
import NoPayLeaveDetailsModal from "./NoPayLeaveDetailsModal";

const emptyForm = {
  id: null,
  no_pay_days: "",
  dies_non_days: "",
  no_pay_more_than_240_days: "",
  suspension_days: "",
  boys_serv_days: "",
};

function applyNoPayData(setForm, data) {
  setForm({
    id: data.id,
    no_pay_days: data.no_pay_days ?? 0,
    dies_non_days: data.dies_non_days ?? 0,
    no_pay_more_than_240_days: data.no_pay_more_than_240_days ?? 0,
    suspension_days: data.suspension_days ?? 0,
    boys_serv_days: data.boys_serv_days ?? 0,
  });
}

export default function NoPayEntry({
  employee,
  showProposalNext = false,
  proposalNextTo = "",
  showNext = false,
  nextTo = "",
  nextLabel = "Next →",
  onBack,
  backLabel = "Back to ESR Check",
}) {
  const [form, setForm] = useState(emptyForm);
  const [recordExists, setRecordExists] = useState(false);
  const [isEditing, setIsEditing] = useState(false);
  const [loading, setLoading] = useState(true);
  const [showLeaveDetails, setShowLeaveDetails] = useState(false);
  const [saveNotice, setSaveNotice] = useState("");

  useEffect(() => {
    if (!employee) return;

    const loadFromDb = async () => {
      setLoading(true);
      setShowLeaveDetails(false);
      setSaveNotice("");

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
        applyNoPayData(setForm, data);
        setRecordExists(true);
        setIsEditing(false);
      } else {
        // No SMPK pension case / no-pay row → blank editable form.
        setRecordExists(false);
        setIsEditing(true);
        setForm({ ...emptyForm });
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
    boys_serv_days: form.boys_serv_days || 0,
  });

  const handleSubmit = async (e) => {
    e.preventDefault();
    const isUpdate = Boolean(form.id);

    const noPayPayload = {
      no_pay_days: form.no_pay_days || 0,
      dies_non_days: form.dies_non_days || 0,
      no_pay_more_than_240_days: form.no_pay_more_than_240_days || 0,
      suspension_days: form.suspension_days || 0,
      boys_serv_days: form.boys_serv_days || 0,
    };

    try {
      const response = isUpdate
        ? await API.put(`first-pension/no-pay/${form.id}/`, noPayPayload)
        : await API.post("first-pension/no-pay/", buildPayload());

      const message = isUpdate
        ? "No-Pay Entry Updated Successfully"
        : "No-Pay Entry Saved Successfully";

      if (response.data.no_pay_data) {
        applyNoPayData(setForm, response.data.no_pay_data);
      }

      setRecordExists(true);
      setIsEditing(false);
      setSaveNotice(message);
    } catch (error) {
      console.error(error);
      setSaveNotice("");
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
  const showNextProposal =
    showProposalNext &&
    Boolean(proposalNextTo) &&
    recordExists &&
    !isEditing;
  const showNextForm =
    showNext && Boolean(nextTo) && recordExists && !isEditing;
  const nextHref = showNextProposal ? proposalNextTo : nextTo;
  const nextText = showNextProposal ? "Next: Pension Proposal →" : nextLabel;

  return (
    <form onSubmit={handleSubmit} className="smpk-form">
      {saveNotice ? (
        <div className="alert alert-success py-2 mb-3" role="status">
          {saveNotice}
          {showNextProposal ? (
            <span className="ms-1">
              Next: complete{" "}
              <strong>Pension Proposal</strong> for this employee.
            </span>
          ) : showNextForm ? (
            <span className="ms-1">
              Continue to <strong>Commutation</strong> for this employee.
            </span>
          ) : null}
        </div>
      ) : null}

      {showNextProposal && !saveNotice ? (
        <div className="alert alert-info py-2 mb-3" role="status">
          No-pay is saved. Continue to Pension Proposal for this employee.
        </div>
      ) : null}
      {showNextForm && !saveNotice && !showNextProposal ? (
        <div className="alert alert-info py-2 mb-3" role="status">
          No-pay is saved. Continue to Commutation for this employee.
        </div>
      ) : null}

      <div className="row g-3">
        <div className="col-6 col-sm-6 col-md-3">
          <label className="form-label">No Pay Days (Prior to 10 Mnths)</label>
          <input type="number"  min="0"  className="form-control" name="no_pay_days" placeholder="Enter No Pay Days" value={form.no_pay_days} onChange={handleChange} disabled={fieldsDisabled} />
        </div>
        <div className="col-6 col-sm-6 col-md-3">
          <label className="form-label">Dies Non Days</label>
          <input type="number" min="0" className="form-control" name="dies_non_days" placeholder="Enter Dies Non Days" value={form.dies_non_days} onChange={handleChange} disabled={fieldsDisabled} />
        </div>
        <div className="col-6 col-sm-6 col-md-2">
          <label className="form-label">No Pay More Than 240 Days</label>
          <input type="number" min="0" className="form-control" name="no_pay_more_than_240_days" placeholder="No Pay More Than 240 Days" value={form.no_pay_more_than_240_days} onChange={handleChange} disabled={fieldsDisabled}  />
        </div>        
        <div className="col-6 col-sm-6 col-md-2">
          <label className="form-label">Suspension Days</label>
          <input type="number" min="0" className="form-control" name="suspension_days" placeholder="Enter Suspension Days" value={form.suspension_days} onChange={handleChange} disabled={fieldsDisabled} />
        </div>
        <div className="col-6 col-sm-6 col-md-2">
          <label className="form-label">Boys Serv Days</label>
          <input type="number" min="0" className="form-control" name="boys_serv_days" placeholder="Enter Boys Serv Days" value={form.boys_serv_days} onChange={handleChange} disabled={fieldsDisabled} />
        </div>
      </div>
      <div className="smpk-form-actions justify-content-end flex-wrap gap-2">
        {onBack ? (
          <button
            type="button"
            className="btn btn-outline-secondary me-auto"
            onClick={onBack}
          >
            {backLabel}
          </button>
        ) : null}
        <button
          type="button"
          className="btn btn-outline-primary"
          onClick={() => setShowLeaveDetails(true)}
          disabled={!employee?.emp_id}
        >
          Details
        </button>
        {recordExists && (
          <button
            type="button"
            className="btn btn-secondary"
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
        {showNextProposal || showNextForm ? (
          <Link
            to={nextHref}
            className="btn btn-primary"
            title={nextText}
          >
            {nextText}
          </Link>
        ) : null}
      </div>

      <NoPayLeaveDetailsModal
        empId={employee?.emp_id}
        open={showLeaveDetails}
        onClose={() => setShowLeaveDetails(false)}
      />
    </form>
  );
}
