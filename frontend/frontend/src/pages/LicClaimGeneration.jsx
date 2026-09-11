import { useCallback, useRef, useState } from "react";
import API from "../services/Api";
import LicClaimNormalPrint from "../components/LicClaimNormalPrint";
import { printPensionReport } from "../utils/pensionReportPrint";
import "../styles/FirstPensionCase.css";
import "../styles/Dashboard.css";

/**
 * Oracle FI_PN_LIC_BILL_GEN_E — Normal pension (PENSION_TYPE = N).
 * Emp ID + Load fills Claim / Roll / Address from DB.
 * LIC SL No is entered manually when not found.
 * Print → FI_PN_LIC_NORMAL_PEN_DTLS (LIC Claim Form-Normal).
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
  pension_type: "N",
  claim_id: "",
  address: "",
};

export default function LicClaimGeneration() {
  const [empId, setEmpId] = useState("");
  const [empName, setEmpName] = useState("");
  const [claim, setClaim] = useState({ ...EMPTY_CLAIM });
  const [aadharNo, setAadharNo] = useState("");
  const [report, setReport] = useState(null);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [printing, setPrinting] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const empRef = useRef(null);
  const licRef = useRef(null);
  const aadharRef = useRef(null);

  const applyPayload = useCallback((data) => {
    const c = data?.claim || {};
    setEmpName(data?.emp_name || "");
    setEmpId(data?.emp_cd || "");
    setClaim({
      emp_cd: data?.emp_cd || "",
      lic_sl_no:
        c.lic_sl_no != null && c.lic_sl_no !== "" ? String(c.lic_sl_no) : "",
      pen_roll_no: c.pen_roll_no || "",
      pension_type: "N",
      claim_id: c.claim_id || "",
      address: c.address || "",
    });
  }, []);

  const loadEmployee = async (rawCode) => {
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
      const { data } = await API.get(
        "first-pension/lic-claim-generation/normal/",
        { params: { emp_cd: code } }
      );
      applyPayload(data);
      const c = data?.claim || {};
      const hasLic = c.lic_sl_no != null && c.lic_sl_no !== "";
      setMessage(
        `Loaded ${data.emp_cd}${data.emp_name ? ` — ${data.emp_name}` : ""}.` +
          (hasLic ? "" : " Enter LIC SL No and click Save.")
      );
      if (!hasLic) {
        setTimeout(() => licRef.current?.focus(), 0);
      }
    } catch (err) {
      setEmpName("");
      setClaim({ ...EMPTY_CLAIM });
      setError(apiError(err, "Could not load LIC claim"));
    } finally {
      setLoading(false);
    }
  };

  const onSearch = (e) => {
    e.preventDefault();
    loadEmployee(empRef.current?.value ?? empId);
  };

  const onSave = async (e) => {
    e.preventDefault();
    if (!claim.emp_cd) {
      setError("Load an employee first");
      return;
    }
    if (!claim.claim_id) {
      setError("Claim ID not found for this employee");
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
      const { data } = await API.post(
        "first-pension/lic-claim-generation/normal/",
        {
          emp_cd: claim.emp_cd,
          lic_sl_no: claim.lic_sl_no,
          pen_roll_no: claim.pen_roll_no,
          claim_id: claim.claim_id,
          address: claim.address,
          pension_type: "N",
        }
      );
      applyPayload(data);
      setReport(null);
      setMessage(`Saved LIC claim for ${data.emp_cd}.`);
    } catch (err) {
      setError(apiError(err, "Could not save LIC claim"));
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
      setError("Claim ID not found for this employee");
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
    setPrinting(true);
    setError("");
    setMessage("");
    try {
      // Persist latest LIC SL so print address/claim row is consistent
      await API.post("first-pension/lic-claim-generation/normal/", {
        emp_cd: claim.emp_cd,
        lic_sl_no: claim.lic_sl_no,
        pen_roll_no: claim.pen_roll_no,
        claim_id: claim.claim_id,
        address: claim.address,
        pension_type: "N",
      });
      const { data } = await API.get(
        "first-pension/lic-claim-generation/normal/print/",
        {
          params: {
            emp_cd: claim.emp_cd,
            claim_id: claim.claim_id,
            aadhar_no: String(aadharNo).trim(),
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
      selector: "#lic-claim-normal-print-root",
      orientation: "portrait",
    });
  };

  const onClear = () => {
    setEmpId("");
    setEmpName("");
    setClaim({ ...EMPTY_CLAIM });
    setAadharNo("");
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
              <h4 className="mb-0">LIC Claim Generation</h4>
            </div>
            <div className="card-body smpk-form">
              <p className="text-muted small mb-3">
                Enter Emp ID and click Load. Claim ID and Roll No come from the
                database. Enter LIC SL No if missing, edit Address if needed,
                then Save. Use Preview Print for LIC Claim Form-Normal.
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
                    placeholder="Emp code"
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
                {empName ? (
                  <div className="col-12">
                    <small className="text-muted">{empName}</small>
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
                      value="N — Normal"
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
                      value={claim.pen_roll_no || "—"}
                      readOnly
                    />
                  </div>
                  <div className="col-12 col-md-6">
                    <label className="form-label">Claim ID / CA Number</label>
                    <input
                      type="text"
                      className="form-control"
                      value={claim.claim_id || "—"}
                      readOnly
                    />
                  </div>
                  <div className="col-12 col-md-6">
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
                      placeholder="Residential address for print"
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
                <LicClaimNormalPrint report={report} />
              </div>
            </div>
          ) : null}
        </div>
      </div>
    </div>
  );
}
