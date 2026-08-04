import { Link } from "react-router-dom";
import "../styles/UserManagement.css";
import "../styles/MasterData.css";

export default function MasterDataManagement() {
  return (
    <div className="master-data-page">
      <h1>Master Data Management</h1>
      <p className="text-muted mb-4">
        Maintain reference data used across pension processing. Changes are
        saved in the local database and appear in pension forms.
      </p>

      <div className="admin-quick-links">
        <Link to="/dashboard/master-data/banks" className="admin-quick-card">
          <h3>Bank Branches</h3>
          <p>
            Add, edit, or delete branch-level banks (Oracle FI_PM_MH_BANK) —
            bank code, name, address, RBI code, etc.
          </p>
        </Link>
        <Link
          to="/dashboard/master-data/bank-abbr"
          className="admin-quick-card"
        >
          <h3>Bank Abbreviations</h3>
          <p>
            Manage bank type codes (Oracle FI_PM_MH_BANKABBR) — e.g. SBI, UCO
            short names.
          </p>
        </Link>
      </div>
    </div>
  );
}
