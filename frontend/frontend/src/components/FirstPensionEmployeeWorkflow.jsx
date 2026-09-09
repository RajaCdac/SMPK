import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import CommutationApplicationEntry from "./CommutationApplicationEntry";
import FirstPensionBasicInfo from "./FirstPensionBasicInfo";
import NoPayEntry from "./NoPayEntry";
import PensionAmountEntry from "./PensionAmountEntry";
import PensionBillJournalTabs from "./PensionBillJournalTabs";
import PensionProposalEntry from "./PensionProposalEntry";
import PensionReports from "./PensionReports";
import PensionSepcomGeneration from "./PensionSepcomGeneration";
import ProcessIntakeForm from "./ProcessIntakeForm";
import { isVoluntaryRetirement } from "../utils/voluntaryRetirement";
import "../styles/EmployeeProcessTabs.css";

/**
 * First Pension: ESR Check → processing (sep type/date) → No-pay →
 * Commutation → Proposal → Amount → Bill & Journal → Reports.
 */
export default function FirstPensionEmployeeWorkflow({
  employee,
  onEmployeeUpdate,
  onPhaseChange,
  step = "esr",
}) {
  const navigate = useNavigate();
  const empId = employee?.emp_id || "";
  const empQs = empId ? `?emp=${encodeURIComponent(empId)}` : "";
  const [esrPhase, setEsrPhase] = useState("basic");

  useEffect(() => {
    setEsrPhase("basic");
  }, [empId, step]);

  useEffect(() => {
    if (!employee) {
      onPhaseChange?.("idle");
      return;
    }
    if (step === "esr") {
      onPhaseChange?.(esrPhase === "intake" ? "intake" : "basic");
      return;
    }
    onPhaseChange?.("form");
  }, [employee, step, esrPhase, onPhaseChange]);

  if (!employee) {
    return null;
  }

  if (step === "esr") {
    if (esrPhase === "intake") {
      return (
        <div className="first-pension-workflow">
          <h5 className="employee-process-tabs__section-title">
            Pension Processing
          </h5>
          <ProcessIntakeForm
            employee={employee}
            onComplete={(res) => {
              if (res?.intake_data) {
                onEmployeeUpdate?.({
                  process_intake_data: res.intake_data,
                  process_intake_completed: res.completed ?? true,
                });
              }
            }}
            onBack={() => setEsrPhase("basic")}
            onContinue={() =>
              navigate(`/dashboard/firstpension/nopay${empQs}`)
            }
          />
        </div>
      );
    }

    return (
      <div className="first-pension-workflow">
        <FirstPensionBasicInfo
          employee={employee}
          nextLabel="Next — Pension processing"
          onNext={() => setEsrPhase("intake")}
        />
      </div>
    );
  }

  if (step === "commutation") {
    return (
      <div className="first-pension-workflow">
        <h5 className="employee-process-tabs__section-title">
          Commutation Application
        </h5>
        <CommutationApplicationEntry
          employee={employee}
          nextTo={`/dashboard/firstpension/proposal${empQs}`}
          nextLabel="Next: Proposal →"
        />
      </div>
    );
  }

  if (step === "proposal") {
    return (
      <div className="first-pension-workflow">
        <PensionProposalEntry
          employee={employee}
          showAmountNext
          amountNextTo={`/dashboard/firstpension/amount${empQs}`}
        />
      </div>
    );
  }

  if (step === "amount") {
    return (
      <div className="first-pension-workflow">
        <h5 className="employee-process-tabs__section-title">
          Pension, Commutation &amp; Gratuity
        </h5>
        <PensionAmountEntry
          employee={employee}
          nextTo={`/dashboard/firstpension/bill${empQs}`}
          nextLabel="Next: Bill & Journal →"
        />
        {isVoluntaryRetirement(employee) ? (
          <PensionSepcomGeneration employee={employee} />
        ) : null}
      </div>
    );
  }

  if (step === "bill") {
    return (
      <div className="first-pension-workflow">
        <h5 className="employee-process-tabs__section-title">
          Bill &amp; Journal
        </h5>
        <PensionBillJournalTabs
          employee={employee}
          idPrefix="fp-bill"
          nextTo={`/dashboard/firstpension/reports${empQs}`}
          nextLabel="Next: Reports →"
        />
      </div>
    );
  }

  if (step === "reports") {
    return (
      <div className="first-pension-workflow">
        <h5 className="employee-process-tabs__section-title">Reports</h5>
        <PensionReports employee={employee} idPrefix="fp-reports" />
      </div>
    );
  }

  return (
    <div className="first-pension-workflow">
      <h5 className="employee-process-tabs__section-title">No-Pay Entry</h5>
      <NoPayEntry
        employee={employee}
        showNext
        nextTo={`/dashboard/firstpension/commutation${empQs}`}
        nextLabel="Next: Commutation →"
        onBack={() => navigate(`/dashboard/firstpension/esr-check${empQs}`)}
        backLabel="Back to ESR Check"
      />
    </div>
  );
}
