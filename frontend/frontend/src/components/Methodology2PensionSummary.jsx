import { useEffect, useMemo, useState } from "react";
import API from "../services/Api";
import Methodology2ConsolidationPrint from "./Methodology2ConsolidationPrint";
import { buildRevisionCards } from "../utils/methodology2RevisionCards";
import { formatCardValue } from "../utils/methodology2RevisionCards";
import { printMethodology2Consolidation } from "../utils/methodology2Print";

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

function class12BlockTitle(lastDescription, startRevision = "") {
  const desc = String(lastDescription || "");
  if (/277\s*CPI|01\.01\.2017/i.test(desc)) {
    return ["Detailed Calculation Breakdown Year 2017 - CPI 277", "2017"];
  }
  if (/126\s*CPI|01\.01\.2007/i.test(desc)) {
    return ["Detailed Calculation Breakdown Year 2007 - CPI 126", "2007"];
  }
  if (/1708|01\.01\.1997/i.test(desc)) {
    return ["Year 1997 (Revised Pay Scale)", "1997"];
  }
  if (/01\.01\.1992/i.test(desc)) return ["Year 1992 (Revised Pay Scale)", "1992"];
  if (/01\.01\.1987/i.test(desc)) return ["Year 1987 (Revised Pay Scale)", "1987"];
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
    if (
      current.length === 1 &&
      /existing scale/i.test(lastDesc)
    ) {
      title = `Year ${startRevision || "start"} (opening basic)`;
      key = String(startRevision || "start");
    }
    title = withScale(title, key);
    blocks.push({
      revision_key: key,
      title,
      scale_band: scaleFor(key),
      rows: current.map((r, idx) => ({
        row: r.row ?? idx + 1,
        code: r.code || "",
        description: r.description,
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
  return blocks;
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
  };
}

export default function Methodology2PensionSummary({
  pensionSummary = null,
  class12Result = null,
  retirementDate,
  scale,
  lastPay,
  empId = "",
  employeeName = "",
  category = "",
  startRevision = "",
  calculationRows = [],
  equivalentScales = null,
  printMaster = null,
}) {
  const [snapshot, setSnapshot] = useState(null);
  const [saving, setSaving] = useState(false);
  const [saveMsg, setSaveMsg] = useState("");

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
    const m2_277 = effectivePension.family_pension_277_cpi;
    const m2_359 = effectivePension.family_pension_359_cpi;
    const m1_277 = master.m1_family_pension_277 ?? null;
    const m1_359 = master.m1_family_pension_359 ?? null;
    return {
      emp_cd: empId || master.emp_cd || "",
      name: employeeName || master.name || "",
      wage_emp_name: master.wage_emp_name || "",
      pensioner_name: master.pensioner_name || "",
      is_employee_pension: master.is_employee_pension || false,
      case_no: master.case_no || "",
      roll_no: master.roll_no || "",
      retirement_date: retirementDate || master.retirement_date || null,
      category: String(category || master.category || ""),
      designation: master.designation || "",
      tqs: master.tqs || "",
      tqs_yr: master.tqs_yr,
      tqs_month: master.tqs_month,
      tqs_days: master.tqs_days,
      average_pay: lastPay,
      last_pay: lastPay,
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
      diff_family_pension_277:
        m2_277 != null && m1_277 != null
          ? Number(m2_277) - Number(m1_277)
          : null,
      diff_family_pension_359:
        m2_359 != null && m1_359 != null
          ? Number(m2_359) - Number(m1_359)
          : null,
    };
  }, [
    effectivePension,
    printMaster,
    empId,
    employeeName,
    retirementDate,
    category,
    lastPay,
    effectiveScale,
    effectiveStart,
    liveBlocks,
    effectiveRows,
  ]);

  useEffect(() => {
    setSnapshot(liveSnapshot);
    setSaveMsg("");
  }, [liveSnapshot]);

  if (!effectivePension) return null;

  const openPrintDialog = () => {
    printMethodology2Consolidation();
  };

  /** Persist one DB row only when user clicks Print (not on every calc). */
  const handlePrint = async () => {
    if (!liveSnapshot) return;

    const emp = String(empId || liveSnapshot.emp_cd || "").trim();
    if (!emp) {
      setSaveMsg("Employee id required to save");
      openPrintDialog();
      return;
    }

    setSaving(true);
    setSaveMsg("");
    try {
      const payload = {
        ...liveSnapshot,
        emp_cd: emp,
        equivalent_scales: effectiveEquivalentScales || {},
        pension: effectivePension,
      };
      const res = await API.post(
        `methodology2/consolidation/${emp}/`,
        payload
      );
      setSnapshot(res.data);
      setSaveMsg("Saved for reprint");
      await new Promise((r) => setTimeout(r, 50));
      openPrintDialog();
    } catch (err) {
      console.error(err);
      setSaveMsg(
        err.response?.data?.error || "Could not save consolidation"
      );
      openPrintDialog();
    } finally {
      setSaving(false);
    }
  };

  return (
    <>
      <div className="row justify-content-center mt-4 no-print">
        <div className="col-md-10">
          <div className="card shadow border-primary">
            <div className="card-header bg-primary text-white d-flex justify-content-between align-items-center">
              <h5 className="mb-0">
                {isClass12
                  ? "Pension / consolidation (Class 1/2)"
                  : "Pension (from calculated basic)"}
              </h5>
              <div className="d-flex align-items-center gap-2">
                {saveMsg && (
                  <span className="small text-white-50">{saveMsg}</span>
                )}
                <button
                  type="button"
                  className="btn btn-light btn-sm"
                  onClick={handlePrint}
                  disabled={!liveSnapshot || saving}
                >
                  {saving ? "Saving…" : "Print consolidation"}
                </button>
              </div>
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
                  Click <strong>Print consolidation</strong> to save one DB row
                  (employee + revision blocks + pension) then print.
                  Header title &amp; FA/CAO footer are print-only.
                  {isClass12 && (
                    <> Class 1/2 chain ends at 2017 (277 CPI); 2022 column stays blank unless calculated.</>
                  )}
                </div>
              </div>

              <div className="row g-3">
                {!isClass12 && (
                  <PensionBlock
                    title="2022 (359 CPI)"
                    basic={effectivePension.basic_pay_2022}
                    pension={effectivePension.pension_359_cpi}
                    familyPension={effectivePension.family_pension_359_cpi}
                  />
                )}
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
