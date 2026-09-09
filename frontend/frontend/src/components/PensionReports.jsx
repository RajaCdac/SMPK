import { useEffect } from "react";
import PensionLicReport from "./PensionLicReport";
import PensionProposalSanctionReport from "./PensionProposalSanctionReport";
import PensionCommutationBillReport from "./PensionCommutationBillReport";
import PensionSeparateCommutationBillReport from "./PensionSeparateCommutationBillReport";
import PensionBillAbstractReport from "./PensionBillAbstractReport";
import PensionJournalSummaryReport from "./PensionJournalSummaryReport";
import PensionFirstPensionAdviceReport from "./PensionFirstPensionAdviceReport";
import PensionBillContextBar from "./PensionBillContextBar";
import { useEmployeeBillContext } from "../hooks/useEmployeeBillContext";
import "../styles/PensionReports.css";

function BillAbstractReportSection({ employee, idPrefix }) {
  const { billContext, loading, reload } = useEmployeeBillContext(employee);

  useEffect(() => {
    const tabIds = [
      `${idPrefix}-billabstract-tab`,
      `${idPrefix.replace(/-reports$/, "")}-reports-tab`,
    ];

    const onShown = () => reload();
    const elements = tabIds
      .map((id) => document.getElementById(id))
      .filter(Boolean);

    elements.forEach((el) => el.addEventListener("shown.bs.tab", onShown));
    return () =>
      elements.forEach((el) => el.removeEventListener("shown.bs.tab", onShown));
  }, [idPrefix, reload]);

  return (
    <>
      <PensionBillContextBar
        billContext={billContext}
        loading={loading}
        onRefresh={reload}
      />
      <PensionBillAbstractReport
        billNo={billContext?.billNo || ""}
        employee={employee}
      />
    </>
  );
}

function JournalSummaryReportSection({ employee, idPrefix }) {
  const { billContext, loading, reload } = useEmployeeBillContext(employee);

  useEffect(() => {
    const tabIds = [
      `${idPrefix}-journalsummary-tab`,
      `${idPrefix.replace(/-reports$/, "")}-reports-tab`,
    ];

    const onShown = () => reload();
    const elements = tabIds
      .map((id) => document.getElementById(id))
      .filter(Boolean);

    elements.forEach((el) => el.addEventListener("shown.bs.tab", onShown));
    return () =>
      elements.forEach((el) => el.removeEventListener("shown.bs.tab", onShown));
  }, [idPrefix, reload]);

  return (
    <>
      <PensionBillContextBar
        billContext={billContext}
        loading={loading}
        onRefresh={reload}
      />
      <PensionJournalSummaryReport
        billNo={billContext?.billNo || ""}
        jvMonth={billContext?.jvMonth || ""}
        jvYear={billContext?.jvYear || ""}
      />
    </>
  );
}

export const REPORT_SECTIONS = [
  {
    key: "lic",
    label: "LIC Report",
    title: "LIC Report (First Bill)",
    Component: PensionLicReport,
  },
  {
    key: "sanction",
    label: "Pension Sanction",
    title: "Recommendation & Sanction of Pension",
    Component: PensionProposalSanctionReport,
  },
  {
    key: "firstpensionadvice",
    label: "First Pension Advice",
    title: "First Pension Advice",
    Component: PensionFirstPensionAdviceReport,
  },
  {
    key: "combill",
    label: "Commutation Sanction",
    title: "Recommendation & Sanction of Commutation",
    Component: PensionCommutationBillReport,
  },
  {
    key: "sepcombill",
    label: "Sep. Commutation Bill",
    title: "Separate Commutation Bill",
    Component: PensionSeparateCommutationBillReport,
  },
  {
    key: "billabstract",
    label: "Bill Abstract",
    title: "Bill Abstract",
    Component: BillAbstractReportSection,
  },
  {
    key: "journalsummary",
    label: "Journal Summary",
    title: "Summary of Journal",
    Component: JournalSummaryReportSection,
  },
];

export default function PensionReports({ employee, idPrefix = "emp" }) {
  const reportsIdPrefix = `${idPrefix}-reports`;

  return (
    <div className="pension-reports">
      <ul className="pension-reports__nav nav nav-pills" role="tablist">
        {REPORT_SECTIONS.map((section, index) => {
          const panelId = `${reportsIdPrefix}-${section.key}`;
          const isFirst = index === 0;
          return (
            <li key={section.key} className="nav-item" role="presentation">
              <button
                className={`nav-link${isFirst ? " active" : ""}`}
                id={`${panelId}-tab`}
                data-bs-toggle="tab"
                data-bs-target={`#${panelId}`}
                type="button"
                role="tab"
                aria-controls={panelId}
                aria-selected={isFirst}
              >
                {section.label}
              </button>
            </li>
          );
        })}
      </ul>

      <div className="tab-content pension-reports__panels">
        {REPORT_SECTIONS.map((section, index) => {
          const panelId = `${reportsIdPrefix}-${section.key}`;
          const SectionComponent = section.Component;
          const isFirst = index === 0;

          return (
            <div
              key={section.key}
              className={`tab-pane fade${isFirst ? " show active" : ""}`}
              id={panelId}
              role="tabpanel"
              aria-labelledby={`${panelId}-tab`}
            >
              <h5 className="pension-reports__section-title">{section.title}</h5>
              <SectionComponent
                employee={employee}
                idPrefix={reportsIdPrefix}
              />
            </div>
          );
        })}
      </div>
    </div>
  );
}
