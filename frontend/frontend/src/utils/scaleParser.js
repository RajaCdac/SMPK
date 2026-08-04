const REVISIONS_WITH_INCREMENT_10 = new Set([
  "2007(126 CPI)",
  "2012(198 CPI)",
]);

export function expandScaleIncrement10(scaleString) {
  if (!scaleString) return scaleString;

  const cleaned = String(scaleString).trim();
  const parts = cleaned.split("-").map((part) => part.trim()).filter(Boolean);
  const numbers = [];
  for (const part of parts) {
    const value = Number(part);
    if (Number.isNaN(value)) return cleaned;
    numbers.push(value);
  }

  if (numbers.length === 2) {
    return `${numbers[0]}-10-${numbers[1]}`;
  }
  return cleaned;
}

export function normalizeScaleForRevision(scaleString, revisionColumn = null) {
  if (REVISIONS_WITH_INCREMENT_10.has(revisionColumn)) {
    return expandScaleIncrement10(scaleString);
  }
  return scaleString;
}

export function parseScale(scaleString) {
  if (!scaleString) return [];

  const parts = String(scaleString).split("-");
  const numbers = parts.map((part) => Number(part.trim()));
  if (numbers.some((value) => Number.isNaN(value))) return [];

  if (numbers.length === 2) {
    return [{ start: numbers[0], increment: 10, end: numbers[1] }];
  }
  if (numbers.length < 3) return [];

  const parsed = [];
  let currentStart = numbers[0];
  for (let i = 1; i < numbers.length; i += 2) {
    parsed.push({
      start: currentStart,
      increment: numbers[i],
      end: numbers[i + 1],
    });
    currentStart = numbers[i + 1];
  }
  return parsed;
}

export function generatePayStages(scaleString) {
  const parsedScale = parseScale(scaleString);
  if (!parsedScale.length) return [];

  const stages = [];
  for (const segment of parsedScale) {
    let current = segment.start;
    while (current <= segment.end) {
      if (!stages.includes(current)) stages.push(current);
      current += segment.increment;
    }
  }
  return stages;
}
