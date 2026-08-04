import CommutationApplicationEntry from "./CommutationApplicationEntry";
import PensionSepcomGeneration from "./PensionSepcomGeneration";
import NoPayEntry from "./NoPayEntry";
import PensionProposalEntry from "./PensionProposalEntry";
import PensionAmountEntry from "./PensionAmountEntry";
import PensionBillJournalTabs from "./PensionBillJournalTabs";
import PensionReports from "./PensionReports";
import { isVoluntaryRetirement } from "../utils/voluntaryRetirement";
import "../styles/EmployeeProcessTabs.css";

function formatAge(age) {
  if (!age || age.years === null) return "N/A";
  let text = `${age.years} yrs`;
  if (age.months !== null) text += ` ${age.months} mn`;
  if (age.days !== null) text += ` ${age.days} days`;
  return text;
}

const INFO_FIELDS = (employee) => [
  { label: "Employee ID", value: employee.emp_id },
  { label: "Name", value: employee.name },
  { label: "Date of Joining", value: employee.join_date },
  { label: "Expected Retirement", value: employee.expected_retirement_date },
  { label: "Date of Birth", value: employee.birth_date },
  { label: "Department", value: employee.designation },
  { label: "Class", value: employee.class },
  {
    label: "Basic Pay",
    value: `Rs.${employee.basic_amount} (${employee.scale})`,
  },
  { label: "Age on Appointment", value: formatAge(employee.age_on_appointment) },
  { label: "Age on Retirement", value: formatAge(employee.age_on_retirement) },
];

const WORKFLOW_TABS = [
  { key: "personal", label: "Basic Info", shortLabel: "Basic", step: 1 },
  { key: "adm", label: "Commutation", shortLabel: "Comm.", step: 2 },
  { key: "nopay", label: "No-Pay", shortLabel: "No-Pay", step: 3 },
  { key: "proposal", label: "Proposal", shortLabel: "Proposal", step: 4 },
  { key: "amount", label: "Amount", shortLabel: "Amount", step: 5 },
  { key: "bill", label: "Bill & Journal", shortLabel: "Bill", step: 6 },
  { key: "reports", label: "Reports", shortLabel: "Reports", step: 7 },
];

export default function EmployeeProcessTabs({ employee, idPrefix = "emp" }) {
  if (!employee) return null;

  const showSepcomGeneration = isVoluntaryRetirement(employee);

  const panelIds = {
    personal: `${idPrefix}-personal`,
    adm: `${idPrefix}-adm`,
    nopay: `${idPrefix}-nopay`,
    proposal: `${idPrefix}-proposal`,
    amount: `${idPrefix}-amount`,
    bill: `${idPrefix}-bill`,
    reports: `${idPrefix}-reports`,
  };

  return (
    <div className="employee-process-tabs">
      <ul className="employee-process-tabs__nav" role="tablist">
        {WORKFLOW_TABS.map((tab, index) => {
          const panelId = panelIds[tab.key];
          const isFirst = index === 0;
          return (
            <li
              key={tab.key}
              className="employee-process-tabs__item"
              role="presentation"
            >
              <button
                className={`employee-process-tabs__btn nav-link${
                  isFirst ? " active" : ""
                }`}
                id={`${idPrefix}-${tab.key}-tab`}
                data-bs-toggle="tab"
                data-bs-target={`#${panelId}`}
                data-tab={tab.key}
                type="button"
                role="tab"
                aria-controls={panelId}
                aria-selected={isFirst}
              >
                <span className="employee-process-tabs__step">{tab.step}</span>
                <span className="employee-process-tabs__label-full">
                  {tab.label}
                </span>
                <span className="employee-process-tabs__label-short">
                  {tab.shortLabel}
                </span>
              </button>
            </li>
          );
        })}
      </ul>

      <div className="tab-content employee-process-tabs__panel">
        <div
          className="tab-pane fade show active"
          id={panelIds.personal}
          role="tabpanel"
          aria-labelledby={`${idPrefix}-personal-tab`}
        >
          <div className="employee-info-grid">
            {INFO_FIELDS(employee).map((item) => (
              <div className="employee-info-item" key={item.label}>
                <span>{item.label}</span>
                <strong>{item.value || "—"}</strong>
              </div>
            ))}
          </div>
        </div>

        <div
          className="tab-pane fade"
          id={panelIds.adm}
          role="tabpanel"
          aria-labelledby={`${idPrefix}-adm-tab`}
        >
          <h5 className="employee-process-tabs__section-title">
            {showSepcomGeneration
              ? "Step 1 — Commutation Application"
              : "Commutation Application"}
          </h5>
          <CommutationApplicationEntry employee={employee} />
          {showSepcomGeneration && (
            <PensionSepcomGeneration employee={employee} />
          )}
        </div>

        <div
          className="tab-pane fade"
          id={panelIds.nopay}
          role="tabpanel"
          aria-labelledby={`${idPrefix}-nopay-tab`}
        >
          <h5 className="employee-process-tabs__section-title">No-Pay Entry</h5>
          <NoPayEntry employee={employee} />
        </div>

        <div
          className="tab-pane fade"
          id={panelIds.proposal}
          role="tabpanel"
          aria-labelledby={`${idPrefix}-proposal-tab`}
        >
          <PensionProposalEntry employee={employee} />
        </div>

        <div
          className="tab-pane fade"
          id={panelIds.amount}
          role="tabpanel"
          aria-labelledby={`${idPrefix}-amount-tab`}
        >
          <h5 className="employee-process-tabs__section-title">
            Pension, Commutation &amp; Gratuity
          </h5>
          <PensionAmountEntry employee={employee} idPrefix={idPrefix} />
        </div>

        <div
          className="tab-pane fade"
          id={panelIds.bill}
          role="tabpanel"
          aria-labelledby={`${idPrefix}-bill-tab`}
        >
          <h5 className="employee-process-tabs__section-title">
            Bill &amp; Journal
          </h5>
          <PensionBillJournalTabs employee={employee} idPrefix={idPrefix} />
        </div>

        <div
          className="tab-pane fade"
          id={panelIds.reports}
          role="tabpanel"
          aria-labelledby={`${idPrefix}-reports-tab`}
        >
          <PensionReports employee={employee} idPrefix={idPrefix} />
        </div>
      </div>
    </div>
  );
}
