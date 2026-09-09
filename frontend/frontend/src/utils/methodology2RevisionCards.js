export const REVISION_ORDER = [
  "1979(REVISED PAY SCALE)",
  "1984(REVISED PAY SCALE)",
  "1988(607 CPI)",
  "1993(1030 CPI)",
  "1997(1708 CPI)",
  "2007(126 CPI)",
  "2012(198 CPI)",
  "2017(277 CPI)",
  "2022(359 CPI)",
];

export const REVISION_CARD_GROUPS = [
  { revisionKey: "1979(REVISED PAY SCALE)", rows: [197901, 197902, 197903, 197904, 197905] },
  { revisionKey: "1984(REVISED PAY SCALE)", rows: [198401, 198402, 198403, 198404, 198405, 198406] },
  { revisionKey: "1988(607 CPI)", rows: [198801, 198802, 198803, 198804, 198805, 198806, 198807] },
  { revisionKey: "1993(1030 CPI)", rows: [199301, 199302, 199303, 199304, 199305, 199306, 199307] },
  { revisionKey: "1997(1708 CPI)", rows: [199701, 199702, 199703, 199704, 199705] },
  { revisionKey: "2007(126 CPI)", rows: [200701, 200702, 200703, 200704, 200705] },
  { revisionKey: "2012(198 CPI)", rows: [201201, 201202, 201203, 201204, 201205, 201206] },
  { revisionKey: "2017(277 CPI)", rows: [201701, 201702, 201703, 201704, 201705, 201706] },
  { revisionKey: "2022(359 CPI)", rows: [202201] },
];

/** "1997(1708 CPI)" → "1997 (1708 CPI)" */
export function formatRevisionCardTitle(revisionKey) {
  const match = revisionKey.match(/^(\d{4})\((\d+)\s*CPI\)$/i);
  if (match) {
    return `Detailed Calculation Breakdown Year ${match[1]} - CPI ${match[2]}`;
  }
  const generic = revisionKey.match(/^(\d{4})\((.+)\)$/);
  if (generic) {
    return `${generic[1]} (${generic[2]})`;
  }
  return revisionKey;
}

export function getRevisionIndex(revisionKey) {
  const idx = REVISION_ORDER.indexOf(revisionKey);
  return idx >= 0 ? idx : 0;
}

function rowHasValue(row) {
  const v = row?.value;
  if (v === null || v === undefined || v === "") return false;
  return Number(v) !== 0;
}

/**
 * Build visible CPI cards from calculation rows.
 * Only shows the retirement start revision and later stages (no prior CPI cards).
 */
export function buildRevisionCards(calculationRows, startRevision) {
  if (!calculationRows?.length) return [];

  const rowMap = new Map(
    calculationRows.map((r) => [r.row, r])
  );
  const startIdx = getRevisionIndex(startRevision);

  return REVISION_CARD_GROUPS.filter((group) => {
    if (getRevisionIndex(group.revisionKey) < startIdx) return false;

    const lines = group.rows
      .map((rowNum) => rowMap.get(rowNum))
      .filter(Boolean);

    if (!lines.length) return false;

    return lines.some(rowHasValue);
  }).map((group) => {
    const lines = group.rows
      .map((rowNum) => rowMap.get(rowNum))
      .filter(Boolean);

    return {
      revisionKey: group.revisionKey,
      title: formatRevisionCardTitle(group.revisionKey),
      rows: lines,
    };
  });
}

export function formatCardValue(value) {
  if (value === null || value === undefined || value === "") return "—";
  const n = Number(value);
  if (Number.isNaN(n)) return value;
  return n.toLocaleString("en-IN", {
    minimumFractionDigits: 0,
    maximumFractionDigits: 2,
  });
}
