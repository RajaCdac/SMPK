import { Navigate, Outlet } from "react-router-dom";
import {
  defaultDashboardPath,
  roleAllows,
} from "../utils/authRoles";

/**
 * @param {{ allow: "admin"|"first_pension"|"family_pension"|string[] }} props
 */
export default function RoleProtectedRoute({ allow = "first_pension" }) {
  const token = localStorage.getItem("access");
  if (!token) {
    return <Navigate to="/login" replace />;
  }

  if (!roleAllows(allow)) {
    return <Navigate to={defaultDashboardPath()} replace />;
  }

  return <Outlet />;
}
