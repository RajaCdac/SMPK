import { useState, useEffect } from "react";
import API from "../services/Api";
import { isVoluntaryRetirement } from "../utils/voluntaryRetirement";
import "../styles/CommutationApplication.css";

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
  bank_cd: "",
  bank_desc: "",
  ref_no: "",
  bill_no: "",
  sanction_parameter: "",
};

const APPLICATION_TIME_OPTIONS = [
  { value: 1, label: "At the Time of Pension Proposal" },
  { value: 2, label: "After 1 year of Pension Proposal" },
  { value: 3, label: "Within 1 year of Pension Proposal" },
  { value: 4, label: "Commutation For Pay Revision" },
];

const MONTH_OPTIONS = [
  { value: 1, label: "January" },
  { value: 2, label: "February" },
  { value: 3, label: "March" },
  { value: 4, label: "April" },
  { value: 5, label: "May" },
  { value: 6, label: "June" },
  { value: 7, label: "July" },
  { value: 8, label: "August" },
  { value: 9, label: "September" },
  { value: 10, label: "October" },
  { value: 11, label: "November" },
  { value: 12, label: "December" },
];

function toInputDate(dateStr) {
  if (!dateStr) return "";
  if (/^\d{4}-\d{2}-\d{2}/.test(dateStr)) return dateStr.slice(0, 10);
  const parts = dateStr.split("-");
  if (parts.length === 3 && parts[0].length <= 2) {
    return `${parts[2]}-${parts[1]}-${parts[0]}`;
  }
  return dateStr;
}

/** Restoration Date = Commutation Date + 15 years */
function restorationFromCommutation(commutationDt) {
  const input = toInputDate(commutationDt);
  if (!input) return "";
  const [year, month, day] = input.split("-").map(Number);
  if (!year || !month || !day) return "";
  const date = new Date(year, month - 1, day);
  date.setFullYear(date.getFullYear() + 15);
  const y = date.getFullYear();
  const m = String(date.getMonth() + 1).padStart(2, "0");
  const d = String(date.getDate()).padStart(2, "0");
  return `${y}-${m}-${d}`;
}

function resolveBankFromMaster(bankMaster, rawValue) {
  const value = String(rawValue || "").trim().toUpperCase();
  if (!value) return { bank_cd: "", bank_desc: "" };

  const exact = bankMaster.find((b) => b.bank_cd === value);
  if (exact) {
    return {
      bank_cd: exact.bank_cd,
      bank_desc: exact.bank_desc || exact.bank_name || "",
    };
  }

  const codePart = value.split("—")[0].split("-")[0].trim();
  const fromLabel = bankMaster.find((b) => b.bank_cd === codePart);
  if (fromLabel) {
    return {
      bank_cd: fromLabel.bank_cd,
      bank_desc: fromLabel.bank_desc || fromLabel.bank_name || "",
    };
  }

  return { bank_cd: value, bank_desc: "" };
}

function buildNewCommutationForm(employee, bankMaster) {
  const defaults = employee?.commutation_defaults || {};
  const isVR = isVoluntaryRetirement(employee);
  const retDate =
    employee.process_intake_data?.separation_date ||
    employee.proposal_data?.separation_date ||
    employee.expected_retirement_date;
  const retInput = toInputDate(defaults.appcn_dt || retDate);
  const proposalDefaults = employee.proposal_defaults || {};
  const bankFromDefaults = resolveBankFromMaster(
    bankMaster,
    defaults.bank_cd || proposalDefaults.bank_cd || ""
  );
  const bankCd = bankFromDefaults.bank_cd || defaults.bank_cd || proposalDefaults.bank_cd || "";
  const bankDesc =
    bankFromDefaults.bank_desc ||
    defaults.bank_desc ||
    proposalDefaults.bank_name ||
    proposalDefaults.bank_desc ||
    "";
  const monthFromRet =
    retInput && retInput.includes("-") ? Number(retInput.split("-")[1]) : 1;

  return {
    ...emptyForm,
    emp_cd: employee.emp_id,
    appcn_dt: retInput,
    application_rcvd_dt: toInputDate(defaults.application_rcvd_dt) || retInput,
    commutation_dt: toInputDate(defaults.commutation_dt) || retInput,
    restoration_dt: restorationFromCommutation(
      toInputDate(defaults.commutation_dt) || retInput
    ),
    comm_start_mnth: defaults.comm_start_mnth || monthFromRet || 1,
    application_time: defaults.application_time || 1,
    impl_fpen_combill: defaults.impl_fpen_combill || (isVR ? "COM" : ""),
    bill_no: defaults.bill_no || "",
    ref_no: defaults.ref_no || "",
    commutation_per:
      defaults.commutation_per !== undefined && defaults.commutation_per !== null
        ? String(defaults.commutation_per)
        : "",
    mo_certificate_ref: defaults.mo_certificate_ref || "",
    mo_certificate_dt: toInputDate(defaults.mo_certificate_dt),
    commutation_reasons: defaults.commutation_reasons || "",
    sanction_parameter: defaults.sanction_parameter || "",
    bank_cd: bankCd,
    bank_desc: bankDesc,
  };
}

function mapCommutationDataToForm(data, employee) {
  return {
    ...emptyForm,
    ...data,
    emp_cd: employee.emp_id,
    application_time: Number(data.application_time) || 1,
    comm_start_mnth: Number(data.comm_start_mnth) || 1,
    appcn_dt: toInputDate(data.appcn_dt),
    application_rcvd_dt: toInputDate(data.application_rcvd_dt),
    commutation_dt: toInputDate(data.commutation_dt),
    restoration_dt: restorationFromCommutation(data.commutation_dt),
    mo_certificate_dt: toInputDate(data.mo_certificate_dt),
    commutation_reasons: data.commutation_reasons ?? "",
    mo_certificate_ref: data.mo_certificate_ref ?? "",
    bank_cd: data.bank_cd ?? "",
    bank_desc: data.bank_desc ?? data.bank_description ?? "",
    ref_no: data.ref_no ?? "",
    bill_no: data.bill_no ?? "",
    sanction_parameter: data.sanction_parameter ?? "",
    impl_fpen_combill: data.impl_fpen_combill ?? "",
    commutation_per:
      data.commutation_per !== undefined && data.commutation_per !== null
        ? String(data.commutation_per)
        : "",
  };
}

export default function CommutationApplicationEntry({ employee }) {
  const [commutationForm, setCommutationForm] = useState(emptyForm);
  const [isSaved, setIsSaved] = useState(false);
  const [isEditing, setIsEditing] = useState(true);
  const [appcnLoading, setAppcnLoading] = useState(true);
  const [bankMaster, setBankMaster] = useState([]);

  const fieldDisabled = isSaved && !isEditing;
  const pensionerName = employee?.name || "";

  useEffect(() => {
    let cancelled = false;
    const loadBanks = async () => {
      try {
        const res = await API.get("first-pension/banks/");
        if (!cancelled) {
          setBankMaster(res.data?.banks || []);
        }
      } catch (error) {
        console.error("Bank master load failed:", error);
      }
    };
    loadBanks();
    return () => {
      cancelled = true;
    };
  }, []);

  const handleChange = (e) => {
    const { name, value } = e.target;
    setCommutationForm((prev) => {
      const next = { ...prev, [name]: value };
      if (name === "commutation_dt") {
        next.restoration_dt = restorationFromCommutation(value);
      }
      return next;
    });
  };

  const handleApplicationTimeChange = (value) => {
    setCommutationForm((prev) => ({
      ...prev,
      application_time: Number(value),
    }));
  };

  const handleBankCdChange = (e) => {
    const { bank_cd, bank_desc } = resolveBankFromMaster(
      bankMaster,
      e.target.value
    );
    setCommutationForm((prev) => ({ ...prev, bank_cd, bank_desc }));
  };

  const handleBankCdBlur = async () => {
    const code = String(commutationForm.bank_cd || "").trim();
    if (!code) {
      setCommutationForm((prev) => ({ ...prev, bank_desc: "" }));
      return;
    }

    const local = resolveBankFromMaster(bankMaster, code);
    if (local.bank_desc) {
      setCommutationForm((prev) => ({
        ...prev,
        bank_cd: local.bank_cd,
        bank_desc: local.bank_desc,
      }));
      return;
    }

    try {
      const res = await API.get(
        `first-pension/banks/${encodeURIComponent(code)}/`
      );
      const bank = res.data;
      if (bank?.bank_cd) {
        setCommutationForm((prev) => ({
          ...prev,
          bank_cd: bank.bank_cd,
          bank_desc: bank.bank_desc || bank.bank_name || "",
        }));
      }
    } catch {
      setCommutationForm((prev) => ({ ...prev, bank_desc: "" }));
    }
  };

  const fetchApplicationNo = async () => {
    try {
      const response = await API.get("first-pension/commutation/");
      const no = response.data.appcn_no;
      if (no !== undefined && no !== null && String(no).trim() !== "") {
        setCommutationForm((prev) => ({
          ...prev,
          appcn_no: String(no),
        }));
      }
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
      setCommutationForm(mapCommutationDataToForm(data, employee));
    } else {
      setIsSaved(false);
      setIsEditing(true);
      setAppcnLoading(true);
      setCommutationForm(buildNewCommutationForm(employee, bankMaster));
      fetchApplicationNo();
    }
  }, [employee, bankMaster]);

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

      let alertText = `${message}\nApplication No: ${response.data.application_no}`;
      if (response.data.oracle_warning) {
        alertText += `\n\n${response.data.oracle_warning}`;
      }
      alert(alertText);

      if (response.data.commutation_data) {
        setCommutationForm(
          mapCommutationDataToForm(response.data.commutation_data, employee)
        );
      }

      setIsSaved(true);
      setIsEditing(false);
    } catch (error) {
      console.error(error);
      const errMsg = error.response?.data?.error || "Save Failed";
      alert(errMsg);
    }
  };

  const handleEdit = () => {
    setIsEditing(true);
    setIsSaved(false);
  };

  if (!employee) return null;

  return (
    <form onSubmit={handleCommutationSubmit} className="smpk-form commutation-form">
      {/* <h2 className="commutation-form-title">
        Application for Commutation of Pension
      </h2> */}

      {/* Club 1: Pensioner, application type, application no / bill / month */}
      <section className="commutation-club">
        <div className="row g-3">
          <div className="col-lg-7">
            <label className="form-label">Name of Pensioner</label>
            <div className="d-flex gap-2 mb-2">
              <input type="text" className="form-control" style={{ maxWidth: "6.5rem" }} name="emp_cd" value={commutationForm.emp_cd} readOnly />
              <input type="text" className="form-control" value={pensionerName} readOnly placeholder="Pensioner name" />
            </div>

            <fieldset className="commutation-app-time">
              <legend>Application</legend>
              {APPLICATION_TIME_OPTIONS.map((opt) => (
                <label key={opt.value} className="commutation-radio">
                  <input type="radio" name="application_time" value={opt.value} checked={ Number(commutationForm.application_time) === opt.value } onChange={() => handleApplicationTimeChange(opt.value)} disabled={fieldDisabled} />
                  <span>{opt.label}</span>
                </label>
              ))}
            </fieldset>
          </div>

          <div className="col-lg-5">
            <div className="row g-3">
              <div className="col-12">
                <label className="form-label">Application No</label>
                <input type="text" className="form-control" name="appcn_no" value={commutationForm.appcn_no} readOnly placeholder={appcnLoading ? "Loading..." : ""}/>
              </div>
              <div className="col-12">
                <label className="form-label">Implement Bill No</label>
                <input type="text" className="form-control" name="bill_no" value={commutationForm.bill_no} onChange={handleChange} disabled={fieldDisabled} placeholder="e.g. PPC/01/2024/305" />
              </div>
              <div className="col-12">
                <label className="form-label">Start Month</label>
                <select
                  className="form-select" name="comm_start_mnth" value={commutationForm.comm_start_mnth} onChange={handleChange} disabled={fieldDisabled}>
                  {MONTH_OPTIONS.map((m) => (
                    <option key={m.value} value={m.value}> {m.label} </option>
                  ))}
                </select>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Club 2: Dates, ref, implementation, commutation values */}
      <section className="commutation-club">
        <div className="row g-3">
          <div className="col-md-3">
            <label className="form-label">Application Date</label>
            <input type="date" className="form-control" name="appcn_dt" value={commutationForm.appcn_dt} readOnly />
          </div>
          <div className="col-md-3">
            <label className="form-label">Application Received Date</label>
            <input type="date" className="form-control" name="application_rcvd_dt" value={commutationForm.application_rcvd_dt || ""} onChange={handleChange} disabled={fieldDisabled} />
          </div>
          <div className="col-md-3">
            <label className="form-label">Ref No</label>
            <input type="text" className="form-control" name="ref_no" value={commutationForm.ref_no} onChange={handleChange} disabled={fieldDisabled}  />
          </div>
          <div className="col-md-3">
            <label className="form-label">To Be Implemented from</label>
            <select className="form-select" name="impl_fpen_combill" value={commutationForm.impl_fpen_combill} onChange={handleChange} disabled={fieldDisabled}
            >
              <option value="">Select</option>
              <option value="PEN">First Pension</option>
              <option value="COM">Separate Commutation</option>
              <option value="TRF">Transfer</option>
            </select>
          </div>
          <div className="col-md-2">
            <label className="form-label">Commutation Date</label>
            <input
              type="date"
              className="form-control"
              name="commutation_dt"
              value={commutationForm.commutation_dt || ""}
              onChange={handleChange}
              disabled={fieldDisabled}
            />
          </div>
          <div className="col-md-2">
            <label className="form-label">Restoration Date</label>
            <input
              type="date"
              className="form-control"
              name="restoration_dt"
              value={commutationForm.restoration_dt || ""}
              readOnly
              title="Commutation Date + 15 years"
            />
          </div>
          <div className="col-md-2">
            <label className="form-label">Commutation %</label>
            <input
              type="text"
              className="form-control"
              name="commutation_per"
              value={commutationForm.commutation_per}
              onChange={handleChange}
              disabled={fieldDisabled}
            />
          </div>
          <div className="col-md-6">
            <label className="form-label">Bank</label>
            <div className="commutation-bank-row">
              <div className="bank-cd-field">
                <input type="text" className="form-control" name="bank_cd" list="commutation-bank-cd-list" value={commutationForm.bank_cd} onChange={handleBankCdChange} onBlur={handleBankCdBlur} disabled={fieldDisabled} placeholder="Code" autoComplete="off" />
              </div>
              <div className="bank-desc-field">
                <input type="text" className="form-control" name="bank_desc" value={commutationForm.bank_desc} readOnly placeholder="Bank description" />
              </div>
            </div>
            <datalist id="commutation-bank-cd-list">
              {bankMaster.map((bank) => (
                <option key={bank.bank_cd} value={bank.bank_cd} label={`${bank.bank_cd} — ${bank.bank_name || bank.bank_desc || ""}`} />
              ))}
            </datalist>
          </div>
        </div>
      </section>

      {/* Club 3: Bank, sanction, reasons, medical */}
      <section className="commutation-club">
        <div className="row g-3">
          
          <div className="col-md-6">
            <label className="form-label">Sanction Parameters</label>
            <input type="text" className="form-control" name="sanction_parameter" value={commutationForm.sanction_parameter} onChange={handleChange} disabled={fieldDisabled} />
          </div>
          <div className="col-md-6">
            <label className="form-label">Commutation Reasons</label>
            <input type="text" className="form-control" name="commutation_reasons" value={commutationForm.commutation_reasons} onChange={handleChange} disabled={fieldDisabled} />
          </div>
          <div className="col-md-6">
            <label className="form-label">Medical Officer Certification Date</label>
            <input type="date" className="form-control" name="mo_certificate_dt" value={commutationForm.mo_certificate_dt || ""} onChange={handleChange} disabled={fieldDisabled}  />
          </div>
          <div className="col-md-6">
            <label className="form-label">Medical Officer Certificate Ref. No</label>
            <input type="text" className="form-control" name="mo_certificate_ref" value={commutationForm.mo_certificate_ref} onChange={handleChange} disabled={fieldDisabled} />
          </div>
        </div>
      </section>

      <div className="smpk-form-actions justify-content-end">
        {isSaved && (
        <button type="button" className="btn btn-secondary me-2" onClick={handleEdit} > Edit </button> )}
        <button type="submit" className="btn btn-success" disabled={fieldDisabled}> Save</button>
      </div>
    </form>
  );
}
