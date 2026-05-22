import "../styles/Dashboard.css";
import "bootstrap/dist/css/bootstrap.min.css";
import "bootstrap/dist/js/bootstrap.bundle.min.js";
import { useEffect, useState } from "react";
import API from "../services/Api";
import EmployeeProcessTabs from "../components/EmployeeProcessTabs";

export default function Dashboard() {

  const [data, setData] = useState({
    total_employees: 0,
    retirement_count: 0,
    retirement_list: [],
  });

  const [filteredData, setFilteredData] = useState([]);

  const [searchMonth, setSearchMonth] = useState("");
  const [searchYear, setSearchYear] = useState("");

  const [selectedEmp, setSelectedEmp] = useState(null);
  const [employeeDetail, setEmployeeDetail] = useState(null);
  const [loadingEmployee, setLoadingEmployee] = useState(false);

  useEffect(() => {
    API.get("dashboard/")
      .then((res) => {
        console.log(res.data);
        setData(res.data);
        setFilteredData(res.data.retirement_list);
      })
      .catch((err) => console.error(err));
  }, []);

  const handleSearch = async () => {

  try {

    const res = await API.get(
      `dashboard/?month=${searchMonth}&year=${searchYear}`
    );

    setData(res.data);

    setFilteredData(res.data.retirement_list);

  } catch (err) {

    console.error(err);

  }

};

  
  const handleReset = () => {
    setSearchMonth("");
    setSearchYear("");
    setFilteredData(data.retirement_list);
  };

  const closeModal = () => {
    setSelectedEmp(null);
    setEmployeeDetail(null);
  };

  const handleProcess = async (emp) => {
    setSelectedEmp(emp);
    setEmployeeDetail(null);
    setLoadingEmployee(true);

    try {
      const res = await API.get(`first-pension/employees/${emp.emp_code}/`);
      setEmployeeDetail(res.data);
    } catch (err) {
      console.error(err);
      alert("Failed to load employee details");
      closeModal();
    } finally {
      setLoadingEmployee(false);
    }
  };

  return (

    <div className="dashboard-page"><div className="dashboard-header">

        <div>

          <h1 className="dashboard-heading" style={{color: "black"}}>
            Pension Dashboard
          </h1>
        </div>

      </div><div className="cards-container">

        <div className="dashboard-card blue-card">

          <div className="card-icon">
            👨‍💼
          </div>

          <div>

            <h3>Total Employees</h3>

            <h2>
              {data.total_employees}
            </h2>

          </div>

        </div>

        <div className="dashboard-card green-card">

          <div className="card-icon">
            📋
          </div>

          <div>

            <h3>
              This Month Retirements
            </h3>

            <h2>
              {data.retirement_count}
            </h2>

          </div>

        </div>

      </div><div className="search-container">

        <h3 className="search-title" style={{color:"black"}}>
          Search Retirement Employees
        </h3>

        <div className="search-box">

          <select
            value={searchMonth}
            style={{color:"black"}}
            onChange={(e) =>
              setSearchMonth(e.target.value) 
            }
          >

            <option value="">
              Select Month
            </option>

            <option value="1">January</option>
            <option value="2">February</option>
            <option value="3">March</option>
            <option value="4">April</option>
            <option value="5">May</option>
            <option value="6">June</option>
            <option value="7">July</option>
            <option value="8">August</option>
            <option value="9">September</option>
            <option value="10">October</option>
            <option value="11">November</option>
            <option value="12">December</option>

          </select>

          <input
            type="number"
            placeholder="Enter Year"
            value={searchYear}
            style={{color:"black"}}
            onChange={(e) =>
              setSearchYear(e.target.value)
            }
          />

          <button
            className="search-btn"
            onClick={handleSearch}
          >
            Search
          </button>

          <button
            className="reset-btn"
            onClick={handleReset}
          >
            Reset
          </button>

        </div>

      </div><div className="table-container" style={{color:"black"}}>

        <h3 className="table-title">
          Employees Retiring This Month
        </h3>

        <table className="employee-table">

          <thead>

            <tr>

              <th>Emp Code</th>
              <th>Name</th>
              <th>Class</th>
              <th>Joining Date</th>
              <th>Retirement Date</th>
              <th>Birth Date</th>
              <th>Age on Appointment</th>
              <th>Age on Retirement</th>
              <th>Designation</th>
              <th>Scale</th>
              <th>Last Basic</th>
              <th>Action</th>

            </tr>

          </thead>

          <tbody>

            {filteredData.length > 0 ? (

              filteredData.map((e, i) => (

                <tr key={i}>

                  <td>{e.emp_code}</td>

                  <td>{e.name}</td>

                  <td>{e.class}</td>

                  <td>{e.joining_date}</td>

                  <td>{e.retirement_date}</td>

                  <td>{e.birth_date}</td>

                  <td>

                    {e.age_on_appointment?.years !== null
                      ? `${e.age_on_appointment.years} yrs`
                      : "N/A"}

                    {e.age_on_appointment?.months !== null
                      ? ` ${e.age_on_appointment.months} mn`
                      : ""}

                    {e.age_on_appointment?.days !== null
                      ? ` ${e.age_on_appointment.days} days`
                      : ""}

                  </td>

                  <td>

                    {e.age_on_retirement?.years !== null
                      ? `${e.age_on_retirement.years} yrs`
                      : "N/A"}

                    {e.age_on_retirement?.months !== null
                      ? ` ${e.age_on_retirement.months} mn`
                      : ""}

                    {e.age_on_retirement?.days !== null
                      ? ` ${e.age_on_retirement.days} days`
                      : ""}

                  </td>

                  <td>{e.designation}</td>

                  <td>{e.scale}</td>

                  <td>
                    ₹ {e.last_basic}
                  </td>

                  <td>

                    <button
                      className="process-btn"
                      onClick={() =>
                        handleProcess(e)
                      }
                    >
                      Process
                    </button>

                  </td>

                </tr>

              ))

            ) : (

              <tr>

                <td
                  colSpan="12"
                  style={{
                    textAlign: "center",
                    padding: "20px",
                    fontWeight: "bold",
                    color: "black",
                  }}
                >
                  No Employee Found
                </td>

              </tr>

            )}

          </tbody>

        </table>

      </div>{selectedEmp && (

  <div className="modal-overlay">

    <div className="modal-box modal-box-wide">

      <div className="modal-header">

        <h2>
          Pension Processing — {selectedEmp.name}
        </h2>

      </div>

      <div className="modal-body">

        <div className="form-section">
          {loadingEmployee ? (
            <p style={{ color: "black", textAlign: "center" }}>
              Loading employee details...
            </p>
          ) : employeeDetail ? (
            <EmployeeProcessTabs
              employee={employeeDetail}
              idPrefix="dashboard-emp"
            />
          ) : (
            <p style={{ color: "black", textAlign: "center" }}>
              Unable to load employee details.
            </p>
          )}

          <div className="modal-buttons">
            <button
              className="close-btn"
              onClick={closeModal}
            >
              Close
            </button>
          </div>

        </div>

      </div>

    </div>

  </div>

)}

    </div>

  );

}
