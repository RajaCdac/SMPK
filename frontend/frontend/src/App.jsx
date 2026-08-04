import "./services/Api";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import MainLayout from "./components/Layout/MainLayout";
import DashboardLayout from "./components/Layout/DashboardLayout";
import Home from "./pages/Home";
import Dashboard from "./pages/Dashboard";
import RoleManagement from "./pages/RoleManagement";
import UserManagement from "./pages/UserManagement";
import AdminDashboard from "./pages/AdminDashboard";
import WorkflowPage from "./pages/WorkflowPage";
import ProtectedRoute from "./components/ProtectedRoute";
import RoleProtectedRoute from "./components/RoleProtectedRoute";
import PageErrorBoundary from "./components/PageErrorBoundary";
import PensionCalculationPrint from "./pages/PensionCalculationPrint";
import PensionCaseList from "./pages/PensionCaseList";
import AuditLogs from "./pages/AuditLogs";
import Methodology1 from "./pages/Methodology1";
import Methodology2 from "./pages/Methodology2";
import FirstPensionCase from "./pages/FirstPensionCase";
import FamilyPensionCase from "./pages/FamilyPensionCase";
import FamilyPension from "./pages/FamilyPension";
import ArchiveFirstPension from "./pages/ArchiveFirstPension";
import MasterDataManagement from "./pages/MasterDataManagement";
import BankBranchManagement from "./pages/BankBranchManagement";
import BankAbbrManagement from "./pages/BankAbbrManagement";
import { isAdminUser, isFamilyPensionUser } from "./utils/authRoles";

function DashboardIndex() {
  if (isAdminUser()) {
    return <Navigate to="/dashboard/admin" replace />;
  }
  if (isFamilyPensionUser()) {
    return <Navigate to="/dashboard/familypensioncases" replace />;
  }
  return <Dashboard />;
}

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<MainLayout />}>
          <Route index element={<Home />} />
          <Route path="login" element={<Home showLoginInitially />} />
        </Route>

        <Route
          path="/dashboard"
          element={
            <ProtectedRoute>
              <DashboardLayout />
            </ProtectedRoute>
          }
        >
          <Route index element={<DashboardIndex />} />

          <Route element={<RoleProtectedRoute allow="admin" />}>
            <Route path="admin" element={<AdminDashboard />} />
            <Route
              path="users"
              element={
                <PageErrorBoundary>
                  <UserManagement />
                </PageErrorBoundary>
              }
            />
            <Route path="roles" element={<RoleManagement />} />
            <Route path="logs" element={<AuditLogs />} />
            <Route path="workflow" element={<WorkflowPage />} />
            <Route path="master-data" element={<MasterDataManagement />} />
            <Route
              path="master-data/banks"
              element={
                <PageErrorBoundary>
                  <BankBranchManagement />
                </PageErrorBoundary>
              }
            />
            <Route
              path="master-data/bank-abbr"
              element={
                <PageErrorBoundary>
                  <BankAbbrManagement />
                </PageErrorBoundary>
              }
            />
          </Route>

          <Route element={<RoleProtectedRoute allow="first_pension" />}>
            <Route path="cases" element={<PensionCaseList />} />
            <Route path="methodology2" element={<Methodology2 />} />
            <Route path="firstpensioncases" element={<FirstPensionCase />} />
            <Route path="archive" element={<ArchiveFirstPension />} />
          </Route>

          <Route element={<RoleProtectedRoute allow="family_pension" />}>
            <Route path="familypensioncases" element={<FamilyPensionCase />} />
            <Route path="familypension" element={<FamilyPension />} />
            <Route path="methodology1" element={<Methodology1 />} />
          </Route>
        </Route>

        <Route path="/pension-report/:id" element={<PensionCalculationPrint />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;
