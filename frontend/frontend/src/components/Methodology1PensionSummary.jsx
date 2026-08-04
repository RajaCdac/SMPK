import { formatCardValue } from "../utils/methodology2RevisionCards";

function PensionBlock({ title, basic, pension, familyPension }) {
  return (
    <div className="col-md-6">
      <div className="border rounded p-3 h-100 bg-light">
        <h6 className="fw-bold text-primary mb-3">{title}</h6>
        <table className="table table-sm table-borderless mb-0">
          <tbody>
            <tr>
              <td className="text-muted">Calculated basic</td>
              <td className="text-end fw-semibold">
                Rs. {formatCardValue(basic)}
              </td>
            </tr>
            <tr>
              <td className="text-muted">Pension (50% of basic)</td>
              <td className="text-end fw-semibold text-primary">
                Rs. {formatCardValue(pension)}
              </td>
            </tr>
            <tr>
              <td className="text-muted">Family pension (30% of basic)</td>
              <td className="text-end fw-semibold text-success">
                Rs. {formatCardValue(familyPension)}
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  );
}

export default function Methodology1PensionSummary({
  pensionSummary,
  retirementDate,
  scale,
  lastPay,
  empId = "",
  employeeName = "",
}) {
  if (!pensionSummary) return null;

  const handlePrint = () => {
    window.print();
  };

  const printDate = retirementDate
    ? new Date(retirementDate).toLocaleDateString("en-IN")
    : "—";

  return (
    <>
      <style>{`
        @media print {
          body * {
            visibility: hidden;
          }
          #methodology1-pension-print,
          #methodology1-pension-print * {
            visibility: visible;
          }
          #methodology1-pension-print {
            position: absolute;
            left: 0;
            top: 0;
            width: 100%;
          }
          .no-print {
            display: none !important;
          }
        }
      `}</style>

      <div className="row justify-content-center mt-4">
        <div className="col-md-10">
          <div
            id="methodology1-pension-print"
            className="card shadow border-primary"
          >
            <div className="card-header bg-primary text-white d-flex justify-content-between align-items-center">
              <h5 className="mb-0">Pension (from calculated basic)</h5>
              <button
                type="button"
                className="btn btn-light btn-sm no-print"
                onClick={handlePrint}
              >
                Print
              </button>
            </div>
            <div className="card-body">
              <div className="mb-3 small text-muted methodology1-print-meta">
                {empId && (
                  <div>
                    <strong>Employee:</strong> {empId}
                    {employeeName ? ` — ${employeeName}` : ""}
                  </div>
                )}
                <div>
                  <strong>Retirement date:</strong> {printDate}
                </div>
                <div>
                  <strong>Scale:</strong> {scale || "—"}
                </div>
                <div>
                  <strong>Last pay:</strong>{" "}
                  {lastPay ? `Rs. ${formatCardValue(lastPay)}` : "—"}
                </div>
                <div className="mt-1">
                  Pension = 50% of calculated basic · Family pension = 30% of
                  calculated basic
                </div>
              </div>

              <div className="row g-3">
                <PensionBlock
                  title="2022 (359 CPI)"
                  basic={pensionSummary.basic_pay_2022}
                  pension={pensionSummary.pension_359_cpi}
                  familyPension={pensionSummary.family_pension_359_cpi}
                />
                <PensionBlock
                  title="2017 (277 CPI)"
                  basic={pensionSummary.basic_pay_2017}
                  pension={pensionSummary.pension_277_cpi}
                  familyPension={pensionSummary.family_pension_277_cpi}
                />
              </div>
            </div>
          </div>
        </div>
      </div>
    </>
  );
}
