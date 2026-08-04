import { useEffect, useState } from "react";
import API from "../services/Api";
import SmpkDataTable from "../components/DataTable/SmpkDataTable";
import "../styles/RoleManagement.css";

export default function RoleManagement() {
  const [roles, setRoles] = useState([]);
  const [loading, setLoading] = useState(true);
  const [name, setName] = useState("");

  const fetchRoles = () => {
    setLoading(true);
    API.get("roles/")
      .then((res) => setRoles(Array.isArray(res.data) ? res.data : []))
      .catch((err) => console.error(err))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    fetchRoles();
  }, []);

  const createRole = async () => {
    try {
      await API.post("roles/", { name });
      setName("");
      fetchRoles();
    } catch (err) {
      console.error(err);
    }
  };

  const toggleRole = async (role) => {
    await API.patch(`roles/${role.id}/`, {
      is_active: !role.is_active,
    });
    fetchRoles();
  };

  return (
    <div className="role-page">
      <h2 className="role-title">Role Management</h2>

      <div className="role-card smpk-form">
        <div className="role-form">
          <input
            type="text"
            placeholder="Enter Role Name"
            value={name}
            onChange={(e) => setName(e.target.value)}
            className="role-input form-control"
          />
          <button type="button" className="add-role-btn" onClick={createRole}>
            + Add Role
          </button>
        </div>
      </div>

      <div className="role-table-container">
        <SmpkDataTable
          ready={!loading}
          tableKey={roles.map((r) => `${r.id}-${r.is_active}`).join("-") || "empty"}
          className="table table-striped table-hover w-100 role-table smpk-datatable"
          options={{
            order: [[0, "asc"]],
            columnDefs: [{ targets: 2, orderable: false, searchable: false }],
            language: { emptyTable: "No roles found" },
          }}
        >
          <thead>
            <tr>
              <th>Role Name</th>
              <th>Status</th>
              <th>Action</th>
            </tr>
          </thead>
          <tbody>
            {roles.map((r) => (
              <tr key={r.id}>
                <td>{r.name}</td>
                <td>
                  <span
                    className={
                      r.is_active
                        ? "status-badge status-active"
                        : "status-badge status-inactive"
                    }
                  >
                    {r.is_active ? "Active" : "Inactive"}
                  </span>
                </td>
                <td>
                  <button
                    type="button"
                    className={
                      r.is_active
                        ? "action-btn deactivate-btn"
                        : "action-btn activate-btn"
                    }
                    onClick={() => toggleRole(r)}
                  >
                    {r.is_active ? "Deactivate" : "Activate"}
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
