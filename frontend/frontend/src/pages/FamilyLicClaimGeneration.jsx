import { useCallback, useRef, useState } from "react";
import API from "../services/Api";
import LicClaimFamilyPrint from "../components/LicClaimFamilyPrint";
import { printPensionReport } from "../utils/pensionReportPrint";
import "../styles/FirstPensionCase.css";
import "../styles/Dashboard.css";

/**
 * Oracle FI_PN_LIC_BILL_GEN_E — Family pension (PENSION_TYPE = F).
 */
function apiError(err, fallback = "Request failed") {
  const data = err?.response?.data;
  if (!data) return err?.message || fallback;
  if (typeof data === "string") return data.slice(0, 400);
  if (data.error) return String(data.error);
  return fallback;
}

const EMPTY_CLAIM = {
  emp_cd: "",
  lic_sl_no: "",
  pen_roll_no: "",
  pension_type: "F",
  claim_id: "",
  address: "",
  applicant_name: "",
};

export default function FamilyLicClaimGeneration() {
  const [empId, setEmpId] = useState("");
  const [empName, setEmpName] = useState("");
  const [applicantName, setApplicantName] = useState("");
  const [claimList, setClaimList] = useState([]);
  const [claim, setClaim] = useState({ ...EMPTY_CLAIM });
  const [aadharNo, setAadharNo] = useState("");
  const [daPct, setDaPct] = useState("");
  const [report, setReport] = useState(null);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [printing, setPrinting] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const empRef = useRef(null);
  const licRef = useRef(null);
  const aadharRef = useRef(null);
  const daRef = useRef(null);

  const applyPayload = useCallback((data) => {
    const c = data?.claim || {};
    setEmpName(data?.emp_name || "");
    setApplicantName(data?.applicant_name || c.applicant_name || "");
    setEmpId(data?.emp_cd || "");
    setClaimList(data?.claims || []);
    setClaim({
      emp_cd: data?.emp_cd || "",
      lic_sl_no:
        c.lic_sl_no != null && c.lic_sl_no !== "" ? String(c.lic_sl_no) : "",
      pen_roll_no: c.pen_roll_no || "",
      pension_type: "F",
      claim_id: c.claim_id || "",
      address: c.address || "",
      applicant_name: c.applicant_name || data?.applicant_name || "",
    });
  }, []);

  const loadEmployee = async (rawCode, claimId) => {
    const code = String(rawCode || "").trim();
    if (!code) {
      setError("Enter Employee ID");
      empRef.current?.focus();
      return;
    }
    setLoading(true);
    setError("");
    setMessage("");
    setReport(null);
    try {
      const params = { emp_cd: code };
      if (claimId) params.claim_id = claimId;
      const { data } = await API.get(
        "family-pension/lic-claim-generation/",
        { params }
      );
      applyPayload(data);
      if (data?.da_pct != null && data.da_pct !== "") {
        setDaPct(String(data.da_pct));
      }
      const c = data?.claim || {};
      const hasLic = c.lic_sl_no != null && c.lic_sl_no !== "";
      setMessage(
        `Loaded ${data.emp_cd}${
          data.applicant_name ? ` — ${data.applicant_name}` : ""
        }.` + (hasLic ? "" : " Enter LIC SL No and Save.")
      );
      if (!hasLic) {
        setTimeout(() => licRef.current?.focus(), 0);
      }
    } catch (err) {
      setEmpName("");
      setApplicantName("");
      setClaimList([]);
      setClaim({ ...EMPTY_CLAIM });
      setError(apiError(err, "Could not load family LIC claim"));
    } finally {
      setLoading(false);
    }
  };

  const onSearch = (e) => {
    e.preventDefault();
    loadEmployee(empRef.current?.value ?? empId);
  };

  const onClaimChange = (e) => {
    const next = e.target.value;
    setClaim((prev) => ({ ...prev, claim_id: next }));
    if (empId && next) {
      loadEmployee(empId, next);
    }
  };

  const onSave = async (e) => {
    e.preventDefault();
    if (!claim.emp_cd) {
      setError("Load an employee first");
      return;
    }
    if (!claim.claim_id) {
      setError("Select Claim ID");
      return;
    }
    if (!String(claim.lic_sl_no || "").trim()) {
      setError("Enter LIC SL No");
      licRef.current?.focus();
      return;
    }
    if (!String(aadharNo || "").trim()) {
      setError("Enter Aadhar No");
      aadharRef.current?.focus();
      return;
    }
    setSaving(true);
    setError("");
    setMessage("");
    try {
      const { data } = await API.post("family-pension/lic-claim-generation/", {
        emp_cd: claim.emp_cd,
        lic_sl_no: claim.lic_sl_no,
        pen_roll_no: claim.pen_roll_no,
        claim_id: claim.claim_id,
        address: claim.address,
        pension_type: "F",
      });
      applyPayload(data);
      setReport(null);
      setMessage(`Saved family LIC claim for ${data.emp_cd}.`);
    } catch (err) {
      setError(apiError(err, "Could not save family LIC claim"));
    } finally {
      setSaving(false);
    }
  };

  const loadPrint = async () => {
    if (!claim.emp_cd) {
      setError("Load an employee first");
      return;
    }
    if (!claim.claim_id) {
      setError("Select Claim ID");
      return;
    }
    if (!String(claim.lic_sl_no || "").trim()) {
      setError("Enter / save LIC SL No before print");
      licRef.current?.focus();
      return;
    }
    if (!String(aadharNo || "").trim()) {
      setError("Enter Aadhar No");
      aadharRef.current?.focus();
      return;
    }
    if (!String(daPct || "").trim()) {
      setError("Enter DA %");
      daRef.current?.focus();
      return;
    }
    setPrinting(true);
    setError("");
    setMessage("");
    try {
      await API.post("family-pension/lic-claim-generation/", {
        emp_cd: claim.emp_cd,
        lic_sl_no: claim.lic_sl_no,
        pen_roll_no: claim.pen_roll_no,
        claim_id: claim.claim_id,
        address: claim.address,
        pension_type: "F",
      });
      const { data } = await API.get(
        "family-pension/lic-claim-generation/print/",
        {
          params: {
            emp_cd: claim.emp_cd,
            claim_id: claim.claim_id,
            aadhar_no: String(aadharNo).trim(),
            da_pct: String(daPct).trim(),
          },
        }
      );
      setReport(data);
      setMessage(`Print preview ready for ${claim.emp_cd}.`);
    } catch (err) {
      setReport(null);
      setError(apiError(err, "Could not load print report"));
    } finally {
      setPrinting(false);
    }
  };

  const onPrint = (e) => {
    if (!report) {
      e.preventDefault();
      setError("Click Preview Print first");
      return;
    }
    printPensionReport(e, {
      selector: "#lic-claim-family-print-root",
      orientation: "portrait",
    });
  };

  const onClear = () => {
    setEmpId("");
    setEmpName("");
    setApplicantName("");
    setClaimList([]);
    setClaim({ ...EMPTY_CLAIM });
    setAadharNo("");
    setDaPct("");
    setReport(null);
    setError("");
    setMessage("");
    empRef.current?.focus();
  };

  return (
    <div className="first-pension-page fp-report-page container-fluid mt-3 mt-md-4 px-2 px-md-3">
      <div className="row justify-content-center">
        <div className="col-12 col-xl-10">
          <div className="card shadow first-pension-search-card">
            <div className="card-header bg-primary text-white">
              <h4 className="mb-0">LIC Claim Generation (Family)</h4>
            </div>
            <div className="card-body smpk-form">
              <p className="text-muted small mb-3">
                Enter Emp ID and click Load. Claim ID, Roll No and Address come
                from family pension claim. Enter LIC SL No / Aadhar / DA% as
                needed, edit Address, then Save / Preview Print.
              </p>

              <form className="row g-2 align-items-end mb-3" onSubmit={onSearch}>
                <div className="col-12 col-md-4">
                  <label className="form-label">Employee ID</label>
                  <input
                    ref={empRef}
                    type="text"
                    className="form-control"
                    value={empId}
                    onChange={(e) => setEmpId(e.target.value)}
                    placeholder="Deceased emp code"
                    disabled={loading || saving || printing}
                  />
                </div>
                <div className="col-auto">
                  <button
                    type="submit"
                    className="btn btn-primary"
                    disabled={loading || saving || printing}
                  >
                    {loading ? "Loading…" : "Load"}
                  </button>
                </div>
                <div className="col-auto">
                  <button
                    type="button"
                    className="btn btn-outline-secondary"
                    onClick={onClear}
                    disabled={loading || saving || printing}
                  >
                    Clear
                  </button>
                </div>
                {empName || applicantName ? (
                  <div className="col-12">
                    <small className="text-muted">
                      {empName ? `Deceased: ${empName}` : ""}
                      {empName && applicantName ? " · " : ""}
                      {applicantName ? `Applicant: ${applicantName}` : ""}
                    </small>
                  </div>
                ) : null}
              </form>

              {error ? (
                <div className="alert alert-danger py-2">{error}</div>
              ) : null}
              {message ? (
                <div className="alert alert-success py-2">{message}</div>
              ) : null}

              {claim.emp_cd ? (
                <form className="row g-3" onSubmit={onSave}>
                  <div className="col-6 col-md-4">
                    <label className="form-label">Pension Type</label>
                    <input
                      type="text"
                      className="form-control"
                      value="F — Family"
                      readOnly
                    />
                  </div>
                  <div className="col-6 col-md-4">
                    <label className="form-label">LIC SL No</label>
                    <input
                      ref={licRef}
                      type="text"
                      className="form-control"
                      value={claim.lic_sl_no}
                      onChange={(e) =>
                        setClaim((prev) => ({
                          ...prev,
                          lic_sl_no: e.target.value,
                        }))
                      }
                      placeholder="Enter if not found"
                      disabled={saving || printing}
                    />
                  </div>
                  <div className="col-12 col-md-4">
                    <label className="form-label">Pension Roll No</label>
                    <input
                      type="text"
                      className="form-control"
                      value={claim.pen_roll_no}
                      onChange={(e) =>
                        setClaim((prev) => ({
                          ...prev,
                          pen_roll_no: e.target.value,
                        }))
                      }
                      disabled={saving || printing}
                    />
                  </div>
                  <div className="col-12 col-md-6">
                    <label className="form-label">Claim ID</label>
                    {claimList.length > 1 ? (
                      <select
                        className="form-select"
                        value={claim.claim_id}
                        onChange={onClaimChange}
                        disabled={saving || printing || loading}
                      >
                        {claimList.map((c) => (
                          <option key={c.claim_id} value={c.claim_id}>
                            {c.claim_id}
                            {c.applicant_name ? ` — ${c.applicant_name}` : ""}
                          </option>
                        ))}
                      </select>
                    ) : (
                      <input
                        type="text"
                        className="form-control"
                        value={claim.claim_id || "—"}
                        readOnly
                      />
                    )}
                  </div>
                  <div className="col-12 col-md-3">
                    <label className="form-label">Aadhar No</label>
                    <input
                      ref={aadharRef}
                      type="text"
                      className="form-control"
                      value={aadharNo}
                      onChange={(e) => setAadharNo(e.target.value)}
                      placeholder="Aadhar number"
                      disabled={saving || printing}
                      required
                    />
                  </div>
                  <div className="col-12 col-md-3">
                    <label className="form-label">DA %</label>
                    <input
                      ref={daRef}
                      type="text"
                      className="form-control"
                      value={daPct}
                      onChange={(e) => setDaPct(e.target.value)}
                      placeholder="DA percent"
                      disabled={saving || printing}
                      required
                    />
                  </div>
                  <div className="col-12">
                    <label className="form-label">Address</label>
                    <textarea
                      className="form-control"
                      rows={3}
                      value={claim.address || ""}
                      onChange={(e) =>
                        setClaim((prev) => ({
                          ...prev,
                          address: e.target.value,
                        }))
                      }
                      disabled={saving || printing}
                    />
                  </div>
                  <div className="col-12 d-flex flex-wrap gap-2">
                    <button
                      type="submit"
                      className="btn btn-success"
                      disabled={saving || loading || printing}
                    >
                      {saving ? "Saving…" : "Save"}
                    </button>
                    <button
                      type="button"
                      className="btn btn-outline-primary"
                      onClick={loadPrint}
                      disabled={saving || loading || printing}
                    >
                      {printing ? "Preparing…" : "Preview Print"}
                    </button>
                    <button
                      type="button"
                      className="btn btn-primary"
                      onClick={onPrint}
                      disabled={!report || printing}
                    >
                      Print
                    </button>
                  </div>
                </form>
              ) : null}
            </div>
          </div>

          {report ? (
            <div className="card shadow mt-3">
              <div className="card-body">
                <LicClaimFamilyPrint report={report} />
              </div>
            </div>
          ) : null}
        </div>
      </div>
    </div>
  );
}
