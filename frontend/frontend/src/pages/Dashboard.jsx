import "../styles/Dashboard.css";
const user = JSON.parse(localStorage.getItem("user"));
const role = user?.role;

export default function Dashboard() {
  return (
    <div className="dashboard-container">
      

      {/* Sidebar */}
      <div className="sidebar">
        <h3>Pension System</h3>

        <ul>
          <li>Dashboard</li>
          {/* Admin only */}
          {role === "Admin" && (
            <>
              <li>Users</li>
              <li>Workflow</li>
              <li>Audit Logs</li>
            </>
          )}
          {/* Clerk + Admin */}
          {(role === "Admin" || role === "Clerk") && (
            <li>Employees</li>
          )}
          
          
        </ul>
      </div>

      {/* Main Content */}
      <div className="main-area">

        {/* Topbar */}
        <div className="topbar">
          
          <span>Welcome, {user?.username} ({role})</span>
          <button
            onClick={() => {
              localStorage.removeItem("access");
              window.location.href = "/";
            }}
          >
            Logout
          </button>
        </div>

        {/* Content */}
        <div className="content">
          <h2>Dashboard</h2>
          <p>Welcome to Pension Management System</p>
        </div>

      </div>
    </div>
  );
}