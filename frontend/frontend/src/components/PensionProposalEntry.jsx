import { useState, useEffect } from "react";
import API from "../services/Api";
import "../styles/PensionProposal.css";
import {
  buildEmptyProposalForm,
  defaultEarningRows,
  emptyEarningRow,
} from "./pensionProposalDefaults";

function toInputDate(v) {
  if (!v) return "";
  if (/^\d{4}-\d{2}-\d{2}/.test(String(v))) return String(v).slice(0, 10);
  const p = String(v).split("-");
  if (p.length === 3 && p[0].length <= 2) return `${p[2]}-${p[1]}-${p[0]}`;
  return v;
}

function normalizeProposalData(data, employee) {
  return {
    ...buildEmptyProposalForm(employee),
    ...data,
    emp_cd: data.emp_cd || employee.emp_id,
    separation_date: toInputDate(data.separation_date),
    regn_date: toInputDate(data.regn_date),
    pension_proposal_date: toInputDate(data.pension_proposal_date),
    double_family_pension_upto_date: toInputDate(
      data.double_family_pension_upto_date
    ),
    vigilance_clearance_ref_dt: toInputDate(data.vigilance_clearance_ref_dt),
    vr_ref_dt: toInputDate(data.vr_ref_dt),
    earning_deductions:
      data.earning_deductions?.length > 0
        ? data.earning_deductions
        : defaultEarningRows(),
  };
}

export default function PensionProposalEntry({ employee }) {
  const [form, setForm] = useState(buildEmptyProposalForm(employee));
  const [recordExists, setRecordExists] = useState(false);
  const [isEditing, setIsEditing] = useState(false);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!employee) return;

    const load = async () => {
      setLoading(true);
      let exists = false;
      let data = null;
      let proposalDefaults = employee.proposal_defaults || null;

      if (employee.proposal_exists && employee.proposal_data) {
        exists = true;
        data = employee.proposal_data;
      } else {
        try {
          const res = await API.get(
            `first-pension/pension-proposal/employee/${employee.emp_id}/`
          );
          exists = res.data.exists;
          data = res.data.proposal_data;
          proposalDefaults =
            res.data.proposal_defaults || proposalDefaults;
        } catch (err) {
          console.error(err);
        }
      }

      const empWithDefaults = {
        ...employee,
        proposal_defaults: proposalDefaults,
      };

      if (exists && data) {
        setForm(normalizeProposalData(data, empWithDefaults));
        setRecordExists(true);
        setIsEditing(false);
      } else {
        setForm(buildEmptyProposalForm(empWithDefaults));
        setRecordExists(false);
        setIsEditing(true);
      }
      setLoading(false);
    };

    load();
  }, [employee]);

  const disabled = recordExists && !isEditing;
  const dbFieldLocked = true;

  const onChange = (e) => {
    const { name, value, type, checked } = e.target;
    setForm((prev) => ({
      ...prev,
      [name]: type === "checkbox" ? checked : value,
    }));
  };

  const onEarningChange = (index, field, value) => {
    setForm((prev) => {
      const rows = [...prev.earning_deductions];
      rows[index] = { ...rows[index], [field]: value };
      return { ...prev, earning_deductions: rows };
    });
  };

  const fetchEarnDednDescription = async (index, code) => {
    const trimmed = String(code || "").trim();
    if (!trimmed) return;

    try {
      const res = await API.get(
        `first-pension/earn-dedn/${encodeURIComponent(trimmed)}/`
      );
      setForm((prev) => {
        const rows = [...prev.earning_deductions];
        rows[index] = {
          ...rows[index],
          code: res.data.code || trimmed,
          desc: res.data.desc || "",
          type: res.data.type || rows[index].type,
        };
        return { ...prev, earning_deductions: rows };
      });
    } catch (error) {
      if (error.response?.status === 404) {
        setForm((prev) => {
          const rows = [...prev.earning_deductions];
          rows[index] = { ...rows[index], desc: "" };
          return { ...prev, earning_deductions: rows };
        });
      } else {
        console.error(error);
      }
    }
  };

  const addEarningRow = () => {
    setForm((prev) => ({
      ...prev,
      earning_deductions: [...prev.earning_deductions, { ...emptyEarningRow }],
    }));
  };

  const handlePopulateDetails = () => {
    alert("Populate Details will load earning/deduction from finance records.");
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    const isUpdate = Boolean(form.id);

    try {
      const response = isUpdate
        ? await API.put(`first-pension/pension-proposal/${form.id}/`, form)
        : await API.post("first-pension/pension-proposal/", form);

      alert(
        isUpdate
          ? "Pension Proposal Updated Successfully"
          : "Pension Proposal Saved Successfully"
      );

      if (response.data.proposal_data) {
        setForm(normalizeProposalData(response.data.proposal_data, employee));
      }
      setRecordExists(true);
      setIsEditing(false);
    } catch (error) {
      console.error(error);
      alert(error.response?.data?.error || "Save Failed");
    }
  };

  if (!employee) return null;
  if (loading) {
    return <p className="text-muted">Loading pension proposal...</p>;
  }

  return (
    <form onSubmit={handleSubmit} className="pension-proposal-form">
      <div className="pp-title-bar">PENSION / FAMILY PENSION PROPOSAL</div>

      <div className="pp-form-scroll">
        <div className="row g-2 mb-2">
          <div className="col-md-6">
            <div className="row g-2 align-items-end">
              <div className="col-3">
                <label className="pp-label">Employee</label>
                <input
                  className="form-control form-control-sm"
                  name="emp_cd"
                  value={form.emp_cd}
                  readOnly
                />
              </div>
              <div className="col-9">
                <input
                  className="form-control form-control-sm pp-readonly"
                  name="emp_name"
                  value={form.emp_name}
                  readOnly
                />
              </div>
              <div className="col-md-6">
                <label className="pp-label">Employee Status</label>
                <select
                  className="form-select form-select-sm"
                  name="employee_status"
                  value={form.employee_status}
                  onChange={onChange}
                  disabled={disabled}
                >
                  <option value="EMPLOYEE">Pensioner</option>
                  <option value="RETIRED">Family Pensioner</option>
                  
                </select>
              </div>
              <div className="col-md-6">
                <label className="pp-label">CA No.</label>
                <input
                  className="form-control form-control-sm"
                  name="ca_number"
                  value={form.ca_number}
                  onChange={onChange}
                  disabled={disabled}
                />
              </div>
              <div className="col-md-6">
                <label className="pp-label">Pension Type</label>
                <select
                  className="form-select form-select-sm"
                  name="pension_type"
                  value={form.pension_type}
                  onChange={onChange}
                  disabled={disabled}
                >
                  <option value="">Select</option>
                  <option value="PN">Normal Pension</option>
                  <option value="FP">Family Pension</option>
                  <option value="PP">Provisional Pension</option>
                  <option value="SG">Service Gratuity</option>
                  <option value="CA">Compassionate Allowance</option>
                  <option value="RG">Resignation</option>
                </select>
              </div>
              <div className="col-md-6">
                <label className="pp-label">Pension Proposal No</label>
                <input
                  className="form-control form-control-sm"
                  name="pension_proposal_no"
                  value={form.pension_proposal_no}
                  onChange={onChange}
                  disabled={disabled}
                />
              </div>
              <div className="col-12">
                <div className="form-check">
                  <input
                    className="form-check-input"
                    type="checkbox"
                    name="eligible_double_family_pension"
                    checked={form.eligible_double_family_pension}
                    onChange={onChange}
                    disabled={disabled}
                  />
                  <label className="form-check-label">
                    Eligible for Double Family Pension
                  </label>
                </div>
              </div>
            </div>
          </div>

          <div className="col-md-6">
            <div className="pp-section h-100">
              <div className="row g-2">
                <div className="col-md-4">
                  <label className="pp-label">Separation type</label>
                  <select
                    className="form-select form-select-sm"
                    name="separation_type"
                    value={form.separation_type}
                    onChange={onChange}
                    disabled={disabled}
                  >
                    <option value="">Select</option>
                    <option value="RT">Retirement</option>
                    <option value="DT">Death</option>
                    <option value="RG">Resignation</option>
                  </select>
                </div>
                <div className="col-md-4">
                  <label className="pp-label">Separation Date</label>
                  <input
                    type="date"
                    className="form-control form-control-sm pp-readonly"
                    name="separation_date"
                    value={form.separation_date || ""}
                    readOnly
                  />
                </div>
                <div className="col-md-2">
                  <label className="pp-label">Impl. Year</label>
                  <input
                    className="form-control form-control-sm"
                    name="implemented_year"
                    value={form.implemented_year}
                    onChange={onChange}
                    disabled={disabled}
                  />
                </div>
                <div className="col-md-2">
                  <label className="pp-label">Impl. Month</label>
                  <input
                    className="form-control form-control-sm"
                    name="implemented_month"
                    value={form.implemented_month}
                    onChange={onChange}
                    disabled={disabled}
                  />
                </div>
                <div className="col-12">
                  <label className="pp-label">Service Tenure</label>
                  <input
                    className="form-control form-control-sm pp-readonly"
                    name="service_tenure"
                    value={form.service_tenure}
                    readOnly
                  />
                </div>
              </div>
            </div>
          </div>
        </div>

        <div className="row g-2 mb-2">
          <div className="col-md-3">
            <label className="pp-label">Pension Option</label>
            <select
              className="form-select form-select-sm"
              name="pension_option"
              value={form.pension_option}
              onChange={onChange}
              disabled={disabled}
            >
              <option value="">Select</option>
              <option value="G">Govt Line</option>
              <option value="P">Port Line</option>
            </select>
          </div>
          <div className="col-md-3">
            <label className="pp-label">Option Given By</label>
            <select
              className="form-select form-select-sm"
              name="option_given_by"
              value={form.option_given_by}
              onChange={onChange}
              disabled={disabled}
            >
              <option value="">Select</option>
              <option value="E">Employee</option>
              <option value="W">Widow</option>
              <option value="S">Son</option>
              <option value="D">Daughter</option>
              <option value="WD">Widow Daughter</option>
              
            </select>
          </div>
          <div className="col-md-3">
            <label className="pp-label">Regn No.</label>
            <input
              className="form-control form-control-sm"
              name="regn_no"
              value={form.regn_no}
              onChange={onChange}
              disabled={disabled}
            />
          </div>
          <div className="col-md-3">
            <label className="pp-label">Regn Date</label>
            <input
              type="date"
              className="form-control form-control-sm"
              name="regn_date"
              value={form.regn_date || ""}
              onChange={onChange}
              disabled={disabled}
            />
          </div>
          <div className="col-md-2">
            <label className="pp-label">Start Month</label>
            <select
              className="form-select form-select-sm pp-readonly"
              name="start_month"
              value={form.start_month}
              disabled={dbFieldLocked}
            >
              <option value="">--</option>
              {Array.from({ length: 12 }, (_, i) => (
                <option key={i + 1} value={i + 1}>
                  {i + 1}
                </option>
              ))}
            </select>
          </div>
          <div className="col-md-2">
            <label className="pp-label">Start Year</label>
            <input
              className="form-control form-control-sm pp-readonly"
              name="start_year"
              value={form.start_year}
              readOnly
            />
          </div>
          <div className="col-md-2">
            <label className="pp-label">Roll No</label>
            <input
              className="form-control form-control-sm"
              name="pension_roll_no"
              value={form.pension_roll_no}
              onChange={onChange}
              disabled={disabled}
            />
          </div>
          <div className="col-md-3">
            <label className="pp-label">Pension Proposal Date</label>
            <input
              type="date"
              className="form-control form-control-sm"
              name="pension_proposal_date"
              value={form.pension_proposal_date || ""}
              onChange={onChange}
              disabled={disabled}
            />
          </div>
          <div className="col-md-3">
            <label className="pp-label">Double Family Pension Upto Date</label>
            <input
              type="date"
              className="form-control form-control-sm"
              name="double_family_pension_upto_date"
              value={form.double_family_pension_upto_date || ""}
              onChange={onChange}
              disabled={disabled}
            />
          </div>
        </div>

        <div className="row g-2 mb-2">
          <div className="col-md-2">
            <label className="pp-label">Provisional Pension %</label>
            <input
              className="form-control form-control-sm"
              name="provisional_pension_pct"
              value={form.provisional_pension_pct}
              onChange={onChange}
              disabled={disabled}
            />
          </div>
          <div className="col-md-2">
            <label className="pp-label">Bank</label>
            <input
              className="form-control form-control-sm pp-readonly"
              name="bank_cd"
              value={form.bank_cd}
              readOnly
              placeholder="Code"
            />
          </div>
          <div className="col-md-3">
            <label className="pp-label">Bank Name</label>
            <input
              className="form-control form-control-sm pp-readonly"
              name="bank_name"
              value={form.bank_name}
              readOnly
              placeholder="Bank Name"
            />
          </div>
          <div className="col-md-2">
            <label className="pp-label">A/C No</label>
            <input
              className="form-control form-control-sm pp-readonly"
              name="account_no"
              value={form.account_no}
              readOnly
            />
          </div>
          <div className="col-md-3">
            <label className="pp-label">Vig. Clearance Ref. No.</label>
            <input
              className="form-control form-control-sm"
              name="vigilance_clearance_ref_no"
              value={form.vigilance_clearance_ref_no}
              onChange={onChange}
              disabled={disabled}
            />
          </div>
          <div className="col-md-2">
            <label className="pp-label">Vig. Clearance Ref. Dt.</label>
            <input
              type="date"
              className="form-control form-control-sm"
              name="vigilance_clearance_ref_dt"
              value={form.vigilance_clearance_ref_dt || ""}
              onChange={onChange}
              disabled={disabled}
            />
          </div>
          <div className="col-md-2">
            <label className="pp-label">Lic Opted Bank</label>
            <input
              className="form-control form-control-sm"
              name="lic_bank_cd"
              value={form.lic_bank_cd}
              onChange={onChange}
              disabled={disabled}
            />
          </div>
          <div className="col-md-3">
            <input
              className="form-control form-control-sm pp-readonly mt-4"
              name="lic_bank_name"
              value={form.lic_bank_name}
              onChange={onChange}
              disabled={disabled}
            />
          </div>
        </div>

        <div className="row g-2 mb-2">
          <div className="col-md-3">
            <label className="pp-label">V.R Ref No</label>
            <input
              className="form-control form-control-sm"
              name="vr_ref_no"
              value={form.vr_ref_no}
              onChange={onChange}
              disabled={disabled}
            />
          </div>
          <div className="col-md-3">
            <label className="pp-label">V.R Ref Date</label>
            <input
              type="date"
              className="form-control form-control-sm"
              name="vr_ref_dt"
              value={form.vr_ref_dt || ""}
              onChange={onChange}
              disabled={disabled}
            />
          </div>
          <div className="col-md-3">
            <label className="pp-label">Compassionate Allowance</label>
            <select
              className="form-select form-select-sm"
              name="compassionate_allowance"
              value={form.compassionate_allowance}
              onChange={onChange}
              disabled={disabled}
            >
              <option value="">Select</option>
              <option value="1">Less Than Equal 1/3 Pension</option>
              <option value="2">Less Than Equal 1/3 Gratuity</option>
              <option value="3">Less Than Equal 1/3 (Pension+Gratuity)</option>
            </select>
          </div>
          <div className="col-md-3">
            <label className="pp-label">Reasons to Withhold</label>
            <select
              className="form-select form-select-sm"
              name="quarter_status"
              value={form.quarter_status}
              onChange={onChange}
              disabled={disabled}
            >
              <option value="">Select</option>
              <option value="1">Electricity Clearence</option>
              <option value="2">Quarter & Elec Clearence</option>
            </select>
          </div>
          <div className="col-md-3">
            <label className="pp-label">Nominee/E-form</label>
            <select
              className="form-select form-select-sm"
              name="nominee_eform"
              value={form.nominee_eform}
              onChange={onChange}
              disabled={disabled}
            >
              <option value="">Select</option>
              <option value="NOMINEE">Nominee</option>
              <option value="EFORM">E-Form</option>
            </select>
          </div>
          <div className="col-md-3">
            <label className="pp-label">Compassionate Allowance Amt</label>
            <input
              className="form-control form-control-sm"
              name="compassionate_allowance_amt"
              value={form.compassionate_allowance_amt}
              onChange={onChange}
              disabled={disabled}
            />
          </div>
          <div className="col-md-2">
            <label className="pp-label">Port City Resident</label>
            <select
              className="form-select form-select-sm"
              name="port_city_resident"
              value={form.port_city_resident}
              onChange={onChange}
              disabled={disabled}
            >
              <option value="">Select</option>
              <option value="YES">Yes</option>
              <option value="NO">No</option>
            </select>
          </div>
          <div className="col-md-2">
            <label className="pp-label">Gratuity Option</label>
            <select
              className="form-select form-select-sm"
              name="gratuity_option"
              value={form.gratuity_option}
              onChange={onChange}
              disabled={disabled}
            >
              <option value="">Select</option>
              <option value="1">Retirement Gratuity Opt1</option>
              <option value="2">Retirement Gratuity Opt2</option>
              <option value="3">Death Gratuity Opt2</option>
            </select>
          </div>
          <div className="col-md-2">
            <label className="pp-label">Retirement CPI</label>
            <input
              className="form-control form-control-sm"
              name="retirement_cpi"
              value={form.retirement_cpi}
              onChange={onChange}
              disabled={disabled}
            />
          </div>
          <div className="col-md-3 d-flex align-items-end gap-3">
            <div className="form-check">
              <input
                className="form-check-input"
                type="checkbox"
                name="id_card_submitted"
                checked={form.id_card_submitted}
                onChange={onChange}
                disabled={disabled}
              />
              <label className="form-check-label">ID Card Submitted</label>
            </div>
            <div className="form-check">
              <input
                className="form-check-input"
                type="checkbox"
                name="vigilance_cleared"
                checked={form.vigilance_cleared}
                onChange={onChange}
                disabled={disabled}
              />
              <label className="form-check-label">Vig. Cleared</label>
            </div>
          </div>
        </div>

        <div className="row g-2 mb-2 align-items-end">
          <div className="col-md-2">
            <label className="pp-label">Inc Holder</label>
            <select
              className="form-select form-select-sm"
              name="incentive_holder"
              value={form.incentive_holder}
              onChange={onChange}
              disabled={disabled}
            >
              <option value="">Select</option>
              <option value="YES">Yes</option>
              <option value="NO">No</option>
            </select>
          </div>
          <div className="col-md-2">
            <label className="pp-label">Held Up Flg</label>
            <select
              className="form-select form-select-sm"
              name="held_up_flag"
              value={form.held_up_flag}
              onChange={onChange}
              disabled={disabled}
            >
              <option value="">Select</option>
              <option value="N">Not Appl</option>
              <option value="G">Gratuity Full</option>
              <option value="GP">Gratuity Partial</option>
              <option value="C">Commutation</option>
              <option value="R">Relief</option>
              <option value="P">Pension</option>
            </select>
          </div>
          <div className="col-md-2">
            <label className="pp-label">Amt.</label>
            <input
              className="form-control form-control-sm"
              name="held_gratuity_amt"
              value={form.held_gratuity_amt}
              onChange={onChange}
              disabled={disabled}
            />
          </div>
          <div className="col-md-6">
            <div className="form-check d-inline-block me-2">
              <input
                className="form-check-input"
                type="checkbox"
                name="extra_tccs_enabled"
                checked={form.extra_tccs_enabled}
                onChange={onChange}
                disabled={disabled}
              />
              <label className="form-check-label">Extra TCCS</label>
            </div>
            <input
              className="form-control form-control-sm d-inline-block"
              style={{ width: 70 }}
              name="extra_tccs_years"
              value={form.extra_tccs_years}
              onChange={onChange}
              disabled={disabled || !form.extra_tccs_enabled}
              placeholder="Yrs"
            />
            <input
              className="form-control form-control-sm d-inline-block ms-1"
              style={{ width: 70 }}
              name="extra_tccs_months"
              value={form.extra_tccs_months}
              onChange={onChange}
              disabled={disabled || !form.extra_tccs_enabled}
              placeholder="Mths"
            />
            <input
              className="form-control form-control-sm d-inline-block ms-1"
              style={{ width: 70 }}
              name="extra_tccs_days"
              value={form.extra_tccs_days}
              onChange={onChange}
              disabled={disabled || !form.extra_tccs_enabled}
              placeholder="Dys"
            />
          </div>
        </div>

        <div className="pp-section">
          <div className="d-flex justify-content-between align-items-center mb-2">
            <span className="pp-section-title mb-0">Earning / Deduction</span>
            <button
              type="button"
              className="btn btn-sm btn-outline-primary"
              onClick={handlePopulateDetails}
              disabled={disabled}
            >
              Populate Details
            </button>
          </div>
          <table className="pp-earn-table">
            <thead>
              <tr>
                <th>Type</th>
                <th>Code</th>
                <th>Desc</th>
                <th>Amount</th>
                <th>Deduction Priority</th>
              </tr>
            </thead>
            <tbody>
              {form.earning_deductions.map((row, idx) => (
                <tr key={idx}>
                  <td>
                    <select
                      className="form-select form-select-sm"
                      value={row.type}
                      onChange={(e) =>
                        onEarningChange(idx, "type", e.target.value)
                      }
                      disabled={disabled}
                    >
                      <option value="EARN">EARNNG</option>
                      <option value="DEDN">DEDUCTION</option>
                    </select>
                  </td>
                  <td>
                    <input
                      className="form-control form-control-sm"
                      value={row.code}
                      onChange={(e) =>
                        onEarningChange(idx, "code", e.target.value)
                      }
                      onBlur={(e) =>
                        fetchEarnDednDescription(idx, e.target.value)
                      }
                      disabled={disabled}
                      placeholder="e.g. 200"
                    />
                  </td>
                  <td>
                    <input
                      className="form-control form-control-sm pp-readonly"
                      value={row.desc}
                      readOnly
                      placeholder="From Oracle"
                    />
                  </td>
                  <td>
                    <input
                      className="form-control form-control-sm"
                      value={row.amount}
                      onChange={(e) =>
                        onEarningChange(idx, "amount", e.target.value)
                      }
                      disabled={disabled}
                    />
                  </td>
                  <td>
                    <select
                      className="form-select form-select-sm"
                      value={row.deduction_priority}
                      onChange={(e) =>
                        onEarningChange(
                          idx,
                          "deduction_priority",
                          e.target.value
                        )
                      }
                      disabled={disabled}
                    >
                      <option value="">--</option>
                      <option value="1">1</option>
                      <option value="2">2</option>
                      <option value="3">3</option>
                    </select>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          <button
            type="button"
            className="btn btn-sm btn-link mt-1"
            onClick={addEarningRow}
            disabled={disabled}
          >
            + Add row
          </button>
        </div>
      </div>

      <div className="text-end mt-3">
        {recordExists && (
          <button
            type="button"
            className="btn btn-secondary me-2"
            onClick={() => setIsEditing(true)}
            disabled={isEditing}
          >
            Edit
          </button>
        )}
        <button
          type="submit"
          className="btn btn-success"
          disabled={recordExists && !isEditing}
        >
          Save
        </button>
      </div>
    </form>
  );
}
