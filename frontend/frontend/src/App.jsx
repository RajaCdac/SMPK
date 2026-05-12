import "./services/Api"; // Ensure API is initialized
import { BrowserRouter, Routes, Route } from "react-router-dom";
import MainLayout from "./components/Layout/MainLayout";
import DashboardLayout from "./components/Layout/DashboardLayout";  
import Home from "./pages/Home";
import Login from "./pages/Login";
import Dashboard from "./pages/Dashboard";
import RoleManagement from "./pages/RoleManagement";
import ProtectedRoute from "./components/ProtectedRoute";
import PensionCalculationPrint from "./pages/PensionCalculationPrint";
import PensionCaseList from "./pages/PensionCaseList";
import AuditLogs from "./pages/AuditLogs";


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
          <Route path="cases" element={<PensionCaseList />} />
          <Route path="logs" element={<AuditLogs />} />

        </Route>
        <Route path="/pension-report/:id" element={<PensionCalculationPrint />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;