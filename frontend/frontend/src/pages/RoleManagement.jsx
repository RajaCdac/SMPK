import { useEffect, useState } from "react";
import API from "../services/Api";


export default function RoleManagement() {
  const [roles, setRoles] = useState([]);
  const [name, setName] = useState("");

  const fetchRoles = () => {
    API.get("roles/").then((res) => setRoles(res.data));
  };

  useEffect(() => {
    fetchRoles();
  }, []);

  const createRole = async () => {
  console.log("BUTTON CLICKED");   // 👈 ADD THIS

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
    <div>
      <h2>Role Management</h2>

      {/* Create */}
      <div className="form-group">
        <input
          placeholder="Role name"
          value={name}
          onChange={(e) => setName(e.target.value)}
          className="form-control"
        />
      </div>
      <button onClick={createRole}>Add Role</button>

      {/* List */}
      <table border="1">
        <thead>
          <tr>
            <th>Name</th>
            <th>Status</th>
            <th>Action</th>
          </tr>
        </thead>

        <tbody>
          {roles.map((r) => (
            <tr key={r.id}>
              <td>{r.name}</td>
              <td>{r.is_active ? "Active" : "Inactive"}</td>
              <td>
                <button onClick={() => toggleRole(r)}>
                  {r.is_active ? "Deactivate" : "Activate"}
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}