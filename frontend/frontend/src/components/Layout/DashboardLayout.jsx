import { Outlet, NavLink } from "react-router-dom";
import "../../styles/Dashboard.css";
import {
  getStoredUser,
  getNavItemsForUser,
  normalizeRoleCode,
} from "../../utils/authRoles";

const linkClass = ({ isActive }) =>
  `sidebar-link${isActive ? " sidebar-link-active" : ""}`;

export default function DashboardLayout() {
  const user = getStoredUser();
  const roleCode = normalizeRoleCode(user);
  const navItems = getNavItemsForUser(user);
  const displayName =
    user?.display_name ||
    [user?.first_name, user?.last_name].filter(Boolean).join(" ") ||
    user?.username ||
    "User";

  return (
    <div className="dashboard-container">
      <div className="sidebar">
        <h3>Pension System</h3>
        <p className="sidebar-role-badge">{user?.role || roleCode}</p>

        <ul className="sidebar-nav">
          {navItems.map((item) => (
            <li key={item.to}>
              <NavLink to={item.to} end={item.end} className={linkClass}>
                {item.label}
              </NavLink>
            </li>
          ))}
        </ul>
      </div>

      <div className="main-area">
        <div className="topbar">
          <span>
            Welcome, {displayName} ({user?.role || roleCode})
          </span>
          <button
            type="button"
            onClick={() => {
              localStorage.clear();
              window.location.href = "/";
            }}
          >
            Logout
          </button>
        </div>

        <div className="content">
          <Outlet />
        </div>
      </div>
    </div>
  );
}
