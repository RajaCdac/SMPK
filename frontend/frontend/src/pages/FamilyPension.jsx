import { useCallback, useEffect, useRef, useState } from "react";
import { useSearchParams } from "react-router-dom";
import API from "../services/Api";
import FamilyPensionProposalPrint from "../components/FamilyPensionProposalPrint";
import FamilyPensionBillPrint from "../components/FamilyPensionBillPrint";
import { printPensionReport } from "../utils/pensionReportPrint";
import "../styles/FamilyPensionClaim.css";
import "../styles/FamilyPensionProposalReport.css";
import "../styles/pension-report-print.css";
import "../styles/FamilyPensionBillPrint.css";

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

function billYearChoices(center) {
  const y = Number(center) || new Date().getFullYear();
  const years = [];
  for (let i = y + 1; i >= y - 20; i -= 1) years.push(String(i));
  if (!years.includes(String(center))) years.unshift(String(center));
  return years;
}

/** FI_PN_MD_FPEN_APPCN.FPEN_CLOS_REASON — N/E/M/P from claim form; R from UNMARR form. */
const FPEN_CLOS_REASON_OPTIONS = [
  ["", ""],
  ["N", "Normal Closure - Exceeding 25 Years"],
  ["E", "Family Pensioner Expired"],
  ["M", "Marriage"],
  ["P", "Emploment"],
];

const FPEN_CLOS_REASON_SUCCESSION = [
  ...FPEN_CLOS_REASON_OPTIONS,
  ["R", "Remarriage or starts earning beyond income criteria"],
];

/** FI_PN_MD_FPEN_APPCN.RELIEF_TAG — blank + YES/NO from form. */
const RELIEF_TAG_OPTIONS = [
  ["", ""],
  ["Y", "YES"],
  ["N", "NO"],
];

/** FI_PN_MD_FPEN_APPCN.STATUS_FLG — marital: blank + Single/Married from form. */
const MARITAL_STATUS_OPTIONS = [
  ["", ""],
  ["S", "Single"],
  ["M", "Married"],
];

const STATUS_OPTIONS = [
  ["1", "VALID"],
  ["0", "INVALID"],
];

/** fi_xx_mh_emp_per.STATUS — Personal Information (claim gate). */
const EMP_PERSONAL_STATUS_FALLBACK = [
  ["RE", "RE — Regular Emp"],
  ["PE", "PE — Probationary Emp"],
  ["TE", "TE — Trainee Emp"],
  ["DW", "DW — Deputationist WB"],
  ["DC", "DC — Deputationist Central"],
  ["PN", "PN — Pensioner"],
  ["FP", "FP — Family Pensioner"],
  ["EG", "EG — Exgratia holder"],
];

/**
 * Oracle FI_PN_MH_FPENSION_CLAIM_E / FI_PN_MH_UNMARR_CLAIM_E list values
 * (same APPLICANT_TYPE column). Unmarr form adds 8–10.
 */
const APPLICANT_TYPE_ALL = [
  ["", "—"],
  ["0", "Widow"],
  ["1", "Widower"],
  ["2", "Guardian"],
  ["3", "Son"],
  ["4", "Daughter"],
  ["5", "Brother"],
  ["6", "Sister"],
  ["7", "Others"],
  ["8", "Divorced daughter"],
  ["9", "Widowed daughter"],
  ["10", "Unmarried daughter"],
];

const APPLICANT_TYPE_NORMAL = APPLICANT_TYPE_ALL.filter(
  ([value]) => value === "" || Number(value) <= 7
);

const APPLICANT_TYPE_SUCCESSION = APPLICANT_TYPE_ALL.filter(([value]) =>
  ["", "2", "4", "8", "9", "10"].includes(value)
);

const SUCCESSION_APPLICANT_TYPES = new Set(["8", "9", "10"]);

function applicantTypeOptions(kind, current) {
  const base =
    kind === "succession" ? APPLICANT_TYPE_SUCCESSION : APPLICANT_TYPE_NORMAL;
  const cur = String(current ?? "");
  if (cur && !base.some(([value]) => value === cur)) {
    const extra = APPLICANT_TYPE_ALL.find(([value]) => value === cur);
    return extra ? [...base, extra] : [...base, [cur, cur]];
  }
  return base;
}

function closReasonOptions(kind) {
  return kind === "succession"
    ? FPEN_CLOS_REASON_SUCCESSION
    : FPEN_CLOS_REASON_OPTIONS;
}

function inferClaimKind(claim) {
  const t = String(claim?.clm_ca_type || "")
    .toUpperCase()
    .slice(0, 2);
  if (t === "CE") return "succession";
  if (SUCCESSION_APPLICANT_TYPES.has(String(claim?.applicant_type ?? ""))) {
    return "succession";
  }
  return "normal";
}

function parseKindParam(value) {
  const t = String(value || "")
    .trim()
    .toLowerCase();
  if (t === "succession" || t === "daughter") return "succession";
  if (t === "normal") return "normal";
  return "";
}

function laterIso(a, b) {
  const x = String(a || "").slice(0, 10);
  const y = String(b || "").slice(0, 10);
  if (!x) return y;
  if (!y) return x;
  return x >= y ? x : y;
}

function monthYearFromIso(iso) {
  const text = String(iso || "").slice(0, 10);
  const parts = text.split("-");
  if (parts.length < 2 || !parts[0] || !parts[1]) return null;
  return { month: String(Number(parts[1])), year: parts[0] };
}

function applySuccessionStartDates(prev) {
  const later = laterIso(prev.dod_emp_pensioner, prev.emp_dod);
  const my = monthYearFromIso(later);
  if (!my) return prev;
  const applicants = [...(prev.applicants || [])];
  if (applicants[0]) {
    applicants[0] = {
      ...applicants[0],
      fpen_start_mnth: my.month,
      fprn_start_yr: my.year,
    };
  }
  return {
    ...prev,
    fpen_start_mnth: my.month,
    fprn_start_yr: my.year,
    applicants,
  };
}

/** Oracle PENSION_OPT: G = Govt. Line, P = Port Line */
const PENSION_OPT_OPTIONS = [
  ["G", "Govt. Line"],
  ["P", "Port Line"],
];

/** fi_pn_mh_familypensioner.APP_CLASS / claim CLASS */
const EMP_CLASS_OPTIONS = [
  ["", "—"],
  ["1", "1"],
  ["2", "2"],
  ["3", "3"],
  ["4", "4"],
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
    emp_birth_dt: "",
    separation_dt: "",
    class_cd: "",
    exp_ret_dt: "",
    separation_type: "",
    applicant_type: "",
    applicant_name: "",
    applicant_address: "",
    dod_emp_pensioner: "",
    emp_dod: "",
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
    handicap_flg: "N",
    bank_cd: "",
    bank_id: "",
    lic_bank_cd: "",
    account_no: "",
    bank_name: "",
    bank_branch: "",
    relief_tag: "",
    fpen_active: 1,
    fpen_clos_reason: "",
    fpen_inactive_from_dt: "",
    status_flg: "",
    fprn_start_yr: "",
    fpen_start_mnth: "",
    impl_yr: "",
    impl_mnth: "",
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

/** Oracle-style add months (clamp day to month end). */
function addMonthsIso(isoDate, months) {
  if (!isoDate) return "";
  const parts = String(isoDate).slice(0, 10).split("-").map(Number);
  if (parts.length < 3 || !parts[0]) return "";
  const [y, m, d] = parts;
  const total = (m - 1) + Number(months);
  const ny = y + Math.floor(total / 12);
  const nm = (total % 12 + 12) % 12;
  const last = new Date(ny, nm + 1, 0).getDate();
  const day = Math.min(d, last);
  const mm = String(nm + 1).padStart(2, "0");
  const dd = String(day).padStart(2, "0");
  return `${ny}-${mm}-${dd}`;
}

/**
 * Normal: MIN(sep/ret + 7y, DOB + age) − 1 day.
 * Die-in-harness (sep type DT and sep < exp ret): straight sep + 10y − 1 day
 * (sep is next day after death; no age cap).
 * Class I/II → age 67 years; else age 65 years (normal path only).
 * Returns yyyy-mm-dd or "".
 */
function ageLimitMonthsForClass(classCd) {
  const n = Number(classCd);
  if (Number.isFinite(n) && (n === 1 || n === 2)) return 804;
  const t = String(classCd ?? "")
    .trim()
    .toUpperCase();
  if (["1", "2", "I", "II", "CLASS 1", "CLASS 2", "CLASS I", "CLASS II"].includes(t)) {
    return 804;
  }
  return 780;
}

function isDieInHarness(sepType, separationDt, expRetDt) {
  const st = String(sepType ?? "")
    .trim()
    .toUpperCase();
  if (!["DT", "DE", "D", "DEATH"].includes(st)) return false;
  if (!separationDt || !expRetDt) return false;
  return String(separationDt).slice(0, 10) < String(expRetDt).slice(0, 10);
}

function minusOneDayIso(iso) {
  if (!iso) return "";
  const d = new Date(`${iso}T00:00:00`);
  if (Number.isNaN(d.getTime())) return iso;
  d.setDate(d.getDate() - 1);
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  return `${y}-${m}-${day}`;
}

function computeDoubleFpenUpto(
  separationDt,
  empBirthDt,
  classCd,
  dodFallback,
  sepType,
  expRetDt
) {
  const dih = isDieInHarness(sepType, separationDt, expRetDt);
  if (dih) {
    if (!separationDt) return "";
    // Straight 10 years from sep (day after death); no age cap
    return minusOneDayIso(addMonthsIso(separationDt, 120));
  }
  const base = separationDt || dodFallback || "";
  if (!base) return "";
  let raw = addMonthsIso(base, 84);
  if (empBirthDt) {
    const ageLim = addMonthsIso(empBirthDt, ageLimitMonthsForClass(classCd));
    if (ageLim && (!raw || ageLim < raw)) raw = ageLim;
  }
  if (!raw) return "";
  return minusOneDayIso(raw);
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
  const [searchParams, setSearchParams] = useSearchParams();
  const urlEmpLoadedRef = useRef(false);
  const urlEmp = (searchParams.get("emp") || "").trim();
  const urlKind = parseKindParam(searchParams.get("kind"));
  const [form, setForm] = useState(emptyClaim);
  const [relations, setRelations] = useState([]);
  const [matches, setMatches] = useState([]);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [isNewMode, setIsNewMode] = useState(false);
  const [claimKind, setClaimKind] = useState(
    urlEmp ? "normal" : urlKind || null
  );
  const [showKindChooser, setShowKindChooser] = useState(
    !urlEmp && !urlKind
  );
  const [showStatusGate, setShowStatusGate] = useState(Boolean(urlEmp));
  const [statusGateEmp, setStatusGateEmp] = useState(urlEmp || "");
  const [statusGateInfo, setStatusGateInfo] = useState(null);
  const [statusGateSelected, setStatusGateSelected] = useState("");
  const [statusGateLoading, setStatusGateLoading] = useState(false);
  const [statusGateSaving, setStatusGateSaving] = useState(false);
  const [statusGateError, setStatusGateError] = useState("");
  const [statusGateMessage, setStatusGateMessage] = useState("");
  const [prefilling, setPrefilling] = useState(false);
  const [report, setReport] = useState(null);
  const [reportLoading, setReportLoading] = useState(false);
  const [bill, setBill] = useState(null);
  const [generatingFp, setGeneratingFp] = useState(false);
  const [generatingBill, setGeneratingBill] = useState(false);
  const [monthlyMonth, setMonthlyMonth] = useState(() =>
    String(new Date().getMonth() + 1)
  );
  const [monthlyYear, setMonthlyYear] = useState(() =>
    String(new Date().getFullYear())
  );
  const [lastBillType, setLastBillType] = useState("N");
  const savingRef = useRef(false);
  const autoPrintRef = useRef(false);
  const autoPrintBillRef = useRef(false);

  useEffect(() => {
    if (autoPrintRef.current && report?.pages?.length) {
      autoPrintRef.current = false;
      const t = setTimeout(() => printPensionReport(null, { selector: ".fp-proposal-print" }), 50);
      return () => clearTimeout(t);
    }
  }, [report]);

  useEffect(() => {
    if (autoPrintBillRef.current && bill?.bill_no) {
      autoPrintBillRef.current = false;
      const t = setTimeout(
        () => printPensionReport(null, { selector: ".fp-bill-print" }),
        80
      );
      return () => clearTimeout(t);
    }
  }, [bill]);

  useEffect(() => {
    API.get("family-pension/relations/")
      .then(({ data }) => setRelations(data?.results || []))
      .catch(() => setRelations([]));
  }, []);

  // Auto Double FP Upto (DIH: sep+10y; else MIN(sep+7y, DOB age); −1 day)
  useEffect(() => {
    const eligible = Number(form.double_fpen_eligibility) === 1;
    if (!eligible) {
      setForm((prev) => {
        if (Number(prev.double_fpen_eligibility) === 1) return prev;
        if (!prev.double_fpen_upto) return prev;
        return { ...prev, double_fpen_upto: "" };
      });
      return;
    }
    setForm((prev) => {
      if (Number(prev.double_fpen_eligibility) !== 1) return prev;
      const next =
        computeDoubleFpenUpto(
          prev.separation_dt,
          prev.emp_birth_dt,
          prev.class_cd,
          prev.dod_emp_pensioner,
          prev.separation_type,
          prev.exp_ret_dt
        ) || "";
      if (next === (prev.double_fpen_upto || "")) return prev;
      return { ...prev, double_fpen_upto: next };
    });
  }, [
    form.double_fpen_eligibility,
    form.separation_dt,
    form.emp_birth_dt,
    form.class_cd,
    form.dod_emp_pensioner,
    form.separation_type,
    form.exp_ret_dt,
  ]);

  const setField = (key, value) => {
    setForm((prev) => {
      const next = { ...prev, [key]: value };
      if (key === "dod_emp_pensioner" || key === "emp_dod") {
        const succession =
          claimKind === "succession" ||
          String(next.clm_ca_type || "")
            .toUpperCase()
            .slice(0, 2) === "CE" ||
          Boolean(next.emp_dod);
        if (succession) return applySuccessionStartDates(next);
      }
      return next;
    });
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
      if (key === "bank_cd") {
        applicants[index].bank_name = "";
        applicants[index].bank_branch = "";
        applicants[index].bank_id = "";
      }
      if (key === "lic_bank_cd") {
        applicants[index].lic_bank_name = "";
        applicants[index].lic_bank_branch = "";
      }
      return { ...prev, applicants };
    });
  };

  const resolveApplicantBank = async (index, field = "bank_cd") => {
    const code = String(form.applicants?.[index]?.[field] || "").trim();
    setForm((prev) => {
      const applicants = [...(prev.applicants || [])];
      if (!applicants[index]) return prev;
      if (!code) {
        if (field === "bank_cd") {
          applicants[index] = {
            ...applicants[index],
            bank_name: "",
            bank_branch: "",
            bank_id: "",
          };
        }
        return { ...prev, applicants };
      }
      return prev;
    });
    if (!code) return;
    try {
      const { data } = await API.get("family-pension/bank-lookup/", {
        params: { bank_cd: code },
      });
      setForm((prev) => {
        const applicants = [...(prev.applicants || [])];
        if (!applicants[index]) return prev;
        if (field === "lic_bank_cd") {
          applicants[index] = {
            ...applicants[index],
            lic_bank_name: data?.found ? data.bank_name || "" : "",
            lic_bank_branch: data?.found ? data.bank_branch || "" : "",
          };
        } else {
          applicants[index] = {
            ...applicants[index],
            bank_name: data?.found ? data.bank_name || "" : "",
            bank_branch: data?.found ? data.bank_branch || "" : "",
            bank_id: data?.found ? data.bank_id || "" : "",
          };
        }
        return { ...prev, applicants };
      });
      if (!data?.found) {
        setError(`Bank code ${code} not found in bank master`);
      } else {
        setError("");
      }
    } catch (err) {
      setError(apiErrorMessage(err, "Bank lookup failed"));
    }
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
    setClaimKind(inferClaimKind(claim));
    setShowKindChooser(false);
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

  const prefillFromEmp = async (empValue, opts = {}) => {
    const emp_cd = String(empValue ?? form.emp_cd ?? "").trim();
    if (!emp_cd) {
      setError("Enter Emp Code");
      return;
    }
    const asNew = Boolean(opts.asNew ?? isNewMode);

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
      setForm((prev) => {
        const succession =
          claimKind === "succession" ||
          String(prev.clm_ca_type || "")
            .toUpperCase()
            .slice(0, 2) === "CE";
        const next = {
          ...prev,
          ...prefill,
          // Keep blank Claim ID while creating a new claim
          clmca_id: asNew ? "" : prev.clmca_id,
          emp_cd,
          // Always blank for user input on new/search prefill
          dod_emp_pensioner: "",
          emp_dod: prefill.emp_dod || prev.emp_dod || "",
          // Ret CPI only when prefill found it; otherwise blank (no inventing)
          retirement_cpi:
            prefill.retirement_cpi != null && prefill.retirement_cpi !== ""
              ? prefill.retirement_cpi
              : "",
          // Default start / last pension period = current month-year
          fpen_start_mnth: prefill.fpen_start_mnth ?? month,
          fprn_start_yr: prefill.fprn_start_yr ?? year,
          last_fpen_mth: prefill.last_fpen_mth ?? month,
          last_fpen_yr: prefill.last_fpen_yr ?? year,
          last_basic_at_ret: asNew ? "" : prev.last_basic_at_ret,
          applicants: prev.applicants?.length
            ? prev.applicants
            : [emptyApplicantRow(1)],
        };
        if (succession) {
          next.clm_ca_type = prev.clm_ca_type || "CE";
          next.double_fpen_eligibility = 0;
          next.double_fpen_upto = "";
          return applySuccessionStartDates(next);
        }
        return next;
      });
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

  // Die-in-Harness / deep link: /die-in-harness/claim?emp=… or ?kind=
  useEffect(() => {
    if (urlEmpLoadedRef.current) return;
    const fromUrl = (searchParams.get("emp") || "").trim();
    const kindFromUrl = parseKindParam(searchParams.get("kind"));
    if (fromUrl) {
      urlEmpLoadedRef.current = true;
      setClaimKind("normal");
      setShowKindChooser(false);
      setShowStatusGate(true);
      setStatusGateEmp(fromUrl);
      setSearchParams({}, { replace: true });
      return;
    }
    if (kindFromUrl) {
      urlEmpLoadedRef.current = true;
      if (kindFromUrl === "normal") {
        setClaimKind("normal");
        setShowKindChooser(false);
        setShowStatusGate(true);
      } else {
        startNewClaim(kindFromUrl);
      }
      setSearchParams({}, { replace: true });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps -- one-shot URL prefill
  }, [searchParams, setSearchParams]);

  const loadStatusGate = async (empValue) => {
    const emp_cd = String(empValue ?? statusGateEmp ?? "").trim();
    if (!emp_cd) {
      setStatusGateError("Enter Emp Code");
      return;
    }
    setStatusGateLoading(true);
    setStatusGateError("");
    setStatusGateMessage("");
    try {
      const { data } = await API.get("family-pension/esr/personal/", {
        params: { emp_cd, status_check: 1 },
      });
      if (data?.error) {
        setStatusGateInfo(null);
        setStatusGateError(data.error);
        return;
      }
      const current = String(data.status || "").toUpperCase();
      setStatusGateInfo(data);
      setStatusGateEmp(data.emp_cd || emp_cd);
      // Client rule: Regular Emp → change to Pensioner
      setStatusGateSelected(current === "RE" ? "PN" : current || "PN");
      setStatusGateMessage(
        current === "RE"
          ? "Status is Regular Emp — change to Pensioner before opening the claim form."
          : `Current status: ${data.status_label || current || "—"}`
      );
    } catch (err) {
      setStatusGateInfo(null);
      setStatusGateError(
        apiErrorMessage(err, "Failed to load Personal Information Status")
      );
    } finally {
      setStatusGateLoading(false);
    }
  };

  useEffect(() => {
    if (!showStatusGate) return;
    const emp = String(statusGateEmp || "").trim();
    if (!emp || statusGateInfo?.emp_cd === emp) return;
    loadStatusGate(emp);
    // eslint-disable-next-line react-hooks/exhaustive-deps -- load once when gate opens with emp
  }, [showStatusGate]);

  const saveStatusGate = async () => {
    const emp_cd = String(statusGateEmp || "").trim();
    const status = String(statusGateSelected || "").trim().toUpperCase();
    if (!emp_cd) {
      setStatusGateError("Enter Emp Code");
      return false;
    }
    if (!status) {
      setStatusGateError("Select Personal Information Status");
      return false;
    }
    setStatusGateSaving(true);
    setStatusGateError("");
    try {
      const { data } = await API.post("family-pension/esr/personal/", {
        emp_cd,
        status,
      });
      if (data?.error) {
        setStatusGateError(data.error);
        return false;
      }
      setStatusGateInfo(data);
      setStatusGateSelected(String(data.status || status).toUpperCase());
      setStatusGateMessage(data.message || `Status saved as ${status}`);
      return true;
    } catch (err) {
      setStatusGateError(
        apiErrorMessage(err, "Failed to update Personal Information Status")
      );
      return false;
    } finally {
      setStatusGateSaving(false);
    }
  };

  const continueFromStatusGate = async () => {
    const emp_cd = String(statusGateEmp || "").trim();
    if (!emp_cd) {
      setStatusGateError("Enter Emp Code");
      return;
    }
    if (!statusGateInfo) {
      await loadStatusGate(emp_cd);
      return;
    }
    const current = String(statusGateInfo.status || "").toUpperCase();
    const selected = String(statusGateSelected || "").toUpperCase();
    if (selected && selected !== current) {
      const ok = await saveStatusGate();
      if (!ok) return;
    } else if (current === "RE") {
      setStatusGateError(
        "Change Personal Information Status from Regular Emp to Pensioner, then Save / Continue."
      );
      return;
    }

    const finalStatus = String(
      statusGateSelected || statusGateInfo?.status || ""
    ).toUpperCase();
    if (finalStatus === "RE") {
      setStatusGateError(
        "Status must not remain Regular Emp. Set to Pensioner before claim."
      );
      return;
    }

    setShowStatusGate(false);
    startNewClaim("normal", { emp_cd, skipStatusGate: true });
  };

  const startNewClaim = (kind, opts = {}) => {
    if (kind === "normal" && !opts.skipStatusGate) {
      setClaimKind("normal");
      setShowKindChooser(false);
      setShowStatusGate(true);
      setStatusGateInfo(null);
      setStatusGateSelected("");
      setStatusGateError("");
      setStatusGateMessage("");
      if (opts.emp_cd) setStatusGateEmp(String(opts.emp_cd).trim());
      return;
    }
    const blank = emptyClaim();
    blank.applicants = [emptyApplicantRow(1)];
    if (kind === "succession") {
      blank.clm_ca_type = "CE";
      blank.double_fpen_eligibility = 0;
      blank.double_fpen_upto = "";
    } else {
      blank.clm_ca_type = "CM";
    }
    const emp_cd = String(opts.emp_cd || "").trim();
    if (emp_cd) blank.emp_cd = emp_cd;
    setForm(blank);
    setMatches([]);
    setIsNewMode(true);
    setClaimKind(kind);
    setShowKindChooser(false);
    setShowStatusGate(false);
    setError("");
    setMessage(
      kind === "succession"
        ? "New succession claim — enter Emp Code and press Enter to prefill. Emp Dod fills automatically; enter family-pensioner death."
        : emp_cd
          ? `New claim for ${emp_cd} — prefilling…`
          : "New claim — enter Emp Code and press Enter to prefill"
    );
    if (emp_cd && kind === "normal") {
      prefillFromEmp(emp_cd, { asNew: true });
    }
  };

  const handleNew = () => {
    setShowStatusGate(false);
    setShowKindChooser(true);
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

  const formatGenerateMessage = (data, regenerated = false) => {
    const fmtMoney = (v) => {
      if (v == null || v === "") return "—";
      const n = Number(v);
      if (Number.isNaN(n)) return String(v);
      return n.toLocaleString("en-IN", {
        minimumFractionDigits: 0,
        maximumFractionDigits: 2,
      });
    };
    const bill = data?.bills?.[0] || {};
    const dbl = data?.double_fpension || {};
    const m1 = data?.methodology1 || {};
    const verb = regenerated ? "regenerated" : "generated";
    const parts = [
      `First FP ${verb}.`,
      `Bill: ${bill.fam_fmpen_id || "—"}.`,
      `Normal (single) FP ₹${fmtMoney(dbl.single_rate ?? m1.selected_amount ?? bill.single_rate)}.`,
    ];
    if (dbl.eligible) {
      parts.push(
        `Full/double pension ₹${fmtMoney(dbl.double_rate)} up to ${dbl.double_fpen_upto || "—"}.`
      );
      // parts.push(
      //   `First period ${dbl.period_start || "—"} → ${dbl.period_end || "—"}: ` +
      //     `${dbl.double_days || 0} day(s) full pension + ${dbl.single_days || 0} day(s) normal FP ` +
      //     `(payable ₹${fmtMoney(dbl.payable_fp_amt ?? bill.fpension_amt)}).`
      // );
    } else {
      parts.push(
        `Payable ₹${fmtMoney(dbl.payable_fp_amt ?? bill.fpension_amt)} ` +
          `(M1 CPI ${m1.process_cpi ?? "—"}).`
      );
    }
    if (data?.dcr_gratuity?.amount != null) {
      parts.push(`Gratuity ₹${fmtMoney(data.dcr_gratuity.amount)}.`);
    }
    return parts.join(" ");
  };

  const handleGenerateFirstFp = async () => {
    const clmca_id = String(form.clmca_id || "").trim();
    if (!clmca_id) {
      setError("Save or load a claim first (Claim ID required)");
      return;
    }
    const isDouble = Number(form.double_fpen_eligibility) === 1;
    if (
      !window.confirm(
        `Generate First Family Pension (type N) for claim ${clmca_id}?\n` +
          "Amount will be calculated using Methodology-1" +
          (isDouble ? " + double/full pension rules." : ".")
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
            setMessage(formatGenerateMessage(res2.data, true));
            return;
          }
        }
        setError(data.error);
        return;
      }
      setMessage(formatGenerateMessage(data, false));
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
            setMessage(formatGenerateMessage(res2.data, true));
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

  const openBillPrint = (billData, { autoPrint = true } = {}) => {
    autoPrintBillRef.current = !!autoPrint;
    setBill(billData);
    const t = String(billData?.bill_type || "").toUpperCase();
    if (t) setLastBillType(t);
    if (billData?.source === "existing") {
      setMessage(
        `Bill ${billData.bill_no} · Earned ₹${billData.total_amt_earned}` +
          (billData.total_amt_deducted
            ? ` · Deducted ₹${billData.total_amt_deducted}`
            : "")
      );
    } else {
      setMessage(
        `Bill generated: ${billData.bill_no} · Earned ₹${billData.total_amt_earned}` +
          (billData.total_amt_deducted
            ? ` · Deducted ₹${billData.total_amt_deducted}`
            : "") +
          ` · ${billData.lines?.length || 0} first-month line(s)`
      );
    }
  };

  const handlePrintBill = async () => {
    const clmca_id = String(form.clmca_id || "").trim();
    if (!clmca_id && !bill?.bill_no) {
      setError("Load a claim or generate a bill first");
      return;
    }
    // Already have print payload for latest bill → just print
    if (bill?.print && bill?.bill_no) {
      printPensionReport(null, { selector: ".fp-bill-print" });
      return;
    }
    setGeneratingBill(true);
    setError("");
    try {
      const { data } = await API.get("family-pension/bill-print/", {
        params: {
          clmca_id: clmca_id || undefined,
          emp_cd: form.emp_cd || undefined,
          bill_no: bill?.bill_no || undefined,
          bill_type: lastBillType || undefined,
          month: monthlyMonth || undefined,
          year: monthlyYear || undefined,
        },
      });
      if (data?.error) {
        setError(data.error);
        return;
      }
      openBillPrint(data, { autoPrint: true });
    } catch (err) {
      setError(apiErrorMessage(err, "Could not load bill for print"));
    } finally {
      setGeneratingBill(false);
    }
  };

  const runGenerateBill = async ({ billType, month, year, confirmText }) => {
    const clmca_id = String(form.clmca_id || "").trim();
    const emp_cd = String(form.emp_cd || "").trim();
    if (!clmca_id) {
      setError("Save or load a claim first (Claim ID required)");
      return;
    }
    if (!window.confirm(confirmText)) {
      return;
    }
    const body = {
      clmca_id,
      emp_cd: emp_cd || undefined,
      month: month || undefined,
      year: year || undefined,
      bill_type: billType,
      regenerate: false,
    };
    const printParams = {
      clmca_id,
      emp_cd: emp_cd || undefined,
      bill_type: billType,
      month: month || undefined,
      year: year || undefined,
    };
    setGeneratingBill(true);
    setError("");
    setMessage("");
    try {
      const { data } = await API.post("family-pension/generate-bill/", body);
      if (data?.error) {
        if (String(data.error).toLowerCase().includes("already billed")) {
          if (
            window.confirm(
              `${data.error}\n\nRegenerate and issue a new PFN bill?`
            )
          ) {
            const res2 = await API.post("family-pension/generate-bill/", {
              ...body,
              regenerate: true,
            });
            if (res2.data?.error) {
              setError(res2.data.error);
              return;
            }
            openBillPrint(res2.data);
            return;
          }
          if (window.confirm("Print the existing PFN bill for this claim?")) {
            const resP = await API.get("family-pension/bill-print/", {
              params: printParams,
            });
            openBillPrint(resP.data);
          }
          return;
        }
        setError(data.error);
        return;
      }
      openBillPrint(data);
    } catch (err) {
      const msg = apiErrorMessage(err, "Bill generation failed");
      if (String(msg).toLowerCase().includes("already billed")) {
        if (window.confirm(`${msg}\n\nRegenerate and issue a new PFN bill?`)) {
          try {
            const res2 = await API.post("family-pension/generate-bill/", {
              ...body,
              regenerate: true,
            });
            openBillPrint(res2.data);
            return;
          } catch (err2) {
            setError(apiErrorMessage(err2, "Bill regenerate failed"));
            return;
          }
        }
        try {
          if (window.confirm("Print the existing PFN bill for this claim?")) {
            const resP = await API.get("family-pension/bill-print/", {
              params: printParams,
            });
            openBillPrint(resP.data);
            return;
          }
        } catch {
          /* fall through */
        }
      }
      setError(msg);
    } finally {
      setGeneratingBill(false);
    }
  };

  const handleGenerateBill = () => {
    const clmca_id = String(form.clmca_id || "").trim();
    const emp_cd = String(form.emp_cd || "").trim();
    return runGenerateBill({
      billType: "N",
      month: monthlyMonth,
      year: monthlyYear,
      confirmText:
        `Generate First Family Pension Bill (disbursement) for claim ${clmca_id}` +
        (emp_cd ? ` / emp ${emp_cd}` : "") +
        ` for ${monthlyMonth}/${monthlyYear}?` +
        "\nFirst FP is the monthly rate. This bill pays family pension + DA" +
        " from the effective date through this month (processing delay)," +
        " holding the current month until month-end.\n" +
        "Landscape bill will print after generate.",
    });
  };

  const handleGenerateMonthlyBill = () => {
    const clmca_id = String(form.clmca_id || "").trim();
    const emp_cd = String(form.emp_cd || "").trim();
    return runGenerateBill({
      billType: "M",
      month: monthlyMonth,
      year: monthlyYear,
      confirmText:
        `Generate Monthly Family Pension Bill (PFN) for claim ${clmca_id}` +
        (emp_cd ? ` / emp ${emp_cd}` : "") +
        ` for ${monthlyMonth}/${monthlyYear}?` +
        "\nIf this is the first disbursement, unpaid months from WEF are included." +
        " Later months are the current month only.\n" +
        "Landscape bill will print after generate.",
    });
  };

  const doubleEligible = Number(form.double_fpen_eligibility) === 1;
  const claimIdReadOnly = isNewMode;
  const isSuccession = claimKind === "succession";
  const closReasons = closReasonOptions(claimKind);

  return (
    <div className="container-fluid mt-2 px-2 px-md-3 fpc-page w-100">
      {showKindChooser ? (
        <div className="fpc-kind-overlay" role="dialog" aria-modal="true">
          <div className="fpc-kind-card">
            <h2>Start Claim Application</h2>
            <p>
              Choose who this claim is for. Amount generation stays the same
              after save.
            </p>
            <div className="fpc-kind-choices">
              <button
                type="button"
                className="fpc-kind-btn"
                onClick={() => startNewClaim("normal")}
              >
                <strong>Normal family pensioner</strong>
                <span>Widow / first claimant — current claim entry</span>
              </button>
              <button
                type="button"
                className="fpc-kind-btn"
                onClick={() => startNewClaim("succession")}
              >
                <strong>Unmarried / widowed / divorced daughter</strong>
                <span>
                  After the family pensioner died — succession (claim type CE)
                </span>
              </button>
            </div>
            <button
              type="button"
              className="btn btn-link btn-sm fpc-kind-skip"
              onClick={() => setShowKindChooser(false)}
            >
              Load an existing claim instead
            </button>
          </div>
        </div>
      ) : null}

      {showStatusGate ? (
        <div className="fpc-kind-overlay" role="dialog" aria-modal="true">
          <div className="fpc-kind-card fpc-status-gate-card">
            <h2>Personal Information Status</h2>
            <p>
              Before opening the claim form, check ESR Personal Status. If it
              shows Regular Emp, change it to Pensioner.
            </p>
            <div className="fpc-status-gate-row">
              <label className="fpc-label" htmlFor="fpc-status-emp">
                Emp Code
              </label>
              <div className="fpc-status-gate-emp">
                <input
                  id="fpc-status-emp"
                  className="form-control form-control-sm"
                  value={statusGateEmp}
                  maxLength={5}
                  onChange={(e) => {
                    setStatusGateEmp(e.target.value);
                    setStatusGateInfo(null);
                    setStatusGateMessage("");
                  }}
                  onKeyDown={(e) => {
                    if (e.key === "Enter") {
                      e.preventDefault();
                      loadStatusGate(e.currentTarget.value);
                    }
                  }}
                />
                <button
                  type="button"
                  className="btn btn-sm btn-primary"
                  disabled={statusGateLoading || statusGateSaving}
                  onClick={() => loadStatusGate()}
                >
                  {statusGateLoading ? "Loading…" : "Lookup"}
                </button>
              </div>
            </div>

            {statusGateInfo ? (
              <>
                <div className="fpc-status-gate-meta">
                  <div>
                    <span className="fpc-label">Employee</span>
                    <strong>
                      {statusGateInfo.display_name || statusGateInfo.emp_cd}
                    </strong>
                  </div>
                  <div>
                    <span className="fpc-label">Current status</span>
                    <strong>
                      {statusGateInfo.status_label ||
                        statusGateInfo.status ||
                        "—"}
                    </strong>
                  </div>
                </div>
                <div className="fpc-status-gate-row">
                  <label className="fpc-label" htmlFor="fpc-status-select">
                    Set status to
                  </label>
                  <select
                    id="fpc-status-select"
                    className="form-select form-select-sm"
                    value={statusGateSelected}
                    onChange={(e) => setStatusGateSelected(e.target.value)}
                  >
                    {(
                      statusGateInfo.status_options ||
                      EMP_PERSONAL_STATUS_FALLBACK
                    ).map(([code, label]) => (
                      <option key={code} value={code}>
                        {label}
                      </option>
                    ))}
                  </select>
                </div>
                {statusGateInfo.suggest_pensioner ||
                String(statusGateInfo.status || "").toUpperCase() === "RE" ? (
                  <p className="fpc-status-gate-hint">
                    Recommended: change <strong>Regular Emp</strong> →{" "}
                    <strong>Pensioner (PN)</strong>.
                  </p>
                ) : null}
              </>
            ) : null}

            {statusGateError ? (
              <div className="alert alert-danger py-2 mb-2" role="alert">
                {statusGateError}
              </div>
            ) : null}
            {statusGateMessage && !statusGateError ? (
              <div className="alert alert-info py-2 mb-2" role="status">
                {statusGateMessage}
              </div>
            ) : null}

            <div className="fpc-status-gate-actions">
              <button
                type="button"
                className="btn btn-sm btn-outline-secondary"
                disabled={statusGateSaving}
                onClick={() => {
                  setShowStatusGate(false);
                  setShowKindChooser(true);
                }}
              >
                Back
              </button>
              <button
                type="button"
                className="btn btn-sm btn-outline-primary"
                disabled={
                  statusGateSaving || statusGateLoading || !statusGateInfo
                }
                onClick={saveStatusGate}
              >
                {statusGateSaving ? "Saving…" : "Save Status"}
              </button>
              <button
                type="button"
                className="btn btn-sm btn-success"
                disabled={
                  statusGateSaving || statusGateLoading || !statusGateInfo
                }
                onClick={continueFromStatusGate}
              >
                Continue to Claim
              </button>
            </div>
          </div>
        </div>
      ) : null}

      <div className="fpc-title-bar">
        {claimKind === "succession"
          ? "FAMILY PENSION CLAIM — Unmarried / widowed / divorced daughter"
          : "FAMILY PENSION CLAIM"}
      </div>

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
                loading ||
                saving ||
                reportLoading ||
                generatingBill ||
                (!form.clmca_id && !form.emp_cd)
              }
              onClick={() => loadProposalReport({}, { autoPrint: true })}
            >
              {reportLoading ? "Report…" : "Print Report"}
            </button>
            <button
              type="button"
              className="btn btn-sm btn-info text-white"
              disabled={
                loading ||
                saving ||
                generatingFp ||
                generatingBill ||
                reportLoading ||
                !form.clmca_id
              }
              onClick={handleGenerateBill}
              title="Generate first family pension PFN bill for the disbursement month (unpaid period from WEF)"
            >
              {generatingBill ? "Billing…" : "Bill Generation"}
            </button>
            <button
              type="button"
              className="btn btn-sm btn-outline-secondary"
              disabled={
                loading ||
                saving ||
                generatingBill ||
                (!form.clmca_id && !bill?.bill_no)
              }
              onClick={handlePrintBill}
              title="Print existing PFN bill for this claim (landscape)"
            >
              Print Bill
            </button>
          </div>
        </div>
        <div className="fpc-toolbar-row">
          <div className="fpc-toolbar-left">
            <Field label="Disbursement Month" w="fpc-w-sm">
              <select
                className="form-select form-select-sm"
                value={monthlyMonth}
                disabled={generatingBill}
                onChange={(e) => setMonthlyMonth(e.target.value)}
              >
                {MONTH_OPTIONS.map(([value, label]) => (
                  <option key={value} value={value}>
                    {label}
                  </option>
                ))}
              </select>
            </Field>
            <Field label="Disbursement Year" w="fpc-w-xs">
              <select
                className="form-select form-select-sm"
                value={monthlyYear}
                disabled={generatingBill}
                onChange={(e) => setMonthlyYear(e.target.value)}
              >
                {billYearChoices(monthlyYear).map((y) => (
                  <option key={y} value={y}>
                    {y}
                  </option>
                ))}
              </select>
            </Field>
          </div>
          <div className="fpc-toolbar-right">
            <button
              type="button"
              className="btn btn-sm btn-info text-white"
              disabled={
                loading ||
                saving ||
                generatingFp ||
                generatingBill ||
                reportLoading ||
                !form.clmca_id
              }
              onClick={handleGenerateMonthlyBill}
              title="Generate monthly PFN for this month, or the unpaid period if this is the first disbursement"
            >
              {generatingBill ? "Billing…" : "Monthly Bill"}
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
              onChange={(e) => {
                const value = e.target.value;
                if (value === "CE") {
                  setClaimKind("succession");
                  setForm((prev) => ({
                    ...prev,
                    clm_ca_type: value,
                    double_fpen_eligibility: 0,
                    double_fpen_upto: "",
                  }));
                } else {
                  if (claimKind === "succession") setClaimKind("normal");
                  setField("clm_ca_type", value);
                }
              }}
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
          <Field label="Class" w="fpc-w-xs">
            <select
              className="form-select form-select-sm"
              value={
                form.class_cd === 0 || form.class_cd
                  ? String(form.class_cd)
                  : ""
              }
              onChange={(e) => setField("class_cd", e.target.value)}
            >
              {EMP_CLASS_OPTIONS.map(([value, label]) => (
                <option key={value || "blank"} value={value}>
                  {label}
                </option>
              ))}
            </select>
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
                {applicantTypeOptions(claimKind, form.applicant_type).map(
                  ([value, label]) => (
                    <option key={value || "blank"} value={value}>
                      {label}
                    </option>
                  )
                )}
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
          <Field label="Emp Dod" w="fpc-w-sm">
            <input
              type="date"
              className="form-control form-control-sm"
              value={form.emp_dod || ""}
              onChange={(e) => setField("emp_dod", e.target.value)}
              title="Autofilled from original family-pension claim or employee death (separation − 1 day). Start month/year uses the later of this and Pensioner Death On."
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
              readOnly={doubleEligible}
              title={
                doubleEligible
                  ? "Auto: die-in-harness (DT & sep < exp ret) → separation + 10 years; else MIN(sep/ret + 7 years, age 67 I/II or 65)"
                  : undefined
              }
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
            <select
              className="form-select form-select-sm"
              value={form.pension_opt || ""}
              onChange={(e) => setField("pension_opt", e.target.value)}
            >
              <option value="">—</option>
              {PENSION_OPT_OPTIONS.map(([value, label]) => (
                <option key={value} value={value}>
                  {label}
                </option>
              ))}
            </select>
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
              title="607 CPI equivalent when last basic is not a scale stage, or salary/scale is missing for old employees. Used by Generate First FP."
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
          <div className="fpc-grid-scroll">
          <table className="fpc-grid fpc-grid-appcn">
            <colgroup>
              <col className="fpc-col-sl" />
              <col className="fpc-col-name" />
              <col className="fpc-col-rel" />
              <col className="fpc-col-dob" />
              <col className="fpc-col-flag" />
              <col className="fpc-col-bank" />
              <col className="fpc-col-branch-cd" />
              <col className="fpc-col-lic" />
              <col className="fpc-col-acc" />
              <col className="fpc-col-bank-name" />
              <col className="fpc-col-branch-name" />
              <col className="fpc-col-flag" />
              <col className="fpc-col-active" />
              <col className="fpc-col-reason" />
              <col className="fpc-col-inactive" />
              <col className="fpc-col-marital" />
              <col className="fpc-col-ym" />
              <col className="fpc-col-ym" />
              <col className="fpc-col-ym" />
              <col className="fpc-col-ym" />
            </colgroup>
            <thead>
              <tr>
                <th>Sl No</th>
                <th>Name</th>
                <th>Relation</th>
                <th>DOB</th>
                <th>Disabled</th>
                <th>Bank Code</th>
                <th>Branch Code</th>
                <th>Lic Bank Cd</th>
                <th>Acc No</th>
                <th>Bank Name</th>
                <th>Branch Name</th>
                <th>Relief</th>
                <th>Active/Inactive</th>
                <th>Reason</th>
                <th>Inactive From</th>
                <th>Marital Status</th>
                <th>Start Yr</th>
                <th>Start Month</th>
                <th>Impl Yr</th>
                <th>Impl Month</th>
              </tr>
            </thead>
            <tbody>
              {(form.applicants || []).length === 0 ? (
                <tr>
                  <td colSpan={20} className="fpc-empty">
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
                        title={a.relation_desc || ""}
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
                        onBlur={() => resolveApplicantBank(idx, "bank_cd")}
                      />
                    </td>
                    <td>
                      <input
                        className="form-control form-control-sm"
                        value={a.bank_id || ""}
                        readOnly
                        tabIndex={-1}
                        title="Branch code (BANK_ID from bank master)"
                      />
                    </td>
                    <td>
                      <input
                        className="form-control form-control-sm"
                        value={a.lic_bank_cd || ""}
                        onChange={(e) =>
                          setApplicant(idx, "lic_bank_cd", e.target.value)
                        }
                        onBlur={() => resolveApplicantBank(idx, "lic_bank_cd")}
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
                    <td>
                      <input
                        className="form-control form-control-sm"
                        value={a.bank_name || ""}
                        readOnly
                        tabIndex={-1}
                        title={a.bank_name || ""}
                      />
                    </td>
                    <td>
                      <input
                        className="form-control form-control-sm"
                        value={a.bank_branch || ""}
                        readOnly
                        tabIndex={-1}
                        title={a.bank_branch || ""}
                      />
                    </td>
                    <td>
                      <select
                        className="form-select form-select-sm"
                        value={a.relief_tag || ""}
                        onChange={(e) =>
                          setApplicant(idx, "relief_tag", e.target.value)
                        }
                      >
                        {RELIEF_TAG_OPTIONS.map(([value, label]) => (
                          <option key={value || "blank"} value={value}>
                            {label}
                          </option>
                        ))}
                      </select>
                    </td>
                    <td>
                      <select
                        className="form-select form-select-sm"
                        value={String(a.fpen_active ?? 1)}
                        onChange={(e) =>
                          setApplicant(idx, "fpen_active", e.target.value)
                        }
                      >
                        <option value="1">Active</option>
                        <option value="0">Inactive</option>
                      </select>
                    </td>
                    <td>
                      <select
                        className="form-select form-select-sm fpc-sel-reason"
                        value={a.fpen_clos_reason || ""}
                        onChange={(e) =>
                          setApplicant(idx, "fpen_clos_reason", e.target.value)
                        }
                        title={
                          closReasons.find(
                            ([v]) => v === (a.fpen_clos_reason || "")
                          )?.[1] || "Reason"
                        }
                      >
                        {closReasons.map(([value, label]) => (
                          <option key={value || "blank"} value={value}>
                            {label}
                          </option>
                        ))}
                      </select>
                    </td>
                    <td>
                      <input
                        type="date"
                        className="form-control form-control-sm"
                        value={a.fpen_inactive_from_dt || ""}
                        onChange={(e) =>
                          setApplicant(
                            idx,
                            "fpen_inactive_from_dt",
                            e.target.value
                          )
                        }
                      />
                    </td>
                    <td>
                      <select
                        className="form-select form-select-sm"
                        value={a.status_flg || ""}
                        onChange={(e) =>
                          setApplicant(idx, "status_flg", e.target.value)
                        }
                      >
                        {MARITAL_STATUS_OPTIONS.map(([value, label]) => (
                          <option key={value || "blank"} value={value}>
                            {label}
                          </option>
                        ))}
                      </select>
                    </td>
                    <td>
                      <input
                        className="form-control form-control-sm"
                        value={a.fprn_start_yr ?? ""}
                        readOnly={isSuccession && idx === 0}
                        tabIndex={isSuccession && idx === 0 ? -1 : undefined}
                        title={
                          isSuccession && idx === 0
                            ? "Taken from the later of family-pensioner death and employee death"
                            : undefined
                        }
                        onChange={(e) =>
                          setApplicant(idx, "fprn_start_yr", e.target.value)
                        }
                        placeholder="YYYY"
                      />
                    </td>
                    <td>
                      <select
                        className="form-select form-select-sm"
                        value={String(a.fpen_start_mnth ?? "")}
                        disabled={isSuccession && idx === 0}
                        title={
                          isSuccession && idx === 0
                            ? "Taken from the later of family-pensioner death and employee death"
                            : undefined
                        }
                        onChange={(e) =>
                          setApplicant(idx, "fpen_start_mnth", e.target.value)
                        }
                      >
                        <option value="">—</option>
                        {MONTH_OPTIONS.map(([value, label]) => (
                          <option key={value} value={value}>
                            {label}
                          </option>
                        ))}
                      </select>
                    </td>
                    <td>
                      <input
                        className="form-control form-control-sm"
                        value={a.impl_yr ?? ""}
                        onChange={(e) =>
                          setApplicant(idx, "impl_yr", e.target.value)
                        }
                        placeholder="YYYY"
                      />
                    </td>
                    <td>
                      <select
                        className="form-select form-select-sm"
                        value={String(a.impl_mnth ?? "")}
                        onChange={(e) =>
                          setApplicant(idx, "impl_mnth", e.target.value)
                        }
                      >
                        <option value="">—</option>
                        {MONTH_OPTIONS.map(([value, label]) => (
                          <option key={value} value={value}>
                            {label}
                          </option>
                        ))}
                      </select>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
          </div>
        </div>
      </div>

      {/* Hidden print roots */}
      <div className="d-none">
        <FamilyPensionProposalPrint report={report} />
        <FamilyPensionBillPrint bill={bill} claim={form} />
      </div>
    </div>
  );
}
