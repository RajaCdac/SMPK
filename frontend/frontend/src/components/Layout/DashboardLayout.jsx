import { useEffect, useState } from "react";
import { Outlet, NavLink, useLocation } from "react-router-dom";
import API from "../../services/Api";
import "../../styles/Dashboard.css";
import {
  getStoredUser,
  getNavItemsForUser,
  normalizeRoleCode,
} from "../../utils/authRoles";

const linkClass = ({ isActive }) =>
  `sidebar-link${isActive ? " sidebar-link-active" : ""}`;

function isPathUnderNavItem(pathname, item) {
  if (item.to) {
    if (item.end) {
      return pathname === item.to;
    }
    return pathname === item.to || pathname.startsWith(`${item.to}/`);
  }
  return (item.children || []).some((child) =>
    isPathUnderNavItem(pathname, child)
  );
}

function SidebarNavItem({ item }) {
  const location = useLocation();
  const hasChildren = Array.isArray(item.children) && item.children.length > 0;
  const childActive = hasChildren && isPathUnderNavItem(location.pathname, item);
  const [open, setOpen] = useState(childActive);

  useEffect(() => {
    if (childActive) {
      setOpen(true);
    }
  }, [childActive, location.pathname]);

  if (!hasChildren) {
    return (
      <li>
        <NavLink to={item.to} end={item.end} className={linkClass}>
          {item.label}
        </NavLink>
      </li>
    );
  }

  return (
    <li
      className={`sidebar-group${open ? " is-open" : ""}${
        childActive ? " has-active" : ""
      }`}
    >
      <button
        type="button"
        className={`sidebar-group-toggle${childActive ? " is-active" : ""}`}
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
      >
        <span>{item.label}</span>
        <span className="sidebar-caret" aria-hidden="true">
          {open ? "▾" : "▸"}
        </span>
      </button>
      {open ? (
        <ul className="sidebar-subnav">
          {item.children.map((child) => (
            <li key={child.to || child.label}>
              <NavLink
                to={child.to}
                end={child.end}
                className={({ isActive }) =>
                  `sidebar-link sidebar-sublink${
                    isActive ? " sidebar-link-active" : ""
                  }`
                }
              >
                {child.label}
              </NavLink>
            </li>
          ))}
        </ul>
      ) : null}
    </li>
  );
}

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
        <div className="sidebar-tricolour" aria-hidden="true">
          <span className="strip-saffron" />
          <span className="strip-white" />
          <span className="strip-green" />
        </div>
        <h3>Pension System</h3>
        <p className="sidebar-role-badge">{user?.role || roleCode}</p>

        <ul className="sidebar-nav">
          {navItems.map((item) => (
            <SidebarNavItem
              key={item.key || item.to || item.label}
              item={item}
            />
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
            onClick={async () => {
              try {
                await API.post("logout/");
              } catch {
                /* still clear session if audit/logout call fails */
              }
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
