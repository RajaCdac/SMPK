import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import API from "../services/Api";
import SmpkDataTable from "../components/DataTable/SmpkDataTable";
import "../styles/MasterData.css";

const emptyForm = {
  bank_type: "",
  bank_name: "",
  bank_short_name: "",
  bank_id: "",
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

export default function BankAbbrManagement() {
  const [rows, setRows] = useState([]);
  const [loading, setLoading] = useState(true);
  const [tableKey, setTableKey] = useState(0);
  const [tableReady, setTableReady] = useState(false);
  const [form, setForm] = useState(emptyForm);
  const [editingType, setEditingType] = useState(null);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  const loadRows = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const res = await API.get("master-data/bank-abbr/");
      setRows(asArray(res.data));
      setTableKey((k) => k + 1);
    } catch (err) {
      console.error(err);
      setError("Could not load bank abbreviations.");
    } finally {
      setLoading(false);
      setTableReady(true);
    }
  }, []);

  useEffect(() => {
    loadRows();
  }, [loadRows]);

  const resetForm = () => {
    setForm(emptyForm);
    setEditingType(null);
    setError("");
    setSuccess("");
  };

  const onChange = (e) => {
    const { name, value } = e.target;
    setForm((prev) => ({ ...prev, [name]: value }));
  };

  const startEdit = (row) => {
    setEditingType(row.bank_type);
    setForm({
      bank_type: row.bank_type || "",
      bank_name: row.bank_name || "",
      bank_short_name: row.bank_short_name || "",
      bank_id: row.bank_id || "",
    });
    setError("");
    setSuccess("");
    window.scrollTo({ top: 0, behavior: "smooth" });
  };

  const handleSave = async () => {
    setError("");
    setSuccess("");

    const payload = {
      bank_type: (form.bank_type || "").trim(),
      bank_name: (form.bank_name || "").trim(),
      bank_short_name: (form.bank_short_name || "").trim(),
      bank_id: (form.bank_id || "").trim(),
    };

    if (!payload.bank_type) {
      setError("Bank type code is required.");
      return;
    }
    if (payload.bank_type.length > 2) {
      setError("Bank type must be at most 2 characters.");
      return;
    }

    setSaving(true);
    try {
      if (editingType) {
        await API.put(
          `master-data/bank-abbr/${encodeURIComponent(editingType)}/`,
          payload
        );
        setSuccess("Bank abbreviation updated.");
      } else {
        await API.post("master-data/bank-abbr/", payload);
        setSuccess("Bank abbreviation added.");
      }
      resetForm();
      setTableReady(false);
      await loadRows();
    } catch (err) {
      console.error(err);
      setError(apiErrorMessage(err));
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (row) => {
    const label = `${row.bank_type} — ${row.bank_name || "abbreviation"}`;
    if (!window.confirm(`Delete bank abbreviation ${label}?`)) return;

    setError("");
    setSuccess("");
    try {
      await API.delete(
        `master-data/bank-abbr/${encodeURIComponent(row.bank_type)}/`
      );
      if (editingType === row.bank_type) resetForm();
      setSuccess("Bank abbreviation deleted.");
      setTableReady(false);
      await loadRows();
    } catch (err) {
      console.error(err);
      setError(apiErrorMessage(err));
    }
  };

  return (
    <div className="bank-mgmt-page">
      <Link to="/dashboard/master-data" className="bank-mgmt-back">
        ← Master Data
      </Link>
      <h1>Bank Abbreviations</h1>
      <p className="text-muted mb-4">
        Manage FI_PM_MH_BANKABBR records — bank type codes and short names.
      </p>

      {error && <div className="bank-alert bank-alert-error">{error}</div>}
      {success && <div className="bank-alert bank-alert-success">{success}</div>}

      <div className="bank-mgmt-card smpk-form">
        <h2 className="h5 mb-3">
          {editingType ? "Edit abbreviation" : "Add abbreviation"}
        </h2>
        <div className="bank-form-grid">
          <div>
            <label htmlFor="bank_type">Bank type *</label>
            <input
              id="bank_type"
              name="bank_type"
              className="form-control"
              value={form.bank_type}
              onChange={onChange}
              maxLength={2}
              disabled={!!editingType}
            />
          </div>
          <div>
            <label htmlFor="bank_name">Bank name</label>
            <input
              id="bank_name"
              name="bank_name"
              className="form-control"
              value={form.bank_name}
              onChange={onChange}
              maxLength={60}
            />
          </div>
          <div>
            <label htmlFor="bank_short_name">Short name</label>
            <input
              id="bank_short_name"
              name="bank_short_name"
              className="form-control"
              value={form.bank_short_name}
              onChange={onChange}
              maxLength={10}
            />
          </div>
          <div>
            <label htmlFor="bank_id">Bank ID</label>
            <input
              id="bank_id"
              name="bank_id"
              className="form-control"
              value={form.bank_id}
              onChange={onChange}
              maxLength={3}
            />
          </div>
        </div>
        <div className="bank-form-actions">
          <button
            type="button"
            className="btn btn-primary"
            onClick={handleSave}
            disabled={saving}
          >
            {saving ? "Saving…" : editingType ? "Update" : "Add"}
          </button>
          {editingType && (
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
            columnDefs: [{ targets: 4, orderable: false, searchable: false }],
            language: { emptyTable: "No bank abbreviations found" },
          }}
        >
          <thead>
            <tr>
              <th>Type</th>
              <th>Bank name</th>
              <th>Short name</th>
              <th>Bank ID</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => (
              <tr key={r.bank_type}>
                <td>{r.bank_type}</td>
                <td>{r.bank_name || "—"}</td>
                <td>{r.bank_short_name || "—"}</td>
                <td>{r.bank_id || "—"}</td>
                <td>
                  <button
                    type="button"
                    className="bank-action-btn bank-edit-btn"
                    onClick={() => startEdit(r)}
                  >
                    Edit
                  </button>
                  <button
                    type="button"
                    className="bank-action-btn bank-delete-btn"
                    onClick={() => handleDelete(r)}
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
