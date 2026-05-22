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
  { revisionKey: "1979(REVISED PAY SCALE)", rows: [27, 28, 29, 30] },
  { revisionKey: "1984(REVISED PAY SCALE)", rows: [31, 32, 33, 34, 35] },
  { revisionKey: "1988(607 CPI)", rows: [36, 37, 38, 39, 40, 41] },
  { revisionKey: "1993(1030 CPI)", rows: [42, 43, 44, 45, 46, 47] },
  { revisionKey: "1997(1708 CPI)", rows: [48, 49, 50, 51] },
  { revisionKey: "2007(126 CPI)", rows: [52, 53, 54, 55] },
  { revisionKey: "2012(198 CPI)", rows: [56, 57, 58, 59] },
  { revisionKey: "2017(277 CPI)", rows: [60, 61, 62, 63] },
  { revisionKey: "2022(359 CPI)", rows: [64, 65] },
];

/** "1997(1708 CPI)" → "1997 (1708 CPI)" */
export function formatRevisionCardTitle(revisionKey) {
  const match = revisionKey.match(/^(\d{4})\((.+)\)$/);
  if (match) {
    return `${match[1]} (${match[2]})`;
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
 * Hides revisions before retirement (all-zero rows).
 */
export function buildRevisionCards(calculationRows, startRevision) {
  if (!calculationRows?.length) return [];

  const rowMap = new Map(
    calculationRows.map((r) => [r.row, r])
  );
  const startIndex = getRevisionIndex(startRevision);

  return REVISION_CARD_GROUPS.filter((group, groupIndex) => {
    if (groupIndex < startIndex) return false;

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
