import { useCallback, useEffect, useRef, useState } from "react";
import API from "../services/Api";
import FamilyPensionProposalPrint from "../components/FamilyPensionProposalPrint";
import { printPensionReport } from "../utils/pensionReportPrint";
import "../styles/FamilyPensionClaim.css";
import "../styles/FamilyPensionProposalReport.css";

/** FI_PN_MH_FPENSION_CLAIM_E.fmb — Family Pension Claim entry */

const MONTH_OPTIONS = [
  ["1", "JAN"],
  ["2", "FEB"],
  ["3", "MAR"],
  ["4", "APR"],
  ["5", "MAY"],
  ["6", "JUN"],
  ["7", "JUL"],
  ["8", "AUG"],
  ["9", "SEP"],
  ["10", "OCT"],
  ["11", "NOV"],
  ["12", "DEC"],
];

const STATUS_OPTIONS = [
  ["1", "VALID"],
  ["0", "INVALID"],
];

const APPLICANT_TYPE_OPTIONS = [
  ["", "—"],
  ["0", "0 - OTHER"],
  ["1", "1 - WIDOW"],
  ["3", "3 - SON"],
  ["4", "4 - DAUGHTER"],
  ["5", "5 - HANDICAPPED SON"],
  ["6", "6 - HANDICAPPED DAUGHTER"],
  ["7", "7 - DIVORCED DAUGHTER"],
  ["8", "8 - WIDOWER"],
  ["9", "9 - DEPENDENT FATHER"],
  ["10", "10 - DEPENDENT MOTHER"],
];

function currentMonthYear() {
  const now = new Date();
  return {
    month: String(now.getMonth() + 1),
    year: String(now.getFullYear()),
  };
}

function emptyClaim() {
  const { month, year } = currentMonthYear();
  return {
    clmca_id: "",
    clm_ca_type: "CM",
    ca_no: "",
    emp_cd: "",
    disp_name: "",
    appcn_no: "",
    appcn_date: "",
    appcn_status: "",
    double_fpen_eligibility: 0,
    double_fpen_upto: "",
    applicant_type: "",
    applicant_name: "",
    applicant_address: "",
    dod_emp_pensioner: "",
    gurdian_relation_cd: "",
    disp_relation: "",
    dob_guardian: "",
    service_pension_amt: "",
    fpen_start_mnth: month,
    fprn_start_yr: year,
    retirement_cpi: "",
    pension_opt: "",
    last_fpen_mth: month,
    last_fpen_yr: year,
    scale_cd: "",
    last_basic_at_ret: "",
    incentive_holder_flg: "",
    consolid_cpi_scl_stamt: "",
    equiv_pay_at_base_cpi: "",
    applicants: [],
  };
}

function emptyApplicantRow(slNo = 1) {
  return {
    sl_no: slNo,
    name: "",
    dob: "",
    relation_cd: "",
    relation_desc: "",
    bank_cd: "",
    account_no: "",
    lic_bank_cd: "",
    handicap_flg: "N",
    fpen_active: 1,
    status_flg: "S",
  };
}

function apiErrorMessage(err, fallback = "Request failed") {
  const data = err?.response?.data;
  if (!data) return err?.message || fallback;
  if (typeof data === "string") return data.slice(0, 400);
  if (data.error) return String(data.error);
  if (data.detail) {
    return typeof data.detail === "string"
      ? data.detail
      : JSON.stringify(data.detail);
  }
  return fallback;
}

function Field({ label, children, w = "fpc-w-md" }) {
  return (
    <div className={`fpc-field ${w}`}>
      <label className="fpc-label">{label}</label>
      {children}
    </div>
  );
}

export default function FamilyPension() {
  const [form, setForm] = useState(emptyClaim);
  const [relations, setRelations] = useState([]);
  const [matches, setMatches] = useState([]);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [isNewMode, setIsNewMode] = useState(false);
  const [prefilling, setPrefilling] = useState(false);
  const [report, setReport] = useState(null);
  const [reportLoading, setReportLoading] = useState(false);
  const [generatingFp, setGeneratingFp] = useState(false);
  const savingRef = useRef(false);
  const autoPrintRef = useRef(false);

  useEffect(() => {
    if (autoPrintRef.current && report?.pages?.length) {
      autoPrintRef.current = false;
      const t = setTimeout(() => printPensionReport(), 50);
      return () => clearTimeout(t);
    }
  }, [report]);

  useEffect(() => {
    API.get("family-pension/relations/")
      .then(({ data }) => setRelations(data?.results || []))
      .catch(() => setRelations([]));
  }, []);

  const setField = (key, value) => {
    setForm((prev) => ({ ...prev, [key]: value }));
  };

  const setApplicant = (index, key, value) => {
    setForm((prev) => {
      const applicants = [...(prev.applicants || [])];
      applicants[index] = { ...applicants[index], [key]: value };
      if (key === "relation_cd") {
        const rel = relations.find(
          (r) => String(r.relation_cd) === String(value)
        );
        applicants[index].relation_desc = rel?.relation_desc || "";
      }
      return { ...prev, applicants };
    });
  };

  const addApplicantRow = () => {
    setForm((prev) => ({
      ...prev,
      applicants: [
        ...(prev.applicants || []),
        emptyApplicantRow((prev.applicants?.length || 0) + 1),
      ],
    }));
  };

  const applyClaim = useCallback((claim) => {
    setForm({ ...emptyClaim(), ...claim, applicants: claim.applicants || [] });
    setMatches([]);
    setIsNewMode(false);
  }, []);

  const loadClaim = async (opts = {}) => {
    const clmca_id = (opts.clmca_id ?? form.clmca_id ?? "").trim();
    const emp_cd = (opts.emp_cd ?? form.emp_cd ?? "").trim();
    if (!clmca_id && !emp_cd) {
      setError("Enter Claim ID (or Emp Code) to load");
      return;
    }

    setLoading(true);
    setError("");
    setMessage("");
    try {
      const params = {};
      if (clmca_id) params.clmca_id = clmca_id;
      else params.emp_cd = emp_cd;

      const { data } = await API.get("family-pension/claim/", { params });
      if (data.claim) {
        applyClaim(data.claim);
        setMessage(`Loaded claim ${data.claim.clmca_id}`);
      } else if (data.matches?.length) {
        setMatches(data.matches);
        setMessage(data.message || "Select a claim from the list");
      } else {
        setError(data.error || "Claim not found");
      }
    } catch (err) {
      setError(apiErrorMessage(err, "Failed to load claim"));
    } finally {
      setLoading(false);
    }
  };

  const prefillFromEmp = async (empValue) => {
    const emp_cd = String(empValue ?? form.emp_cd ?? "").trim();
    if (!emp_cd) {
      setError("Enter Emp Code");
      return;
    }

    setPrefilling(true);
    setError("");
    setMessage("");
    try {
      const { data } = await API.get("family-pension/claim/", {
        params: {
          emp_cd,
          prefill: 1,
          clm_ca_type: form.clm_ca_type || "CM",
        },
      });
      if (data?.error) {
        setError(data.error);
        return;
      }
      const prefill = data?.prefill || {};
      const { month, year } = currentMonthYear();
      setForm((prev) => ({
        ...prev,
        ...prefill,
        // Keep blank Claim ID while creating a new claim
        clmca_id: isNewMode ? "" : prev.clmca_id,
        emp_cd,
        // Always blank for user input on new/search prefill
        dod_emp_pensioner: "",
        // Default start / last pension period = current month-year
        fpen_start_mnth: prefill.fpen_start_mnth ?? month,
        fprn_start_yr: prefill.fprn_start_yr ?? year,
        last_fpen_mth: prefill.last_fpen_mth ?? month,
        last_fpen_yr: prefill.last_fpen_yr ?? year,
        last_basic_at_ret: isNewMode ? "" : prev.last_basic_at_ret,
        applicants: prev.applicants?.length
          ? prev.applicants
          : [emptyApplicantRow(1)],
      }));
      if (data?.matches?.length) {
        setMatches(data.matches);
        setMessage(
          `Prefill done for ${emp_cd}. Existing claim(s) found — select to open, or continue as new.`
        );
      } else {
        setMatches([]);
        setMessage(`Prefill done for employee ${emp_cd}`);
      }
    } catch (err) {
      setError(apiErrorMessage(err, "Failed to prefill from Emp Code"));
    } finally {
      setPrefilling(false);
    }
  };

  const handleNew = () => {
    const blank = emptyClaim();
    blank.applicants = [emptyApplicantRow(1)];
    setForm(blank);
    setMatches([]);
    setIsNewMode(true);
    setMessage("New claim — enter Emp Code and press Enter to prefill");
    setError("");
  };

  const loadProposalReport = useCallback(async (opts = {}, { autoPrint = false } = {}) => {
    const clmca_id = String(opts.clmca_id || form.clmca_id || "").trim();
    const emp_cd = String(opts.emp_cd || form.emp_cd || "").trim();
    if (!clmca_id && !emp_cd) {
      setError("Save or load a claim before printing the report");
      return null;
    }

    setReportLoading(true);
    try {
      const params = {};
      if (clmca_id) params.clmca_id = clmca_id;
      else params.emp_cd = emp_cd;
      const { data } = await API.get(
        "family-pension/proposal-sanction-report/",
        { params }
      );
      autoPrintRef.current = !!autoPrint;
      setReport(data);
      return data;
    } catch (err) {
      autoPrintRef.current = false;
      setReport(null);
      setError(apiErrorMessage(err, "Could not load proposal report"));
      return null;
    } finally {
      setReportLoading(false);
    }
  }, [form.clmca_id, form.emp_cd]);

  const handleSave = async () => {
    if (savingRef.current) return;

    const emp_cd = String(form.emp_cd || "").trim();
    if (!emp_cd) {
      setError("Employee Code is required to save");
      return;
    }

    savingRef.current = true;
    setSaving(true);
    setError("");
    setMessage("");
    try {
      const payload = {
        ...form,
        emp_cd,
        // New form must not send an old Claim ID
        clmca_id: isNewMode ? "" : String(form.clmca_id || "").trim(),
        incentive_holder_flg: form.incentive_holder_flg || "Y",
      };
      const { data } = await API.post("family-pension/claim/", payload);
      if (data?.error) {
        setError(data.error);
        return;
      }
      if (data?.claim) {
        applyClaim(data.claim);
        setMessage(
          data.created
            ? `Saved new claim ${data.claim.clmca_id}`
            : `Updated claim ${data.claim.clmca_id}`
        );
        await loadProposalReport(
          {
            clmca_id: data.claim.clmca_id,
            emp_cd: data.claim.emp_cd || emp_cd,
          },
          { autoPrint: true }
        );
      } else {
        setError("Save failed — empty response from server");
      }
    } catch (err) {
      setError(apiErrorMessage(err, "Failed to save claim"));
    } finally {
      savingRef.current = false;
      setSaving(false);
    }
  };

  const handleGenerateFirstFp = async () => {
    const clmca_id = String(form.clmca_id || "").trim();
    if (!clmca_id) {
      setError("Save or load a claim first (Claim ID required)");
      return;
    }
    if (
      !window.confirm(
        `Generate First Family Pension (type N) for claim ${clmca_id}?\n` +
          "Amount will be calculated using Methodology-1."
      )
    ) {
      return;
    }
    setGeneratingFp(true);
    setError("");
    setMessage("");
    try {
      const { data } = await API.post("family-pension/generate-first-fp/", {
        clmca_id,
        month: form.fpen_start_mnth || undefined,
        year: form.fprn_start_yr || undefined,
        regenerate: false,
      });
      if (data?.error) {
        if (String(data.error).toLowerCase().includes("already generated")) {
          if (
            window.confirm(
              `${data.error}\n\nRegenerate and replace existing First FP rows?`
            )
          ) {
            const res2 = await API.post("family-pension/generate-first-fp/", {
              clmca_id,
              month: form.fpen_start_mnth || undefined,
              year: form.fprn_start_yr || undefined,
              regenerate: true,
            });
            if (res2.data?.error) {
              setError(res2.data.error);
              return;
            }
            const amt =
              res2.data?.methodology1?.selected_amount ??
              res2.data?.bills?.[0]?.fpension_amt;
            setMessage(
              `First FP regenerated. Amount ₹${amt}. Bill: ${
                res2.data?.bills?.[0]?.fam_fmpen_id || "—"
              }`
            );
            return;
          }
        }
        setError(data.error);
        return;
      }
      const amt =
        data?.methodology1?.selected_amount ?? data?.bills?.[0]?.fpension_amt;
      setMessage(
        `First FP generated. Amount ₹${amt} (M1 CPI ${data?.methodology1?.process_cpi}). ` +
          `Bill: ${data?.bills?.[0]?.fam_fmpen_id || "—"}`
      );
    } catch (err) {
      const msg = apiErrorMessage(err, "First FP generation failed");
      if (String(msg).toLowerCase().includes("already generated")) {
        if (
          window.confirm(`${msg}\n\nRegenerate and replace existing First FP rows?`)
        ) {
          try {
            const res2 = await API.post("family-pension/generate-first-fp/", {
              clmca_id,
              month: form.fpen_start_mnth || undefined,
              year: form.fprn_start_yr || undefined,
              regenerate: true,
            });
            const amt =
              res2.data?.methodology1?.selected_amount ??
              res2.data?.bills?.[0]?.fpension_amt;
            setMessage(
              `First FP regenerated. Amount ₹${amt}. Bill: ${
                res2.data?.bills?.[0]?.fam_fmpen_id || "—"
              }`
            );
            return;
          } catch (err2) {
            setError(apiErrorMessage(err2, "First FP regenerate failed"));
            return;
          }
        }
      }
      setError(msg);
    } finally {
      setGeneratingFp(false);
    }
  };

  const doubleEligible = Number(form.double_fpen_eligibility) === 1;
  const claimIdReadOnly = isNewMode;

  return (
    <div className="container-fluid mt-2 px-2 px-md-3 fpc-page w-100">
      <div className="fpc-title-bar">FAMILY PENSION CLAIM</div>

      <div className="fpc-toolbar smpk-form">
        <div className="fpc-toolbar-row">
          <div className="fpc-toolbar-left">
            <Field label="Claim ID" w="fpc-w-grow">
              <input
                className="form-control form-control-sm"
                value={form.clmca_id || ""}
                readOnly={claimIdReadOnly}
                placeholder={
                  claimIdReadOnly
                    ? "Auto on save"
                    : "Type Claim ID and Load"
                }
                onChange={(e) => {
                  if (!claimIdReadOnly) setField("clmca_id", e.target.value);
                }}
                onKeyDown={(e) => {
                  if (e.key === "Enter" && !claimIdReadOnly) {
                    e.preventDefault();
                    loadClaim({ clmca_id: e.currentTarget.value, emp_cd: "" });
                  }
                }}
              />
            </Field>
            <button
              type="button"
              className="btn btn-sm btn-primary"
              disabled={loading || saving}
              onClick={() => loadClaim()}
            >
              {loading ? "Loading…" : "Load"}
            </button>
          </div>
          <div className="fpc-toolbar-right">
            <button
              type="button"
              className="btn btn-sm btn-outline-secondary"
              disabled={saving}
              onClick={handleNew}
            >
              New
            </button>
            <button
              type="button"
              className="btn btn-sm btn-success"
              disabled={loading || saving}
              onClick={handleSave}
            >
              {saving ? "Saving…" : "Save"}
            </button>
            <button
              type="button"
              className="btn btn-sm btn-warning"
              disabled={
                loading ||
                saving ||
                generatingFp ||
                reportLoading ||
                !form.clmca_id
              }
              onClick={handleGenerateFirstFp}
              title="Generate First Family Pension using Methodology-1 amount"
            >
              {generatingFp ? "Generating…" : "Generate First FP"}
            </button>
            <button
              type="button"
              className="btn btn-sm btn-outline-primary"
              disabled={
                loading || saving || reportLoading || (!form.clmca_id && !form.emp_cd)
              }
              onClick={() => loadProposalReport({}, { autoPrint: true })}
            >
              {reportLoading ? "Report…" : "Print Report"}
            </button>
          </div>
        </div>
        {message ? <div className="fpc-msg ok">{message}</div> : null}
        {error ? <div className="fpc-msg err">{error}</div> : null}
        {matches.length > 0 ? (
          <div className="fpc-match-list">
            {matches.map((m) => (
              <button
                key={m.clmca_id}
                type="button"
                className="btn btn-sm btn-outline-primary"
                onClick={() => {
                  loadClaim({ clmca_id: m.clmca_id, emp_cd: "" });
                }}
              >
                {m.clmca_id}
              </button>
            ))}
          </div>
        ) : null}
      </div>

      <div className="fpc-panel smpk-form">
        <div className="fpc-row">
          <Field label="Claim Type" w="fpc-w-lg">
            <select
              className="form-select form-select-sm"
              value={form.clm_ca_type || "CM"}
              onChange={(e) => setField("clm_ca_type", e.target.value)}
            >
              <option value="CM">FROM E-FORM</option>
              <option value="CA">FROM PROPOSAL</option>
              <option value="CE">EXISTING FAMILY PENSIONER</option>
            </select>
          </Field>
          <Field label="Emp Code" w="fpc-w-xs">
            <input
              className="form-control form-control-sm"
              value={form.emp_cd || ""}
              onChange={(e) => setField("emp_cd", e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter") {
                  e.preventDefault();
                  prefillFromEmp(e.currentTarget.value);
                }
              }}
              placeholder="Enter"
              disabled={prefilling || loading}
            />
          </Field>
          <Field label="Name" w="fpc-w-grow">
            <input
              className="form-control form-control-sm"
              value={form.disp_name || ""}
              readOnly
            />
          </Field>
        </div>

        <div className="fpc-row">
          <Field label="CA No" w="fpc-w-sm">
            <input
              className="form-control form-control-sm"
              value={form.ca_no || ""}
              onChange={(e) => setField("ca_no", e.target.value)}
            />
          </Field>
          <Field label="Start Year" w="fpc-w-sm">
            <input
              className="form-control form-control-sm"
              value={form.fprn_start_yr ?? ""}
              onChange={(e) => setField("fprn_start_yr", e.target.value)}
            />
          </Field>
          <Field label="Incentive Holder" w="fpc-w-sm">
            <select
              className="form-select form-select-sm"
              value={form.incentive_holder_flg || "Y"}
              onChange={(e) => setField("incentive_holder_flg", e.target.value)}
            >
              <option value="Y">Yes</option>
              <option value="N">No</option>
            </select>
          </Field>
          <Field label="Month" w="fpc-w-sm">
            <select
              className="form-select form-select-sm"
              value={String(form.fpen_start_mnth ?? "")}
              onChange={(e) => setField("fpen_start_mnth", e.target.value)}
            >
              <option value="">—</option>
              {MONTH_OPTIONS.map(([value, label]) => (
                <option key={value} value={value}>
                  {label}
                </option>
              ))}
            </select>
          </Field>
        </div>

        <fieldset className="fpc-group">
          <legend>Application Information</legend>
          <div className="fpc-row">
            <Field label="Application No" w="fpc-w-sm">
              <input
                className="form-control form-control-sm"
                value={form.appcn_no || ""}
                onChange={(e) => setField("appcn_no", e.target.value)}
              />
            </Field>
            <Field label="Application Date" w="fpc-w-sm">
              <input
                type="date"
                className="form-control form-control-sm"
                value={form.appcn_date || ""}
                onChange={(e) => setField("appcn_date", e.target.value)}
              />
            </Field>
            <Field label="Applicant Type" w="fpc-w-sm">
              <select
                className="form-select form-select-sm"
                value={String(form.applicant_type ?? "")}
                onChange={(e) => setField("applicant_type", e.target.value)}
              >
                {APPLICANT_TYPE_OPTIONS.map(([value, label]) => (
                  <option key={value || "blank"} value={value}>
                    {label}
                  </option>
                ))}
              </select>
            </Field>
            <Field label="Status" w="fpc-w-sm">
              <select
                className="form-select form-select-sm"
                value={String(form.appcn_status ?? "")}
                onChange={(e) => setField("appcn_status", e.target.value)}
              >
                <option value="">—</option>
                {STATUS_OPTIONS.map(([value, label]) => (
                  <option key={value} value={value}>
                    {label}
                  </option>
                ))}
              </select>
            </Field>
          </div>
          <div className="fpc-row">
            <Field label="Applicant Name" w="fpc-w-half">
              <input
                className="form-control form-control-sm"
                value={form.applicant_name || ""}
                onChange={(e) => setField("applicant_name", e.target.value)}
              />
            </Field>
            <Field label="Last Pension Month" w="fpc-w-sm">
              <select
                className="form-select form-select-sm"
                value={String(form.last_fpen_mth ?? "")}
                onChange={(e) => setField("last_fpen_mth", e.target.value)}
              >
                <option value="">—</option>
                {MONTH_OPTIONS.map(([value, label]) => (
                  <option key={value} value={value}>
                    {label}
                  </option>
                ))}
              </select>
            </Field>
            <Field label="Last Pension Yr" w="fpc-w-xs">
              <input
                className="form-control form-control-sm"
                value={form.last_fpen_yr ?? ""}
                onChange={(e) => setField("last_fpen_yr", e.target.value)}
              />
            </Field>
          </div>
          <div className="fpc-row">
            <Field label="Applicant Address" w="fpc-w-full">
              <input
                className="form-control form-control-sm"
                value={form.applicant_address || ""}
                onChange={(e) => setField("applicant_address", e.target.value)}
              />
            </Field>
          </div>
        </fieldset>

        <div className="fpc-row">
          <Field label="Pensioner Death On" w="fpc-w-sm">
            <input
              type="date"
              className="form-control form-control-sm"
              value={form.dod_emp_pensioner || ""}
              onChange={(e) => setField("dod_emp_pensioner", e.target.value)}
            />
          </Field>
          <Field label="Guardian Relation" w="fpc-w-md">
            <select
              className="form-select form-select-sm"
              value={form.gurdian_relation_cd ?? ""}
              onChange={(e) => {
                const cd = e.target.value;
                setField("gurdian_relation_cd", cd);
                const rel = relations.find(
                  (r) => String(r.relation_cd) === String(cd)
                );
                setField("disp_relation", rel?.relation_desc || "");
              }}
            >
              <option value="">—</option>
              {relations.map((r) => (
                <option key={r.relation_cd} value={r.relation_cd}>
                  {r.relation_desc}
                </option>
              ))}
            </select>
          </Field>
          <Field label="DOB Guardian" w="fpc-w-sm">
            <input
              type="date"
              className="form-control form-control-sm"
              value={form.dob_guardian || ""}
              onChange={(e) => setField("dob_guardian", e.target.value)}
            />
          </Field>
          <Field label="Eligible for Double Family Pension" w="fpc-w-md">
            <select
              className="form-select form-select-sm"
              value={form.double_fpen_eligibility ?? 0}
              onChange={(e) =>
                setField("double_fpen_eligibility", Number(e.target.value))
              }
            >
              <option value={0}>Not Eligible</option>
              <option value={1}>Eligible</option>
            </select>
          </Field>
          <Field label="Double Family Pension Upto" w="fpc-w-sm">
            <input
              type="date"
              className="form-control form-control-sm"
              disabled={!doubleEligible}
              value={form.double_fpen_upto || ""}
              onChange={(e) => setField("double_fpen_upto", e.target.value)}
            />
          </Field>
        </div>

        <div className="fpc-row">
          <Field label="Service Pension Amt" w="fpc-w-sm">
            <input
              className="form-control form-control-sm"
              value={form.service_pension_amt ?? ""}
              onChange={(e) => setField("service_pension_amt", e.target.value)}
            />
          </Field>
          <Field label="Ret CPI" w="fpc-w-xs">
            <input
              className="form-control form-control-sm"
              value={form.retirement_cpi ?? ""}
              onChange={(e) => setField("retirement_cpi", e.target.value)}
            />
          </Field>
          <Field label="Pension Option" w="fpc-w-sm">
            <input
              className="form-control form-control-sm"
              value={form.pension_opt || ""}
              onChange={(e) => setField("pension_opt", e.target.value)}
            />
          </Field>
          <Field label="Scale Cd" w="fpc-w-xs">
            <input
              className="form-control form-control-sm"
              value={form.scale_cd || ""}
              onChange={(e) => setField("scale_cd", e.target.value)}
            />
          </Field>
          <Field label="Last Basic" w="fpc-w-sm">
            <input
              className="form-control form-control-sm"
              value={form.last_basic_at_ret ?? ""}
              onChange={(e) => setField("last_basic_at_ret", e.target.value)}
            />
          </Field>
          <Field label="Base CPI Pay when not matched" w="fpc-w-md">
            <input
              className="form-control form-control-sm"
              value={form.equiv_pay_at_base_cpi ?? ""}
              onChange={(e) =>
                setField("equiv_pay_at_base_cpi", e.target.value)
              }
            />
          </Field>
          <Field label="St. Amt. at Consolidtn CPI" w="fpc-w-md">
            <input
              className="form-control form-control-sm"
              value={form.consolid_cpi_scl_stamt ?? ""}
              onChange={(e) =>
                setField("consolid_cpi_scl_stamt", e.target.value)
              }
            />
          </Field>
        </div>

        <div className="fpc-grid-wrap">
          <div className="fpc-grid-head">
            <span>Family Pensioner Detail</span>
            <button
              type="button"
              className="btn btn-sm btn-outline-secondary"
              onClick={addApplicantRow}
            >
              + Row
            </button>
          </div>
          <table className="fpc-grid">
            <thead>
              <tr>
                <th>Sl No</th>
                <th>Name</th>
                <th>Relation</th>
                <th>DOB</th>
                <th>Disabled</th>
                <th>Bank Code</th>
                <th>Lic Bank Cd</th>
                <th>Account No</th>
              </tr>
            </thead>
            <tbody>
              {(form.applicants || []).length === 0 ? (
                <tr>
                  <td colSpan={8} className="fpc-empty">
                    No detail rows
                  </td>
                </tr>
              ) : (
                form.applicants.map((a, idx) => (
                  <tr key={`${a.sl_no}-${idx}`}>
                    <td className="fpc-sl">{a.sl_no ?? idx + 1}</td>
                    <td>
                      <input
                        className="form-control form-control-sm"
                        value={a.name || ""}
                        onChange={(e) =>
                          setApplicant(idx, "name", e.target.value)
                        }
                      />
                    </td>
                    <td>
                      <select
                        className="form-select form-select-sm"
                        value={a.relation_cd ?? ""}
                        onChange={(e) =>
                          setApplicant(idx, "relation_cd", e.target.value)
                        }
                      >
                        <option value="">—</option>
                        {relations.map((r) => (
                          <option key={r.relation_cd} value={r.relation_cd}>
                            {r.relation_desc}
                          </option>
                        ))}
                      </select>
                    </td>
                    <td>
                      <input
                        type="date"
                        className="form-control form-control-sm"
                        value={a.dob || ""}
                        onChange={(e) =>
                          setApplicant(idx, "dob", e.target.value)
                        }
                      />
                    </td>
                    <td>
                      <select
                        className="form-select form-select-sm"
                        value={a.handicap_flg || "N"}
                        onChange={(e) =>
                          setApplicant(idx, "handicap_flg", e.target.value)
                        }
                      >
                        <option value="N">No</option>
                        <option value="Y">Yes</option>
                      </select>
                    </td>
                    <td>
                      <input
                        className="form-control form-control-sm"
                        value={a.bank_cd || ""}
                        onChange={(e) =>
                          setApplicant(idx, "bank_cd", e.target.value)
                        }
                      />
                    </td>
                    <td>
                      <input
                        className="form-control form-control-sm"
                        value={a.lic_bank_cd || ""}
                        onChange={(e) =>
                          setApplicant(idx, "lic_bank_cd", e.target.value)
                        }
                      />
                    </td>
                    <td>
                      <input
                        className="form-control form-control-sm"
                        value={a.account_no || ""}
                        onChange={(e) =>
                          setApplicant(idx, "account_no", e.target.value)
                        }
                      />
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Hidden print root — used after Save / Print Report */}
      <div className="d-none">
        <FamilyPensionProposalPrint report={report} />
      </div>
    </div>
  );
}
