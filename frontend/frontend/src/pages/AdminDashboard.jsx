import { Link } from "react-router-dom";

export default function AdminDashboard() {
  return (
    <div className="admin-dashboard-page">
      <h1>Administration</h1>
      <p className="text-muted mb-4">
        Central place for user activity, audit, workflow, user creation, roles,
        and assignments. Detailed widgets will be added here next.
      </p>

      <div className="admin-quick-links">
        <Link to="/dashboard/users" className="admin-quick-card">
          <h3>User Management</h3>
          <p>Create users and assign roles with employee profile details.</p>
        </Link>
        <Link to="/dashboard/roles" className="admin-quick-card">
          <h3>Role Management</h3>
          <p>Create and activate or deactivate application roles.</p>
        </Link>
        <Link to="/dashboard/logs" className="admin-quick-card">
          <h3>Audit Logs</h3>
          <p>Review system changes and user activity records.</p>
        </Link>
        <Link to="/dashboard/workflow" className="admin-quick-card">
          <h3>Workflow</h3>
          <p>Configure approval steps and track workflow instances.</p>
        </Link>
        <Link to="/dashboard/master-data" className="admin-quick-card">
          <h3>Master Data Management</h3>
          <p>Add, edit, or delete bank branches and bank abbreviation codes.</p>
        </Link>
        <Link to="/dashboard/oracle-transfer" className="admin-quick-card">
          <h3>Database transfer &amp; update</h3>
          <p>
            Oracle → MySQL finance dump, and finance → smpk_pension incremental
            or full table update from Admin.
          </p>
        </Link>
      </div>
    </div>
  );
}
