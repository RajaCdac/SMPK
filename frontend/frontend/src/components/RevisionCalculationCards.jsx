import {
  buildRevisionCards,
} from "../utils/methodology2RevisionCards";
import CpiRevisionCard from "./CpiRevisionCard";

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
        <CpiRevisionCard
          key={card.revisionKey}
          title={card.title}
          rows={card.rows}
        />
      ))}
    </div>
  );
}
