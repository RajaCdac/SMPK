const STEP_META = [
  { key: "intake", title: "Separation / process intake" },
  { key: "commutation", title: "Commutation application" },
  { key: "no_pay", title: "No-pay entry" },
  { key: "proposal", title: "Pension proposal" },
  { key: "amount", title: "Pension amount calculated" },
];

function buildAriaLabel(steps) {
  if (!steps) return "No processing started";
  const parts = STEP_META.map(
    (meta) => `${meta.title}: ${steps[meta.key] ? "done" : "pending"}`
  );
  return `Form progress — ${parts.join("; ")}`;
}

export function WorkflowStepDots({ steps }) {
  if (!steps) return null;
  return (
    <div
      className="wf-steps"
      role="img"
      aria-label={buildAriaLabel(steps)}
    >
      {STEP_META.map((meta) => (
        <span
          key={meta.key}
          className={`wf-step${steps[meta.key] ? " wf-step--done" : ""}`}
          title={`${meta.title}: ${steps[meta.key] ? "Done" : "Pending"}`}
        >
          <span className="wf-step__dot" />
        </span>
      ))}
    </div>
  );
}

export default function DashboardWorkflowStatus({ row }) {
  return (
    <div className="wf-status-cell wf-status-cell--dots-only">
      <WorkflowStepDots steps={row.workflow_steps} />
    </div>
  );
}
