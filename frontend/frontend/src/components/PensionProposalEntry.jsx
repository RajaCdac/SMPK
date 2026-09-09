import { useState, useEffect } from "react";
import { Link, useNavigate } from "react-router-dom";
import API from "../services/Api";
import "../styles/PensionProposal.css";
import {
  applyVrStartPeriod,
  buildEmptyProposalForm,
  defaultEarningRows,
  emptyEarningRow,
  formatServiceTenureYearsOnly,
} from "./pensionProposalDefaults";
import {
  lookupBankByCode,
  resolveBankFromMaster,
} from "../utils/bankAutocomplete";
import {
  HELD_UP_FLAG_OPTIONS,
  heldFlagIsActive,
  heldFlagRequiresAmount,
  normalizeHeldUpFlag,
} from "../constants/heldUpFlagOptions";
import {
  WITHHOLD_REASON_OPTIONS,
  normalizeWithholdReason,
  withholdReasonIsActive,
} from "../constants/withholdReasonOptions";
import {
  sanitizePensionProposalForm,
  validatePensionProposalForm,
} from "../utils/pensionProposalValidation";
import EarnDednCodeHintModal from "./EarnDednCodeHintModal";

function toInputDate(v) {
  if (!v) return "";
  if (/^\d{4}-\d{2}-\d{2}/.test(String(v))) return String(v).slice(0, 10);
  const p = String(v).split("-");
  if (p.length === 3 && p[0].length <= 2) return `${p[2]}-${p[1]}-${p[0]}`;
  return v;
}

function toCheckboxBool(v) {
  if (v === true || v === 1 || v === "1" || v === "Y" || v === "y") return true;
  if (v === false || v === 0 || v === "0" || v === "N" || v === "n") return false;
  if (v == null || v === "") return false;
  if (typeof v === "string") {
    return ["true", "yes", "on", "y"].includes(v.trim().toLowerCase());
  }
  return Boolean(v);
}

function fieldStr(v) {
  if (v === null || v === undefined) return "";
  return String(v);
}

function normalizeProposalData(data, employee) {
  const merged = {
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
    held_recovery_date: toInputDate(data.held_recovery_date),
    held_up_flag: normalizeHeldUpFlag(data.held_up_flag),
    quarter_status: normalizeWithholdReason(data.quarter_status),
    id_card_submitted: toCheckboxBool(data.id_card_submitted),
    vigilance_cleared: toCheckboxBool(data.vigilance_cleared),
    extra_tccs_enabled: toCheckboxBool(data.extra_tccs_enabled),
    eligible_double_family_pension: toCheckboxBool(
      data.eligible_double_family_pension
    ),
    service_tenure: formatServiceTenureYearsOnly(
      employee?.amount_data?.total_service ||
        employee?.proposal_defaults?.service_tenure ||
        data.service_tenure ||
        ""
    ),
    earning_deductions:
      data.earning_deductions?.length > 0
        ? data.earning_deductions
        : defaultEarningRows(),
  };

  return applyVrStartPeriod(
    {
      ...merged,
      ca_number: fieldStr(merged.ca_number),
      pension_proposal_no: fieldStr(merged.pension_proposal_no),
      regn_no: fieldStr(merged.regn_no),
      pension_roll_no: fieldStr(merged.pension_roll_no),
      provisional_pension_pct: fieldStr(merged.provisional_pension_pct),
      bank_cd: fieldStr(merged.bank_cd),
      bank_name: fieldStr(merged.bank_name),
      account_no: fieldStr(merged.account_no),
      vigilance_clearance_ref_no: fieldStr(merged.vigilance_clearance_ref_no),
      lic_bank_cd: fieldStr(merged.lic_bank_cd),
      lic_bank_name: fieldStr(merged.lic_bank_name),
      vr_ref_no: fieldStr(merged.vr_ref_no),
      compassionate_allowance: fieldStr(merged.compassionate_allowance),
      compassionate_allowance_amt: fieldStr(merged.compassionate_allowance_amt),
      retirement_cpi: fieldStr(merged.retirement_cpi),
      held_gratuity_amt: fieldStr(merged.held_gratuity_amt),
      held_recovery_amt: fieldStr(merged.held_recovery_amt),
      held_recovery_ref_no: fieldStr(merged.held_recovery_ref_no),
      held_recovery_remarks: fieldStr(merged.held_recovery_remarks),
      implemented_year: fieldStr(merged.implemented_year),
      implemented_month: fieldStr(merged.implemented_month),
      start_month: merged.start_month ?? "",
      start_year: fieldStr(merged.start_year),
    },
    employee
  );
}

export default function PensionProposalEntry({
  employee,
  showClaimNext = false,
  claimNextTo = "",
  showAmountNext = false,
  amountNextTo = "",
}) {
  const [form, setForm] = useState(buildEmptyProposalForm(employee));
  const [recordExists, setRecordExists] = useState(false);
  const [isEditing, setIsEditing] = useState(false);
  const [loading, setLoading] = useState(true);
  const [bankMaster, setBankMaster] = useState([]);
  const [earnDednHintRow, setEarnDednHintRow] = useState(null);
  const [saveNotice, setSaveNotice] = useState("");
  const navigate = useNavigate();

  useEffect(() => {
    let cancelled = false;
    const loadBanks = async () => {
      try {
        const res = await API.get("first-pension/banks/?limit=2000");
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

  useEffect(() => {
    if (!form.bank_cd || form.bank_name || bankMaster.length === 0) return;

    let cancelled = false;
    lookupBankByCode(API, bankMaster, form.bank_cd).then(
      ({ bank_cd, bank_name }) => {
        if (cancelled || !bank_name) return;
        setForm((prev) =>
          prev.bank_name ? prev : { ...prev, bank_cd, bank_name }
        );
      }
    );
    return () => {
      cancelled = true;
    };
  }, [form.bank_cd, form.bank_name, bankMaster]);

  useEffect(() => {
    if (!form.lic_bank_cd || form.lic_bank_name || bankMaster.length === 0) return;

    let cancelled = false;
    lookupBankByCode(API, bankMaster, form.lic_bank_cd).then(
      ({ bank_cd, bank_name }) => {
        if (cancelled || !bank_name) return;
        setForm((prev) =>
          prev.lic_bank_name
            ? prev
            : { ...prev, lic_bank_cd: bank_cd, lic_bank_name: bank_name }
        );
      }
    );
    return () => {
      cancelled = true;
    };
  }, [form.lic_bank_cd, form.lic_bank_name, bankMaster]);

  useEffect(() => {
    if (!employee) return;

    const load = async () => {
      setLoading(true);
      setSaveNotice("");
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
          const apiDefaults = res.data.proposal_defaults || null;
          // Prefer full Oracle MH/MD legacy prefill over thin bank/date defaults.
          if (apiDefaults?.legacy && apiDefaults?.pension_type) {
            proposalDefaults = apiDefaults;
          } else if (proposalDefaults?.legacy && proposalDefaults?.pension_type) {
            proposalDefaults = {
              ...apiDefaults,
              ...proposalDefaults,
            };
          } else {
            proposalDefaults = {
              ...(proposalDefaults || {}),
              ...(apiDefaults || {}),
            };
          }
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
      } else if (proposalDefaults?.legacy && proposalDefaults?.ca_number) {
        setForm(normalizeProposalData(proposalDefaults, empWithDefaults));
        setRecordExists(false);
        setIsEditing(true);
      } else {
        setForm(buildEmptyProposalForm(empWithDefaults));
        setRecordExists(false);
        setIsEditing(true);
      }
      setLoading(false);
    };

    load();
  }, [employee?.emp_id]);

  const fieldDisabled = recordExists && !isEditing;
  const pensionType = String(form.pension_type || "").toUpperCase();
  const legacyPrefill =
    !recordExists && Boolean(employee?.proposal_defaults?.legacy);
  const heldAmtEnabled = heldFlagRequiresAmount(form.held_up_flag);
  const hasWithholdSetup =
    heldFlagIsActive(form.held_up_flag) ||
    withholdReasonIsActive(form.quarter_status);
  const hasRecoveryData = [
    form.held_recovery_amt,
    form.held_recovery_date,
    form.held_recovery_ref_no,
    form.held_recovery_remarks,
  ].some((v) => String(v ?? "").trim() !== "");
  // Recovery is record-keeping for a later refund — only after the proposal exists,
  // and only in edit mode (or readonly view when recovery was already saved).
  const showHeldRecovery =
    recordExists && (hasRecoveryData || (isEditing && hasWithholdSetup));

  const onChange = (e) => {
    const { name, value, type, checked } = e.target;
    setForm((prev) => {
      const next = {
        ...prev,
        [name]: type === "checkbox" ? checked : value,
      };
      if (name === "pension_type") {
        const pt = String(value || "").toUpperCase();
        if (recordExists && pt !== "C") {
          next.compassionate_allowance = "";
          next.compassionate_allowance_amt = "";
        }
        if (pt !== "P") {
          next.provisional_pension_pct = "";
        }
      }
      if (name === "held_up_flag") {
        const flag = normalizeHeldUpFlag(value);
        next.held_up_flag = flag;
        if (!heldFlagRequiresAmount(flag)) {
          next.held_gratuity_amt = "";
        }
      }
      if (name === "quarter_status") {
        next.quarter_status = normalizeWithholdReason(value);
      }
      return next;
    });
  };

  const handleBankCdChange = (e) => {
    const { bank_cd, bank_name } = resolveBankFromMaster(
      bankMaster,
      e.target.value
    );
    setForm((prev) => ({ ...prev, bank_cd, bank_name }));
  };

  const handleBankCdBlur = async () => {
    const { bank_cd, bank_name } = await lookupBankByCode(
      API,
      bankMaster,
      form.bank_cd
    );
    setForm((prev) => ({ ...prev, bank_cd, bank_name }));
  };

  const handleLicBankCdChange = (e) => {
    const { bank_cd, bank_name } = resolveBankFromMaster(
      bankMaster,
      e.target.value
    );
    setForm((prev) => ({
      ...prev,
      lic_bank_cd: bank_cd,
      ...(bank_name ? { lic_bank_name: bank_name } : {}),
    }));
  };

  const handleLicBankCdBlur = async () => {
    const { bank_cd, bank_name } = await lookupBankByCode(
      API,
      bankMaster,
      form.lic_bank_cd
    );
    setForm((prev) => ({
      ...prev,
      lic_bank_cd: bank_cd,
      lic_bank_name: bank_name || prev.lic_bank_name,
    }));
  };

  const onEarningChange = (index, field, value) => {
    setForm((prev) => {
      const rows = [...prev.earning_deductions];
      const row = { ...rows[index], [field]: value };
      if (field === "type" && !String(value).toUpperCase().startsWith("D")) {
        row.deduction_priority = "";
      }
      rows[index] = row;
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

  const removeEarningRow = (index) => {
    setForm((prev) => {
      if (prev.earning_deductions.length <= 1) {
        return prev;
      }
      return {
        ...prev,
        earning_deductions: prev.earning_deductions.filter((_, i) => i !== index),
      };
    });
    setEarnDednHintRow((current) => {
      if (current === null) return null;
      if (current === index) return null;
      if (current > index) return current - 1;
      return current;
    });
  };

  const handlePopulateDetails = () => {
    alert("Populate Details will load earning/deduction from finance records.");
  };

  const openEarnDednHint = (index) => {
    const row = form.earning_deductions[index];
    if (!String(row?.type || "").toUpperCase().startsWith("D")) return;
    setEarnDednHintRow(index);
  };

  const handleEarnDednHintSelect = (item) => {
    if (earnDednHintRow === null) return;
    const idx = earnDednHintRow;
    setForm((prev) => {
      const rows = [...prev.earning_deductions];
      rows[idx] = {
        ...rows[idx],
        code: item.code || "",
        desc: item.desc || "",
        type: "D",
      };
      return { ...prev, earning_deductions: rows };
    });
    setEarnDednHintRow(null);
  };

  const handleCodeKeyDown = (e, index) => {
    if (e.key !== "F9") return;
    const row = form.earning_deductions[index];
    if (!String(row?.type || "").toUpperCase().startsWith("D")) return;
    e.preventDefault();
    openEarnDednHint(index);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    const isUpdate = Boolean(form.id);

    const sanitized = sanitizePensionProposalForm(form);
    const validationErrors = validatePensionProposalForm(sanitized, {
      recordExists: Boolean(form.id) || recordExists,
    });
    if (validationErrors.length > 0) {
      alert(validationErrors.join("\n"));
      return;
    }

    try {
      const payload = {
        ...sanitized,
        implemented_year:
          String(sanitized.implemented_year || "").trim() === ""
            ? null
            : Number(sanitized.implemented_year),
        implemented_month:
          String(sanitized.implemented_month || "").trim() === ""
            ? null
            : Number(sanitized.implemented_month),
      };

      const response = isUpdate
        ? await API.put(`first-pension/pension-proposal/${form.id}/`, payload)
        : await API.post("first-pension/pension-proposal/", payload);

      let alertMessage = response.data.message || (
        isUpdate
          ? "Pension Proposal Updated Successfully"
          : "Pension Proposal Saved Successfully"
      );
      if (response.data.oracle_warning) {
        alertMessage += ` ${response.data.oracle_warning}`;
      }

      if (response.data.proposal_data) {
        setForm(normalizeProposalData(response.data.proposal_data, employee));
      }
      setRecordExists(true);
      setIsEditing(false);
      setSaveNotice(alertMessage);
      if (amountNextTo) {
        navigate(amountNextTo);
      }
    } catch (error) {
      console.error(error);
      setSaveNotice("");
      const apiErrors = error.response?.data?.errors;
      if (Array.isArray(apiErrors) && apiErrors.length > 0) {
        alert(apiErrors.join("\n"));
      } else {
        alert(error.response?.data?.error || "Save Failed");
      }
    }
  };

  if (!employee) return null;
  if (loading) {
    return <p className="text-muted">Loading pension proposal...</p>;
  }

  const showNextClaim =
    showClaimNext && Boolean(claimNextTo) && recordExists && !isEditing;
  const showNextAmount =
    showAmountNext && Boolean(amountNextTo) && recordExists && !isEditing;

  return (
    <form onSubmit={handleSubmit} className="pension-proposal-form smpk-form">
      <div className="pp-title-bar">PENSION / FAMILY PENSION PROPOSAL</div>
      {saveNotice ? (
        <div className="alert alert-success py-2 mb-2 mx-2 mt-2" role="status">
          {saveNotice}
          {showNextClaim ? (
            <span className="ms-1">
              Next: complete <strong>Pension Application</strong> (claim form)
              for this employee.
            </span>
          ) : null}
          {showNextAmount ? (
            <span className="ms-1">
              Next: open <strong>Amount</strong> (pension / commutation /
              gratuity calculation).
            </span>
          ) : null}
        </div>
      ) : null}
      {showNextClaim && !saveNotice ? (
        <div className="alert alert-info py-2 mb-2 mx-2 mt-2" role="status">
          Proposal is saved. Continue to Pension Application (claim form) for
          this employee.
        </div>
      ) : null}
      {showNextAmount && !saveNotice ? (
        <div className="alert alert-info py-2 mb-2 mx-2 mt-2" role="status">
          Proposal is saved. Continue to Amount (calculation) for this employee.
        </div>
      ) : null}
      {legacyPrefill && (
        <div className="alert alert-info py-2 mb-2 mx-2 mt-2">
          Prefill from Oracle FI_PN_MH_PENSION_PROPOSAL / FI_PN_MD_PENSION_PROPOSAL
          ({employee?.proposal_defaults?.source || "legacy"}). Review and Save to
          store in SMPK.
        </div>
      )}

      <div className="pp-form-scroll">
        <div className="row g-2 mb-2">
          <div className="col-12 col-lg-6">
            <div className="row g-2 align-items-end">
              {/* <div className="col-12 col-sm-4 col-md-3">
                <label className="pp-label">Employee</label>
                <input className="form-control" name="emp_cd" value={form.emp_cd} readOnly />
              </div>
              <div className="col-12 col-sm-8 col-md-9">
                <label className="pp-label d-sm-none">Name</label>
                <input className="form-control pp-readonly" name="emp_name" value={form.emp_name} readOnly />
              </div> */}
              <div className="col-12 col-lg-6">
                <label className="pp-label">Employee Status</label>
                <select className="form-select" name="employee_status" value={form.employee_status} onChange={onChange} disabled={fieldDisabled} >
                  <option value="P">Pensioner</option>
                  <option value="F">Family Pensioner</option>
                </select>
              </div>
              <div className="col-12 col-lg-6">
                <label className="pp-label">CA No. *</label>
                <input className="form-control" name="ca_number" value={form.ca_number} onChange={onChange} disabled={fieldDisabled} required maxLength={22} autoComplete="off" />
              </div>
              <div className="col-md-4">
                <label className="pp-label">Pension Type</label>
                <select className="form-select" name="pension_type" value={form.pension_type} onChange={onChange} disabled={fieldDisabled} >
                  <option value="">Select</option>
                  <option value="N">Normal Pension</option>
                  <option value="F">Family Pension</option>
                  <option value="P">Provisional Pension</option>
                  <option value="S">Service Gratuity</option>
                  <option value="C">Compassionate Allowance</option>
                  <option value="R">Resignation</option>
                </select>
              </div>
              <div className="col-md-4">
                <label className="pp-label">Pension Proposal No</label>
                <input className="form-control" name="pension_proposal_no" value={form.pension_proposal_no} onChange={onChange} disabled={fieldDisabled} />
              </div>
              <div className="col-md-4">
                <label className="pp-label">Pension Proposal Date</label>
                <input
                  type="date"
                  className="form-control"
                  name="pension_proposal_date"
                  value={form.pension_proposal_date || ""}
                  onChange={onChange}
                  disabled={fieldDisabled}
                />
              </div>
              
            </div>
          </div>

          <div className="col-12 col-lg-6">
            <div className="pp-section h-100">
              <div className="row g-2">
                <div className="col-md-4">
                  <label className="pp-label">Separation type</label>
                  <select className="form-select" name="separation_type" value={form.separation_type} onChange={onChange} disabled={fieldDisabled} >
                    <option value="">Select</option>
                    <option value="RT">Superannuation</option>
                    <option value="DT">Death</option>
                    <option value="VR">Voluntary Retirement</option>
                  </select>
                </div>
                <div className="col-md-4">
                  <label className="pp-label">Separation Date</label>
                  <input type="date" className="form-control pp-readonly" name="separation_date" value={form.separation_date || ""} readOnly />
                </div>
                {/* Impl. Year / Month — hidden for now; kept in model/API for later use
                <div className="col-6 col-sm-4 col-lg-2">
                  <label className="pp-label">Impl. Year</label>
                  <input
                    className="form-control"
                    name="implemented_year"
                    value={form.implemented_year}
                    onChange={onChange}
                    disabled={fieldDisabled}
                  />
                </div>
                <div className="col-6 col-sm-4 col-lg-2">
                  <label className="pp-label">Impl. Month</label>
                  <input
                    className="form-control"
                    name="implemented_month"
                    value={form.implemented_month}
                    onChange={onChange}
                    disabled={fieldDisabled}
                  />
                </div>
                */}
                <div className="col-md-4">
                  <label className="pp-label">Total Service (Yrs)</label>
                  <input className="form-control pp-readonly" name="service_tenure" value={form.service_tenure} readOnly />
                </div>
                <div className="col-6">
                <div className="form-check">
                  <input className="form-check-input" type="checkbox" name="eligible_double_family_pension" checked={form.eligible_double_family_pension} onChange={onChange} disabled={fieldDisabled} />
                  <label className="form-check-label">
                    Eligible for Double Family Pension
                  </label>
                </div>
              </div>
              
              <div className="col-6">
                <label className="pp-label">Double Family Pension Upto Date</label>
                <input
                  type="date"
                  className="form-control"
                  name="double_family_pension_upto_date"
                  value={form.double_family_pension_upto_date || ""}
                  onChange={onChange}
                  disabled={fieldDisabled}
                />
              </div>
              </div>
            </div>
          </div>
        </div>

        <div className="row g-2 mb-2">
          <div className="col-12 col-sm-6 col-lg-3">
            <label className="pp-label">Pension Option</label>
            <select className="form-select" name="pension_option" value={form.pension_option} onChange={onChange} disabled={fieldDisabled} >
              <option value="">Select</option>
              <option value="G">Govt Line</option>
              <option value="P">Port Line</option>
            </select>
          </div>
          <div className="col-12 col-sm-6 col-lg-3">
            <label className="pp-label">Option Given By</label>
            <select className="form-select" name="option_given_by" value={form.option_given_by} onChange={onChange} disabled={fieldDisabled} >
              <option value="">Select</option>
              <option value="E">Employee</option>
              <option value="W">Widow</option>
              <option value="S">Son</option>
              <option value="D">Daughter</option>
              <option value="WD">Widow Daughter</option>
              
            </select>
          </div>
          <div className="col-12 col-sm-6 col-lg-3">
            <label className="pp-label">Regn No.</label>
            <input
              className="form-control"
              name="regn_no"
              value={form.regn_no}
              onChange={onChange}
              disabled={fieldDisabled}
            />
          </div>
          <div className="col-12 col-sm-6 col-lg-3">
            <label className="pp-label">Regn Date</label>
            <input
              type="date"
              className="form-control"
              name="regn_date"
              value={form.regn_date || ""}
              onChange={onChange}
              disabled={fieldDisabled}
            />
          </div>
          <div className="col-6 col-sm-4 col-lg-2">
            <label className="pp-label">Start Month</label>
            <select
              className="form-select pp-readonly"
              name="start_month"
              value={form.start_month}
              disabled
            >
              <option value="">--</option>
              {Array.from({ length: 12 }, (_, i) => (
                <option key={i + 1} value={i + 1}>
                  {i + 1}
                </option>
              ))}
            </select>
          </div>
          <div className="col-6 col-sm-4 col-lg-2">
            <label className="pp-label">Start Year</label>
            <input
              className="form-control pp-readonly"
              name="start_year"
              value={form.start_year}
              readOnly
            />
          </div>
          <div className="col-6 col-sm-4 col-lg-2">
            <label className="pp-label">Roll No</label>
            <input
              className="form-control"
              name="pension_roll_no"
              value={form.pension_roll_no}
              onChange={onChange}
              disabled={fieldDisabled}
            />
          </div>
          <div className="col-6 col-sm-4 col-lg-2">
            <label className="pp-label">Bank</label>
            <input type="text" className="form-control" name="bank_cd" list="proposal-bank-list" value={form.bank_cd}  onChange={handleBankCdChange}  onBlur={handleBankCdBlur} disabled={fieldDisabled} placeholder="Type or select code" autoComplete="off" />
            <datalist id="proposal-bank-list">
              {bankMaster.map((bank) => (
                <option key={bank.bank_cd} value={bank.bank_cd} label={`${bank.bank_cd} — ${bank.bank_name || bank.bank_desc || ""}`} />
              ))}
            </datalist>
          </div>
          <div className="col-12 col-sm-4 col-lg-2">
            <label className="pp-label">Bank Name</label>
            <input className="form-control pp-readonly" name="bank_name"  value={form.bank_name} readOnly placeholder="Filled from bank code" />
          </div>
          <div className="col-6 col-sm-4 col-lg-2">
            <label className="pp-label">A/C No</label>
            <input className="form-control" name="account_no" value={form.account_no} onChange={onChange} disabled={fieldDisabled} />
          </div>
          
        </div>

        <div className="row g-2 mb-2">
          <div className="col-6 col-sm-4 col-lg-2">
            <label className="pp-label">Provisional Pension %</label>
            <input
              className="form-control"
              name="provisional_pension_pct"
              value={form.provisional_pension_pct}
              onChange={onChange}
              disabled={fieldDisabled}
              required={pensionType === "P"}
            />
          </div>
          
          <div className="col-12 col-sm-6 col-lg-3">
            <label className="pp-label">Vig. Clearance Ref. No.</label>
            <input
              className="form-control"
              name="vigilance_clearance_ref_no"
              value={form.vigilance_clearance_ref_no}
              onChange={onChange}
              disabled={fieldDisabled}
            />
          </div>
          <div className="col-6 col-sm-4 col-lg-2">
            <label className="pp-label">Vig. Clearance Ref. Dt.</label>
            <input
              type="date"
              className="form-control"
              name="vigilance_clearance_ref_dt"
              value={form.vigilance_clearance_ref_dt || ""}
              onChange={onChange}
              disabled={fieldDisabled}
            />
          </div>
          <div className="col-6 col-sm-4 col-lg-2">
            <label className="pp-label">Lic Opted Bank</label>
            <input
              type="text"
              className="form-control"
              name="lic_bank_cd"
              list="proposal-lic-bank-list"
              value={form.lic_bank_cd}
              onChange={handleLicBankCdChange}
              onBlur={handleLicBankCdBlur}
              disabled={fieldDisabled}
              placeholder="Type or select code"
              autoComplete="off"
            />
            <datalist id="proposal-lic-bank-list">
              {bankMaster.map((bank) => (
                <option
                  key={bank.bank_cd}
                  value={bank.bank_cd}
                  label={`${bank.bank_cd} — ${bank.bank_name || bank.bank_desc || ""}`}
                />
              ))}
            </datalist>
          </div>
          <div className="col-12 col-sm-6 col-lg-3">
            <label className="pp-label">Lic Opted Bank Name</label>
            <input
              className="form-control"
              name="lic_bank_name"
              value={form.lic_bank_name}
              onChange={onChange}
              disabled={fieldDisabled}
              placeholder="Bank name"
            />
          </div>
        </div>

        <div className="row g-2 mb-2">
          <div className="col-12 col-sm-6 col-lg-3">
            <label className="pp-label">V.R Ref No</label>
            <input
              className="form-control"
              name="vr_ref_no"
              value={form.vr_ref_no}
              onChange={onChange}
              disabled={fieldDisabled}
            />
          </div>
          <div className="col-12 col-sm-6 col-lg-3">
            <label className="pp-label">V.R Ref Date</label>
            <input
              type="date"
              className="form-control"
              name="vr_ref_dt"
              value={form.vr_ref_dt || ""}
              onChange={onChange}
              disabled={fieldDisabled}
            />
          </div>
          <div className="col-12 col-sm-6 col-lg-3">
            <label className="pp-label">Compassionate Allowance</label>
            <select
              className="form-select"
              name="compassionate_allowance"
              value={form.compassionate_allowance}
              onChange={onChange}
              disabled={fieldDisabled}
            >
              <option value="">Select</option>
              <option value="1">Less Than Equal 1/3 Pension</option>
              <option value="2">Less Than Equal 1/3 Gratuity</option>
              <option value="3">Less Than Equal 1/3 (Pension+Gratuity)</option>
            </select>
          </div>
          <div className="col-12 col-sm-6 col-lg-3">
            <label className="pp-label">Compassionate Allowance Amt</label>
            <input
              className="form-control"
              name="compassionate_allowance_amt"
              value={form.compassionate_allowance_amt}
              onChange={onChange}
              disabled={fieldDisabled}
              required={pensionType === "C" && !fieldDisabled}
            />
          </div>
          
          <div className="col-12 col-sm-6 col-lg-3">
            <label className="pp-label">Nominee/E-form</label>
            <select
              className="form-select"
              name="nominee_eform"
              value={form.nominee_eform}
              onChange={onChange}
              disabled={fieldDisabled}
            >
              <option value="">Select</option>
              <option value="N">Nominee</option>
              <option value="E">E-Form</option>
            </select>
          </div>
          <div className="col-12 col-sm-6 col-lg-3">
            <label className="pp-label">Reasons to Withhold</label>
            <select
              className="form-select"
              name="quarter_status"
              value={form.quarter_status}
              onChange={onChange}
              disabled={fieldDisabled}
            >
              <option value="">Select</option>
              {WITHHOLD_REASON_OPTIONS.map((opt) => (
                <option key={opt.value} value={opt.value}>
                  {opt.label}
                </option>
              ))}
            </select>
          </div>
          
          <div className="col-6 col-sm-4 col-lg-2">
            <label className="pp-label">Port City Resident</label>
            <select
              className="form-select"
              name="port_city_resident"
              value={form.port_city_resident}
              onChange={onChange}
              disabled={fieldDisabled}
            >
              <option value="">Select</option>
              <option value="YES">Yes</option>
              <option value="NO">No</option>
            </select>
          </div>
          <div className="col-6 col-sm-4 col-lg-2">
            <label className="pp-label">Gratuity Option</label>
            <select
              className="form-select"
              name="gratuity_option"
              value={form.gratuity_option}
              onChange={onChange}
              disabled={fieldDisabled}
            >
              <option value="">Select</option>
              <option value="0">Retirement Gratuity Opt-I</option>
              <option value="1">Retirement Gratuity Opt-II</option>
              <option value="2">Death Gratuity Opt-II</option>
            </select>
          </div>
          <div className="col-6 col-sm-4 col-lg-2">
            <label className="pp-label">Retirement CPI</label>
            <input
              className="form-control"
              name="retirement_cpi"
              value={form.retirement_cpi}
              onChange={onChange}
              disabled={fieldDisabled}
            />
          </div>
          <div className="col-12 col-sm-6 col-lg-3 d-flex align-items-end gap-3">
            <div className="form-check">
              <input
                className="form-check-input"
                type="checkbox"
                name="id_card_submitted"
                checked={form.id_card_submitted}
                onChange={onChange}
                disabled={fieldDisabled}
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
                disabled={fieldDisabled}
              />
              <label className="form-check-label">Vig. Cleared</label>
            </div>
          </div>
        </div>

        <div className="row g-2 mb-2 align-items-end">
          <div className="col-6 col-sm-4 col-lg-2">
            <label className="pp-label">Inc Holder</label>
            <select
              className="form-select"
              name="incentive_holder"
              value={form.incentive_holder}
              onChange={onChange}
              disabled={fieldDisabled}
            >
              <option value="">Select</option>
              <option value="YES">Yes</option>
              <option value="NO">No</option>
            </select>
          </div>
          <div className="col-6 col-sm-4 col-lg-2">
            <label className="pp-label">Held Up Flg</label>
            <select
              className="form-select"
              name="held_up_flag"
              value={form.held_up_flag}
              onChange={onChange}
              disabled={fieldDisabled}
            >
              <option value="">Select</option>
              {HELD_UP_FLAG_OPTIONS.map((opt) => (
                <option key={opt.value} value={opt.value}>
                  {opt.label}
                </option>
              ))}
            </select>
          </div>
          <div className="col-6 col-sm-4 col-lg-2">
            <label className="pp-label">Amt.</label>
            <input
              className="form-control"
              name="held_gratuity_amt"
              value={form.held_gratuity_amt}
              onChange={onChange}
              disabled={fieldDisabled || !heldAmtEnabled}
              required={heldAmtEnabled}
            />
          </div>
          <div className="col-12 col-lg-6">
            <div className="form-check mb-2">
              <input
                className="form-check-input"
                type="checkbox"
                name="extra_tccs_enabled"
                checked={form.extra_tccs_enabled}
                onChange={onChange}
                disabled={fieldDisabled}
              />
              <label className="form-check-label">Extra TCCS</label>
            </div>
            <div className="pp-tccs-inline">
              <input
                className="form-control pp-tccs-field"
                name="extra_tccs_years"
                value={form.extra_tccs_years}
                onChange={onChange}
                disabled={fieldDisabled || !form.extra_tccs_enabled}
                placeholder="Years"
                aria-label="Extra TCCS years"
              />
              <input
                className="form-control pp-tccs-field"
                name="extra_tccs_months"
                value={form.extra_tccs_months}
                onChange={onChange}
                disabled={fieldDisabled || !form.extra_tccs_enabled}
                placeholder="Months"
                aria-label="Extra TCCS months"
              />
              <input
                className="form-control pp-tccs-field"
                name="extra_tccs_days"
                value={form.extra_tccs_days}
                onChange={onChange}
                disabled={fieldDisabled || !form.extra_tccs_enabled}
                placeholder="Days"
                aria-label="Extra TCCS days"
              />
            </div>
          </div>
        </div>

        {showHeldRecovery && (
          <div className="row g-2 mb-2 pp-held-recovery">
            <div className="col-12">
              <div className="pp-section-title">Withheld Amount Recovery</div>
              {isEditing && (
                <p className="pp-held-recovery-hint mb-2">
                  Record refund details here when the employee returns the withheld
                  amount (weeks, months, or years after the initial proposal). Leave
                  blank on first processing.
                </p>
              )}
            </div>
            <div className="col-6 col-sm-4 col-lg-3">
              <label className="pp-label">Amount Recovered</label>
              <input
                className="form-control"
                name="held_recovery_amt"
                value={form.held_recovery_amt}
                onChange={onChange}
                disabled={fieldDisabled}
                inputMode="decimal"
              />
            </div>
            <div className="col-6 col-sm-4 col-lg-3">
              <label className="pp-label">Recovery Date</label>
              <input
                type="date"
                className="form-control"
                name="held_recovery_date"
                value={form.held_recovery_date}
                onChange={onChange}
                disabled={fieldDisabled}
              />
            </div>
            <div className="col-6 col-sm-4 col-lg-3">
              <label className="pp-label">Ref / Letter No.</label>
              <input
                className="form-control"
                name="held_recovery_ref_no"
                value={form.held_recovery_ref_no}
                onChange={onChange}
                disabled={fieldDisabled}
                maxLength={30}
              />
            </div>
            <div className="col-12 col-lg-3">
              <label className="pp-label">Remarks</label>
              <input
                className="form-control"
                name="held_recovery_remarks"
                value={form.held_recovery_remarks}
                onChange={onChange}
                disabled={fieldDisabled}
                maxLength={500}
              />
            </div>
          </div>
        )}

        <div className="pp-section">
          <div className="d-flex justify-content-between align-items-center mb-2">
            <span className="pp-section-title mb-0">Earning / Deduction</span>
            <button
              type="button"
              className="btn btn-sm btn-outline-primary"
              onClick={handlePopulateDetails}
              disabled={fieldDisabled}
            >
              Populate Details
            </button>
          </div>
          <div className="pp-earn-table-wrap">
          <table className="pp-earn-table table table-bordered mb-0">
            <thead>
              <tr>
                <th>Type</th>
                <th>Code</th>
                <th>Desc</th>
                <th>Amount</th>
                <th>Deduction Priority</th>
                <th className="pp-earn-actions-col">Actions</th>
              </tr>
            </thead>
            <tbody>
              {form.earning_deductions.map((row, idx) => (
                <tr key={idx}>
                  <td>
                    <select
                      className="form-select"
                      value={row.type}
                      onChange={(e) =>
                        onEarningChange(idx, "type", e.target.value)
                      }
                      disabled={fieldDisabled}
                    >
                      <option value="E">EARNNG</option>
                      <option value="D">DEDUCTION</option>
                    </select>
                  </td>
                  <td>
                    <div className="pp-code-cell">
                      <input
                        className="form-control"
                        value={row.code}
                        onChange={(e) =>
                          onEarningChange(idx, "code", e.target.value)
                        }
                        onBlur={(e) =>
                          fetchEarnDednDescription(idx, e.target.value)
                        }
                        onKeyDown={(e) => handleCodeKeyDown(e, idx)}
                        disabled={fieldDisabled}
                        placeholder="e.g. 603"
                        title={
                          String(row.type || "").toUpperCase().startsWith("D")
                            ? "F9 — deduction code list"
                            : undefined
                        }
                      />
                      {String(row.type || "").toUpperCase().startsWith("D") && (
                        <button
                          type="button"
                          className="pp-code-hint-btn"
                          onClick={() => openEarnDednHint(idx)}
                          disabled={fieldDisabled}
                          title="Deduction codes (F9)"
                          aria-label="Show deduction codes"
                        >
                          i
                        </button>
                      )}
                    </div>
                  </td>
                  <td>
                    <input
                      className="form-control pp-readonly"
                      value={row.desc}
                      readOnly
                      placeholder="From Oracle"
                    />
                  </td>
                  <td>
                    <input
                      className="form-control"
                      value={row.amount}
                      onChange={(e) =>
                        onEarningChange(idx, "amount", e.target.value)
                      }
                      disabled={fieldDisabled}
                    />
                  </td>
                  <td>
                    <select
                      className="form-select"
                      value={row.deduction_priority}
                      onChange={(e) =>
                        onEarningChange(
                          idx,
                          "deduction_priority",
                          e.target.value
                        )
                      }
                      disabled={
                        fieldDisabled ||
                        !String(row.type || "").toUpperCase().startsWith("D")
                      }
                    >
                      <option value="">--</option>
                      <option value="1">1</option>
                      <option value="2">2</option>
                      <option value="3">3</option>
                    </select>
                  </td>
                  <td className="pp-earn-actions-col text-center">
                    <button
                      type="button"
                      className="btn btn-sm btn-outline-danger pp-earn-delete-btn"
                      onClick={() => removeEarningRow(idx)}
                      disabled={
                        fieldDisabled || form.earning_deductions.length <= 1
                      }
                      title={
                        form.earning_deductions.length <= 1
                          ? "At least one row is required"
                          : "Delete row"
                      }
                      aria-label={`Delete earning/deduction row ${idx + 1}`}
                    >
                      Delete
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          </div>
          <button
            type="button"
            className="btn btn-sm btn-link mt-1"
            onClick={addEarningRow}
            disabled={fieldDisabled}
          >
            + Add row
          </button>
        </div>
      </div>

      <div className="smpk-form-actions justify-content-end flex-wrap gap-2 mt-3">
        {recordExists && (
          <button
            type="button"
            className="btn btn-secondary"
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
        {showNextClaim ? (
          <Link
            to={claimNextTo}
            className="btn btn-primary"
            title="Open Pension Application (claim form) for this employee"
          >
            Next: Pension Application →
          </Link>
        ) : null}
        {showNextAmount ? (
          <Link
            to={amountNextTo}
            className="btn btn-primary"
            title="Open Amount (pension / commutation / gratuity calculation)"
          >
            Next: Amount →
          </Link>
        ) : null}
      </div>

      <EarnDednCodeHintModal
        open={earnDednHintRow !== null}
        onClose={() => setEarnDednHintRow(null)}
        onSelect={handleEarnDednHintSelect}
      />
    </form>
  );
}
