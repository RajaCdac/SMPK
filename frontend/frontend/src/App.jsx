import { BrowserRouter, Routes, Route } from "react-router-dom";
import MainLayout from "./components/Layout/MainLayout";
import DashboardLayout from "./components/Layout/DashboardLayout";  
import Home from "./pages/Home";
import Login from "./pages/Login";
import Dashboard from "./pages/Dashboard";
import RoleManagement from "./pages/RoleManagement";
import ProtectedRoute from "./components/ProtectedRoute";

function App() {
  return (
    <BrowserRouter>
      <Routes>
        {/* Public Home Page */}
        <Route path="/" element={<MainLayout />}>
          <Route index element={<Home />} />
          {/* Login Page */}
          <Route path="login" element={<Login />} />
          <Route path="roles" element={<RoleManagement />} />
        
        </Route>
        {/* Protected Dashboard */}
        <Route
          path="/dashboard"
          element={
            <ProtectedRoute>
              <DashboardLayout />
            </ProtectedRoute>
          }
        >
          <Route index element={<Dashboard />} />
          <Route path="roles" element={<RoleManagement />} />
        </Route>
        
      </Routes>
    </BrowserRouter>
  );
}

export default App;