import { useMemo, useState } from "react";
import API from "../services/Api";
import "../styles/FirstPensionCase.css";
import "../styles/EmployeeProcessTabs.css";

function formatMoney(value) {
  if (value === null || value === undefined || value === "") return "—";
  const n = Number(value);
  if (Number.isNaN(n)) return "—";
  return n.toLocaleString("en-IN", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
}

function InfoGrid({ employee }) {
  const fields = [
    { label: "Employee ID", value: employee?.emp_id },
    { label: "Name", value: employee?.name },
    { label: "Date of Joining", value: employee?.join_date },
    { label: "Retirement / Separation", value: employee?.expected_retirement_date },
    { label: "Date of Birth", value: employee?.birth_date },
    { label: "Class", value: employee?.class },
    {
      label: "Basic Pay",
      value:
        employee?.basic_amount != null
          ? `Rs.${formatMoney(employee.basic_amount)} (${employee.scale || "—"})`
          : "—",
    },
    { label: "Separation Type", value: employee?.separation_type },
  ];
  return (
    <div className="employee-info-grid">
      {fields.map((item) => (
        <div className="employee-info-item" key={item.label}>
          <span>{item.label}</span>
          <strong>{item.value || "—"}</strong>
        </div>
      ))}
    </div>
  );
}

function ReadonlyNoPay({ data }) {
  if (!data) {
    return <p className="text-muted mb-0">No no-pay record in archive.</p>;
  }
  const fields = [
    ["No Pay Days (Prior to 10 Mnths)", data.no_pay_days],
    ["Dies Non Days", data.dies_non_days],
    ["No Pay More Than 240 Days", data.no_pay_more_than_240_days],
    ["Suspension Days", data.suspension_days],
    ["Boys Serv Days", data.boys_serv_days],
  ];
  return (
    <div className="smpk-form">
      <div className="row g-3">
        {fields.map(([label, value]) => (
          <div className="col-6 col-md-4 col-lg-3" key={label}>
            <label className="form-label">{label}</label>
            <input className="form-control" value={value ?? 0} readOnly />
          </div>
        ))}
      </div>
    </div>
  );
}

function ReadonlyCommutation({ list, selectedNo, onSelect }) {
  if (!list?.length) {
    return <p className="text-muted mb-0">No commutation application in archive.</p>;
  }
  const selected =
    list.find((x) => x.appcn_no === selectedNo) || list[0];
  return (
    <div>
      {list.length > 1 && (
        <div className="mb-3">
          <label className="form-label">Select application (APPCN_NO)</label>
          <select
            className="form-select"
            value={selected.appcn_no}
            onChange={(e) => onSelect(e.target.value)}
          >
            {list.map((item) => (
              <option key={item.appcn_no} value={item.appcn_no}>
                {item.appcn_no} — {item.appcn_dt || "no date"} —{" "}
                {item.commutation_per ?? 0}%
              </option>
            ))}
          </select>
        </div>
      )}
      <div className="smpk-form">
        <div className="row g-3">
          {[
            ["Application No", selected.appcn_no],
            ["Application Date", selected.appcn_dt],
            ["Commutation %", selected.commutation_per],
            ["Commutation Date", selected.commutation_dt],
            ["Restoration Date", selected.restoration_dt],
            ["Commutation Amount", formatMoney(selected.commutation_amt)],
            ["Pension Amount", formatMoney(selected.pen_amt)],
            ["Bank Code", selected.bank_cd],
            ["CA No", selected.ca_no],
            ["Bill No", selected.bill_no],
            ["Impl FPen/ComBill", selected.impl_fpen_combill],
          ].map(([label, value]) => (
            <div className="col-6 col-md-4" key={label}>
              <label className="form-label">{label}</label>
              <input className="form-control" value={value ?? "—"} readOnly />
            </div>
          ))}
          <div className="col-12">
            <label className="form-label">Reasons</label>
            <textarea
              className="form-control"
              rows={2}
              value={selected.commutation_reasons || ""}
              readOnly
            />
          </div>
        </div>
      </div>
    </div>
  );
}

function ReadonlyAmount({ data }) {
  if (!data) {
    return <p className="text-muted mb-0">No pensioner amount record in archive.</p>;
  }
  return (
    <div className="smpk-form">
      <div className="row g-3 mb-3">
        {[
          ["CA Number", data.ca_number],
          ["Pension Emoluments", formatMoney(data.pension_emoluments)],
          ["Original Pension", formatMoney(data.original_pension_amount)],
          ["Payable Pension", formatMoney(data.payable_pension)],
          ["Commutation %", data.commutation_percent],
          ["Commuted Portion", formatMoney(data.commuted_portion)],
          ["Gratuity", formatMoney(data.gratuity_amount)],
          ["Gratuity Emoluments", formatMoney(data.gratuity_emoluments)],
          ["TCCS", data.tccs],
          ["TQS", data.tqs],
          ["Total Service", data.total_service],
          ["Effective From", data.effective_stdt_pension],
        ].map(([label, value]) => (
          <div className="col-6 col-md-4" key={label}>
            <label className="form-label">{label}</label>
            <input className="form-control" value={value ?? "—"} readOnly />
          </div>
        ))}
      </div>
    </div>
  );
}

function ReadonlyProposal({ data }) {
  if (!data) {
    return <p className="text-muted mb-0">No proposal in archive.</p>;
  }
  return (
    <div className="smpk-form">
      <div className="row g-3">
        {[
          ["CA Number", data.ca_number],
          ["Proposal Date", data.pension_proposal_dt],
          ["Separation Date", data.separation_dt],
          ["Pension Type", data.pension_type],
        ].map(([label, value]) => (
          <div className="col-6 col-md-3" key={label}>
            <label className="form-label">{label}</label>
            <input className="form-control" value={value ?? "—"} readOnly />
          </div>
        ))}
      </div>
    </div>
  );
}

function ArchiveBillJournal({ bills }) {
  const [selectedBillNo, setSelectedBillNo] = useState("");
  const [detail, setDetail] = useState(null);
  const [journal, setJournal] = useState(null);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState("");

  const openBill = async (billNo) => {
    setSelectedBillNo(billNo);
    setLoading(true);
    setMessage("");
    setDetail(null);
    setJournal(null);
    try {
      const res = await API.get(
        `first-pension/archive/bill/${encodeURIComponent(billNo)}/`
      );
      setDetail(res.data);
      const voucher =
        res.data.voucher_no ||
        res.data.journals?.[0]?.voucher_no ||
        "";
      if (voucher) {
        const jres = await API.get(
          `first-pension/archive/journal/${encodeURIComponent(voucher)}/`
        );
        setJournal(jres.data);
      }
    } catch (error) {
      setMessage(error.response?.data?.error || "Could not load bill.");
    } finally {
      setLoading(false);
    }
  };

  if (!bills?.length) {
    return <p className="text-muted mb-0">No bills found in archive for this employee.</p>;
  }

  return (
    <div>
      <div className="table-responsive mb-3">
        <table className="table table-sm table-bordered">
          <thead className="table-light">
            <tr>
              <th>Bill No</th>
              <th>Type</th>
              <th>Month/Year</th>
              <th>Voucher No</th>
              <th>Total Earned</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {bills.map((b) => (
              <tr key={b.bill_no}>
                <td>{b.bill_no}</td>
                <td>{b.bill_type}</td>
                <td>
                  {b.bill_month}/{b.bill_year}
                </td>
                <td>{b.voucher_no || "—"}</td>
                <td>{formatMoney(b.total_earned)}</td>
                <td>
                  <button
                    type="button"
                    className="btn btn-sm btn-outline-primary"
                    onClick={() => openBill(b.bill_no)}
                  >
                    Open
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {loading && <p className="text-muted">Loading bill…</p>}
      {message && <div className="alert alert-warning py-2">{message}</div>}

      {detail && (
        <div className="card mb-3">
          <div className="card-header">
            Bill detail — <strong>{selectedBillNo}</strong>
          </div>
          <div className="card-body smpk-form">
            <div className="row g-3 mb-3">
              {[
                ["Bill Type", detail.bill_type],
                ["Month/Year", `${detail.bill_month}/${detail.bill_year}`],
                ["Voucher No", detail.voucher_no || "—"],
                ["Total Earned", formatMoney(detail.total_earned)],
                ["Total Deducted", formatMoney(detail.total_deducted)],
                ["Posted", detail.posted || "—"],
              ].map(([label, value]) => (
                <div className="col-6 col-md-4" key={label}>
                  <label className="form-label">{label}</label>
                  <input className="form-control" value={value ?? "—"} readOnly />
                </div>
              ))}
            </div>
            {detail.journals?.length > 0 && (
              <p className="mb-2">
                Linked journal IDs:{" "}
                {detail.journals.map((j) => j.voucher_no).join(", ")}
              </p>
            )}
          </div>
        </div>
      )}

      {journal && (
        <div className="card">
          <div className="card-header">
            Journal — <strong>{journal.voucher_no}</strong>
          </div>
          <div className="card-body">
            {(journal.headers || []).map((h) => (
              <div key={h.voucher_no} className="mb-3 smpk-form">
                <div className="row g-3">
                  {[
                    ["Voucher Date", h.voucher_dt],
                    ["Ref No", h.ref_no],
                    ["Tran Type", h.tran_type],
                    ["Total Amt", formatMoney(h.tot_amt)],
                  ].map(([label, value]) => (
                    <div className="col-6 col-md-3" key={label}>
                      <label className="form-label">{label}</label>
                      <input className="form-control" value={value ?? "—"} readOnly />
                    </div>
                  ))}
                  <div className="col-12">
                    <label className="form-label">Narration</label>
                    <textarea
                      className="form-control"
                      rows={2}
                      value={h.narration || ""}
                      readOnly
                    />
                  </div>
                </div>
              </div>
            ))}
            <div className="table-responsive">
              <table className="table table-sm table-bordered mb-0">
                <thead className="table-light">
                  <tr>
                    <th>SL</th>
                    <th>Alloc1</th>
                    <th>Alloc2</th>
                    <th>Dr/Cr</th>
                    <th>Amount</th>
                    <th>Remarks</th>
                  </tr>
                </thead>
                <tbody>
                  {(journal.details || []).map((d) => (
                    <tr key={`${d.voucher_no}-${d.sl_no}`}>
                      <td>{d.sl_no}</td>
                      <td>{d.aloc_cd1}</td>
                      <td>{d.aloc_cd2}</td>
                      <td>{d.dr_cr_flag}</td>
                      <td>{formatMoney(d.amount)}</td>
                      <td>{d.remarks || "—"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

const TABS = [
  { key: "basic", label: "Basic Info" },
  { key: "comm", label: "Commutation" },
  { key: "nopay", label: "No-Pay" },
  { key: "proposal", label: "Proposal" },
  { key: "amount", label: "Amount" },
  { key: "bill", label: "Bill & Journal" },
];

function ArchiveWorkflow({ payload }) {
  const [active, setActive] = useState("basic");
  const [selectedAppcn, setSelectedAppcn] = useState(
    payload.commutation_data?.appcn_no || ""
  );
  const idPrefix = "archive";

  const panel = useMemo(() => {
    switch (active) {
      case "basic":
        return <InfoGrid employee={payload.employee} />;
      case "comm":
        return (
          <ReadonlyCommutation
            list={payload.commutation_list}
            selectedNo={selectedAppcn}
            onSelect={setSelectedAppcn}
          />
        );
      case "nopay":
        return <ReadonlyNoPay data={payload.no_pay_data} />;
      case "proposal":
        return <ReadonlyProposal data={payload.proposal_data} />;
      case "amount":
        return <ReadonlyAmount data={payload.amount_data} />;
      case "bill":
        return <ArchiveBillJournal bills={payload.bills} />;
      default:
        return null;
    }
  }, [active, payload, selectedAppcn]);

  return (
    <div className="employee-process-tabs">
      <ul className="employee-process-tabs__nav" role="tablist">
        {TABS.map((tab, index) => (
          <li key={tab.key} className="employee-process-tabs__item">
            <button
              type="button"
              className={`employee-process-tabs__btn nav-link${
                active === tab.key ? " active" : ""
              }`}
              id={`${idPrefix}-${tab.key}-tab`}
              onClick={() => setActive(tab.key)}
            >
              <span className="employee-process-tabs__step">{index + 1}</span>
              <span className="employee-process-tabs__label-full">{tab.label}</span>
              <span className="employee-process-tabs__label-short">{tab.label}</span>
            </button>
          </li>
        ))}
      </ul>
      <div className="tab-content employee-process-tabs__panel p-3">
        <div className="badge text-bg-secondary mb-3">Archive — read only</div>
        {panel}
      </div>
    </div>
  );
}

export default function ArchiveFirstPension() {
  const [employeeId, setEmployeeId] = useState("");
  const [payload, setPayload] = useState(null);
  const [message, setMessage] = useState("");
  const [loading, setLoading] = useState(false);

  const handleSearch = async (e) => {
    e.preventDefault();
    const code = employeeId.trim();
    if (!code) {
      setMessage("Please enter Employee ID");
      return;
    }
    setLoading(true);
    setMessage("");
    setPayload(null);
    try {
      const res = await API.get(
        `first-pension/archive/employee/${encodeURIComponent(code)}/`
      );
      setPayload(res.data);
      if (res.data.prefer_live_message) {
        setMessage(res.data.prefer_live_message);
      } else if (!res.data.has_archive_data) {
        setMessage("Employee found, but no first-pension archive data.");
      }
    } catch (error) {
      setMessage(
        error.response?.data?.error || "Employee not found in archive."
      );
    } finally {
      setLoading(false);
    }
  };

  const handleClear = () => {
    setPayload(null);
    setMessage("");
    setEmployeeId("");
  };

  return (
    <div className="first-pension-page container-fluid mt-3 mt-md-4 px-2 px-md-3">
      <div className="row justify-content-center">
        <div className="col-12 col-xl-11">
          {!payload && (
            <div className="card shadow first-pension-search-card">
              <div className="card-header bg-secondary text-white">
                <h4 className="mb-0">Archive — First Pension (read only)</h4>
              </div>
              <div className="card-body smpk-form">
                <p className="text-muted">
                  Searches historical Oracle dump in MySQL <code>finance</code>{" "}
                  (port 3307). Prefer live First Pension for new processing.
                </p>
                <form onSubmit={handleSearch}>
                  <div className="row g-3 align-items-end">
                    <div className="col-12 col-lg-8">
                      <label className="form-label">Employee ID</label>
                      <input
                        type="text"
                        className="form-control"
                        placeholder="Enter Employee ID"
                        value={employeeId}
                        onChange={(e) => setEmployeeId(e.target.value)}
                        disabled={loading}
                        autoComplete="off"
                      />
                    </div>
                    <div className="col-12 col-lg-4">
                      <button
                        type="submit"
                        className="btn btn-secondary w-100"
                        disabled={loading || !employeeId.trim()}
                      >
                        {loading ? "Loading…" : "Search Archive"}
                      </button>
                    </div>
                  </div>
                </form>
                {message && (
                  <div className="alert alert-info mt-3 mb-0 py-2">{message}</div>
                )}
              </div>
            </div>
          )}

          {payload && (
            <>
              <div className="d-flex flex-wrap gap-2 align-items-center mb-3">
                <h5 className="mb-0">
                  Archive: {payload.employee?.emp_id} — {payload.employee?.name}
                </h5>
                <button
                  type="button"
                  className="btn btn-outline-secondary btn-sm"
                  onClick={handleClear}
                >
                  Search another
                </button>
              </div>
              {message && (
                <div className="alert alert-warning py-2">{message}</div>
              )}
              <ArchiveWorkflow payload={payload} />
            </>
          )}
        </div>
      </div>
    </div>
  );
}
