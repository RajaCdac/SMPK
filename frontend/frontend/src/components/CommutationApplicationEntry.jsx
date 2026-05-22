import { useState, useEffect } from "react";
import API from "../services/Api";

const emptyForm = {
  appcn_no: "",
  emp_cd: "",
  application_time: 1,
  comm_start_mnth: 1,
  appcn_dt: "",
  application_rcvd_dt: "",
  impl_fpen_combill: "",
  commutation_dt: "",
  restoration_dt: "",
  commutation_per: "",
  mo_certificate_dt: "",
  mo_certificate_ref: "",
  commutation_reasons: "",
};

function toInputDate(dateStr) {
  if (!dateStr) return "";
  if (/^\d{4}-\d{2}-\d{2}/.test(dateStr)) return dateStr.slice(0, 10);
  const parts = dateStr.split("-");
  if (parts.length === 3 && parts[0].length <= 2) {
    return `${parts[2]}-${parts[1]}-${parts[0]}`;
  }
  return dateStr;
}

export default function CommutationApplicationEntry({ employee }) {
  const [commutationForm, setCommutationForm] = useState(emptyForm);
  const [isSaved, setIsSaved] = useState(false);
  const [isEditing, setIsEditing] = useState(true);
  const [appcnLoading, setAppcnLoading] = useState(true);

  const handleChange = (e) => {
    const { name, value } = e.target;
    setCommutationForm((prev) => ({ ...prev, [name]: value }));
  };

  const fetchApplicationNo = async () => {
    try {
      const response = await API.get("first-pension/commutation/");
      setCommutationForm((prev) => ({
        ...prev,
        appcn_no: response.data.appcn_no,
      }));
    } catch (error) {
      console.error(error);
    } finally {
      setAppcnLoading(false);
    }
  };

  useEffect(() => {
    if (!employee) return;

    if (employee.commutation_exists && employee.commutation_data) {
      const data = employee.commutation_data;
      setIsSaved(true);
      setIsEditing(false);
      setAppcnLoading(false);
      setCommutationForm({
        ...emptyForm,
        ...data,
        emp_cd: employee.emp_id,
        appcn_dt: toInputDate(data.appcn_dt),
        restoration_dt: toInputDate(data.restoration_dt),
        mo_certificate_dt: toInputDate(data.mo_certificate_dt),
        commutation_reasons: data.commutation_reasons ?? "",
        mo_certificate_ref: data.mo_certificate_ref ?? "",
      });
    } else {
      setIsSaved(false);
      setIsEditing(true);
      setAppcnLoading(true);
      const retDate = employee.expected_retirement_date;
      setCommutationForm({
        ...emptyForm,
        emp_cd: employee.emp_id,
        appcn_dt: toInputDate(retDate),
        comm_start_mnth: retDate?.split("-")[1] || 1,
      });
      fetchApplicationNo();
    }
  }, [employee]);

  const handleCommutationSubmit = async (e) => {
    e.preventDefault();
    const isUpdate = Boolean(commutationForm.id);

    try {
      const response = isUpdate
        ? await API.put(
            `first-pension/commutation/${commutationForm.id}/`,
            commutationForm
          )
        : await API.post("first-pension/commutation/", commutationForm);

      const message = isUpdate
        ? "Application Updated Successfully"
        : "Application Saved Successfully";

      alert(
        `${message}\nApplication No: ${response.data.application_no}`
      );

      if (response.data.commutation_data) {
        const data = response.data.commutation_data;
        setCommutationForm({
          ...emptyForm,
          ...data,
          emp_cd: employee.emp_id,
          appcn_dt: toInputDate(data.appcn_dt),
          restoration_dt: toInputDate(data.restoration_dt),
          mo_certificate_dt: toInputDate(data.mo_certificate_dt),
        });
      }

      setIsSaved(true);
      setIsEditing(false);
    } catch (error) {
      console.error(error);
      const errMsg =
        error.response?.data?.error || "Save Failed";
      alert(errMsg);
    }
  };

  const handleEdit = () => {
    setIsEditing(true);
    setIsSaved(false);
  };

  if (!employee) return null;

  return (
    <form onSubmit={handleCommutationSubmit}>
      <div className="row">
        <div className="col-md-3 mb-3">
          <label className="form-label fw-bold">Employee Code</label>
          <input
            type="text"
            className="form-control"
            name="emp_cd"
            value={commutationForm.emp_cd}
            readOnly
          />
        </div>
        <div className="col-md-3 mb-3">
          <label className="form-label fw-bold">Application No</label>
          <input
            type="text"
            className="form-control"
            name="appcn_no"
            value={commutationForm.appcn_no}
            readOnly
            placeholder={appcnLoading ? "Loading..." : ""}
          />
        </div>
        <div className="col-md-3 mb-3">
          <label className="form-label fw-bold">Application Date</label>
          <input
            type="date"
            className="form-control"
            name="appcn_dt"
            value={commutationForm.appcn_dt}
            readOnly
          />
        </div>
        <div className="col-md-3 mb-3">
          <label className="form-label fw-bold">Application Time</label>
          <select
            className="form-select"
            name="application_time"
            value={commutationForm.application_time}
            onChange={handleChange}
            disabled={isSaved && !isEditing}
          >
            <option value="1">At the time of Pension Proposal</option>
            <option value="2">After 1 Yr of Pension Proposal</option>
            <option value="3">Within 1 Yr of Pension Proposal</option>
            <option value="4">Commutation for Pay Revision</option>
          </select>
        </div>
        <div className="col-md-3 mb-3">
          <label className="form-label fw-bold">Commutation Start Month</label>
          <input
            type="text"
            className="form-control"
            name="comm_start_mnth"
            value={commutationForm.comm_start_mnth}
            readOnly
          />
        </div>
        <div className="col-md-3 mb-3">
          <label className="form-label fw-bold">Implemented From</label>
          <select
            className="form-select"
            name="impl_fpen_combill"
            value={commutationForm.impl_fpen_combill}
            onChange={handleChange}
            disabled={isSaved && !isEditing}
          >
            <option value="">Select</option>
            <option value="PEN">First Pension</option>
            <option value="COM">Separate Commutation</option>
            <option value="TRF">Transfer</option>
          </select>
        </div>
        <div className="col-md-3 mb-3">
          <label className="form-label fw-bold">Restoration Date</label>
          <input
            type="date"
            className="form-control"
            name="restoration_dt"
            value={commutationForm.restoration_dt || ""}
            onChange={handleChange}
            disabled={isSaved && !isEditing}
          />
        </div>
        <div className="col-md-3 mb-3">
          <label className="form-label fw-bold">Commutation Percentage</label>
          <input
            type="text"
            className="form-control"
            name="commutation_per"
            value={commutationForm.commutation_per}
            onChange={handleChange}
            disabled={isSaved && !isEditing}
          />
        </div>
        <div className="col-md-6 mb-3">
          <label className="form-label fw-bold">Commutation Reasons</label>
          <input
            type="text"
            className="form-control"
            name="commutation_reasons"
            value={commutationForm.commutation_reasons}
            onChange={handleChange}
            disabled={isSaved && !isEditing}
          />
        </div>
        <div className="col-md-3 mb-3">
          <label className="form-label fw-bold">MO Certificate Date</label>
          <input
            type="date"
            className="form-control"
            name="mo_certificate_dt"
            value={commutationForm.mo_certificate_dt || ""}
            onChange={handleChange}
            disabled={isSaved && !isEditing}
          />
        </div>
        <div className="col-md-3 mb-3">
          <label className="form-label fw-bold">MO Certificate Ref</label>
          <input
            type="text"
            className="form-control"
            name="mo_certificate_ref"
            value={commutationForm.mo_certificate_ref}
            onChange={handleChange}
            disabled={isSaved && !isEditing}
          />
        </div>
      </div>
      <div className="text-end">
        {isSaved && (
          <button
            type="button"
            className="btn btn-secondary me-2"
            onClick={handleEdit}
          >
            Edit
          </button>
        )}
        <button
          type="submit"
          className="btn btn-success"
          disabled={isSaved && !isEditing}
        >
          Save
        </button>
      </div>
    </form>
  );
}
