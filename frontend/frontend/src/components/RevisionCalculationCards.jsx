import {
  buildRevisionCards,
  formatCardValue,
} from "../utils/methodology2RevisionCards";

export default function RevisionCalculationCards({
  calculationRows,
  startRevision,
}) {
  const cards = buildRevisionCards(calculationRows, startRevision);

  if (!cards.length) {
    return (
      <p className="text-muted mb-0">
        No revision calculation rows for this retirement date.
      </p>
    );
  }

  return (
    <div className="row g-3">
      {cards.map((card) => (
        <div
          key={card.revisionKey}
          className="col-12 col-sm-6 col-lg-3"
        >
          <div className="card h-100 shadow-sm border-0 revision-cpi-card">
            <div className="card-header bg-warning text-dark py-2">
              <h6 className="mb-0 fw-bold text-center">{card.title}</h6>
            </div>
            <div className="card-body p-0">
              <table className="table table-sm table-bordered mb-0">
                <tbody>
                  {card.rows.map((line) => (
                    <tr key={line.row}>
                      <td className="small text-muted" style={{ width: "58%" }}>
                        {line.description}
                      </td>
                      <td className="small fw-semibold text-end">
                        {formatCardValue(line.value)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}
