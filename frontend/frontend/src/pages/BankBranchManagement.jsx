import { useCallback, useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import API from "../services/Api";
import SmpkDataTable from "../components/DataTable/SmpkDataTable";
import "../styles/MasterData.css";

const emptyForm = {
  bank_type: "",
  disp_bank_name: "",
  disp_bank_id: "",
  bank_cd: "",
  bank_desc: "",
  bank_id: "",
  control_bank_cd: "",
  control_bank_desc: "",
  addr1: "",
  addr2: "",
  ps: "",
  city: "",
  dist: "",
  state: "",
  pin: "",
  country: "",
  contact1: "",
  contact2: "",
  fax_no: "",
  email_id: "",
  rbi_cd: "",
};

function asArray(data) {
  if (Array.isArray(data)) return data;
  if (data?.results && Array.isArray(data.results)) return data.results;
  return [];
}

function apiErrorMessage(err) {
  const data = err?.response?.data;
  if (!data || typeof data !== "object") return "Request failed.";
  if (typeof data.error === "string") return data.error;
  if (typeof data.detail === "string") return data.detail;
  for (const key of Object.keys(data)) {
    const msg = data[key];
    if (Array.isArray(msg) && msg[0]) return `${key}: ${msg[0]}`;
    if (typeof msg === "string") return msg;
  }
  return "Request failed.";
}

function toPayload(form, { editing }) {
  const pin = String(form.pin || "").trim();
  const payload = {
    bank_type: (form.bank_type || "").trim().toUpperCase(),
    bank_desc: (form.bank_desc || "").trim(),
    bank_id: (form.bank_id || "").trim(),
    control_bank_cd: (form.control_bank_cd || "").trim(),
    addr1: (form.addr1 || "").trim(),
    addr2: (form.addr2 || "").trim(),
    ps: (form.ps || "").trim(),
    city: (form.city || "").trim(),
    dist: (form.dist || "").trim(),
    state: (form.state || "").trim(),
    pin: pin === "" ? null : Number(pin),
    country: (form.country || "").trim(),
    contact1: (form.contact1 || "").trim(),
    contact2: (form.contact2 || "").trim(),
    fax_no: (form.fax_no || "").trim(),
    email_id: (form.email_id || "").trim(),
    rbi_cd: (form.rbi_cd || "").trim(),
  };
  if (editing) {
    payload.bank_cd = (form.bank_cd || "").trim().toUpperCase();
  }
  return payload;
}

function sortBanksByCode(rows) {
  return [...rows].sort((a, b) =>
    String(a.bank_cd || "").localeCompare(String(b.bank_cd || ""), undefined, {
      numeric: true,
    })
  );
}

export default function BankBranchManagement() {
  const [banks, setBanks] = useState([]);
  const [abbrs, setAbbrs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [tableKey, setTableKey] = useState(0);
  const [tableReady, setTableReady] = useState(false);
  const [form, setForm] = useState(emptyForm);
  const [editingCd, setEditingCd] = useState(null);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  const loadAbbrs = useCallback(async () => {
    try {
      const res = await API.get("master-data/bank-abbr/");
      setAbbrs(asArray(res.data));
    } catch (err) {
      console.error(err);
      setError("Could not load bank abbreviations.");
    }
  }, []);

  const loadBanks = useCallback(async ({ silent = false } = {}) => {
    if (!silent) {
      setLoading(true);
      setError("");
    }
    try {
      const res = await API.get("master-data/banks/");
      setBanks(sortBanksByCode(asArray(res.data)));
      setTableKey((k) => k + 1);
    } catch (err) {
      console.error(err);
      if (!silent) setError("Could not load bank branches.");
    } finally {
      if (!silent) {
        setLoading(false);
        setTableReady(true);
      }
    }
  }, []);

  const upsertBankInList = useCallback((row) => {
    if (!row?.bank_cd) return;
    setBanks((prev) => {
      const idx = prev.findIndex((b) => b.bank_cd === row.bank_cd);
      const next =
        idx >= 0
          ? prev.map((b, i) => (i === idx ? { ...b, ...row } : b))
          : [...prev, row];
      return sortBanksByCode(next);
    });
    setTableKey((k) => k + 1);
  }, []);

  const removeBankFromList = useCallback((bankCd) => {
    setBanks((prev) => prev.filter((b) => b.bank_cd !== bankCd));
    setTableKey((k) => k + 1);
  }, []);

  useEffect(() => {
    loadAbbrs();
    loadBanks();
  }, [loadAbbrs, loadBanks]);

  const sortedAbbrs = useMemo(() => {
    return [...abbrs].sort((a, b) =>
      String(a.bank_type || "").localeCompare(String(b.bank_type || ""), undefined, {
        numeric: true,
      })
    );
  }, [abbrs]);

  const abbrByType = useMemo(() => {
    const map = {};
    abbrs.forEach((row) => {
      map[String(row.bank_type || "").toUpperCase()] = row;
    });
    return map;
  }, [abbrs]);

  const controlBanks = useMemo(() => {
    const prefix = (form.bank_type || "").toUpperCase();
    if (!prefix) return [];
    return banks
      .filter((b) => String(b.bank_cd || "").toUpperCase().startsWith(prefix))
      .sort((a, b) =>
        String(a.bank_cd || "").localeCompare(String(b.bank_cd || ""), undefined, {
          numeric: true,
        })
      );
  }, [banks, form.bank_type]);

  const applyBankType = (bankType, prev = form) => {
    const type = String(bankType || "").toUpperCase();
    const abbr = abbrByType[type];
    const nextControl =
      prev.control_bank_cd &&
      String(prev.control_bank_cd).toUpperCase().startsWith(type)
        ? prev.control_bank_cd
        : "";
    const controlRow = banks.find((b) => b.bank_cd === nextControl);
    return {
      ...prev,
      bank_type: type,
      disp_bank_name: abbr?.bank_name || "",
      disp_bank_id: abbr?.bank_id || "",
      control_bank_cd: nextControl,
      control_bank_desc: controlRow?.bank_desc || controlRow?.control_bank_desc || "",
    };
  };

  const clearForm = () => {
    setForm(emptyForm);
    setEditingCd(null);
    setError("");
  };

  const resetForm = () => {
    clearForm();
    setSuccess("");
  };

  const fillFormFromBank = (bank, { scroll = false } = {}) => {
    const type = (bank.bank_type || bank.bank_cd || "").slice(0, 2).toUpperCase();
    const abbr = abbrByType[type];
    const controlRow = banks.find((b) => b.bank_cd === bank.control_bank_cd);
    setEditingCd(bank.bank_cd);
    setForm({
      bank_type: type,
      disp_bank_name: bank.disp_bank_name || abbr?.bank_name || "",
      disp_bank_id: bank.disp_bank_id || abbr?.bank_id || "",
      bank_cd: bank.bank_cd || "",
      bank_desc: bank.bank_desc || "",
      bank_id: bank.bank_id || "",
      control_bank_cd: bank.control_bank_cd || "",
      control_bank_desc:
        bank.control_bank_desc || controlRow?.bank_desc || "",
      addr1: bank.addr1 || "",
      addr2: bank.addr2 || "",
      ps: bank.ps || "",
      city: bank.city || "",
      dist: bank.dist || "",
      state: bank.state || "",
      pin: bank.pin ?? "",
      country: bank.country || "",
      contact1: bank.contact1 || "",
      contact2: bank.contact2 || "",
      fax_no: bank.fax_no || "",
      email_id: bank.email_id || "",
      rbi_cd: bank.rbi_cd || "",
    });
    if (scroll) {
      window.scrollTo({ top: 0, behavior: "smooth" });
    }
  };

  const onChange = (e) => {
    const { name, value } = e.target;
    if (name === "bank_type") {
      setForm((prev) => applyBankType(value, prev));
      return;
    }
    if (name === "control_bank_cd") {
      const row = banks.find((b) => b.bank_cd === value);
      setForm((prev) => ({
        ...prev,
        control_bank_cd: value,
        control_bank_desc: row?.bank_desc || row?.control_bank_desc || "",
      }));
      return;
    }
    setForm((prev) => ({ ...prev, [name]: value }));
  };

  const startEdit = (bank) => {
    fillFormFromBank(bank, { scroll: true });
    setError("");
    setSuccess("");
  };

  const handleSave = async () => {
    setError("");
    setSuccess("");

    if (!form.bank_type) {
      setError("Select the bank from Bank Abbreviation Master first.");
      return;
    }
    if (!abbrByType[form.bank_type]) {
      setError(
        "Sorry !. This Bank is not available in Bank Abbreviation Master. Enter the Bank Abbreviation first."
      );
      return;
    }
    const payload = toPayload(form, { editing: !!editingCd });
    if (payload.pin !== null && Number.isNaN(payload.pin)) {
      setError("PIN must be a number.");
      return;
    }

    setSaving(true);
    try {
      if (editingCd) {
        const res = await API.put(
          `master-data/banks/${encodeURIComponent(editingCd)}/`,
          payload
        );
        upsertBankInList(res.data);
        fillFormFromBank(res.data);
        setSuccess("Bank branch updated.");
      } else {
        const res = await API.post("master-data/banks/", payload);
        const newCd = res?.data?.bank_cd || "";
        upsertBankInList(res.data);
        clearForm();
        setSuccess(
          newCd
            ? `Bank branch added. System generated Branch Code : ${newCd}`
            : "Bank branch added."
        );
      }
    } catch (err) {
      console.error(err);
      setError(apiErrorMessage(err));
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (bank) => {
    const label = `${bank.bank_cd} — ${bank.bank_desc || "branch"}`;
    if (!window.confirm(`Delete bank branch ${label}?`)) return;

    setError("");
    setSuccess("");
    try {
      await API.delete(`master-data/banks/${encodeURIComponent(bank.bank_cd)}/`);
      removeBankFromList(bank.bank_cd);
      if (editingCd === bank.bank_cd) clearForm();
      setSuccess("Bank branch deleted.");
    } catch (err) {
      console.error(err);
      setError(apiErrorMessage(err));
    }
  };

  const renderField = (field) => (
    <div key={field.name}>
      <label htmlFor={field.name}>{field.label}</label>
      <input
        id={field.name}
        name={field.name}
        type={field.type || "text"}
        className="form-control"
        value={form[field.name]}
        onChange={onChange}
        maxLength={field.maxLength}
      />
    </div>
  );

  return (
    <div className="bank-mgmt-page">
      <Link to="/dashboard/master-data" className="bank-mgmt-back">
        ← Master Data
      </Link>
      <h1>Bank Branches</h1>
      <p className="text-muted mb-4">
        Same as Oracle FI_PM_MH_BANK_E — pick the bank from abbreviation master
        (code, name, ID), then enter the branch. Branch code is generated on save.
        Click a branch code in the list below to load it into the form.
      </p>

      <div className="bank-mgmt-card smpk-form">
        {error && <div className="bank-alert bank-alert-error">{error}</div>}
        {success && <div className="bank-alert bank-alert-success">{success}</div>}
        <h2 className="h5 mb-3">{editingCd ? "Edit bank branch" : "Add bank branch"}</h2>
        <div className="bank-form-grid">
          <div>
            <label htmlFor="bank_type">Short name *</label>
            <select
              id="bank_type"
              name="bank_type"
              className="form-control"
              value={form.bank_type}
              onChange={onChange}
              disabled={!!editingCd}
            >
              <option value="">Select bank…</option>
              {sortedAbbrs.map((row) => (
                <option key={row.bank_type} value={row.bank_type}>
                  {(row.bank_short_name || row.bank_type).trim()} — {row.bank_type} —{" "}
                  {row.bank_name || "—"} — {row.bank_id || "—"}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label htmlFor="disp_bank_name">Bank name</label>
            <input
              id="disp_bank_name"
              className="form-control"
              value={form.disp_bank_name}
              readOnly
              placeholder="From abbreviation master"
            />
          </div>
          <div>
            <label htmlFor="disp_bank_id">Bank ID</label>
            <input
              id="disp_bank_id"
              className="form-control"
              value={form.disp_bank_id}
              readOnly
              placeholder="From abbreviation master"
            />
          </div>
          <div>
            <label htmlFor="bank_cd">Branch code</label>
            <input
              id="bank_cd"
              className="form-control"
              value={form.bank_cd}
              readOnly
              placeholder={editingCd ? "" : "Generated on save"}
            />
          </div>
          <div>
            <label htmlFor="bank_desc">Branch name</label>
            <input
              id="bank_desc"
              name="bank_desc"
              className="form-control"
              value={form.bank_desc}
              onChange={onChange}
              maxLength={50}
            />
          </div>
          <div>
            <label htmlFor="bank_id">Branch ID</label>
            <input
              id="bank_id"
              name="bank_id"
              className="form-control"
              value={form.bank_id}
              onChange={onChange}
              maxLength={7}
            />
          </div>
          <div>
            <label htmlFor="control_bank_cd">Control bank</label>
            <select
              id="control_bank_cd"
              name="control_bank_cd"
              className="form-control"
              value={form.control_bank_cd}
              onChange={onChange}
              disabled={!form.bank_type}
            >
              <option value="">Select controlling branch…</option>
              {controlBanks.map((b) => (
                <option key={b.bank_cd} value={b.bank_cd}>
                  {b.bank_cd} — {b.bank_desc || "—"}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label htmlFor="control_bank_desc">Control bank description</label>
            <input
              id="control_bank_desc"
              className="form-control"
              value={form.control_bank_desc}
              readOnly
            />
          </div>
          {renderField({ name: "rbi_cd", label: "RBI code", maxLength: 9 })}
        </div>
        <div className="bank-form-row bank-form-row-2">
          {renderField({ name: "addr1", label: "Address 1", maxLength: 25 })}
          {renderField({ name: "addr2", label: "Address 2", maxLength: 25 })}
        </div>
        <div className="bank-form-row bank-form-row-4">
          {renderField({ name: "city", label: "City", maxLength: 20 })}
          {renderField({ name: "ps", label: "P.S.", maxLength: 30 })}
          {renderField({ name: "dist", label: "District", maxLength: 20 })}
          {renderField({ name: "state", label: "State", maxLength: 20 })}
        </div>
        <div className="bank-form-row bank-form-row-6">
          {renderField({ name: "pin", label: "PIN", type: "number" })}
          {renderField({ name: "country", label: "Country", maxLength: 20 })}
          {renderField({ name: "contact1", label: "Contact 1", maxLength: 15 })}
          {renderField({ name: "contact2", label: "Contact 2", maxLength: 15 })}
          {renderField({ name: "fax_no", label: "Fax", maxLength: 15 })}
          {renderField({ name: "email_id", label: "Email", maxLength: 30 })}
        </div>
        <div className="bank-form-actions">
          <button
            type="button"
            className="btn btn-primary"
            onClick={handleSave}
            disabled={saving}
          >
            {saving ? "Saving…" : editingCd ? "Update" : "Add bank"}
          </button>
          {editingCd && (
            <button type="button" className="btn btn-outline-secondary" onClick={resetForm}>
              Cancel edit
            </button>
          )}
        </div>
      </div>

      <div className="bank-table-wrap">
        <SmpkDataTable
          ready={tableReady && !loading}
          tableKey={tableKey}
          className="table table-striped table-hover w-100 smpk-datatable"
          options={{
            order: [[0, "asc"]],
            columnDefs: [{ targets: 5, orderable: false, searchable: false }],
            language: { emptyTable: "No bank branches found" },
          }}
        >
          <thead>
            <tr>
              <th>Branch code</th>
              <th>Branch name</th>
              <th>City</th>
              <th>State</th>
              <th>RBI code</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {banks.map((b) => (
              <tr
                key={b.bank_cd}
                className={editingCd === b.bank_cd ? "bank-row-selected" : undefined}
              >
                <td>
                  <button
                    type="button"
                    className="bank-code-link"
                    onClick={() => startEdit(b)}
                    title="Load branch in form"
                  >
                    {b.bank_cd}
                  </button>
                </td>
                <td>{b.bank_desc || "—"}</td>
                <td>{b.city || "—"}</td>
                <td>{b.state || "—"}</td>
                <td>{b.rbi_cd || "—"}</td>
                <td>
                  <button
                    type="button"
                    className="bank-action-btn bank-edit-btn"
                    onClick={() => startEdit(b)}
                  >
                    Edit
                  </button>
                  <button
                    type="button"
                    className="bank-action-btn bank-delete-btn"
                    onClick={() => handleDelete(b)}
                  >
                    Delete
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </SmpkDataTable>
      </div>
    </div>
  );
}
