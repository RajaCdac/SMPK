import CommutationApplicationEntry from "./CommutationApplicationEntry";
import NoPayEntry from "./NoPayEntry";
import PensionProposalEntry from "./PensionProposalEntry";
import PensionAmountEntry from "./PensionAmountEntry";

function formatAge(age) {
  if (!age || age.years === null) return "N/A";
  let text = `${age.years} yrs`;
  if (age.months !== null) text += ` ${age.months} mn`;
  if (age.days !== null) text += ` ${age.days} days`;
  return text;
}

export default function EmployeeProcessTabs({ employee, idPrefix = "emp" }) {
  if (!employee) return null;

  const personalId = `${idPrefix}-personal`;
  const admId = `${idPrefix}-adm`;
  const noPayId = `${idPrefix}-nopay`;
  const proposalId = `${idPrefix}-proposal`;
  const amountId = `${idPrefix}-amount`;

  return (
    <div>
      <ul className="nav nav-tabs" role="tablist">
        <li className="nav-item" role="presentation">
          <button
            className="nav-link active"
            id={`${idPrefix}-personal-tab`}
            data-bs-toggle="tab"
            data-bs-target={`#${personalId}`}
            type="button"
            role="tab"
          >
            Basic Info
          </button>
        </li>
        <li className="nav-item" role="presentation">
          <button
            className="nav-link"
            id={`${idPrefix}-adm-tab`}
            data-bs-toggle="tab"
            data-bs-target={`#${admId}`}
            type="button"
            role="tab"
          >
            Commutation
          </button>
        </li>
        <li className="nav-item" role="presentation">
          <button
            className="nav-link"
            id={`${idPrefix}-nopay-tab`}
            data-bs-toggle="tab"
            data-bs-target={`#${noPayId}`}
            type="button"
            role="tab"
          >
            No-Pay Entry
          </button>
        </li>
        <li className="nav-item" role="presentation">
          <button
            className="nav-link"
            id={`${idPrefix}-proposal-tab`}
            data-bs-toggle="tab"
            data-bs-target={`#${proposalId}`}
            type="button"
            role="tab"
          >
            Pension Proposal
          </button>
        </li>
        <li className="nav-item" role="presentation">
          <button
            className="nav-link"
            id={`${idPrefix}-amount-tab`}
            data-bs-toggle="tab"
            data-bs-target={`#${amountId}`}
            type="button"
            role="tab"
          >
            Amount
          </button>
        </li>
      </ul>

      <div className="tab-content border border-top-0 p-3 bg-white">
        <div
          className="tab-pane fade show active"
          id={personalId}
          role="tabpanel"
        >
          <table className="table table-bordered mb-0">
            <tbody>
              <tr>
                <th>Employee ID</th>
                <td>{employee.emp_id}</td>
                <th>Name</th>
                <td>{employee.name}</td>
              </tr>
              <tr>
                <th>Date of Joining</th>
                <td>{employee.join_date}</td>
                <th>Expected Retirement Date</th>
                <td>{employee.expected_retirement_date}</td>
              </tr>
              <tr>
                <th>Date of Birth</th>
                <td>{employee.birth_date}</td>
                <th>Designation</th>
                <td>{employee.designation}</td>
              </tr>
              <tr>
                <th>Class</th>
                <td>{employee.class}</td>
                <th>Basic Pay</th>
                <td>
                  Rs.{employee.basic_amount} ({employee.scale})
                </td>
              </tr>
              <tr>
                <th>Age on Appointment</th>
                <td>{formatAge(employee.age_on_appointment)}</td>
                <th>Age on Retirement</th>
                <td>{formatAge(employee.age_on_retirement)}</td>
              </tr>
            </tbody>
          </table>
        </div>

        <div className="tab-pane fade" id={admId} role="tabpanel">
          <div className="card shadow border-0">
            <div className="card-header bg-primary text-white">
              <h5 className="mb-0">Commutation Application Entry</h5>
            </div>
            <div className="card-body">
              <CommutationApplicationEntry employee={employee} />
            </div>
          </div>
        </div>

        <div className="tab-pane fade" id={noPayId} role="tabpanel">
          <div className="card shadow border-0">
            <div className="card-header bg-primary text-white">
              <h5 className="mb-0">No-Pay Entry</h5>
            </div>
            <div className="card-body">
              <NoPayEntry employee={employee} />
            </div>
          </div>
        </div>

        <div className="tab-pane fade" id={proposalId} role="tabpanel">
          <div className="card shadow border-0 pension-proposal-card">
            <div className="card-body pension-proposal-card-body">
              <PensionProposalEntry employee={employee} />
            </div>
          </div>
        </div>

        <div className="tab-pane fade" id={amountId} role="tabpanel">
          <div className="card shadow border-0">
            <div className="card-header bg-primary text-white">
              <h5 className="mb-0">Pension, Commutation &amp; Gratuity</h5>
            </div>
            <div className="card-body">
              <PensionAmountEntry employee={employee} idPrefix={idPrefix} />
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
