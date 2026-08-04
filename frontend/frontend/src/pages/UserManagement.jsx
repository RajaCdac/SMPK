import { useCallback, useEffect, useState } from "react";
import API from "../services/Api";
import SmpkDataTable from "../components/DataTable/SmpkDataTable";
import "../styles/UserManagement.css";

const emptyForm = {
  username: "",
  password: "",
  email: "",
  first_name: "",
  last_name: "",
  role_id: "",
  emp_code: "",
  designation: "",
  department: "",
  mobile_no: "",
};

function formatUserName(u) {
  return (
    u.display_name ||
    [u.first_name, u.last_name].filter(Boolean).join(" ") ||
    "—"
  );
}

function asArray(data) {
  if (Array.isArray(data)) return data;
  if (data?.results && Array.isArray(data.results)) return data.results;
  return [];
}

function apiErrorMessage(data) {
  if (!data || typeof data !== "object") return "";
  if (typeof data.error === "string") return data.error;
  const fields = [
    "username",
    "password",
    "email",
    "role_id",
    "first_name",
    "last_name",
  ];
  for (const key of fields) {
    const msg = data[key];
    if (Array.isArray(msg) && msg[0]) return msg[0];
    if (typeof msg === "string") return msg;
  }
  const firstKey = Object.keys(data)[0];
  const first = data[firstKey];
  if (Array.isArray(first) && first[0]) return first[0];
  if (typeof first === "string") return first;
  return "";
}

export default function UserManagement() {
  const [users, setUsers] = useState([]);
  const [roles, setRoles] = useState([]);
  const [loading, setLoading] = useState(true);
  const [tableKey, setTableKey] = useState(0);
  const [tableReady, setTableReady] = useState(false);
  const [saving, setSaving] = useState(false);
  const [form, setForm] = useState(emptyForm);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  const loadData = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const [usersRes, rolesRes] = await Promise.all([
        API.get("users/"),
        API.get("roles/"),
      ]);
      setUsers(asArray(usersRes.data));
      setRoles(asArray(rolesRes.data).filter((r) => r.is_active));
      setTableKey((k) => k + 1);
    } catch (err) {
      console.error(err);
      setError("Could not load users or roles.");
    } finally {
      setLoading(false);
      setTableReady(true);
    }
  }, []);

  const remountUsersTable = useCallback(async (loadUsers) => {
    setTableReady(false);
    await loadUsers();
    setTableKey((k) => k + 1);
    requestAnimationFrame(() => setTableReady(true));
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const onChange = (e) => {
    const { name, value } = e.target;
    setForm((prev) => ({ ...prev, [name]: value }));
  };

  const handleCreate = async () => {
    setError("");
    setSuccess("");

    if (!form.role_id) {
      setError("Please select a role.");
      return;
    }
    if ((form.password || "").length < 6) {
      setError("Password must be at least 6 characters.");
      return;
    }
    if (form.email && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(form.email)) {
      setError("Enter a valid email address.");
      return;
    }

    setSaving(true);
    try {
      const { role_id, ...rest } = form;
      const res = await API.post("users/", {
        ...rest,
        role_id: Number(role_id),
      });
      setForm(emptyForm);
      setSuccess(
        `User "${res.data?.username || rest.username}" created successfully.`
      );
      await remountUsersTable(async () => {
        const usersRes = await API.get("users/");
        setUsers(asArray(usersRes.data));
      });
    } catch (err) {
      console.error(err);
      setError(
        apiErrorMessage(err.response?.data) || "Failed to create user."
      );
    } finally {
      setSaving(false);
    }
  };

  const toggleUserActive = async (user) => {
    try {
      await API.patch(`users/${user.id}/`, { is_active: !user.is_active });
      await remountUsersTable(async () => {
        const usersRes = await API.get("users/");
        setUsers(asArray(usersRes.data));
      });
    } catch (err) {
      console.error(err);
      alert("Could not update user status.");
    }
  };

  return (
    <div className="user-mgmt-page">
      <h1>User Management</h1>
      <p className="text-muted mb-4">
        Create login accounts (username, password, name, email) and link
        employee details (code, designation, department, mobile) with a role.
      </p>

      <div className="user-mgmt-card smpk-form">
        <h2 className="h5 mb-3">Create user</h2>
        <div className="user-mgmt-create-form">
          <div className="row g-3">
            <div className="col-12 col-md-6 col-lg-4">
              <label className="form-label">Username *</label>
              <input
                className="form-control"
                name="username"
                value={form.username}
                onChange={onChange}
              />
            </div>
            <div className="col-12 col-md-6 col-lg-4">
              <label className="form-label">Password *</label>
              <input
                type="password"
                className="form-control"
                name="password"
                value={form.password}
                onChange={onChange}
                autoComplete="new-password"
              />
              <div className="form-text">At least 6 characters.</div>
            </div>
            <div className="col-12 col-md-6 col-lg-4">
              <label className="form-label">Email</label>
              <input
                type="email"
                className="form-control"
                name="email"
                value={form.email}
                onChange={onChange}
              />
            </div>
            <div className="col-12 col-md-6 col-lg-4">
              <label className="form-label">First name</label>
              <input
                className="form-control"
                name="first_name"
                value={form.first_name}
                onChange={onChange}
              />
            </div>
            <div className="col-12 col-md-6 col-lg-4">
              <label className="form-label">Last name</label>
              <input
                className="form-control"
                name="last_name"
                value={form.last_name}
                onChange={onChange}
              />
            </div>
            <div className="col-12 col-md-6 col-lg-4">
              <label className="form-label">Role *</label>
              <select
                className="form-select"
                name="role_id"
                value={form.role_id}
                onChange={onChange}
              >
                <option value="">Select role</option>
                {roles.map((r) => (
                  <option key={r.id} value={r.id}>
                    {r.name} ({r.code})
                  </option>
                ))}
              </select>
            </div>
            <div className="col-12 col-md-6 col-lg-4">
              <label className="form-label">Employee code</label>
              <input
                className="form-control"
                name="emp_code"
                value={form.emp_code}
                onChange={onChange}
              />
            </div>
            <div className="col-12 col-md-6 col-lg-4">
              <label className="form-label">Designation</label>
              <input
                className="form-control"
                name="designation"
                value={form.designation}
                onChange={onChange}
              />
            </div>
            <div className="col-12 col-md-6 col-lg-4">
              <label className="form-label">Department</label>
              <input
                className="form-control"
                name="department"
                value={form.department}
                onChange={onChange}
              />
            </div>
            <div className="col-12 col-md-6 col-lg-4">
              <label className="form-label">Mobile no.</label>
              <input
                className="form-control"
                name="mobile_no"
                value={form.mobile_no}
                onChange={onChange}
              />
            </div>
          </div>

          {error && (
            <p className="text-danger mt-3 mb-0" role="alert">
              {error}
            </p>
          )}

          {success && (
            <p className="text-success mt-3 mb-0" role="status">
              {success}
            </p>
          )}

          <div className="smpk-form-actions mt-3">
            <button
              type="button"
              className="btn btn-primary"
              disabled={saving}
              onClick={handleCreate}
            >
              {saving ? "Creating…" : "Create user"}
            </button>
          </div>
        </div>
      </div>

      <div className="user-mgmt-table-wrap mt-4">
        <h2 className="h5 mb-3">Users</h2>
        <SmpkDataTable
          ready={!loading && tableReady}
          tableKey={`users-${tableKey}`}
          className="table table-striped table-hover w-100 smpk-datatable user-mgmt-table"
          options={{
            order: [[0, "asc"]],
            columnDefs: [{ targets: 9, orderable: false, searchable: false }],
            language: { emptyTable: "No users found" },
          }}
        >
          <thead>
            <tr>
              <th>Username</th>
              <th>Name</th>
              <th>Email</th>
              <th>Emp Code</th>
              <th>Designation</th>
              <th>Department</th>
              <th>Mobile</th>
              <th>Role</th>
              <th>Status</th>
              <th>Action</th>
            </tr>
          </thead>
          <tbody>
            {users.map((u) => (
              <tr key={u.id}>
                <td>{u.username}</td>
                <td>{formatUserName(u)}</td>
                <td>{u.email || "—"}</td>
                <td>{u.profile?.emp_code || "—"}</td>
                <td>{u.profile?.designation || "—"}</td>
                <td>{u.profile?.department || "—"}</td>
                <td>{u.profile?.mobile_no || "—"}</td>
                <td>{u.role_name || "—"}</td>
                <td>{u.is_active ? "Active" : "Inactive"}</td>
                <td>
                  <button
                    type="button"
                    className={
                      u.is_active
                        ? "btn btn-sm btn-outline-danger"
                        : "btn btn-sm btn-outline-success"
                    }
                    onClick={() => toggleUserActive(u)}
                  >
                    {u.is_active ? "Deactivate" : "Activate"}
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
