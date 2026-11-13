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

function class12BlockYear(block) {
  const key = String(block?.revision_key || block?.revisionKey || "");
  const fromKey = key.match(/^(\d{4})/);
  if (fromKey) return fromKey[1];
  const fromTitle = String(block?.title || "").match(/Year\s+(\d{4})/i);
  return fromTitle ? fromTitle[1] : "";
}

function isClass12OpeningBasic(description) {
  return /basic\s+pay\s+(as\s+on|in\s+the\s+existing\s+scale|over)/i.test(
    String(description || "")
  );
}

// CR 12-11-2026: class 1/2 opening lines read like class 3/4
// ("Basic Pay Over 126 CPI Points as on 01.01.2007"). CPI of each 1 January
// class 1/2 stage; the final 01.01.2017 block stays "Basic Pay as on 01.01.2017"
// like the class 3/4 final 01.01.2022 block.
// CR 12-11-2026: 1987 stage is 686 CPI (user confirmed), not the 685 of the DA line.
const CLASS12_STAGE_CPI = { 1987: "686", 1992: "1099", 1997: "1708", 2007: "126" };

function class12OpeningLabel(description) {
  const text = String(description || "").trim();
  // CR 12-11-2026 (emp 21908): the first block's "Basic Pay in the existing
  // scale (1992 revised pay scale)" reads the same CPI way.
  const m = text.match(
    /^Basic\s+Pay\s+(?:as\s+on\s+01\.01\.(\d{4})|in\s+the\s+existing\s+scale\s+\((\d{4})\s+revised\s+pay\s+scale\))$/i
  );
  const year = m ? m[1] || m[2] : null;
  if (year && CLASS12_STAGE_CPI[year]) {
    return `Basic Pay Over ${CLASS12_STAGE_CPI[year]} CPI Points as on 01.01.${year}`;
  }
  return text;
}

/** CR 12-11-2026: "Year 1992 (Revised Pay Scale)" → class 3/4 style
 *  "Detailed Calculation Breakdown Year 1992 - CPI 1099" (same for 1987). */
function class12CpiTitle(title) {
  const text = String(title || "");
  const m = text.match(/^Year\s+(\d{4})\s+\(Revised Pay Scale\)/i);
  if (m && CLASS12_STAGE_CPI[m[1]]) {
    return `Detailed Calculation Breakdown Year ${m[1]} - CPI ${CLASS12_STAGE_CPI[m[1]]}${text.slice(m[0].length)}`;
  }
  return text;
}

// CR 12-11-2026 (emp 21908): wording of saved class 1/2 lines, so reprints of
// older consolidations read the same as new ones.
const CLASS12_ROW_TEXT = {
  "D.A (As per Slab based lookup)": "D.A (As per Slab)*",
  "Fitment @ 20%": "Fitment @ 20% on Basic",
};
export const CLASS12_DA_SLAB_MARK = "As per Slab)*";

function class12RowText(description) {
  const text = String(description || "").trim();
  return CLASS12_ROW_TEXT[text] || text;
}

const round2 = (n) => Math.round((Number(n) || 0) * 100) / 100;

/** CR 12-11-2026: class 3/4 shows "Aggregate of A+B+C" before the rounded
 *  notional pay; class 1/2 had no such row. */
function withClass12Aggregate(rows) {
  if (rows.some((r) => /^Aggregate\b/i.test(String(r.description || "")))) return rows;
  const idx = rows.findIndex(
    (r, i) => i >= 2 && /Rounded to the next 10/i.test(String(r.description || ""))
  );
  if (idx < 0) return rows;
  const parts = rows.slice(0, idx);
  const letters = parts.map((_, i) => String.fromCharCode(65 + i)).join("+");
  const aggregate = {
    description: `Aggregate of ${letters}`,
    value: round2(parts.reduce((s, r) => s + (Number(r.value) || 0), 0)),
  };
  if (parts.some((r) => r.npa != null)) {
    aggregate.pay = round2(parts.reduce((s, r) => s + (Number(r.pay) || 0), 0));
    aggregate.npa = round2(parts.reduce((s, r) => s + (Number(r.npa) || 0), 0));
  }
  return [...parts, aggregate, ...rows.slice(idx)];
}

/**
 * Each class 1/2 scale block starts with that scale's basic
 * (e.g. Basic Pay Over 126 CPI Points as on 01.01.2007), then DA, fitment
 * and Aggregate of A+B+C.
 */
export function ensureClass12OpeningBasic(blocks) {
  let previous = null;
  return (blocks || []).map((block) => {
    const year = class12BlockYear(block);
    let rows = (block.rows || []).map((row) => ({ ...row }));
    if (rows.length) {
      const first = String(rows[0].description || "");
      // Later scales open with the prior stage's basic; class12OpeningLabel
      // turns it (and the first "existing scale" line) into the CPI wording.
      if (year && previous && !isClass12OpeningBasic(first)) {
        rows.unshift({
          description: `Basic Pay as on 01.01.${year}`,
          value: previous.value,
          ...(previous.npa != null ? { pay: previous.pay, npa: previous.npa } : {}),
        });
      }
      rows.forEach((row) => {
        row.description = class12RowText(row.description);
      });
      rows[0].description = class12OpeningLabel(rows[0].description);
      rows = withClass12Aggregate(rows);
      rows.forEach((row, idx) => {
        row.row = idx + 1;
        row.code = idx < 26 ? String.fromCharCode(65 + idx) : String(idx + 1);
      });
      const last = rows[rows.length - 1];
      if (last?.value != null && last.value !== "") previous = last;
    }
    return { ...block, title: class12CpiTitle(block.title), rows };
  });
}
