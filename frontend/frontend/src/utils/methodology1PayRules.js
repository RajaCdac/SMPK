import { generatePayStages } from "./scaleParser";
import { map1030PayTo607FromPdf } from "./parallelCpiLookup";

export const CPI_607_REVISION = "1988(607 CPI)";
export const CPI_1030_REVISION = "1993(1030 CPI)";
export const CPI_1979_REVISION = "1979(REVISED PAY SCALE)";
export const CPI_1984_REVISION = "1984(REVISED PAY SCALE)";
export const CPI_1708_REVISION = "1997(1708 CPI)";

export const MIN_PAY_PROTECT = {
  "1997(1708 CPI)": 1850,
  "2007(126 CPI)": 3900,
  "2012(198 CPI)": 6750,
  "2017(277 CPI)": 10450,
  "2022(359 CPI)": 14750,
};

const MIN_PAY_30 = 375;
const MIN_PAY_20 = 450;
const MIN_PAY_15 = 600;

const CPI_30_REVISIONS = new Set([
  CPI_1708_REVISION,
  "2007(126 CPI)",
  "2012(198 CPI)",
  "2017(277 CPI)",
  "2022(359 CPI)",
]);

function round2(value) {
  return Math.round(Number(value) * 100) / 100;
}

function applyFactor(pay, factor, minimum) {
  return Math.max(round2(pay * factor), minimum);
}

function protectNotional(rawNotional, revisionKey) {
  const min = MIN_PAY_PROTECT[revisionKey];
  if (min == null || rawNotional == null) return rawNotional;
  return Math.max(Number(rawNotional), min);
}

function notionalLabel(baseLabel, rawValue, revisionKey) {
  const min = MIN_PAY_PROTECT[revisionKey];
  if (min != null && Number(rawValue) < min) {
    return `${baseLabel} (pay protect min ${min})`;
  }
  return baseLabel;
}

/** Separation scale maps to its own CPI card (1030 is no longer folded into 1708). */
export function mapScaleToCardRevision(scaleRevision) {
  return scaleRevision;
}

export function isSeparationScale1030(scaleRevision) {
  return scaleRevision === CPI_1030_REVISION;
}

/** Separation before 01/01/1988 (1979 / 1984 scales → 607 equivalent). */
export function isPre1988Separation(separationDate) {
  if (!separationDate) return false;
  const parsed = new Date(`${separationDate}T00:00:00`);
  if (Number.isNaN(parsed.getTime())) return false;
  return parsed < new Date("1988-01-01T00:00:00");
}

export function isPre1988ScaleRevision(scaleRevision) {
  return (
    scaleRevision === CPI_1979_REVISION ||
    scaleRevision === CPI_1984_REVISION
  );
}

export function resolvePre1988InitialPay(scaleRevision, equivalentScales) {
  if (!equivalentScales || !isPre1988ScaleRevision(scaleRevision)) {
    return null;
  }
  const stages = generatePayStages(String(equivalentScales[scaleRevision] || ""));
  return stages.length ? stages[0] : null;
}
/** Separation 01/01/1995–31/12/1996: map 1030→607, then flat 30% at 607 CPI. */
export function is1030Direct607Period(separationDate) {
  if (!separationDate) return false;
  const parsed = new Date(`${separationDate}T00:00:00`);
  if (Number.isNaN(parsed.getTime())) return false;
  const start = new Date("1995-01-01T00:00:00");
  const end = new Date("1996-12-31T00:00:00");
  return parsed >= start && parsed <= end;
}

export function map1030PayTo607(scale1030, scale607, lastPay) {
  return map1030PayTo607FromPdf(
    scale1030,
    scale607,
    lastPay,
    generatePayStages
  );
}

export function get607BasePayForRules(
  lastPay,
  scaleRevision,
  equivalentScales,
  separationDate = null
) {
  if (
    isSeparationScale1030(scaleRevision) &&
    equivalentScales &&
    !is1030Direct607Period(separationDate)
  ) {
    const mapped = map1030PayTo607(
      equivalentScales[CPI_1030_REVISION],
      equivalentScales[CPI_607_REVISION],
      lastPay
    );
    if (mapped != null) return mapped;
  }
  return Number(lastPay);
}

export function resolve607LastPay(lastPay) {
  const pay = Number(lastPay);
  if (Number.isNaN(pay) || pay <= 0) return null;

  if (pay <= 1499) {
    const effective = applyFactor(pay, 0.3, MIN_PAY_30);
    return {
      original: pay,
      effective,
      factor: 0.3,
      minimum: MIN_PAY_30,
      adjusted: effective !== pay,
    };
  }

  if (pay > 1500 && pay <= 3000) {
    const effective = applyFactor(pay, 0.2, MIN_PAY_20);
    return {
      original: pay,
      effective,
      factor: 0.2,
      minimum: MIN_PAY_20,
      adjusted: effective !== pay,
    };
  }

  if (pay > 3001) {
    const effective = applyFactor(pay, 0.15, MIN_PAY_15);
    return {
      original: pay,
      effective,
      factor: 0.15,
      minimum: MIN_PAY_15,
      adjusted: effective !== pay,
    };
  }

  return {
    original: pay,
    effective: pay,
    factor: null,
    minimum: null,
    adjusted: false,
  };
}

export function get607Pay(lastPay) {
  const resolved = resolve607LastPay(lastPay);
  return resolved?.effective ?? null;
}

export function get607ChainPay(lastPay) {
  const pay = get607Pay(lastPay);
  if (pay == null) return null;
  return roundUpWholeRupee(pay);
}

export function get607Direct1030ChainPay(lastPay, equivalentScales = null) {
  let pay = Number(lastPay);
  const mapped = map1030PayTo607(
    equivalentScales?.[CPI_1030_REVISION],
    equivalentScales?.[CPI_607_REVISION],
    lastPay
  );
  if (mapped != null) {
    pay = Number(mapped);
  }
  if (Number.isNaN(pay) || pay <= 0) return null;
  return roundUpWholeRupee(round2(pay * 0.3));
}

export function resolve607ChainPay(
  lastPay,
  scaleRevision,
  equivalentScales = null,
  separationDate = null
) {
  if (
    isSeparationScale1030(scaleRevision) &&
    is1030Direct607Period(separationDate)
  ) {
    return get607Direct1030ChainPay(lastPay, equivalentScales);
  }
  if (
    isPre1988Separation(separationDate) &&
    isPre1988ScaleRevision(scaleRevision) &&
    equivalentScales
  ) {
    const initial = resolvePre1988InitialPay(scaleRevision, equivalentScales);
    if (initial != null) return get607ChainPay(initial);
  }
  const base = get607BasePayForRules(
    lastPay,
    scaleRevision,
    equivalentScales,
    separationDate
  );
  return get607ChainPay(base);
}

function roundUpWholeRupee(value) {
  return Math.ceil(Number(value));
}

export function computeDaRelief(pay) {
  const value = Number(pay);
  if (Number.isNaN(value) || value <= 0) return null;

  const rate = value <= 758 ? 2.7525 : 1.8138;
  return Math.min(round2(value * rate), 1377);
}

export function compute1708Fitment(pay) {
  const value = Number(pay);
  if (Number.isNaN(value) || value <= 0) return null;
  return round2(value * 0.43);
}

export function compute1708Notional(pay, daRelief, fitment) {
  const total = Number(pay) + Number(daRelief) + Number(fitment);
  if (Number.isNaN(total)) return null;
  return roundUpWholeRupee(total);
}

export function startsFrom1708Cpi(startRevision) {
  return (
    startRevision === CPI_1708_REVISION || startRevision === CPI_1030_REVISION
  );
}

export function get1708DirectPay(lastPay) {
  const value = Number(lastPay);
  if (Number.isNaN(value) || value <= 0) return null;
  return round2(value * 0.3);
}

export function getSeparationScaleChainPay(
  lastPay,
  scaleRevision,
  equivalentScales = null,
  separationDate = null,
  startRevision = null
) {
  if (isSeparationScale1030(scaleRevision)) {
    return null;
  }
  if (
    isPre1988Separation(separationDate) &&
    startRevision === CPI_607_REVISION &&
    isPre1988ScaleRevision(scaleRevision) &&
    equivalentScales
  ) {
    return resolve607ChainPay(
      lastPay,
      scaleRevision,
      equivalentScales,
      separationDate
    );
  }
  if (scaleRevision === CPI_607_REVISION) {
    const base = get607BasePayForRules(
      lastPay,
      scaleRevision,
      equivalentScales,
      separationDate
    );
    return get607ChainPay(base);
  }
  if (!CPI_30_REVISIONS.has(scaleRevision)) {
    return null;
  }
  const raw = get1708DirectPay(lastPay);
  if (raw == null) return null;
  return roundUpWholeRupee(raw);
}

export function getFirstChainStagePay(
  lastPay,
  scaleRevision,
  startRevision,
  equivalentScales = null,
  separationDate = null
) {
  return getSeparationScaleChainPay(
    lastPay,
    scaleRevision,
    equivalentScales,
    separationDate,
    startRevision
  );
}

export function isSeparationScale1708(scaleRevision) {
  return scaleRevision === CPI_1708_REVISION;
}

export function buildPre1988SeparationCardRows(lastPay) {
  const pay = Number(lastPay);
  if (Number.isNaN(pay) || pay <= 0) return [];
  return [
    {
      row: "last-pay",
      description: "Last pay (at separation scale)",
      value: pay,
    },
  ];
}

export function build1030PayCardRows(lastPay) {
  const pay = Number(lastPay);
  if (Number.isNaN(pay) || pay <= 0) return [];

  return [
    {
      row: "last-pay",
      description: "Last pay (1030 CPI scale)",
      value: pay,
    },
  ];
}

export function build607CardRowsFromPre1988(scaleRevision, equivalentScales) {
  const initial = resolvePre1988InitialPay(scaleRevision, equivalentScales);
  if (initial == null) return [];

  const rows = [];
  const equiv607 = equivalentScales?.[CPI_607_REVISION];
  if (equiv607) {
    rows.push({
      row: "equiv-scale",
      description: "Equivalent scale at 607 CPI",
      value: String(equiv607).trim(),
    });
  }
  rows.push({
    row: "initial-pay",
    description: "Initial scale value (used as last pay)",
    value: initial,
  });

  const bandRows = build607PayCardRows(initial).filter(
    (row) => row.row !== "last-pay"
  );
  return [...rows, ...bandRows];
}

export function build607Direct1030CardRows(lastPay) {
  const pay = Number(lastPay);
  if (Number.isNaN(pay) || pay <= 0) return [];

  return [
    { row: "last-pay", description: "Last pay (1030 CPI scale)", value: pay },
  ];
}

export function build607CardRowsFrom1030(
  lastPay,
  equivalentScales,
  separationDate = null
) {
  if (is1030Direct607Period(separationDate)) {
    const mapped = map1030PayTo607(
      equivalentScales?.[CPI_1030_REVISION],
      equivalentScales?.[CPI_607_REVISION],
      lastPay
    );
    const basePay = mapped != null ? Number(mapped) : Number(lastPay);
    if (Number.isNaN(basePay) || basePay <= 0) return [];

    const rows = [
      { row: "last-pay", description: "Last pay (1030 CPI scale)", value: Number(lastPay) },
    ];
    if (mapped != null) {
      rows.push({
        row: "equiv-pay",
        description: "Equivalent pay at 607 CPI (parallel mapping)",
        value: mapped,
      });
    }
    const amount = round2(basePay * 0.3);
    const notional = roundUpWholeRupee(amount);
    rows.push(
      {
        row: "pay-amount",
        description: "Pay amount (30% of 607 equivalent pay)",
        value: amount,
      },
      {
        row: "notional",
        description: "Notional pay (rounded up, for next CPI)",
        value: notional,
      }
    );
    return rows;
  }

  const mapped = map1030PayTo607(
    equivalentScales?.[CPI_1030_REVISION],
    equivalentScales?.[CPI_607_REVISION],
    lastPay
  );
  if (mapped == null) return [];

  const rows = [
    {
      row: "equiv-pay",
      description: "Equivalent pay at 607 CPI (parallel mapping)",
      value: mapped,
    },
  ];

  const ruleRows = build607PayCardRows(mapped).filter((row) => row.row !== "last-pay");
  return [...rows, ...ruleRows];
}

export function buildSeparationScaleCardRows(lastPay, scaleRevision) {
  if (scaleRevision === CPI_607_REVISION) {
    return build607PayCardRows(lastPay);
  }

  const rawPay = get1708DirectPay(lastPay);
  if (rawPay == null) return [];

  return [
    {
      row: "pay",
      description: "Pay (30% of last pay)",
      value: rawPay,
    },
  ];
}

export function build1708CardRows(
  lastPay,
  scaleRevision,
  startRevision,
  equivalentScales = null,
  separationDate = null
) {
  if (isSeparationScale1708(scaleRevision)) {
    return buildSeparationScaleCardRows(lastPay, scaleRevision);
  }

  const pay = resolve607ChainPay(
    lastPay,
    scaleRevision,
    equivalentScales,
    separationDate
  );
  if (pay == null) return [];

  const daRelief = computeDaRelief(pay);
  const fitment = compute1708Fitment(pay);
  const rawNotional = compute1708Notional(pay, daRelief, fitment);
  const notional = protectNotional(rawNotional, CPI_1708_REVISION);

  return [
    { row: "pay", description: "Pay", value: pay },
    {
      row: "da-relief",
      description:
        pay <= 758
          ? "DA relief (275.25% of pay, max 1377)"
          : "DA relief (181.38% of pay, max 1377)",
      value: daRelief,
    },
    {
      row: "fitment",
      description: "Fitment @ 43% on pay",
      value: fitment,
    },
    {
      row: "notional",
      description: notionalLabel(
        "Pay + DA relief + fitment (rounded up)",
        rawNotional,
        CPI_1708_REVISION
      ),
      value: notional,
    },
  ];
}

export function compute1708NotionalFromLastPay(
  lastPay,
  scaleRevision,
  startRevision,
  equivalentScales = null,
  separationDate = null
) {
  if (isSeparationScale1708(scaleRevision)) {
    const raw = get1708DirectPay(lastPay);
    return raw == null ? null : roundUpWholeRupee(raw);
  }
  if (
    scaleRevision !== CPI_607_REVISION &&
    !isSeparationScale1030(scaleRevision) &&
    !(
      separationDate &&
      isPre1988Separation(separationDate) &&
      isPre1988ScaleRevision(scaleRevision)
    )
  ) {
    return null;
  }

  const pay = resolve607ChainPay(
    lastPay,
    scaleRevision,
    equivalentScales,
    separationDate
  );
  if (pay == null) return null;
  const daRelief = computeDaRelief(pay);
  const fitment = compute1708Fitment(pay);
  const notional = compute1708Notional(pay, daRelief, fitment);
  return protectNotional(notional, CPI_1708_REVISION);
}

export function compute126Da(pay) {
  const value = Number(pay);
  if (Number.isNaN(value) || value <= 0) return null;
  return round2(value * 0.782);
}

export function compute126Fitment(pay, da) {
  const base = Number(pay) + Number(da);
  if (Number.isNaN(base) || base <= 0) return null;
  return round2(base * 0.23);
}

export function compute126Notional(pay, da, fitment) {
  const total = Number(pay) + Number(da) + Number(fitment);
  if (Number.isNaN(total)) return null;
  return roundUpWholeRupee(total);
}

export function get126CpiPay(
  lastPay,
  scaleRevision,
  startRevision,
  equivalentScales = null,
  separationDate = null
) {
  if (startRevision === "2007(126 CPI)") {
    return getFirstChainStagePay(
      lastPay,
      scaleRevision,
      startRevision,
      equivalentScales,
      separationDate
    );
  }
  return compute1708NotionalFromLastPay(
    lastPay,
    scaleRevision,
    startRevision,
    equivalentScales,
    separationDate
  );
}

export function compute126NotionalFromLastPay(
  lastPay,
  scaleRevision,
  startRevision,
  equivalentScales = null,
  separationDate = null
) {
  const pay = get126CpiPay(
    lastPay,
    scaleRevision,
    startRevision,
    equivalentScales,
    separationDate
  );
  if (pay == null) return null;

  const da = compute126Da(pay);
  const fitment = compute126Fitment(pay, da);
  const raw = compute126Notional(pay, da, fitment);
  return protectNotional(raw, "2007(126 CPI)");
}

export function get198CpiPay(
  lastPay,
  scaleRevision,
  startRevision,
  equivalentScales = null,
  separationDate = null
) {
  if (startRevision === "2012(198 CPI)") {
    return getFirstChainStagePay(
      lastPay,
      scaleRevision,
      startRevision,
      equivalentScales,
      separationDate
    );
  }
  return compute126NotionalFromLastPay(
    lastPay,
    scaleRevision,
    startRevision,
    equivalentScales,
    separationDate
  );
}

export function compute198Da(pay) {
  const value = Number(pay);
  if (Number.isNaN(value) || value <= 0) return null;
  return round2(value * 0.5714);
}

export function compute198Fitment(pay, da) {
  const base = Number(pay) + Number(da);
  if (Number.isNaN(base) || base <= 0) return null;
  return round2(base * 0.105);
}

export function compute198Notional(pay, da, fitment) {
  const total = Number(pay) + Number(da) + Number(fitment);
  if (Number.isNaN(total)) return null;
  return roundUpWholeRupee(total);
}

export function build198CardRows(
  lastPay,
  scaleRevision,
  startRevision,
  equivalentScales = null,
  separationDate = null
) {
  const pay = get198CpiPay(
    lastPay,
    scaleRevision,
    startRevision,
    equivalentScales,
    separationDate
  );
  if (pay == null) return [];

  const da = compute198Da(pay);
  const fitment = compute198Fitment(pay, da);
  const rawNotional = compute198Notional(pay, da, fitment);
  const notional = protectNotional(rawNotional, "2012(198 CPI)");

  return [
    { row: "pay", description: "Pay", value: pay },
    {
      row: "da",
      description: "DA @ 57.14% on pay",
      value: da,
    },
    {
      row: "fitment",
      description: "Fitment @ 10.5% on (pay + DA)",
      value: fitment,
    },
    {
      row: "notional",
      description: notionalLabel(
        "Notional pay (pay + DA + fitment, rounded up)",
        rawNotional,
        "2012(198 CPI)"
      ),
      value: notional,
    },
  ];
}

export function compute198NotionalFromLastPay(
  lastPay,
  scaleRevision,
  startRevision,
  equivalentScales = null,
  separationDate = null
) {
  const pay = get198CpiPay(
    lastPay,
    scaleRevision,
    startRevision,
    equivalentScales,
    separationDate
  );
  if (pay == null) return null;
  const da = compute198Da(pay);
  const fitment = compute198Fitment(pay, da);
  const raw = compute198Notional(pay, da, fitment);
  return protectNotional(raw, "2012(198 CPI)");
}

export function get277CpiPay(
  lastPay,
  scaleRevision,
  startRevision,
  equivalentScales = null,
  separationDate = null
) {
  if (startRevision === "2017(277 CPI)") {
    return getFirstChainStagePay(
      lastPay,
      scaleRevision,
      startRevision,
      equivalentScales,
      separationDate
    );
  }
  return compute198NotionalFromLastPay(
    lastPay,
    scaleRevision,
    startRevision,
    equivalentScales,
    separationDate
  );
}

export function compute277Da(pay) {
  const value = Number(pay);
  if (Number.isNaN(value) || value <= 0) return null;
  return round2(value * 0.4);
}

export function compute277Fitment(pay, da) {
  const base = Number(pay) + Number(da);
  if (Number.isNaN(base) || base <= 0) return null;
  return round2(base * 0.106);
}

export function compute277Notional(pay, da, fitment) {
  const total = Number(pay) + Number(da) + Number(fitment);
  if (Number.isNaN(total)) return null;
  return roundUpWholeRupee(total);
}

export function build277CardRows(
  lastPay,
  scaleRevision,
  startRevision,
  equivalentScales = null,
  separationDate = null
) {
  const pay = get277CpiPay(
    lastPay,
    scaleRevision,
    startRevision,
    equivalentScales,
    separationDate
  );
  if (pay == null) return [];

  const da = compute277Da(pay);
  const fitment = compute277Fitment(pay, da);
  const rawNotional = compute277Notional(pay, da, fitment);
  const notional = protectNotional(rawNotional, "2017(277 CPI)");

  return [
    { row: "pay", description: "Pay", value: pay },
    {
      row: "da",
      description: "DA @ 40% on pay",
      value: da,
    },
    {
      row: "fitment",
      description: "Fitment @ 10.6% on (pay + DA)",
      value: fitment,
    },
    {
      row: "notional",
      description: notionalLabel(
        "Notional pay (pay + DA + fitment, rounded up)",
        rawNotional,
        "2017(277 CPI)"
      ),
      value: notional,
    },
  ];
}

export function compute277NotionalFromLastPay(
  lastPay,
  scaleRevision,
  startRevision,
  equivalentScales = null,
  separationDate = null
) {
  const pay = get277CpiPay(
    lastPay,
    scaleRevision,
    startRevision,
    equivalentScales,
    separationDate
  );
  if (pay == null) return null;
  const da = compute277Da(pay);
  const fitment = compute277Fitment(pay, da);
  const raw = compute277Notional(pay, da, fitment);
  return protectNotional(raw, "2017(277 CPI)");
}

export function get359CpiPay(
  lastPay,
  scaleRevision,
  startRevision,
  equivalentScales = null,
  separationDate = null
) {
  if (startRevision === "2022(359 CPI)") {
    return getFirstChainStagePay(
      lastPay,
      scaleRevision,
      startRevision,
      equivalentScales,
      separationDate
    );
  }
  return compute277NotionalFromLastPay(
    lastPay,
    scaleRevision,
    startRevision,
    equivalentScales,
    separationDate
  );
}

export function compute359Da(pay) {
  const value = Number(pay);
  if (Number.isNaN(value) || value <= 0) return null;
  return round2(value * 0.3);
}

export function compute359Fitment(pay, da) {
  const base = Number(pay) + Number(da);
  if (Number.isNaN(base) || base <= 0) return null;
  return round2(base * 0.085);
}

export function compute359Notional(pay, da, fitment) {
  const total = Number(pay) + Number(da) + Number(fitment);
  if (Number.isNaN(total)) return null;
  return roundUpWholeRupee(total);
}

export function build359CardRows(
  lastPay,
  scaleRevision,
  startRevision,
  equivalentScales = null,
  separationDate = null
) {
  const pay = get359CpiPay(
    lastPay,
    scaleRevision,
    startRevision,
    equivalentScales,
    separationDate
  );
  if (pay == null) return [];

  const da = compute359Da(pay);
  const fitment = compute359Fitment(pay, da);
  const rawNotional = compute359Notional(pay, da, fitment);
  const notional = protectNotional(rawNotional, "2022(359 CPI)");

  return [
    { row: "pay", description: "Pay", value: pay },
    {
      row: "da",
      description: "DA @ 30% on pay",
      value: da,
    },
    {
      row: "fitment",
      description: "Fitment @ 8.5% on (pay + DA)",
      value: fitment,
    },
    {
      row: "notional",
      description: notionalLabel(
        "Notional pay (pay + DA + fitment, rounded up)",
        rawNotional,
        "2022(359 CPI)"
      ),
      value: notional,
    },
  ];
}

export function build126CardRows(
  lastPay,
  scaleRevision,
  startRevision,
  equivalentScales = null,
  separationDate = null
) {
  const pay = get126CpiPay(
    lastPay,
    scaleRevision,
    startRevision,
    equivalentScales,
    separationDate
  );
  if (pay == null) return [];

  const da = compute126Da(pay);
  const fitment = compute126Fitment(pay, da);
  const rawNotional = compute126Notional(pay, da, fitment);
  const notional = protectNotional(rawNotional, "2007(126 CPI)");

  return [
    { row: "pay", description: "Pay", value: pay },
    {
      row: "da",
      description: "DA @ 78.2% on pay",
      value: da,
    },
    {
      row: "fitment",
      description: "Fitment @ 23% on (pay + DA)",
      value: fitment,
    },
    {
      row: "notional",
      description: notionalLabel(
        "Pay + DA + fitment (rounded up)",
        rawNotional,
        "2007(126 CPI)"
      ),
      value: notional,
    },
  ];
}

export function build607PayCardRows(lastPay) {
  const resolved = resolve607LastPay(lastPay);
  if (!resolved) return [];

  const rows = [
    { row: "last-pay", description: "Last pay", value: resolved.original },
  ];

  if (resolved.adjusted) {
    const floorNote =
      resolved.effective === resolved.minimum
        ? `, min ${resolved.minimum}`
        : "";
    rows.push({
      row: "pay-amount",
      description: `Pay amount (${resolved.factor * 100}% of last pay${floorNote})`,
      value: resolved.effective,
    });
    rows.push({
      row: "notional",
      description: "Notional pay (rounded up, for next CPI)",
      value: roundUpWholeRupee(resolved.effective),
    });
  } else {
    rows.push({
      row: "pay-amount",
      description: "Pay amount (as per last pay)",
      value: resolved.effective,
    });
  }

  return rows;
}

function build607BridgedCardRows(
  lastPay,
  scaleRevision,
  startRevision,
  equivalentScales,
  separationDate = null
) {
  if (isSeparationScale1030(scaleRevision)) {
    return build607CardRowsFrom1030(lastPay, equivalentScales, separationDate);
  }
  if (
    isPre1988Separation(separationDate) &&
    isPre1988ScaleRevision(scaleRevision)
  ) {
    return build607CardRowsFromPre1988(scaleRevision, equivalentScales);
  }
  return build607PayCardRows(lastPay);
}

export const METHODOLOGY1_CARDS = [
  {
    revision: CPI_1979_REVISION,
    title: "1979 (Revised Pay Scale)",
    build: (lastPay) => buildPre1988SeparationCardRows(lastPay),
  },
  {
    revision: CPI_1984_REVISION,
    title: "1984 (Revised Pay Scale)",
    build: (lastPay) => buildPre1988SeparationCardRows(lastPay),
  },
  {
    revision: CPI_1030_REVISION,
    title: "1993 (1030 CPI)",
    build: build1030PayCardRows,
  },
  {
    revision: CPI_607_REVISION,
    title: "1988 (607 CPI)",
    build: build607BridgedCardRows,
  },
  {
    revision: CPI_1708_REVISION,
    title: "1997 (1708 CPI)",
    build: build1708CardRows,
  },
  {
    revision: "2007(126 CPI)",
    title: "2007 (126 CPI)",
    build: build126CardRows,
  },
  {
    revision: "2012(198 CPI)",
    title: "2012 (198 CPI)",
    build: build198CardRows,
  },
  {
    revision: "2017(277 CPI)",
    title: "2017 (277 CPI)",
    build: build277CardRows,
  },
  {
    revision: "2022(359 CPI)",
    title: "2022 (359 CPI)",
    build: build359CardRows,
  },
];

export function getMethodology1CardStartIndex(startRevision) {
  if (!startRevision) return -1;
  if (startRevision === CPI_1030_REVISION) {
    return METHODOLOGY1_CARDS.findIndex(
      (card) => card.revision === CPI_1708_REVISION
    );
  }
  return METHODOLOGY1_CARDS.findIndex(
    (card) => card.revision === startRevision
  );
}

export function getMethodology1VisibleCards(scaleRevision, startRevision) {
  const indices = new Set();
  const startIdx = getMethodology1CardStartIndex(startRevision);

  if (scaleRevision === CPI_1030_REVISION) {
    const idx1030 = METHODOLOGY1_CARDS.findIndex(
      (card) => card.revision === CPI_1030_REVISION
    );
    const idx607 = METHODOLOGY1_CARDS.findIndex(
      (card) => card.revision === CPI_607_REVISION
    );
    if (idx1030 >= 0) indices.add(idx1030);
    if (idx607 >= 0) indices.add(idx607);
  } else if (isPre1988ScaleRevision(scaleRevision)) {
    const scaleIdx = METHODOLOGY1_CARDS.findIndex(
      (card) => card.revision === scaleRevision
    );
    const idx607 = METHODOLOGY1_CARDS.findIndex(
      (card) => card.revision === CPI_607_REVISION
    );
    if (scaleIdx >= 0) indices.add(scaleIdx);
    if (idx607 >= 0) indices.add(idx607);
  } else {
    const scaleIdx = METHODOLOGY1_CARDS.findIndex(
      (card) => card.revision === scaleRevision
    );
    if (scaleIdx >= 0) indices.add(scaleIdx);
  }

  if (startIdx >= 0) {
    for (let i = startIdx; i < METHODOLOGY1_CARDS.length; i += 1) {
      indices.add(i);
    }
  }

  return [...indices]
    .sort((a, b) => a - b)
    .map((i) => METHODOLOGY1_CARDS[i]);
}

export function buildMethodology1CardRows(
  card,
  lastPay,
  scaleRevision,
  startRevision,
  equivalentScales = null,
  separationDate = null
) {
  if (card.revision === CPI_1030_REVISION) {
    return build1030PayCardRows(lastPay);
  }

  if (
    card.revision === CPI_1979_REVISION ||
    card.revision === CPI_1984_REVISION
  ) {
    return buildPre1988SeparationCardRows(lastPay);
  }

  if (card.revision === CPI_607_REVISION && isSeparationScale1030(scaleRevision)) {
    return build607CardRowsFrom1030(lastPay, equivalentScales, separationDate);
  }

  if (
    card.revision === CPI_607_REVISION &&
    isPre1988ScaleRevision(scaleRevision)
  ) {
    return build607CardRowsFromPre1988(scaleRevision, equivalentScales);
  }

  const startCard =
    startRevision === CPI_1030_REVISION ? CPI_1708_REVISION : startRevision;

  if (card.revision === scaleRevision && card.revision !== startCard) {
    return buildSeparationScaleCardRows(lastPay, scaleRevision);
  }
  if (card.revision === scaleRevision && card.revision === startCard) {
    return buildSeparationScaleCardRows(lastPay, scaleRevision);
  }

  if (card.revision === CPI_607_REVISION) {
    return build607PayCardRows(lastPay);
  }

  return card.build(
    lastPay,
    scaleRevision,
    startRevision,
    equivalentScales,
    separationDate
  );
}
