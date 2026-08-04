import mappingData from "../data/parallelCpiMappings.json";

function normalizeScale(scaleString) {
  return String(scaleString || "").trim().replace(/\s+/g, "");
}

function mappingKey(scale1030, scale607) {
  return `${normalizeScale(scale1030)}|${normalizeScale(scale607)}`;
}

const PDF_TABLES = (() => {
  const tables = new Map();
  for (const entry of mappingData.mappings || []) {
    const key = mappingKey(entry.scale_1030, entry.scale_607);
    const rows = new Map();
    for (const row of entry.rows || []) {
      const pay1030 = Array.isArray(row) ? row[0] : row.pay_1030;
      const pay607 = Array.isArray(row) ? row[1] : row.pay_607;
      rows.set(Number(pay1030), Number(pay607));
    }
    tables.set(key, rows);
  }
  return tables;
})();

export function lookupPdfParallelMapping(scale1030, scale607, lastPay) {
  const rows = PDF_TABLES.get(mappingKey(scale1030, scale607));
  if (!rows) return null;
  const pay = Number(lastPay);
  if (Number.isNaN(pay)) return null;
  return rows.has(pay) ? rows.get(pay) : null;
}

export function map1030PayTo607Index(scale1030, scale607, lastPay, generatePayStages) {
  if (!scale1030 || !scale607 || lastPay == null || lastPay === "") {
    return null;
  }

  const stages1030 = generatePayStages(String(scale1030).trim());
  const stages607 = generatePayStages(String(scale607).trim());
  if (!stages1030.length || !stages607.length) return null;

  const pay = Number(lastPay);
  const stageIndex = stages1030.indexOf(pay);
  if (stageIndex < 0) return null;

  if (stageIndex >= stages607.length) {
    return stages607[stages607.length - 1];
  }
  return stages607[stageIndex];
}

export function map1030PayTo607FromPdf(scale1030, scale607, lastPay, generatePayStages) {
  const mapped = lookupPdfParallelMapping(scale1030, scale607, lastPay);
  if (mapped != null) return mapped;
  return map1030PayTo607Index(scale1030, scale607, lastPay, generatePayStages);
}
