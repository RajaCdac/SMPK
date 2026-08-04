import { useCallback, useEffect, useMemo, useState } from "react";
import API from "../services/Api";
import "../styles/PensionJournalSummary.css";

const EMPTY_LINE = () => ({
  zonal_cd: "",
  aloc_cd1: "",
  aloc_cd2: "",
  aloc_cd3: "",
  dr_cr_flag: "D",
  amount: "",
  remarks: "",
});

function formatMoney(value) {
  if (value === null || value === undefined || value === "") return "—";
  const n = Number(value);
  if (Number.isNaN(n)) return "—";
  return n.toLocaleString("en-IN", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
}

function sumLines(lines) {
  let debit = 0;
  let credit = 0;
  for (const line of lines) {
    const amt = Number(line.amount);
    if (!amt || Number.isNaN(amt)) continue;
    if (line.dr_cr_flag === "D") debit += amt;
    if (line.dr_cr_flag === "C") credit += amt;
  }
  return { debit, credit };
}

export default function PensionManualJournal({
  billNo,
  jvMonth,
  jvYear,
  autoPreview,
  employee,
  embedded = false,
}) {
  const [voucherNo, setVoucherNo] = useState("");
  const [voucherDt, setVoucherDt] = useState("");
  const [refNo, setRefNo] = useState(billNo || "");
  const [refDt, setRefDt] = useState("");
  const [narration, setNarration] = useState("");
  const [tranType, setTranType] = useState("PNJV/N");
  const [month, setMonth] = useState(jvMonth || "");
  const [year, setYear] = useState(jvYear || "");
  const [lines, setLines] = useState([EMPTY_LINE(), EMPTY_LINE()]);
  const [summary, setSummary] = useState(null);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState("");

  const totals = useMemo(() => sumLines(lines), [lines]);
  const balanced = totals.debit > 0 && totals.debit === totals.credit;

  useEffect(() => {
    if (billNo) setRefNo(billNo);
  }, [billNo]);

  useEffect(() => {
    if (jvMonth) setMonth(String(jvMonth));
    if (jvYear) setYear(String(jvYear));
  }, [jvMonth, jvYear]);

  const loadTemplate = useCallback(async () => {
    try {
      const res = await API.get("first-pension/pension-bill/manual-journal/template/", {
        params: {
          ref_no: billNo || refNo || "",
          emp_code: employee?.emp_id || undefined,
          jv_month: month || undefined,
          jv_year: year || undefined,
        },
      });
      setVoucherDt(res.data.voucher_dt || "");
      setTranType(res.data.tran_type || "PNJV/N");
      if (!month && res.data.jv_month) setMonth(String(res.data.jv_month));
      if (!year && res.data.jv_year) setYear(String(res.data.jv_year));
      if (!voucherNo && (res.data.narration || res.data.default_narration)) {
        setNarration(res.data.narration || res.data.default_narration);
      }
    } catch (error) {
      console.error(error);
    }
  }, [billNo, refNo, month, year, employee?.emp_id, voucherNo]);

  const loadSummary = useCallback(async () => {
    const lookupRef = refNo || billNo;
    const lookupVoucher = voucherNo;
    if (!lookupRef && !lookupVoucher) return;

    setLoading(true);
    setMessage("");
    try {
      const res = await API.get("first-pension/pension-bill/manual-journal/summary/", {
        params: lookupVoucher
          ? { voucher_no: lookupVoucher }
          : { ref_no: lookupRef },
      });
      const data = res.data;
      setSummary(data);
      setVoucherNo(data.voucher_no || "");
      setVoucherDt(data.voucher_dt || "");
      setRefNo(data.ref_no || lookupRef || "");
      setRefDt(data.ref_dt || "");
      setNarration(data.narration || "");
      setTranType(data.tran_type || "PNJV/N");
      setMonth(String(data.mth || month || ""));
      setYear(String(data.yr || year || ""));
      if (data.lines?.length) {
        setLines(
          data.lines.map((line) => ({
            zonal_cd: String(line.zonal_cd ?? ""),
            aloc_cd1: line.aloc_cd1 || "",
            aloc_cd2: line.aloc_cd2 || "",
            aloc_cd3: line.aloc_cd3 || "",
            dr_cr_flag: line.dr_cr_flag || "D",
            amount: String(line.amount ?? ""),
            remarks: line.remarks || "",
          }))
        );
      }
    } catch (error) {
      if (error.response?.status !== 404) {
        setMessage(
          error.response?.data?.error || "Could not load journal summary."
        );
      }
      setSummary(null);
    } finally {
      setLoading(false);
    }
  }, [billNo, refNo, voucherNo, month, year]);

  useEffect(() => {
    loadTemplate();
  }, [loadTemplate]);

  useEffect(() => {
    if (billNo || voucherNo) {
      loadSummary();
    }
  }, [billNo]); // eslint-disable-line react-hooks/exhaustive-deps

  const loadFromAutoPreview = () => {
    if (!autoPreview?.lines?.length) {
      alert("Generate or preview the automatic PPN voucher lines first.");
      return;
    }
    setLines(
      autoPreview.lines.map((line) => ({
        zonal_cd: String(line.zonal_cd ?? ""),
        aloc_cd1: line.aloc_cd1 || "",
        aloc_cd2: line.aloc_cd2 || "",
        aloc_cd3: line.aloc_cd3 || "",
        dr_cr_flag: line.dr_cr_flag || "D",
        amount: String(line.amount ?? ""),
        remarks: "",
      }))
    );
    setMessage("Loaded lines from automatic voucher preview.");
  };

  const updateLine = (index, field, value) => {
    setLines((prev) =>
      prev.map((line, i) => (i === index ? { ...line, [field]: value } : line))
    );
  };

  const addLine = () => setLines((prev) => [...prev, EMPTY_LINE()]);

  const removeLine = (index) => {
    setLines((prev) => prev.filter((_, i) => i !== index));
  };

  const handleSave = async () => {
    if (!month || !year) {
      alert("JV month and year are required.");
      return;
    }
    if (!balanced) {
      alert("Debit and credit amounts must be the same.");
      return;
    }

    setLoading(true);
    setMessage("");
    try {
      const payload = {
        voucher_no: voucherNo || undefined,
        voucher_dt: voucherDt || null,
        jv_month: Number(month),
        jv_year: Number(year),
        ref_no: refNo,
        ref_dt: refDt || null,
        narration,
        tran_type: tranType,
        lines: lines
          .filter((line) => line.zonal_cd || line.aloc_cd1 || line.amount)
          .map((line) => ({
            zonal_cd: Number(line.zonal_cd),
            aloc_cd1: line.aloc_cd1,
            aloc_cd2: line.aloc_cd2,
            aloc_cd3: line.aloc_cd3,
            dr_cr_flag: line.dr_cr_flag,
            amount: Number(line.amount),
            remarks: line.remarks,
          })),
      };
      const res = await API.post(
        "first-pension/pension-bill/manual-journal/save/",
        payload
      );
      setVoucherNo(res.data.voucher_no);
      setSummary(res.data.summary);
      setMessage(res.data.message || "Journal saved.");
      alert(res.data.message || "Journal saved.");
    } catch (error) {
      const err =
        error.response?.data?.error || "Manual journal save failed.";
      setMessage(err);
      alert(err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className={`${embedded ? "" : "mt-3 "}card manual-journal`}>
      {!embedded ? (
        <div className="card-header py-2 d-flex justify-content-between align-items-center">
          <strong>Manual Journal Voucher</strong>
          {voucherNo ? (
            <span className="badge text-bg-primary">{voucherNo}</span>
          ) : (
            <span className="badge text-bg-secondary">New</span>
          )}
        </div>
      ) : null}
      <div className={`card-body smpk-form${embedded ? " px-0 pt-0" : ""}`}>
        <p className="text-muted small mb-3">
          Entry/edit screen from FI_PN_T_H_JRVOUCHR_E — manual JV (PNJV/N) with
          debit/credit balance check before save.
        </p>

        {message && (
          <div className="alert alert-warning py-2" role="status">
            {message}
          </div>
        )}

        <div className="row g-3 mb-3">
          <div className="col-md-3">
            <label className="form-label">Voucher No</label>
            <input className="form-control" value={voucherNo} readOnly placeholder="Auto on save" />
          </div>
          <div className="col-md-3">
            <label className="form-label">Voucher date</label>
            <input
              type="date"
              className="form-control"
              value={voucherDt}
              onChange={(e) => setVoucherDt(e.target.value)}
            />
          </div>
          <div className="col-md-2">
            <label className="form-label">JV month</label>
            <input
              type="number"
              min={1}
              max={12}
              className="form-control"
              value={month}
              onChange={(e) => setMonth(e.target.value)}
            />
          </div>
          <div className="col-md-2">
            <label className="form-label">JV year</label>
            <input
              type="number"
              min={2000}
              max={2100}
              className="form-control"
              value={year}
              onChange={(e) => setYear(e.target.value)}
            />
          </div>
          <div className="col-md-2">
            <label className="form-label">Tran type</label>
            <select
              className="form-select"
              value={tranType}
              onChange={(e) => setTranType(e.target.value)}
            >
              <option value="PNJV/N">PNJV/N — Manual</option>
              <option value="PNJV/P">PNJV/P — First pension</option>
              <option value="PNJV/M">PNJV/M — Monthly</option>
            </select>
          </div>
          <div className="col-md-4">
            <label className="form-label">Ref No (bill)</label>
            <input
              className="form-control"
              value={refNo}
              onChange={(e) => setRefNo(e.target.value)}
            />
          </div>
          <div className="col-md-3">
            <label className="form-label">Ref date</label>
            <input
              type="date"
              className="form-control"
              value={refDt}
              onChange={(e) => setRefDt(e.target.value)}
            />
          </div>
          <div className="col-12">
            <label className="form-label">Narration</label>
            <textarea
              className="form-control"
              rows={2}
              value={narration}
              onChange={(e) => setNarration(e.target.value)}
              placeholder="Amount passed in favour of …, case no …, Retd. W.e.f …, emp code …"
            />
          </div>
        </div>

        <div className="manual-journal__summary-bar mb-3">
          <div>
            <strong>Debit Amt.</strong>
            {formatMoney(totals.debit)}
          </div>
          <div>
            <strong>Credit Amt.</strong>
            {formatMoney(totals.credit)}
          </div>
          <div className={balanced ? "balanced" : "unbalanced"}>
            <strong>Status</strong>
            {balanced ? "Balanced" : "Not balanced"}
          </div>
        </div>

        <div className="table-responsive mb-3">
          <table className="table table-sm table-bordered">
            <thead className="table-light">
              <tr>
                <th>Zonal</th>
                <th>Aloc 1</th>
                <th>Aloc 2</th>
                <th>Aloc 3</th>
                <th>Dr/Cr</th>
                <th className="text-end">Amount</th>
                <th>Remarks</th>
                <th />
              </tr>
            </thead>
            <tbody>
              {lines.map((line, index) => (
                <tr key={`line-${index}`}>
                  <td>
                    <input
                      className="form-control form-control-sm"
                      value={line.zonal_cd}
                      onChange={(e) => updateLine(index, "zonal_cd", e.target.value)}
                    />
                  </td>
                  <td>
                    <input
                      className="form-control form-control-sm"
                      value={line.aloc_cd1}
                      onChange={(e) => updateLine(index, "aloc_cd1", e.target.value)}
                    />
                  </td>
                  <td>
                    <input
                      className="form-control form-control-sm"
                      value={line.aloc_cd2}
                      onChange={(e) => updateLine(index, "aloc_cd2", e.target.value)}
                    />
                  </td>
                  <td>
                    <input
                      className="form-control form-control-sm"
                      value={line.aloc_cd3}
                      onChange={(e) => updateLine(index, "aloc_cd3", e.target.value)}
                    />
                  </td>
                  <td>
                    <select
                      className="form-select form-select-sm"
                      value={line.dr_cr_flag}
                      onChange={(e) => updateLine(index, "dr_cr_flag", e.target.value)}
                    >
                      <option value="D">D</option>
                      <option value="C">C</option>
                    </select>
                  </td>
                  <td>
                    <input
                      type="number"
                      step="0.01"
                      className="form-control form-control-sm text-end"
                      value={line.amount}
                      onChange={(e) => updateLine(index, "amount", e.target.value)}
                    />
                  </td>
                  <td>
                    <input
                      className="form-control form-control-sm"
                      value={line.remarks}
                      onChange={(e) => updateLine(index, "remarks", e.target.value)}
                    />
                  </td>
                  <td>
                    <button
                      type="button"
                      className="btn btn-outline-danger btn-sm"
                      onClick={() => removeLine(index)}
                      disabled={lines.length <= 1}
                    >
                      ×
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <div className="d-flex flex-wrap gap-2 mb-3">
          <button type="button" className="btn btn-outline-secondary btn-sm" onClick={addLine}>
            Add line
          </button>
          <button
            type="button"
            className="btn btn-outline-secondary btn-sm"
            onClick={loadFromAutoPreview}
            disabled={!autoPreview?.lines?.length}
          >
            Load from auto preview
          </button>
          <button
            type="button"
            className="btn btn-outline-secondary btn-sm"
            onClick={loadSummary}
            disabled={loading}
          >
            Reload summary
          </button>
          <button
            type="button"
            className="btn btn-primary btn-sm"
            onClick={handleSave}
            disabled={loading || !balanced}
          >
            Save journal
          </button>
        </div>

        {summary?.lines?.length > 0 && (
          <div className="border rounded p-3 bg-light">
            <h6 className="mb-2">Summary of Journal</h6>
            <div className="table-responsive">
              <table className="table table-sm table-bordered mb-0">
                <thead className="table-light">
                  <tr>
                    <th>Sl</th>
                    <th>Zonal</th>
                    <th>Aloc 1</th>
                    <th>Aloc 2</th>
                    <th>Aloc 3</th>
                    <th>Dr/Cr</th>
                    <th className="text-end">Amount</th>
                  </tr>
                </thead>
                <tbody>
                  {summary.lines.map((line) => (
                    <tr key={`sum-${line.sl_no}`}>
                      <td>{line.sl_no}</td>
                      <td>{line.zonal_cd}</td>
                      <td>{line.aloc_cd1}</td>
                      <td>{line.aloc_cd2}</td>
                      <td>{line.aloc_cd3}</td>
                      <td>{line.dr_cr_flag}</td>
                      <td className="text-end">{formatMoney(line.amount)}</td>
                    </tr>
                  ))}
                </tbody>
                <tfoot>
                  <tr>
                    <th colSpan={6}>Debit / Credit</th>
                    <th className="text-end">
                      {formatMoney(summary.debit_amt)} / {formatMoney(summary.credit_amt)}
                    </th>
                  </tr>
                </tfoot>
              </table>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
