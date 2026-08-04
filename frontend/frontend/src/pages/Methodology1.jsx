import { useCallback, useEffect, useState } from "react";
import API from "../services/Api";
import CpiRevisionCard from "../components/CpiRevisionCard";
import MethodologyClass12Result from "../components/MethodologyClass12Result";
import { generatePayStages } from "../utils/scaleParser";
import {
  buildMethodology1CardRows,
  CPI_1030_REVISION,
  getMethodology1VisibleCards,
  is1030Direct607Period,
  isPre1988Separation,
  mapScaleToCardRevision,
} from "../utils/methodology1PayRules";

function normalizeScaleText(value) {
  return String(value || "").replace(/\s+/g, "");
}

function formatScaleLabel(scaleString) {
  const stages = generatePayStages(scaleString);
  if (stages.length >= 2) {
    return `${stages[0]} - ${stages[stages.length - 1]}`;
  }
  return scaleString;
}

function getClass12ScaleValue(item) {
  return item && typeof item === "object" ? item.grade : item;
}

function getClass12ScaleLabel(item) {
  if (item && typeof item === "object") {
    return item.label || item.pay_band || item.scale || item.grade;
  }
  return item;
}

function getScaleOptionValue(item) {
  if (item && typeof item === "object") {
    return item.scale || "";
  }
  return String(item || "");
}

function getScaleOptionLabel(item) {
  if (item && typeof item === "object") {
    return item.label || formatScaleLabel(item.scale);
  }
  return formatScaleLabel(item);
}

async function resolveScaleFor1030(separationDate, employeeScale) {
  if (!employeeScale) return "";

  const scalesRes = await API.get(
    `methodology1/get-scales/?retirement_date=${separationDate}`
  );
  const options = scalesRes.data || [];
  const target = normalizeScaleText(employeeScale);
  const direct = options.find(
    (item) => normalizeScaleText(getScaleOptionValue(item)) === target
  );
  if (direct) return getScaleOptionValue(direct);

  try {
    const equivRes = await API.get(
      `methodology1/get-equivalent-scales/?retirement_date=${separationDate}&scale=${encodeURIComponent(employeeScale)}`
    );
    const fromEquiv = equivRes.data?.[CPI_1030_REVISION];
    if (fromEquiv) {
      const matched = options.find(
        (item) =>
          normalizeScaleText(getScaleOptionValue(item)) ===
          normalizeScaleText(fromEquiv)
      );
      return matched ? getScaleOptionValue(matched) : String(fromEquiv).trim();
    }
  } catch {
    // fall through
  }

  return String(employeeScale).trim();
}

const CPI_REVISIONS = [
  { label: "1988(607 CPI)", cpi: 607, year: 1988 },
  { label: "1993(1030 CPI)", cpi: 1030, year: 1993 },
  { label: "1997(1708 CPI)", cpi: 1708, year: 1997 },
  { label: "2007(126 CPI)", cpi: 126, year: 2007 },
  { label: "2012(198 CPI)", cpi: 198, year: 2012 },
  { label: "2017(277 CPI)", cpi: 277, year: 2017 },
  { label: "2022(359 CPI)", cpi: 359, year: 2022 },
];

function formatDisplayDate(isoDate) {
  if (!isoDate) return "";
  const parsed = new Date(`${isoDate}T00:00:00`);
  if (Number.isNaN(parsed.getTime())) return isoDate;
  return parsed.toLocaleDateString("en-IN");
}

function getCpiDetails(scaleRevision, startRevision) {
  const scaleCard = mapScaleToCardRevision(scaleRevision);
  const scaleIndex = CPI_REVISIONS.findIndex((item) => item.label === scaleCard);
  const startIndex = CPI_REVISIONS.findIndex((item) => item.label === startRevision);
  const fromIndex = scaleIndex >= 0 ? scaleIndex : startIndex;

  if (fromIndex >= 0) {
    return CPI_REVISIONS.slice(fromIndex);
  }

  const match = String(startRevision || "").match(/\((\d+)\s+CPI\)/i);
  if (match) {
    return [{ label: startRevision, cpi: Number(match[1]), year: null }];
  }

  return [];
}

async function loadRevisionInfo(separationDate) {
  const res = await API.get(
    `methodology1/get-scale-type/?retirement_date=${separationDate}`
  );
  return {
    startRevision: res.data.revision || "",
    scaleRevision: res.data.scale_revision || "",
  };
}

export default function Methodology1() {
  const [empId, setEmpId] = useState("");
  const [employeeName, setEmployeeName] = useState("");
  const [loadingEmployee, setLoadingEmployee] = useState(false);

  const [retirementDate, setRetirementDate] = useState("");
  const [category, setCategory] = useState("3");
  const [scale, setScale] = useState("");
  const [lastPay, setLastPay] = useState("");
  const [startRevision, setStartRevision] = useState("");
  const [scaleRevision, setScaleRevision] = useState("");
  const [equivalentScales, setEquivalentScales] = useState(null);
  const [scaleOptions, setScaleOptions] = useState([]);
  const [class12Scales, setClass12Scales] = useState([]);
  const [payStages, setPayStages] = useState([]);
  const [class12Result, setClass12Result] = useState(null);

  const isClass12 = category === "1" || category === "2";
  const isCategory34 = category === "3" || category === "4";
  const is1030ScalePeriod =
    isCategory34 && scaleRevision === CPI_1030_REVISION;
  const isPre1988ScalePeriod =
    isCategory34 &&
    isPre1988Separation(retirementDate) &&
    (scaleRevision === "1979(REVISED PAY SCALE)" ||
      scaleRevision === "1984(REVISED PAY SCALE)");
  const showScaleField = isClass12 || is1030ScalePeriod || isPre1988ScalePeriod;
  const inputColClass = showScaleField ? "col-12 col-md-3" : "col-12 col-md-4";

  const loadEquivalentScales = useCallback(async (sepDate, scaleValue) => {
    if (!sepDate || !scaleValue) {
      setEquivalentScales(null);
      return;
    }
    try {
      const res = await API.get(
        `methodology1/get-equivalent-scales/?retirement_date=${sepDate}&scale=${encodeURIComponent(scaleValue)}`
      );
      setEquivalentScales(res.data || null);
    } catch {
      setEquivalentScales(null);
    }
  }, []);

  const runClass12Calculation = useCallback(async (date, grade, pay) => {
    if (!date || !grade || !pay) return;

    try {
      const res = await API.post("methodology2/calculate-class12/", {
        separation_date: date,
        scale: grade,
        last_pay: pay,
      });
      setClass12Result(res.data);
    } catch (err) {
      console.error(err);
      setClass12Result(null);
      alert(err.response?.data?.error || "Calculation failed. Check inputs.");
    }
  }, []);

  const loadEmployeeById = async (code) => {
    const trimmed = code.trim();
    if (!trimmed) return;

    setLoadingEmployee(true);
    setClass12Result(null);

    try {
      const res = await API.get(`methodology1/employee/${trimmed}/`);
      const data = res.data;

      setEmployeeName(data.name || "");
      setEmpId(data.emp_id);

      const sepDate = data.separation_date;
      const revisionInfo = await loadRevisionInfo(sepDate);
      setStartRevision(revisionInfo.startRevision);
      setScaleRevision(revisionInfo.scaleRevision);

      setRetirementDate(sepDate);
      setLastPay(data.last_pay != null ? String(data.last_pay) : "");

      if (isClass12) {
        setScale("");
        setEquivalentScales(null);
      } else if (revisionInfo.scaleRevision === CPI_1030_REVISION) {
        const resolvedScale = await resolveScaleFor1030(
          sepDate,
          data.scale || ""
        );
        setScale(resolvedScale);
        if (resolvedScale) {
          await loadEquivalentScales(sepDate, resolvedScale);
        } else {
          setEquivalentScales(null);
        }
      } else {
        setScale(data.scale || "");
        setEquivalentScales(null);
      }
    } catch (err) {
      console.error(err);
      const msg =
        err.response?.data?.error ||
        err.response?.data?.message ||
        "Could not load employee.";
      alert(msg);
    } finally {
      setLoadingEmployee(false);
    }
  };

  const handleEmpKeyDown = (e) => {
    if (e.key === "Enter") {
      e.preventDefault();
      loadEmployeeById(empId);
    }
  };

  const resetInputs = useCallback(() => {
    setScale("");
    setLastPay("");
    setClass12Result(null);
    setEquivalentScales(null);
    setPayStages([]);
  }, []);

  useEffect(() => {
    resetInputs();
  }, [category, resetInputs]);

  useEffect(() => {
    if (!retirementDate) {
      setStartRevision("");
      setScaleRevision("");
      setEquivalentScales(null);
      setScaleOptions([]);
      setClass12Scales([]);
      setPayStages([]);
      return;
    }

    if (isCategory34) {
      loadRevisionInfo(retirementDate)
        .then(({ startRevision: start, scaleRevision: scaleRev }) => {
          setStartRevision(start);
          setScaleRevision(scaleRev);
        })
        .catch(console.error);
    }
  }, [retirementDate, isCategory34]);

  useEffect(() => {
    if (!isClass12 || !retirementDate) {
      setClass12Scales([]);
      return;
    }

    API.get(
      `methodology2/get-scales-class12/?separation_date=${retirementDate}`
    )
      .then((res) => setClass12Scales(res.data || []))
      .catch(() => setClass12Scales([]));
  }, [retirementDate, isClass12]);

  useEffect(() => {
    if ((!is1030ScalePeriod && !isPre1988ScalePeriod) || !retirementDate) {
      if (!is1030ScalePeriod && !isPre1988ScalePeriod) setScaleOptions([]);
      return;
    }

    API.get(`methodology1/get-scales/?retirement_date=${retirementDate}`)
      .then((res) => setScaleOptions(res.data || []))
      .catch(() => setScaleOptions([]));
  }, [retirementDate, is1030ScalePeriod, isPre1988ScalePeriod]);

  useEffect(() => {
    if (isClass12) {
      if (!retirementDate || !scale) {
        setPayStages([]);
        return;
      }
      API.get(
        `methodology2/get-pay-stages-class12/?separation_date=${retirementDate}&scale=${encodeURIComponent(scale)}`
      )
        .then((res) => setPayStages(res.data || []))
        .catch(() => setPayStages([]));
      return;
    }

    if ((!is1030ScalePeriod && !isPre1988ScalePeriod) || !scale) {
      setPayStages([]);
      return;
    }

    API.get(
      `methodology1/get-pay-stages/?scale=${encodeURIComponent(scale)}&retirement_date=${retirementDate}`
    )
      .then((res) => setPayStages(res.data || []))
      .catch(() => setPayStages([]));

    loadEquivalentScales(retirementDate, scale);
  }, [
    scale,
    isClass12,
    is1030ScalePeriod,
    isPre1988ScalePeriod,
    retirementDate,
    loadEquivalentScales,
  ]);

  useEffect(() => {
    if (!showScaleField || !payStages.length || !lastPay) return;

    if (!payStages.includes(Number(lastPay))) {
      setLastPay("");
    }
  }, [payStages, showScaleField, lastPay]);

  useEffect(() => {
    if (!isClass12) {
      setClass12Result(null);
      return;
    }

    if (retirementDate && scale && lastPay) {
      runClass12Calculation(retirementDate, scale, lastPay);
    } else {
      setClass12Result(null);
    }
  }, [retirementDate, scale, lastPay, isClass12, runClass12Calculation]);

  const cpiDetails = getCpiDetails(scaleRevision, startRevision);
  const visibleCards = getMethodology1VisibleCards(scaleRevision, startRevision);
  const is1030Direct607 = is1030Direct607Period(retirementDate);
  const needsEquivalentScales =
    (scaleRevision === CPI_1030_REVISION && !is1030Direct607) ||
    isPre1988ScalePeriod;
  const showMethodology1Cards =
    isCategory34 &&
    retirementDate &&
    startRevision &&
    scaleRevision &&
    lastPay &&
    Number(lastPay) > 0 &&
    visibleCards.length > 0 &&
    (!needsEquivalentScales || equivalentScales);

  return (
    <div className="container-fluid mt-3 mt-md-4 px-2 px-md-3 methodology-page">
      <div className="row justify-content-center">
        <div className="col-12 col-xl-10">
          <div className="card shadow">
            <div className="card-header bg-primary text-white">
              <h4 className="mb-0">Methodology I</h4>
            </div>
            <div className="card-body smpk-form">
              <div className="row g-3 mb-3">
                <div className="col-12 col-lg-6">
                  <label className="form-label">Employee ID</label>
                  <div className="input-group">
                    <input
                      type="text"
                      className="form-control"
                      placeholder="Enter emp code and press Enter"
                      value={empId}
                      onChange={(e) => setEmpId(e.target.value)}
                      onKeyDown={handleEmpKeyDown}
                      disabled={loadingEmployee}
                    />
                    <button
                      type="button"
                      className="btn btn-outline-primary"
                      onClick={() => loadEmployeeById(empId)}
                      disabled={loadingEmployee || !empId.trim()}
                    >
                      {loadingEmployee ? "Loading..." : "Load"}
                    </button>
                  </div>
                  {employeeName && (
                    <small className="text-muted d-block mt-1">
                      {employeeName}
                      {scale && !isClass12 ? (
                        <>
                          <br />
                          Scale: {scale}
                        </>
                      ) : null}
                    </small>
                  )}
                </div>
              </div>

              <div className="text-center text-muted small mb-3">— OR —</div>

              <div className="row g-3">
                <div className={inputColClass}>
                  <label className="form-label">Retirement / Separation Date</label>
                  <input
                    type="date"
                    className="form-control"
                    value={retirementDate}
                    onChange={(e) => {
                      setRetirementDate(e.target.value);
                      setScale("");
                      setLastPay("");
                      setEquivalentScales(null);
                      setClass12Result(null);
                    }}
                  />
                </div>

                <div className={inputColClass}>
                  <label className="form-label">Category</label>
                  <select
                    className="form-select"
                    value={category}
                    onChange={(e) => setCategory(e.target.value)}
                  >
                    <option value="1">1</option>
                    <option value="2">2</option>
                    <option value="3">3</option>
                    <option value="4">4</option>
                  </select>
                </div>

                {isClass12 && (
                  <div className={inputColClass}>
                    <label className="form-label">Scale</label>
                    <select
                      className="form-select"
                      value={scale}
                      onChange={(e) => {
                        setScale(e.target.value);
                        setLastPay("");
                      }}
                      disabled={!retirementDate}
                    >
                      <option value="">
                        {retirementDate
                          ? "Select scale"
                          : "Enter separation date first"}
                      </option>
                      {class12Scales.map((item, index) => (
                        <option
                          key={index}
                          value={getClass12ScaleValue(item)}
                        >
                          {getClass12ScaleLabel(item)}
                        </option>
                      ))}
                    </select>
                  </div>
                )}

                {(is1030ScalePeriod || isPre1988ScalePeriod) && (
                  <div className={inputColClass}>
                    <label className="form-label">
                      {is1030ScalePeriod ? "Scale (1030 CPI)" : "Scale (pre-1988)"}
                    </label>
                    <select
                      className="form-select"
                      value={scale}
                      onChange={(e) => {
                        setScale(e.target.value);
                        setLastPay("");
                      }}
                      disabled={!retirementDate}
                    >
                      <option value="">
                        {retirementDate
                          ? "Select scale"
                          : "Enter separation date first"}
                      </option>
                      {scaleOptions.map((item, index) => (
                        <option key={index} value={getScaleOptionValue(item)}>
                          {getScaleOptionLabel(item)}
                        </option>
                      ))}
                    </select>
                  </div>
                )}

                <div className={inputColClass}>
                  <label className="form-label">Last Pay</label>
                  {showScaleField ? (
                    <select
                      className="form-select"
                      value={lastPay}
                      onChange={(e) => setLastPay(e.target.value)}
                      disabled={!scale}
                    >
                      <option value="">
                        {scale ? "Select last pay" : "Select scale first"}
                      </option>
                      {payStages.map((item, index) => (
                        <option key={index} value={item}>
                          {item}
                        </option>
                      ))}
                    </select>
                  ) : (
                    <input
                      type="number"
                      className="form-control"
                      placeholder="Enter last pay"
                      min="1"
                      step="1"
                      value={lastPay}
                      onChange={(e) => setLastPay(e.target.value)}
                    />
                  )}
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      {isCategory34 && retirementDate && startRevision && (
        <div className="row justify-content-center mt-3">
          <div className="col-12 col-xl-10">
            <div className="card shadow-sm border-info">
              <div className="card-body py-3">
                <h6 className="mb-2 text-primary">CPI (from separation date)</h6>
                <p className="mb-1 small mb-md-2">
                  <strong>Separation date:</strong>{" "}
                  {formatDisplayDate(retirementDate)}
                </p>
                <p className="mb-1 small">
                  <strong>Category:</strong> {category}
                </p>
                <p className="mb-1 small">
                  <strong>Scale at separation:</strong> {scaleRevision}
                </p>
                <p className="mb-2 small">
                  <strong>Fitment from:</strong> {startRevision}
                </p>
                {cpiDetails.length > 0 ? (
                  <div className="d-flex flex-wrap gap-2">
                    {cpiDetails.map((item) => (
                      <span
                        key={item.label}
                        className="badge bg-info text-dark"
                      >
                        {item.year ? `${item.year} — ` : ""}
                        {item.cpi} CPI
                      </span>
                    ))}
                  </div>
                ) : (
                  <p className="mb-0 small text-muted">
                    No CPI band applies for this revision period.
                  </p>
                )}
                {!lastPay && (
                  <p className="mb-0 mt-2 small text-muted">
                    {showScaleField
                      ? "Select scale and last pay to see CPI calculation cards."
                      : "Enter last pay to see CPI calculation cards."}
                  </p>
                )}
              </div>
            </div>
          </div>
        </div>
      )}

      {showMethodology1Cards && (
        <div className="row justify-content-center mt-3">
          <div className="col-12">
            <div className="row g-3">
              {visibleCards.map((card) => (
                <CpiRevisionCard
                  key={card.revision}
                  title={card.title}
                  rows={buildMethodology1CardRows(
                    card,
                    lastPay,
                    scaleRevision,
                    startRevision,
                    equivalentScales,
                    retirementDate
                  )}
                />
              ))}
            </div>
          </div>
        </div>
      )}

      {isClass12 && (
        <MethodologyClass12Result
          category={category}
          class12Result={class12Result}
        />
      )}
    </div>
  );
}
