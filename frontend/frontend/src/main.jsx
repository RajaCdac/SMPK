import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import './styles/responsive-forms.css'
import './styles/pension-report-print.css'
import './styles/PensionProposal.css'
import './styles/FirstPensionCase.css'
import './styles/EmployeeProcessTabs.css'
import './styles/process-modal.css'
import App from './App.jsx'
import 'bootstrap/dist/css/bootstrap.min.css'
import 'bootstrap/dist/js/bootstrap.bundle.min.js'
import 'datatables.net-bs5/css/dataTables.bootstrap5.min.css'
import 'datatables.net-responsive-bs5/css/responsive.bootstrap5.min.css'

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <App />
  </StrictMode>,
)
