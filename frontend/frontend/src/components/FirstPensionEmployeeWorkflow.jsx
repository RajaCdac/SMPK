import { useEffect, useState } from "react";
import EmployeeProcessTabs from "./EmployeeProcessTabs";
import ProcessIntakeForm from "./ProcessIntakeForm";

/**
 * Same step flow as First Pension page: process intake → tabbed forms.
 */
export default function FirstPensionEmployeeWorkflow({
  employee,
  onEmployeeUpdate,
  onPhaseChange,
  idPrefix = "first-pension",
}) {
  const [showTabs, setShowTabs] = useState(false);

  useEffect(() => {
    setShowTabs(false);
  }, [employee?.emp_id]);

  useEffect(() => {
    if (!employee) {
      onPhaseChange?.("idle");
      return;
    }
    onPhaseChange?.(showTabs ? "tabs" : "intake");
  }, [employee, showTabs, onPhaseChange]);

  if (!employee) {
    return null;
  }

  const handleIntakeComplete = (res) => {
    if (res?.intake_data) {
      onEmployeeUpdate?.({
        process_intake_data: res.intake_data,
        process_intake_completed: res.completed ?? true,
      });
    }
  };

  const handleContinueToTabs = () => {
    setShowTabs(true);
  };

  if (showTabs) {
    return (
      <div className="first-pension-workflow">
        <EmployeeProcessTabs employee={employee} idPrefix={idPrefix} />
      </div>
    );
  }

  return (
    <div className="first-pension-workflow">
    <ProcessIntakeForm
      employee={employee}
      onComplete={handleIntakeComplete}
      onContinue={handleContinueToTabs}
    />
    </div>
  );
}
