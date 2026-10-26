import { useEffect, useMemo, useState } from "react";
import API from "../services/Api";
import Methodology2ConsolidationPrint from "./Methodology2ConsolidationPrint";
import MethodologyClass12Result from "./MethodologyClass12Result";
import { buildRevisionCards } from "../utils/methodology2RevisionCards";
import { ensureClass12OpeningBasic } from "../utils/methodology2RevisionCards";
import { formatCardValue } from "../utils/methodology2RevisionCards";
import { printMethodology2Consolidation } from "../utils/methodology2Print";
import {
  isProportionateReduced,
  proportionateNoteFromPension,
} from "../utils/methodology2ProportionatePension";

function PensionBlock({ title, basic, pension, familyPension }) {
  return (
    <div className="col-md-6">
      <div className="border rounded p-3 h-100 bg-light">
        <h6 className="fw-bold text-primary mb-3">{title}</h6>
        <table className="table table-sm table-borderless mb-0">
          <tbody>
            <tr>
              <td className="text-muted">Calculated basic</td>
              <td className="text-end fw-semibold">
                Rs. {formatCardValue(basic)}
              </td>
            </tr>
            <tr>
              <td className="text-muted">Pension (50% of basic)</td>
              <td className="text-end fw-semibold text-primary">
                Rs. {formatCardValue(pension)}
              </td>
            </tr>
            <tr>
              <td className="text-muted">Family pension (30% of basic)</td>
              <td className="text-end fw-semibold text-success">
                Rs. {formatCardValue(familyPension)}
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  );
}

const REVISION_YEARS = [
  1979, 1984, 1988, 1993, 1997, 2007, 2012, 2017, 2022,
];

/** Class 1/2 stages only (no 2012/2022). */
const CLASS12_REVISION_YEARS = [1984, 1987, 1992, 1997, 2007, 2017];

/** Next CPI year for "As per {year} Wage Revision Order". */
function nextWageRevisionYear(revisionKeyOrTitle) {
  const m = String(revisionKeyOrTitle || "").match(/(\d{4})/);
  if (!m) return null;
  const year = Number(m[1]);
  const idx = REVISION_YEARS.indexOf(year);
  if (idx < 0 || idx >= REVISION_YEARS.length - 1) return null;
  return REVISION_YEARS[idx + 1];
}

function nextClass12WageRevisionYear(revisionKeyOrTitle) {
  const m = String(revisionKeyOrTitle || "").match(/(\d{4})/);
  if (!m) return null;
  const year = Number(m[1]);
  const idx = CLASS12_REVISION_YEARS.indexOf(year);
  if (idx < 0 || idx >= CLASS12_REVISION_YEARS.length - 1) return null;
  return CLASS12_REVISION_YEARS[idx + 1];
}

function withWageRevisionOrder(title, revisionKey) {
  const text = String(title || "");
  if (/As per\s+\d{4}\s+Wage Revision Order/i.test(text)) return text;
  const next = nextWageRevisionYear(revisionKey || text);
  if (!next) return text;
  return `${text} — As per ${next} Wage Revision Order`;
}

/** Class 3/4 ends each CPI block on Notional Pay (final 2022 keeps Basic Pay).
 *  Class 1/2: rename last-row Basic Pay… → Notional Pay…, except final 01.01.2017.
 */
function class12NotionalizeLastDescription(desc) {
  const text = String(desc || "").trim();
  if (!text) return text;
  if (/^Basic\s+Pay\s+as\s+on\s+01\.01\.2017$/i.test(text)) return text;
  if (/Notional/i.test(text)) return text;
  if (/^Basic\s+[Pp]ay\b/.test(text)) {
    return text.replace(/^Basic\s+[Pp]ay/, "Notional Pay");
  }
  return text;
}

function class12RoundNote(desc) {
  const text = String(desc || "").trim();
  if (!text || /Rounded to the next 10/i.test(text)) return text;
  if (/minimum basic/i.test(text)) return text;
  if (/^Basic\s+Pay\s+as\s+on\s+01\.01\.2017$/i.test(text)) return text;
  if (/Notional/i.test(text) || /Basic Pay Over/i.test(text)) {
    return `${text} (Rounded to the next 10 Rupees)`;
  }
  return text;
}

function withClass12WageRevisionOrder(title, revisionKey) {
  let text = String(title || "")
    .replace(/Wage Revision Order/gi, "Pay Revision Order")
    .replace(/\s*[—\-]\s*As per\s+2022\s+Pay Revision Order/gi, "")
    .trim();
  if (/As per\s+\d{4}\s+Pay Revision Order/i.test(text)) return text;
  const next = nextClass12WageRevisionYear(revisionKey || text);
  if (!next) return text;
  return `${text} — As per ${next} Pay Revision Order`;
}

function cardsToRevisionBlocks(cards, equivalentScales = null) {
  const scales = equivalentScales || {};
  return cards.map((card) => {
    const raw = scales[card.revisionKey];
    let scaleBand = "";
    if (typeof raw === "string") {
      const parts = raw.split("-").map((p) => p.trim()).filter(Boolean);
      const nums = parts.map((p) => Number(p)).filter((n) => !Number.isNaN(n));
      if (nums.length >= 2) {
        scaleBand = `${nums[0]}-${nums[nums.length - 1]}`;
      } else {
        scaleBand = raw;
      }
    }
    const yearCpi = String(card.revisionKey || "").match(
      /^(\d{4})\((\d+)\s*CPI\)$/i
    );
    let title = card.title;
    if (yearCpi) {
      title = `Detailed Calculation Breakdown Year ${yearCpi[1]} - CPI ${yearCpi[2]}`;
      if (scaleBand) title += ` (${scaleBand})`;
    } else if (scaleBand) {
      title = `${card.title} (${scaleBand})`;
    }
    title = withWageRevisionOrder(title, card.revisionKey);
    return {
      revision_key: card.revisionKey,
      title,
      scale_band: scaleBand,
      rows: (card.rows || []).map((r) => ({
        row: r.row,
        code: r.code || "",
        description: r.description,
        value: r.value,
      })),
    };
  });
}

/**
 * Source-year titles (class 3/4 style). Stage-ending lines name the
 * destination basic; print labels the block as the source scale year.
 * Final "Basic Pay as on 01.01.2017" is the 277 CPI destination block
 * (mirrors class 3/4 last 359 CPI block).
 */
function class12BlockTitle(lastDescription, startRevision = "") {
  const desc = String(lastDescription || "");
  if (/Basic Pay as on 01\.01\.2017/i.test(desc)) {
    return ["Detailed Calculation Breakdown Year 2017 - CPI 277", "2017"];
  }
  if (/Basic Pay Over.*277|277\s*CPI Points/i.test(desc)) {
    return ["Detailed Calculation Breakdown Year 2007 - CPI 126", "2007"];
  }
  if (/126\s*CPI|01\.01\.2007/i.test(desc)) {
    return ["Detailed Calculation Breakdown Year 1997 - CPI 1708", "1997"];
  }
  if (/1708|01\.01\.1997/i.test(desc)) {
    return ["Year 1992 (Revised Pay Scale)", "1992"];
  }
  if (/01\.01\.1992/i.test(desc)) return ["Year 1987 (Revised Pay Scale)", "1987"];
  if (/01\.01\.1987/i.test(desc)) return ["Year 1984 (Revised Pay Scale)", "1984"];
  if (/01\.01\.1984|1984/i.test(desc)) {
    return ["Year 1984 (Revised Pay Scale)", "1984"];
  }
  const start = String(startRevision || "").trim() || "start";
  return [`Year ${start} (Revised Pay Scale)`, start];
}

/** Split class 1/2 flat rows into year print blocks. */
export function buildClass12RevisionBlocks(
  calculationRows,
  startRevision = "",
  equivalentScales = null
) {
  const rows = (calculationRows || []).filter((r) => r && typeof r === "object");
  if (!rows.length) return [];

  const scales = equivalentScales || {};
  const scaleFor = (key) => {
    const raw = scales[key] || scales[String(key)] || "";
    if (raw && typeof raw === "object") {
      return raw.scale || raw.pay_band || raw.label || "";
    }
    if (typeof raw !== "string") return "";
    const parts = raw.split("-").map((p) => p.trim()).filter(Boolean);
    const nums = parts.map((p) => Number(p)).filter((n) => !Number.isNaN(n));
    if (nums.length >= 2) return `${nums[0]}-${nums[nums.length - 1]}`;
    return raw.trim();
  };
  const withScale = (title, key) => {
    const band = scaleFor(key);
    if (band && !title.includes(`(${band})`)) return `${title} (${band})`;
    return title;
  };

  const blocks = [];
  let current = [];

  const flush = () => {
    if (!current.length) return;
    const lastDesc = current[current.length - 1].description || "";
    let [title, key] = class12BlockTitle(lastDesc, startRevision);
    if (current.length === 1 && /existing scale/i.test(lastDesc)) {
      key = String(startRevision || "start");
      if (key === "1997") {
        title = "Detailed Calculation Breakdown Year 1997 - CPI 1708";
      } else if (key === "2007") {
        title = "Detailed Calculation Breakdown Year 2007 - CPI 126";
      } else if (key === "2017") {
        title = "Detailed Calculation Breakdown Year 2017 - CPI 277";
      } else {
        title = `Year ${key} (Revised Pay Scale)`;
      }
    }
    title = withScale(title, key);
    title = withClass12WageRevisionOrder(title, key);
    const lastIdx = current.length - 1;
    blocks.push({
      revision_key: key,
      title,
      scale_band: scaleFor(key),
      rows: current.map((r, idx) => ({
        row: r.row ?? idx + 1,
        // Class 1/2 calc rows have no Excel codes — A, B, C… per year block.
        code:
          String(r.code || "").trim() ||
          (idx < 26 ? String.fromCharCode(65 + idx) : String(idx + 1)),
        description: class12RoundNote(
          idx === lastIdx
            ? class12NotionalizeLastDescription(r.description)
            : r.description
        ),
        value: r.value,
      })),
    });
    current = [];
  };

  rows.forEach((row) => {
    current.push(row);
    const desc = String(row.description || "");
    const endsStage =
      /minimum basic/i.test(desc) ||
      /Basic Pay Over/i.test(desc) ||
      (/Basic pay as on/i.test(desc) && !/existing scale/i.test(desc));
    if (endsStage) flush();
  });
  flush();
  return ensureClass12OpeningBasic(blocks);
}

function normalizePensionSummary(pensionSummary, class12Result) {
  if (pensionSummary) return pensionSummary;
  if (!class12Result) return null;
  return {
    basic_pay_2017: class12Result.basic_pay_2017,
    basic_pay_2022: null,
    pension_277_cpi: class12Result.pension,
    pension_359_cpi: null,
    family_pension_277_cpi: class12Result.family_pension,
    family_pension_359_cpi: null,
    proportionate: class12Result.proportionate || null,
  };
}

export default function Methodology2PensionSummary({
  pensionSummary = null,
  class12Result = null,
  retirementDate,
  scale,
  lastPay,
  stagnationAmount = "",
  npaAmount = "",
  includeBunching = false,
  isDoctor = false,
  effectivePay = null,
  empId = "",
  employeeName = "",
  category = "",
  startRevision = "",
  calculationRows = [],
  equivalentScales = null,
  printMaster = null,
  dateOfBirth = "",
  oldageBenefit = null,
}) {
  const [snapshot, setSnapshot] = useState(null);
  const [saving, setSaving] = useState(false);
  const [saveMsg, setSaveMsg] = useState("");
  const [saveOk, setSaveOk] = useState(false);

  const isClass12 = category === "1" || category === "2" || Boolean(class12Result);
  const effectivePension = useMemo(
    () => normalizePensionSummary(pensionSummary, class12Result),
    [pensionSummary, class12Result]
  );
  const effectiveRows = useMemo(() => {
    if (class12Result?.rows?.length) return class12Result.rows;
    return calculationRows || [];
  }, [class12Result, calculationRows]);
  const effectiveStart =
    startRevision || class12Result?.start_revision || "";
  const effectiveScale =
    scale ||
    class12Result?.scale_display ||
    class12Result?.grade ||
    "";

  const effectiveEquivalentScales = useMemo(() => {
    if (class12Result?.equivalent_scales) return class12Result.equivalent_scales;
    return equivalentScales || null;
  }, [class12Result, equivalentScales]);

  const liveBlocks = useMemo(() => {
    if (isClass12 || effectiveRows.some((r) => r && r.row == null)) {
      return buildClass12RevisionBlocks(
        effectiveRows,
        effectiveStart,
        effectiveEquivalentScales
      );
    }
    const cards = buildRevisionCards(effectiveRows, effectiveStart);
    return cardsToRevisionBlocks(cards, effectiveEquivalentScales);
  }, [
    isClass12,
    effectiveRows,
    effectiveStart,
    effectiveEquivalentScales,
  ]);

  const liveSnapshot = useMemo(() => {
    if (!effectivePension) return null;
    const master = printMaster || {};
    const employeeCase = !!master.is_employee_pension;
    const m2_277 = effectivePension.family_pension_277_cpi;
    const m2_359 = effectivePension.family_pension_359_cpi;
    // m1_* is Methodology-1 pension already in payment (employee or family).
    const m1_277 = master.m1_family_pension_277 ?? null;
    const m1_359 = master.m1_family_pension_359 ?? null;
    const compared277 = employeeCase
      ? effectivePension.pension_277_cpi
      : m2_277;
    const compared359 = employeeCase
      ? effectivePension.pension_359_cpi
      : m2_359;
    const stagNum = Number(stagnationAmount);
    const stagnation =
      stagnationAmount !== "" &&
      stagnationAmount != null &&
      !Number.isNaN(stagNum)
        ? stagNum
        : null;
    return {
      emp_cd: empId || master.emp_cd || "",
      name: employeeName || master.name || "",
      wage_emp_name: master.wage_emp_name || "",
      pensioner_name: master.pensioner_name || "",
      is_employee_pension: master.is_employee_pension || false,
      date_of_death: master.date_of_death || null,
      family_pensioner_dob: master.family_pensioner_dob || null,
      double_fpension_upto: master.double_fpension_upto || null,
      enhanced_family_pension: !!master.enhanced_family_pension,
      case_no: master.case_no || "",
      roll_no: master.roll_no || "",
      retirement_type: master.retirement_type || "",
      retirement_date: retirementDate || master.retirement_date || null,
      date_of_birth:
        dateOfBirth || master.date_of_birth || master.dob || null,
      category: String(category || master.category || ""),
      designation: master.designation || "",
      tqs: master.tqs || "",
      tqs_yr: master.tqs_yr,
      tqs_month: master.tqs_month,
      tqs_days: master.tqs_days,
      // Average Pay entered on the family header form; else the last pay.
      average_pay:
        master.average_pay != null && String(master.average_pay).trim() !== ""
          ? master.average_pay
          : lastPay,
      last_pay: lastPay,
      stagnation_amount: stagnation,
      npa_amount:
        npaAmount !== "" && npaAmount != null && !Number.isNaN(Number(npaAmount))
          ? Number(npaAmount)
          : null,
      doctor_flg: isDoctor ? 1 : 0,
      apply_bunching: isDoctor ? !!includeBunching : true,
      scale: effectiveScale,
      start_revision: effectiveStart,
      revision_blocks: liveBlocks,
      calculation_rows: effectiveRows,
      m2_basic_2017: effectivePension.basic_pay_2017,
      m2_basic_2022: effectivePension.basic_pay_2022,
      m2_pension_277: effectivePension.pension_277_cpi,
      m2_pension_359: effectivePension.pension_359_cpi,
      m2_family_pension_277: m2_277,
      m2_family_pension_359: m2_359,
      m1_family_pension_277: m1_277,
      m1_family_pension_359: m1_359,
      m1_bunching:
        isDoctor && !includeBunching ? null : master.m1_bunching || null,
      diff_family_pension_277:
        compared277 != null && m1_277 != null
          ? Number(compared277) - Number(m1_277)
          : null,
      diff_family_pension_359:
        compared359 != null && m1_359 != null
          ? Number(compared359) - Number(m1_359)
          : null,
      // OA mid-CPI columns + calc table (from oldage/calculate) so preview = print
      pension_comparison: oldageBenefit?.pension_comparison || undefined,
    };
  }, [
    effectivePension,
    printMaster,
    empId,
    employeeName,
    retirementDate,
    category,
    lastPay,
    stagnationAmount,
    npaAmount,
    includeBunching,
    isDoctor,
    effectiveScale,
    effectiveStart,
    liveBlocks,
    effectiveRows,
    dateOfBirth,
    oldageBenefit,
  ]);

  useEffect(() => {
    setSnapshot(liveSnapshot);
    setSaveMsg("");
    setSaveOk(false);
  }, [liveSnapshot]);

  if (!effectivePension) return null;

  const openPrintDialog = () => {
    printMethodology2Consolidation(liveSnapshot?.case_no);
  };

  /** Print only. Does not write the consolidation row. */
  const handlePrint = () => {
    if (!liveSnapshot) return;
    openPrintDialog();
  };

  /** Persist one DB row only when the user clicks Save (not on print or calc). */
  const handleSave = async () => {
    if (!liveSnapshot) return;

    const emp = String(empId || liveSnapshot.emp_cd || "").trim();
    if (!emp) {
      setSaveOk(false);
      setSaveMsg("Employee id required to save");
      return;
    }

    setSaving(true);
    setSaveMsg("");
    setSaveOk(false);
    try {
      const payload = {
        ...liveSnapshot,
        emp_cd: emp,
        equivalent_scales: effectiveEquivalentScales || {},
        pension: effectivePension,
        date_of_birth: dateOfBirth || printMaster?.date_of_birth || null,
        oldage_benefit: oldageBenefit || null,
      };
      await API.post(`m2-oldage-arrear/consolidation/${emp}/`, payload);
      setSaveOk(true);
      setSaveMsg("Saved to database");
    } catch (err) {
      console.error(err);
      setSaveOk(false);
      setSaveMsg(
        err.response?.data?.error || "Could not save consolidation"
      );
    } finally {
      setSaving(false);
    }
  };

  const actionButtons = (
    <div className="d-flex align-items-center gap-2">
      <button
        type="button"
        className="btn btn-outline-light btn-sm"
        onClick={handleSave}
        disabled={!liveSnapshot || saving}
      >
        {saving ? "Saving…" : "Save"}
      </button>
      <button
        type="button"
        className="btn btn-light btn-sm"
        onClick={handlePrint}
        disabled={!liveSnapshot}
      >
        Print
      </button>
    </div>
  );

  const statusNotice = (
    <>
      {saveMsg ? (
        <div
          className={`alert py-2 px-3 mt-2 mb-0 small ${
            saveOk ? "alert-success" : "alert-danger"
          }`}
          role="status"
        >
          {saveMsg}
        </div>
      ) : null}
      {isProportionateReduced(effectivePension) ? (
        <div className="alert alert-warning py-2 px-3 mt-2 mb-0 small">
          {proportionateNoteFromPension(effectivePension)}
        </div>
      ) : null}
    </>
  );

  if (isClass12 && class12Result) {
    return (
      <>
        <MethodologyClass12Result
          category={category}
          class12Result={class12Result}
          headerExtra={actionButtons}
          notice={statusNotice}
        />
        <Methodology2ConsolidationPrint snapshot={snapshot} />
      </>
    );
  }

  return (
    <>
      <div className="row justify-content-center mt-4 no-print">
        <div className="col-md-10">
          <div className="card shadow border-primary">
            <div className="card-header bg-primary text-white d-flex justify-content-between align-items-center">
              <h5 className="mb-0">Pension (from calculated basic)</h5>
              {actionButtons}
            </div>
            <div className="card-body">
              <div className="mb-3 small text-muted">
                {empId && (
                  <div>
                    <strong>Employee:</strong> {empId}
                    {employeeName ? ` — ${employeeName}` : ""}
                  </div>
                )}
                <div>
                  <strong>Save</strong> writes one database row (employee,
                  revision blocks, and pension) and does not print.{" "}
                  <strong>Print</strong> opens the print dialog and does not
                  save. Header title &amp; FA/CAO footer are print-only.
                </div>
                {statusNotice}
              </div>

              <div className="row g-3">
                <PensionBlock
                  title="2022 (359 CPI)"
                  basic={effectivePension.basic_pay_2022}
                  pension={effectivePension.pension_359_cpi}
                  familyPension={effectivePension.family_pension_359_cpi}
                />
                <PensionBlock
                  title="2017 (277 CPI)"
                  basic={effectivePension.basic_pay_2017}
                  pension={effectivePension.pension_277_cpi}
                  familyPension={effectivePension.family_pension_277_cpi}
                />
              </div>
            </div>
          </div>
        </div>
      </div>

      <Methodology2ConsolidationPrint snapshot={snapshot} />
    </>
  );
}
