import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import API from "../services/Api";
import SmpkDataTable from "../components/DataTable/SmpkDataTable";
import "../styles/MasterData.css";

const emptyForm = {
  bank_cd: "",
  bank_desc: "",
  bank_id: "",
  control_bank_cd: "",
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
  old_bank_cd: "",
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

function toPayload(form) {
  const pin = String(form.pin || "").trim();
  return {
    bank_cd: (form.bank_cd || "").trim().toUpperCase(),
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
    old_bank_cd: (form.old_bank_cd || "").trim(),
  };
}

export default function BankBranchManagement() {
  const [banks, setBanks] = useState([]);
  const [loading, setLoading] = useState(true);
  const [tableKey, setTableKey] = useState(0);
  const [tableReady, setTableReady] = useState(false);
  const [form, setForm] = useState(emptyForm);
  const [editingCd, setEditingCd] = useState(null);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  const loadBanks = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const res = await API.get("master-data/banks/");
      setBanks(asArray(res.data));
      setTableKey((k) => k + 1);
    } catch (err) {
      console.error(err);
      setError("Could not load bank branches.");
    } finally {
      setLoading(false);
      setTableReady(true);
    }
  }, []);

  useEffect(() => {
    loadBanks();
  }, [loadBanks]);

  const resetForm = () => {
    setForm(emptyForm);
    setEditingCd(null);
    setError("");
    setSuccess("");
  };

  const onChange = (e) => {
    const { name, value } = e.target;
    setForm((prev) => ({ ...prev, [name]: value }));
  };

  const startEdit = (bank) => {
    setEditingCd(bank.bank_cd);
    setForm({
      bank_cd: bank.bank_cd || "",
      bank_desc: bank.bank_desc || "",
      bank_id: bank.bank_id || "",
      control_bank_cd: bank.control_bank_cd || "",
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
      old_bank_cd: bank.old_bank_cd || "",
    });
    setError("");
    setSuccess("");
    window.scrollTo({ top: 0, behavior: "smooth" });
  };

  const handleSave = async () => {
    setError("");
    setSuccess("");

    const payload = toPayload(form);
    if (!payload.bank_cd) {
      setError("Bank code is required.");
      return;
    }
    if (payload.bank_cd.length > 6) {
      setError("Bank code must be at most 6 characters.");
      return;
    }
    if (payload.pin !== null && Number.isNaN(payload.pin)) {
      setError("PIN must be a number.");
      return;
    }

    setSaving(true);
    try {
      if (editingCd) {
        await API.put(`master-data/banks/${encodeURIComponent(editingCd)}/`, payload);
        setSuccess("Bank branch updated.");
      } else {
        await API.post("master-data/banks/", payload);
        setSuccess("Bank branch added.");
      }
      resetForm();
      setTableReady(false);
      await loadBanks();
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
      if (editingCd === bank.bank_cd) resetForm();
      setSuccess("Bank branch deleted.");
      setTableReady(false);
      await loadBanks();
    } catch (err) {
      console.error(err);
      setError(apiErrorMessage(err));
    }
  };

  const fields = [
    { name: "bank_cd", label: "Bank code *", maxLength: 6, disabled: !!editingCd },
    { name: "bank_desc", label: "Bank description", maxLength: 50 },
    { name: "bank_id", label: "Bank ID", maxLength: 7 },
    { name: "control_bank_cd", label: "Control bank code", maxLength: 6 },
    { name: "rbi_cd", label: "RBI code", maxLength: 9 },
    { name: "old_bank_cd", label: "Old bank code", maxLength: 6 },
    { name: "addr1", label: "Address 1", maxLength: 25 },
    { name: "addr2", label: "Address 2", maxLength: 25 },
    { name: "ps", label: "P.S.", maxLength: 30 },
    { name: "city", label: "City", maxLength: 20 },
    { name: "dist", label: "District", maxLength: 20 },
    { name: "state", label: "State", maxLength: 20 },
    { name: "pin", label: "PIN", type: "number" },
    { name: "country", label: "Country", maxLength: 20 },
    { name: "contact1", label: "Contact 1", maxLength: 15 },
    { name: "contact2", label: "Contact 2", maxLength: 15 },
    { name: "fax_no", label: "Fax", maxLength: 15 },
    { name: "email_id", label: "Email", maxLength: 30 },
  ];

  return (
    <div className="bank-mgmt-page">
      <Link to="/dashboard/master-data" className="bank-mgmt-back">
        ← Master Data
      </Link>
      <h1>Bank Branches</h1>
      <p className="text-muted mb-4">
        Manage FI_PM_MH_BANK records — used in pension proposal and employee bank
        details.
      </p>

      {error && <div className="bank-alert bank-alert-error">{error}</div>}
      {success && <div className="bank-alert bank-alert-success">{success}</div>}

      <div className="bank-mgmt-card smpk-form">
        <h2 className="h5 mb-3">{editingCd ? "Edit bank branch" : "Add bank branch"}</h2>
        <div className="bank-form-grid">
          {fields.map((field) => (
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
                disabled={field.disabled}
              />
            </div>
          ))}
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
            order: [[1, "asc"]],
            columnDefs: [{ targets: 5, orderable: false, searchable: false }],
            language: { emptyTable: "No bank branches found" },
          }}
        >
          <thead>
            <tr>
              <th>Code</th>
              <th>Description</th>
              <th>City</th>
              <th>State</th>
              <th>RBI code</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {banks.map((b) => (
              <tr key={b.bank_cd}>
                <td>{b.bank_cd}</td>
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
