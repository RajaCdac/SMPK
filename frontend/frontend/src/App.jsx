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
import Methodology2OldAge from "./pages/Methodology2OldAge";
import FirstPensionCase from "./pages/FirstPensionCase";
import FamilyPensionCase from "./pages/FamilyPensionCase";
import FamilyPension from "./pages/FamilyPension";
import FamilyPensionArrear from "./pages/FamilyPensionArrear";
import FamilyPensionCpiUpgrade from "./pages/FamilyPensionCpiUpgrade";
import FamilyPensionRecoveryDeduction from "./pages/FamilyPensionRecoveryDeduction";
import NomineeEntry from "./pages/NomineeEntry";
import DieInHarness from "./pages/DieInHarness";
import EsrPersonal from "./pages/EsrPersonal";
import EsrAdmin from "./pages/EsrAdmin";
import EsrFinance from "./pages/EsrFinance";
import EsrSalary from "./pages/EsrSalary";
import FamilyPensionReport from "./pages/FamilyPensionReport";
import FirstPensionReport from "./pages/FirstPensionReport";
import LicClaimGeneration from "./pages/LicClaimGeneration";
import FamilyLicClaimGeneration from "./pages/FamilyLicClaimGeneration";
import ArchiveFirstPension from "./pages/ArchiveFirstPension";
import MasterDataManagement from "./pages/MasterDataManagement";
import BankBranchManagement from "./pages/BankBranchManagement";
import BankAbbrManagement from "./pages/BankAbbrManagement";
import FinanceTransfer from "./pages/FinanceTransfer";
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
              path="oracle-transfer"
              element={
                <PageErrorBoundary>
                  <FinanceTransfer />
                </PageErrorBoundary>
              }
            />
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

          <Route
            element={
              <RoleProtectedRoute
                allow={["FIRST_PENSION_USER", "PENSION_USER", "FAMILY_PENSION_USER"]}
              />
            }
          >
            <Route path="esr/personal" element={<EsrPersonal />} />
            <Route path="esr/admin" element={<EsrAdmin />} />
            <Route path="esr/finance" element={<EsrFinance />} />
            <Route path="esr/salary" element={<EsrSalary />} />
            <Route path="nominee" element={<NomineeEntry />} />
          </Route>

          <Route element={<RoleProtectedRoute allow="first_pension" />}>
            <Route path="cases" element={<PensionCaseList />} />
            <Route path="methodology2" element={<Methodology2 />} />
            <Route
              path="methodology2-oldage-arrear"
              element={<Methodology2OldAge />}
            />
            <Route
              path="firstpensioncases"
              element={<Navigate to="/dashboard/firstpension/esr-check" replace />}
            />
            <Route
              path="firstpension/esr-check"
              element={<FirstPensionCase step="esr" />}
            />
            <Route
              path="firstpension/nopay"
              element={<FirstPensionCase step="nopay" />}
            />
            <Route
              path="firstpension/commutation"
              element={<FirstPensionCase step="commutation" />}
            />
            <Route
              path="firstpension/proposal"
              element={<FirstPensionCase step="proposal" />}
            />
            <Route
              path="firstpension/amount"
              element={<FirstPensionCase step="amount" />}
            />
            <Route
              path="firstpension/bill"
              element={<FirstPensionCase step="bill" />}
            />
            <Route
              path="firstpension/reports"
              element={<FirstPensionCase step="reports" />}
            />
            <Route
              path="fp-reports"
              element={<Navigate to="/dashboard/fp-reports/sanction" replace />}
            />
            <Route
              path="fp-reports/lic"
              element={<FirstPensionReport section="lic" />}
            />
            <Route
              path="fp-reports/sanction"
              element={<FirstPensionReport section="sanction" />}
            />
            <Route
              path="fp-reports/firstpensionadvice"
              element={<FirstPensionReport section="firstpensionadvice" />}
            />
            <Route
              path="fp-reports/combill"
              element={<FirstPensionReport section="combill" />}
            />
            <Route
              path="fp-reports/sepcombill"
              element={<FirstPensionReport section="sepcombill" />}
            />
            <Route
              path="fp-reports/billabstract"
              element={<FirstPensionReport section="billabstract" />}
            />
            <Route
              path="fp-reports/journalsummary"
              element={<FirstPensionReport section="journalsummary" />}
            />
            <Route
              path="lic-claim-generation"
              element={<LicClaimGeneration />}
            />
            <Route path="archive" element={<ArchiveFirstPension />} />
          </Route>

          <Route element={<RoleProtectedRoute allow="family_pension" />}>
            <Route path="familypensioncases" element={<FamilyPensionCase />} />
            <Route path="familypension" element={<FamilyPension />} />
            <Route
              path="familypension/recovery-deduction"
              element={<FamilyPensionRecoveryDeduction />}
            />
            <Route
              path="familypension/proposal"
              element={<Navigate to="/dashboard/familypensioncases" replace />}
            />
            <Route
              path="familypension/arrear"
              element={<Navigate to="/dashboard/reports/arrear" replace />}
            />
            <Route
              path="die-in-harness"
              element={<DieInHarness step="nopay" />}
            />
            <Route
              path="die-in-harness/proposal"
              element={<DieInHarness step="proposal" />}
            />
            <Route path="die-in-harness/claim" element={<FamilyPension />} />
            <Route
              path="die-in-harness/proposal-report"
              element={
                <Navigate to="/dashboard/reports/fp-dih-application" replace />
              }
            />
            <Route path="methodology1" element={<Methodology1 />} />
            <Route
              path="reports/first-pension-generation"
              element={
                <FamilyPensionReport section="first-pension-generation" />
              }
            />
            <Route
              path="reports/fp-dih-application"
              element={<FamilyPensionReport section="fp-dih-application" />}
            />
            <Route
              path="reports/bill-generation"
              element={<FamilyPensionReport section="bill-generation" />}
            />
            <Route
              path="reports/bill-abstract"
              element={<FamilyPensionReport section="bill-abstract" />}
            />
            <Route
              path="reports/journal-voucher"
              element={<FamilyPensionReport section="journal-voucher" />}
            />
            <Route
              path="reports/first-fp-bill-lic"
              element={<FamilyPensionReport section="first-fp-bill-lic" />}
            />
            <Route path="reports/arrear" element={<FamilyPensionArrear />} />
            <Route
              path="reports/cpi-upgrade"
              element={<FamilyPensionCpiUpgrade />}
            />
            <Route
              path="family-lic-claim-generation"
              element={<FamilyLicClaimGeneration />}
            />
          </Route>
        </Route>

        <Route path="/pension-report/:id" element={<PensionCalculationPrint />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;
