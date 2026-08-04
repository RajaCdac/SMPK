import { useCallback, useEffect, useState } from "react";
import API from "../services/Api";

function formatMoney(value) {
  if (value === null || value === undefined || value === "") return "—";
  const n = Number(value);
  if (Number.isNaN(n)) return "—";
  return n.toLocaleString("en-IN", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
}

export default function PensionVoucherGeneration({
  employee,
  billStatus,
  onVoucherChange,
}) {
  const [jvMonth, setJvMonth] = useState("");
  const [jvYear, setJvYear] = useState("");
  const [abstractNo, setAbstractNo] = useState("");
  const [abstractDate, setAbstractDate] = useState("");
  const [narration, setNarration] = useState("");
  const [voucherStatus, setVoucherStatus] = useState(null);
  const [preview, setPreview] = useState(null);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState("");

  const billNo = billStatus?.bill_no || "";

  useEffect(() => {
    if (billStatus?.pension_month) {
      setJvMonth(String(billStatus.pension_month));
      setJvYear(String(billStatus.pension_yr));
    }
  }, [billStatus]);

  const loadStatus = useCallback(async () => {
    if (!billNo) {
      setVoucherStatus(null);
      return;
    }
    try {
      const res = await API.get("first-pension/pension-bill/voucher/status/", {
        params: { bill_no: billNo },
      });
      setVoucherStatus(res.data);
      if (res.data.bill_abstract_no) setAbstractNo(res.data.bill_abstract_no);
      if (res.data.abstract_date) {
        setAbstractDate(String(res.data.abstract_date).slice(0, 10));
      }
      if (res.data.jv?.narration) {
        setNarration(res.data.jv.narration);
      } else if (res.data.default_narration) {
        setNarration(res.data.default_narration);
      }
      if (res.data.preview?.lines?.length) {
        setPreview(res.data.preview);
      }
    } catch (error) {
      console.error(error);
      setVoucherStatus(null);
    }
  }, [billNo]);

  useEffect(() => {
    loadStatus();
  }, [loadStatus]);

  const loadPreview = useCallback(async () => {
    if (!billNo || !jvMonth || !jvYear) return;
    setLoading(true);
    setMessage("");
    try {
      const res = await API.get("first-pension/pension-bill/voucher/preview/", {
        params: {
          bill_no: billNo,
          jv_month: jvMonth,
          jv_year: jvYear,
        },
      });
      setPreview(res.data);
    } catch (error) {
      console.error(error);
      setPreview(null);
      setMessage(
        error.response?.data?.error || "Could not preview journal voucher."
      );
    } finally {
      setLoading(false);
    }
  }, [billNo, jvMonth, jvYear]);

  const handleGenerate = async (regenerate = false) => {
    if (!billNo) {
      alert("Generate a PPN bill first.");
      return;
    }
    if (!jvMonth || !jvYear) {
      alert("JV month and year are required.");
      return;
    }

    setLoading(true);
    setMessage("");
    try {
      const res = await API.post("first-pension/pension-bill/voucher/generate/", {
        bill_no: billNo,
        jv_month: Number(jvMonth),
        jv_year: Number(jvYear),
        abstract_no: abstractNo,
        abstract_date: abstractDate || null,
        narration,
        regenerate,
        voucher_no: regenerate ? voucherStatus?.voucher_no || "" : "",
      });
      alert(res.data.message || "Voucher generated.");
      setMessage(
        regenerate
          ? `Voucher ${res.data.voucher_no} regenerated.`
          : `Voucher ${res.data.voucher_no} created.`
      );
      await loadStatus();
      await loadPreview();
      onVoucherChange?.();
    } catch (error) {
      console.error(error);
      const err =
        error.response?.data?.error || "Journal voucher generation failed.";
      setMessage(err);
      alert(err);
    } finally {
      setLoading(false);
    }
  };

  if (!billStatus?.has_first_month) {
    return (
      <p className="text-muted small mb-0">
        Generate first-month pension on the Amount tab before creating a journal
        voucher.
      </p>
    );
  }

  if (!billNo || !billStatus?.has_pension_bill) {
    return (
      <p className="text-muted small mb-0">
        Generate the PPN bill on the Generate Bill tab first, then create the
        journal voucher here.
      </p>
    );
  }

  return (
    <div className="pension-voucher-generation">
      {message && (
        <div className="alert alert-warning py-2" role="status">
          {message}
        </div>
      )}

      <div className="d-flex flex-wrap align-items-center justify-content-between gap-2 mb-3">
        <p className="text-muted small mb-0">
          Auto JV from PPN bill for employee {employee?.emp_id || "—"}.
          {voucherStatus?.source === "finance_archive" ? (
            <>
              {" "}
              Prefill from finance archive
              {voucherStatus.legacy_bill_no
                ? ` (${voucherStatus.legacy_bill_no})`
                : ""}
              .
            </>
          ) : null}
        </p>
        {voucherStatus?.voucher_no ? (
          <span className="badge text-bg-success">{voucherStatus.voucher_no}</span>
        ) : null}
      </div>

      <div className="row g-3 mb-3">
        <div className="col-md-3">
          <label className="form-label">Bill No</label>
          <input className="form-control" value={billNo} readOnly />
        </div>
        <div className="col-md-2">
          <label className="form-label">JV month</label>
          <input
            type="number"
            className="form-control"
            min={1}
            max={12}
            value={jvMonth}
            onChange={(e) => setJvMonth(e.target.value)}
          />
        </div>
        <div className="col-md-2">
          <label className="form-label">JV year</label>
          <input
            type="number"
            className="form-control"
            min={2000}
            max={2100}
            value={jvYear}
            onChange={(e) => setJvYear(e.target.value)}
          />
        </div>
        <div className="col-md-2">
          <label className="form-label">Abstract No</label>
          <input
            className="form-control"
            value={abstractNo}
            onChange={(e) => setAbstractNo(e.target.value)}
          />
        </div>
        <div className="col-md-3">
          <label className="form-label">Abstract date</label>
          <input
            type="date"
            className="form-control"
            value={abstractDate}
            onChange={(e) => setAbstractDate(e.target.value)}
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

      <div className="d-flex flex-wrap gap-2 mb-3">
        <button
          type="button"
          className="btn btn-outline-secondary btn-sm"
          onClick={loadPreview}
          disabled={loading}
        >
          Preview lines
        </button>
        <button
          type="button"
          className="btn btn-primary btn-sm"
          onClick={() => handleGenerate(false)}
          disabled={loading || Boolean(voucherStatus?.voucher_no)}
        >
          Generate voucher
        </button>
        {voucherStatus?.voucher_no && (
          <button
            type="button"
            className="btn btn-outline-warning btn-sm"
            onClick={() => {
              if (
                window.confirm(
                  `Regenerate voucher ${voucherStatus.voucher_no}?`
                )
              ) {
                handleGenerate(true);
              }
            }}
            disabled={loading}
          >
            Regenerate
          </button>
        )}
      </div>

      {preview?.lines?.length > 0 && (
        <div className="table-responsive">
          <table className="table table-sm table-bordered">
            <thead className="table-light">
              <tr>
                <th>Dr/Cr</th>
                <th>Zonal</th>
                <th>Aloc 1</th>
                <th>Aloc 2</th>
                <th>Aloc 3</th>
                <th className="text-end">Amount</th>
              </tr>
            </thead>
            <tbody>
              {preview.lines.map((line, index) => (
                <tr
                  key={`${line.dr_cr_flag}-${line.aloc_cd1}-${index}`}
                  className={line.balancing ? "table-info" : ""}
                >
                  <td>{line.dr_cr_flag}</td>
                  <td>{line.zonal_cd}</td>
                  <td>{line.aloc_cd1}</td>
                  <td>{line.aloc_cd2}</td>
                  <td>{line.aloc_cd3}</td>
                  <td className="text-end">{formatMoney(line.amount)}</td>
                </tr>
              ))}
            </tbody>
            <tfoot>
              <tr>
                <th colSpan={5}>Total Dr / Cr</th>
                <th className="text-end">
                  {formatMoney(preview.total_dr)} / {formatMoney(preview.total_cr)}
                </th>
              </tr>
            </tfoot>
          </table>
        </div>
      )}
    </div>
  );
}
