import { useRef, useState } from "react";
import API from "../services/Api";
import FamilyPensionLicBillPrint from "../components/FamilyPensionLicBillPrint";
import { printPensionReport } from "../utils/pensionReportPrint";
import "../styles/FamilyPensionLicBillPrint.css";
import "../styles/pension-report-print.css";
import "../styles/FamilyPensionSanctionReport.css";

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

/**
 * Report: First FP Bill (LIC) — Oracle FI_PN_FPENBILL_LIC.
 * Enter Emp ID → load latest First Family Pension (PFN) LIC bill → print.
 */
export default function FamilyPensionLicBillReport() {
  const [empCd, setEmpCd] = useState("");
  const [bill, setBill] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const empRef = useRef(null);

  const loadBill = async (rawEmp) => {
    const emp = String(rawEmp ?? empCd ?? "").trim();
    if (!emp) {
      setError("Enter Emp ID");
      empRef.current?.focus();
      return;
    }

    setLoading(true);
    setError("");
    setMessage("");
    setBill(null);
    setEmpCd(emp);

    try {
      const { data } = await API.get("family-pension/bill-print/", {
        params: {
          emp_cd: emp,
          bill_type: "N",
          gen_lic_tag: "L",
          print_style: "lic",
        },
      });
      if (data?.error) {
        setError(data.error);
        return;
      }
      setBill(data);
      setMessage(
        `Bill ${data.bill_no}` +
          (data.print?.deceased_name ? ` · ${data.print.deceased_name}` : "") +
          (data.print?.net_earn_disp
            ? ` · Net ₹${data.print.net_earn_disp}`
            : "")
      );
    } catch (err) {
      setError(apiErrorMessage(err, "Could not load First FP Bill (LIC)"));
    } finally {
      setLoading(false);
    }
  };

  const onSubmit = (e) => {
    e.preventDefault();
    loadBill(empRef.current?.value ?? empCd);
  };

  const onPrint = (e) => {
    if (!bill?.print) {
      setError("Load a bill first");
      return;
    }
    printPensionReport(e, {
      selector: "#fp-lic-bill-print-root .fp-lic-bill-print",
      orientation: "portrait",
    });
  };

  return (
    <div className="container-fluid mt-3 mt-md-4 px-2 px-md-3 family-pension-sanction-report">
      <div className="row justify-content-center">
        <div className="col-12 col-xl-11">
          <div className="card shadow">
            <div className="card-header bg-primary text-white d-flex flex-wrap justify-content-between align-items-center gap-2">
              <h4 className="mb-0">First FP Bill (LIC)</h4>
              <button
                type="button"
                className="btn btn-light btn-sm"
                onClick={onPrint}
                disabled={!bill?.print || loading}
              >
                Print
              </button>
            </div>
            <div className="card-body">
              <form
                className="row g-2 align-items-end mb-3"
                onSubmit={onSubmit}
              >
                <div className="col-12 col-sm-4 col-md-3">
                  <label className="form-label mb-1" htmlFor="fp-lic-emp">
                    Emp ID
                  </label>
                  <input
                    id="fp-lic-emp"
                    ref={empRef}
                    className="form-control"
                    value={empCd}
                    onChange={(e) => setEmpCd(e.target.value)}
                    placeholder="e.g. 44962"
                    autoComplete="off"
                    autoFocus
                  />
                </div>
                <div className="col-auto">
                  <button
                    type="submit"
                    className="btn btn-primary"
                    disabled={loading}
                  >
                    {loading ? "Loading…" : "Show Bill"}
                  </button>
                </div>
              </form>

              {error ? (
                <div className="alert alert-danger py-2" role="alert">
                  {error}
                </div>
              ) : null}
              {message && !error ? (
                <div className="alert alert-success py-2" role="status">
                  {message}
                </div>
              ) : null}

              {bill?.print ? (
                <div
                  id="fp-lic-bill-print-root"
                  className="fp-lic-bill-preview border rounded bg-white p-2 overflow-auto"
                >
                  <FamilyPensionLicBillPrint bill={bill} />
                </div>
              ) : (
                <p className="text-muted mb-0">
                  Enter Emp ID to load the First Family Pension Bill (LIC
                  format). Bill must already be generated (Bill Generation).
                </p>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
