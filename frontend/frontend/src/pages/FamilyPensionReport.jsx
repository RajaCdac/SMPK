import FamilyPensionSanctionReport from "./FamilyPensionSanctionReport";
import FamilyPensionBillGenerationReport from "./FamilyPensionBillGenerationReport";
import FamilyPensionBillAbstractReport from "./FamilyPensionBillAbstractReport";
import FamilyPensionJournalVoucherReport from "./FamilyPensionJournalVoucherReport";
import FamilyPensionLicBillReport from "./FamilyPensionLicBillReport";
import FamilyPensionDihApplicationPrint from "../components/FamilyPensionDihApplicationPrint";

export default function FamilyPensionReport({ section = "first-pension-generation" }) {
  if (section === "first-pension-generation") {
    return <FamilyPensionSanctionReport />;
  }
  if (section === "fp-dih-application") {
    return (
      <FamilyPensionSanctionReport
        apiPath="family-pension/dnh-proposal-report/"
        pageTitle="Application for FP(DIH)"
        PrintComponent={FamilyPensionDihApplicationPrint}
        printSelector="#family-pension-sanction-print-root .fp-dih-print"
      />
    );
  }
  if (section === "bill-generation") {
    return <FamilyPensionBillGenerationReport />;
  }
  if (section === "bill-abstract") {
    return <FamilyPensionBillAbstractReport />;
  }
  if (section === "journal-voucher") {
    return <FamilyPensionJournalVoucherReport />;
  }
  if (section === "first-fp-bill-lic") {
    return <FamilyPensionLicBillReport />;
  }

  return (
    <div className="container-fluid mt-3 mt-md-4 px-2 px-md-3">
      <div className="row justify-content-center">
        <div className="col-12 col-xl-11">
          <div className="card shadow">
            <div className="card-header bg-primary text-white">
              <h4 className="mb-0">Report</h4>
            </div>
            <div className="card-body">
              <p className="mb-0 text-muted">
                This report section is not yet available.
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
