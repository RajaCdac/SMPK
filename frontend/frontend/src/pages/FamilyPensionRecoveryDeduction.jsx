import { useCallback, useEffect, useMemo, useState } from "react";
import API from "../services/Api";
import "../styles/Dashboard.css";
import "../styles/FirstPensionCase.css";
import "../styles/FamilyPensionClaim.css";

const MONTHS = [
  { value: 1, label: "January (01)" },
  { value: 2, label: "February (02)" },
  { value: 3, label: "March (03)" },
  { value: 4, label: "April (04)" },
  { value: 5, label: "May (05)" },
  { value: 6, label: "June (06)" },
  { value: 7, label: "July (07)" },
  { value: 8, label: "August (08)" },
  { value: 9, label: "September (09)" },
  { value: 10, label: "October (10)" },
  { value: 11, label: "November (11)" },
  { value: 12, label: "December (12)" },
];

function fmtAmt(value) {
  if (value == null || value === "") return "—";
  const n = Number(value);
  if (Number.isNaN(n)) return String(value);
  return n.toLocaleString("en-IN", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
}

function apiError(err, fallback = "Request failed") {
  const data = err?.response?.data;
  if (!data) return err?.message || fallback;
  if (typeof data === "string") return data.slice(0, 400);
  if (data.error) return String(data.error);
  return fallback;
}

const EMPTY_HEADER = {
  fam_fmpen_id: "",
  emp_cd: "",
  clmca_id: "",
  case_no: "",
  name: "",
  bill_no: "",
  lines: [],
};

/**
 * Family Pension — Recovery / Deduction entry
 * Oracle: fi_pn_ded_fam_form.fmb → FI_PN_TD_FIRST_MONTH_FPENSION
 */
export default function FamilyPensionRecoveryDeduction() {
  const now = new Date();
  const [month, setMonth] = useState(now.getMonth() + 1);
  const [year, setYear] = useState(now.getFullYear());
  const [empCd, setEmpCd] = useState("");

  const [header, setHeader] = useState(EMPTY_HEADER);
  const [lines, setLines] = useState([]);

  const [earnType, setEarnType] = useState("D");
  const [code, setCode] = useState("");
  const [description, setDescription] = useState("");
  const [amount, setAmount] = useState("");
  const [codeOptions, setCodeOptions] = useState([]);

  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");

  const loaded = Boolean(header.fam_fmpen_id);

  const yearOptions = useMemo(() => {
    const y = now.getFullYear();
    const out = [];
    for (let i = y + 1; i >= y - 30; i -= 1) out.push(i);
    return out;
  }, [now]);

  const resetEntry = () => {
    setCode("");
    setDescription("");
    setAmount("");
  };

  const loadCodes = useCallback(async (type) => {
    try {
      const { data } = await API.get("family-pension/recovery-deduction/codes/", {
        params: { type: type || "" },
      });
      setCodeOptions(data?.codes || []);
    } catch {
      setCodeOptions([]);
    }
  }, []);

  useEffect(() => {
    loadCodes(earnType);
  }, [earnType, loadCodes]);

  const handleLookup = async (e) => {
    if (e) e.preventDefault();
    const emp = String(empCd || "").trim();
    if (!emp) {
      setError("Enter employee code.");
      return;
    }
    setLoading(true);
    setError("");
    setMessage("");
    try {
      const { data } = await API.get("family-pension/recovery-deduction/lookup/", {
        params: { month, year, emp_cd: emp },
      });
      setHeader({
        fam_fmpen_id: data.fam_fmpen_id || "",
        emp_cd: data.emp_cd || emp,
        clmca_id: data.clmca_id || "",
        case_no: data.case_no || "",
        name: data.name || "",
        bill_no: data.bill_no || "",
        lines: data.lines || [],
      });
      setLines(data.lines || []);
      setEmpCd(data.emp_cd || emp);
      setMessage(`Loaded bill ${data.fam_fmpen_id || ""}${data.bill_no ? ` (${data.bill_no})` : ""}.`);
      resetEntry();
    } catch (err) {
      setHeader(EMPTY_HEADER);
      setLines([]);
      setError(apiError(err, "No entry for this employee / month / year."));
    } finally {
      setLoading(false);
    }
  };

  const resolveDescription = async (nextCode) => {
    const cd = String(nextCode || "").trim();
    if (!cd) {
      setDescription("");
      return;
    }
    const fromList = codeOptions.find(
      (c) => String(c.code).trim() === cd
    );
    if (fromList?.description) {
      setDescription(fromList.description);
      return;
    }
    try {
      const { data } = await API.get("family-pension/recovery-deduction/codes/", {
        params: { code: cd, type: earnType },
      });
      setDescription(data?.description || "");
      if (!data?.description) {
        setError(`Code ${cd} not found in master for type ${earnType}.`);
      } else {
        setError("");
      }
    } catch (err) {
      setDescription("");
      setError(apiError(err, "Code not found."));
    }
  };

  const handleSave = async (e) => {
    if (e) e.preventDefault();
    if (!header.fam_fmpen_id) {
      setError("Load employee / month / year first.");
      return;
    }
    setSaving(true);
    setError("");
    setMessage("");
    try {
      const { data } = await API.post("family-pension/recovery-deduction/line/", {
        fam_fmpen_id: header.fam_fmpen_id,
        earn_dedn_type: earnType,
        earn_dedn_cd: code,
        amount,
      });
      setLines(data.lines || []);
      setMessage(
        data.action === "updated"
          ? `Updated ${earnType}/${String(code).trim()}.`
          : `Saved ${earnType}/${String(code).trim()}.`
      );
      resetEntry();
    } catch (err) {
      setError(apiError(err, "Could not save line."));
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (line) => {
    if (!header.fam_fmpen_id) return;
    if (
      !window.confirm(
        `Delete ${line.earn_dedn_type}/${line.earn_dedn_cd} (${fmtAmt(line.amount)})?`
      )
    ) {
      return;
    }
    setSaving(true);
    setError("");
    setMessage("");
    try {
      const { data } = await API.delete("family-pension/recovery-deduction/line/", {
        data: {
          fam_fmpen_id: header.fam_fmpen_id,
          earn_dedn_type: line.earn_dedn_type,
          earn_dedn_cd: line.earn_dedn_cd,
        },
      });
      setLines(data.lines || []);
      setMessage(`Deleted ${line.earn_dedn_type}/${line.earn_dedn_cd}.`);
    } catch (err) {
      setError(apiError(err, "Could not delete line."));
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="first-pension-case-page fpc-page container-fluid mt-3">
      <div className="d-flex flex-wrap justify-content-between align-items-center gap-2 mb-3">
        <h2 className="mb-0">Recovery / Deduction</h2>
      </div>

      <form className="fpc-toolbar smpk-form mb-3" onSubmit={handleLookup}>
        <div className="row g-2 align-items-end">
          <div className="col-6 col-md-2">
            <label className="form-label mb-1">Month</label>
            <select
              className="form-select"
              value={month}
              onChange={(e) => setMonth(Number(e.target.value))}
            >
              {MONTHS.map((m) => (
                <option key={m.value} value={m.value}>
                  {m.label}
                </option>
              ))}
            </select>
          </div>
          <div className="col-6 col-md-2">
            <label className="form-label mb-1">Year</label>
            <select
              className="form-select"
              value={year}
              onChange={(e) => setYear(Number(e.target.value))}
            >
              {yearOptions.map((y) => (
                <option key={y} value={y}>
                  {y}
                </option>
              ))}
            </select>
          </div>
          <div className="col-8 col-md-3">
            <label className="form-label mb-1">Emp Code</label>
            <input
              className="form-control"
              value={empCd}
              onChange={(e) => setEmpCd(e.target.value)}
              onBlur={(e) => setEmpCd(String(e.target.value || "").trim())}
              maxLength={5}
              placeholder="e.g. 11830"
            />
          </div>
          <div className="col-4 col-md-2">
            <button
              type="submit"
              className="btn btn-primary w-100"
              disabled={loading}
            >
              {loading ? "Loading…" : "Load"}
            </button>
          </div>
        </div>
      </form>

      {error ? <div className="alert alert-danger py-2">{error}</div> : null}
      {message ? <div className="alert alert-success py-2">{message}</div> : null}

      {loaded ? (
        <>
          <div className="fpc-panel smpk-form mb-3">
            <div className="row g-2">
              <div className="col-md-3">
                <label className="form-label mb-1">Case No</label>
                <input className="form-control" value={header.case_no} readOnly />
              </div>
              <div className="col-md-3">
                <label className="form-label mb-1">Claim ID</label>
                <input className="form-control" value={header.clmca_id} readOnly />
              </div>
              <div className="col-md-4">
                <label className="form-label mb-1">Name</label>
                <input className="form-control" value={header.name} readOnly />
              </div>
              <div className="col-md-2">
                <label className="form-label mb-1">FMPEN ID</label>
                <input className="form-control" value={header.fam_fmpen_id} readOnly />
              </div>
            </div>
          </div>

          <form className="fpc-panel smpk-form mb-3" onSubmit={handleSave}>
            <h3 className="h6 mb-2">Add / Update line</h3>
            <div className="row g-2 align-items-end">
              <div className="col-md-2">
                <label className="form-label mb-1">Type</label>
                <select
                  className="form-select"
                  value={earnType}
                  onChange={(e) => {
                    setEarnType(e.target.value);
                    setCode("");
                    setDescription("");
                  }}
                >
                  <option value="E">E — Earning</option>
                  <option value="D">D — Deduction</option>
                </select>
              </div>
              <div className="col-md-2">
                <label className="form-label mb-1">Code</label>
                <input
                  className="form-control"
                  list="fp-recovery-codes"
                  value={code}
                  onChange={(e) => setCode(e.target.value)}
                  onBlur={(e) => resolveDescription(e.target.value)}
                  maxLength={10}
                  required
                />
                <datalist id="fp-recovery-codes">
                  {codeOptions.map((c) => (
                    <option key={`${c.type}-${c.code}`} value={c.code}>
                      {c.description}
                    </option>
                  ))}
                </datalist>
              </div>
              <div className="col-md-4">
                <label className="form-label mb-1">Description</label>
                <input className="form-control" value={description} readOnly />
              </div>
              <div className="col-md-2">
                <label className="form-label mb-1">Amount</label>
                <input
                  className="form-control"
                  type="number"
                  step="0.01"
                  value={amount}
                  onChange={(e) => setAmount(e.target.value)}
                  required
                />
              </div>
              <div className="col-md-2">
                <button
                  type="submit"
                  className="btn btn-success w-100"
                  disabled={saving}
                >
                  {saving ? "Saving…" : "Save"}
                </button>
              </div>
            </div>
          </form>

          <div className="table-responsive">
            <table className="table table-sm table-striped table-bordered align-middle">
              <thead>
                <tr>
                  <th>Type</th>
                  <th>Code</th>
                  <th>Description</th>
                  <th className="text-end">Amount</th>
                  <th style={{ width: 90 }} />
                </tr>
              </thead>
              <tbody>
                {!lines.length ? (
                  <tr>
                    <td colSpan={5} className="text-center text-muted py-3">
                      No earn / dedn lines yet.
                    </td>
                  </tr>
                ) : (
                  lines.map((line) => (
                    <tr key={`${line.earn_dedn_type}-${line.earn_dedn_cd}`}>
                      <td>{line.earn_dedn_type}</td>
                      <td>
                        <code>{line.earn_dedn_cd}</code>
                      </td>
                      <td>{line.description || "—"}</td>
                      <td className="text-end">{fmtAmt(line.amount)}</td>
                      <td>
                        <button
                          type="button"
                          className="btn btn-sm btn-outline-danger"
                          disabled={saving}
                          onClick={() => handleDelete(line)}
                        >
                          Delete
                        </button>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </>
      ) : (
        <p className="text-muted">
          Enter month, year and emp code, then Load. Case no, claim ID and name
          will appear from the family pension bill header.
        </p>
      )}
    </div>
  );
}
