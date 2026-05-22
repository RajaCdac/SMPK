import { Outlet, Link } from "react-router-dom";

export default function DashboardLayout() {
  const user = JSON.parse(localStorage.getItem("user"));
  const role = user?.role;

  return (
    <div className="dashboard-container">

      {/* Sidebar */}
      <div className="sidebar">
        <h3>Pension System</h3>

        <ul>
          <li><Link to="/dashboard" style={{color: "white", textDecoration: "none",}} >Dashboard</Link></li>
          {role === "User" && (
            <>
              {/* <li>Users</li> */}
              {/* <li><Link to="/dashboard/roles" style={{color: "white", textDecoration: "none",}}>Role Management</Link></li> */}
              {/* <li>Workflow</li> */}
              <li> <Link to="/dashboard/logs" style={{color: "white", textDecoration: "none",}}>Audit Logs</Link></li>
              <li><Link to="/dashboard/cases" style={{color: "white", textDecoration: "none",}}>Pension Cases</Link></li>
              <li><Link to="/dashboard/firstpensioncases" style={{color: "white", textDecoration: "none",}}>First Pension</Link></li>
              <li><Link to="/dashboard/methodology2" style={{color: "white", textDecoration: "none",}}>Methodology2</Link></li>
            </>
          )}

          {(role === "Admin" || role === "Clerk") && (
            <li>Employees</li>
          )}
        </ul>
      </div>

      {/* Main Area */}
      <div className="main-area">

        {/* Topbar */}
        <div className="topbar">
          <span>Welcome, {user?.username} ({role})</span>

          <button
            onClick={() => {
              localStorage.clear();
              window.location.href = "/";
            }}
          >
            Logout
          </button>
        </div>

        {/* 🔥 THIS IS THE KEY */}
        <div className="content">
          <Outlet />
        </div>

      </div>
    </div>
  );
}