import { useCallback, useEffect, useMemo } from "react";
import PensionBillGeneration from "./PensionBillGeneration";
import PensionPpcBillGeneration from "./PensionPpcBillGeneration";
import PensionVoucherGeneration from "./PensionVoucherGeneration";
import PensionManualJournal from "./PensionManualJournal";
import PensionBillContextBar from "./PensionBillContextBar";
import { useEmployeeBillContext } from "../hooks/useEmployeeBillContext";
import { isVoluntaryRetirement } from "../utils/voluntaryRetirement";
import "../styles/PensionReports.css";

const BILL_JOURNAL_SECTIONS = [
  {
    key: "generate",
    label: "PPN Bill",
    title: "PPN Bill Generation (First Pension)",
    vrOnly: false,
  },
  {
    key: "ppc",
    label: "PPC Bill",
    title: "PPC Bill Generation (Separate Commutation)",
    vrOnly: true,
  },
  {
    key: "voucher",
    label: "Journal Voucher",
    title: "Auto Journal Voucher (PPN)",
    vrOnly: false,
  },
  {
    key: "manual",
    label: "Manual Journal",
    title: "Manual Journal Voucher",
    vrOnly: false,
  },
];

function renderBillJournalPanel(section, { employee, journalIdPrefix, idPrefix, billStatus, billContext, refreshBillContext }) {
  switch (section.key) {
    case "generate":
      return (
        <PensionBillGeneration
          employee={employee}
          idPrefix={journalIdPrefix}
          workflowTabPrefix={idPrefix}
          onBillStatusChange={refreshBillContext}
        />
      );
    case "ppc":
      return (
        <PensionPpcBillGeneration
          employee={employee}
          idPrefix={journalIdPrefix}
          workflowTabPrefix={idPrefix}
          onBillStatusChange={refreshBillContext}
        />
      );
    case "voucher":
      return (
        <PensionVoucherGeneration
          employee={employee}
          billStatus={billStatus}
          onVoucherChange={refreshBillContext}
        />
      );
    case "manual":
      return (
        <PensionManualJournal
          billNo={billContext?.billNo || ""}
          jvMonth={billContext?.jvMonth || ""}
          jvYear={billContext?.jvYear || ""}
          employee={employee}
          embedded
        />
      );
    default:
      return null;
  }
}

export default function PensionBillJournalTabs({ employee, idPrefix = "emp" }) {
  const journalIdPrefix = `${idPrefix}-billjournal`;
  const { billContext, loading, reload } = useEmployeeBillContext(employee);
  const showPpcBill = isVoluntaryRetirement(employee);

  const visibleSections = useMemo(
    () =>
      BILL_JOURNAL_SECTIONS.filter(
        (section) => !section.vrOnly || showPpcBill
      ),
    [showPpcBill]
  );

  const refreshBillContext = useCallback(
    (options) => {
      reload(options);
    },
    [reload]
  );

  const handleManualRefresh = useCallback(() => {
    refreshBillContext({ showLoading: true });
  }, [refreshBillContext]);

  useEffect(() => {
    const tabIds = [
      `${idPrefix}-bill-tab`,
      ...visibleSections.map(
        (section) => `${journalIdPrefix}-${section.key}-tab`
      ),
    ];

    const onShown = () => refreshBillContext();
    const elements = tabIds
      .map((id) => document.getElementById(id))
      .filter(Boolean);

    elements.forEach((el) => el.addEventListener("shown.bs.tab", onShown));
    return () =>
      elements.forEach((el) => el.removeEventListener("shown.bs.tab", onShown));
  }, [idPrefix, journalIdPrefix, refreshBillContext, visibleSections]);

  const billStatus = billContext?.status || null;

  return (
    <div className="pension-bill-journal">
      <PensionBillContextBar
        billContext={billContext}
        loading={loading}
        onRefresh={handleManualRefresh}
      />

      <ul className="pension-reports__nav nav nav-pills" role="tablist">
        {visibleSections.map((section, index) => {
          const panelId = `${journalIdPrefix}-${section.key}`;
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
        {visibleSections.map((section, index) => {
          const panelId = `${journalIdPrefix}-${section.key}`;
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
              {renderBillJournalPanel(section, {
                employee,
                journalIdPrefix,
                idPrefix,
                billStatus,
                billContext,
                refreshBillContext,
              })}
            </div>
          );
        })}
      </div>
    </div>
  );
}
