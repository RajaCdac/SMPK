import "../styles/Dashboard.css";
import { useEffect, useState } from "react";
import API from "../services/Api";

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

  const [formData, setFormData] = useState({
    noPayDays: "",
    diesNonDays: "",
    commutationPercent: "",
    commutationReason: "",
  });

  useEffect(() => {
    API.get("dashboard/")
      .then((res) => {
        console.log(res.data);
        setData(res.data);
        setFilteredData(res.data.retirement_list);
      })
      .catch((err) => console.error(err));
  }, []);

  const handleSearch = () => {

    let filtered = data.retirement_list;

    filtered = filtered.filter((emp) => {

      if (!emp.retirement_date) return false;

      let month = "";
      let year = "";

      const parts = emp.retirement_date.split("-");
      if (parts[0].length === 4) {
        year = parts[0];
        month = parts[1];
      }
      else {
        month = parts[1];
        year = parts[2];
      }

      const monthMatch =
        searchMonth === "" ||
        Number(month) === Number(searchMonth);

      const yearMatch =
        searchYear === "" ||
        Number(year) === Number(searchYear);

      return monthMatch && yearMatch;

    });

    setFilteredData(filtered);

  };

  const handleReset = () => {
    setSearchMonth("");
    setSearchYear("");
    setFilteredData(data.retirement_list);
  };

  const handleProcess = (emp) => {
    setSelectedEmp(emp);
  };
const handleSubmit = async () => {

    try {

      const payload = {
        ...selectedEmp,
        no_pay_days: formData.noPayDays || 0,
        dies_non_days: formData.diesNonDays || 0,
        commutation_percent: formData.commutationPercent || 0,
        commutation_reason: formData.commutationReason || "",
      };

      console.log(payload);

      const res = await API.post(
        "first-pension/process/",
        payload
      );

      console.log(res.data);

      window.open(
        `/pension-report/${res.data.case_id}`,
        "_blank"
      );

      setSelectedEmp(null);

    } catch (err) {

      console.error(err);

      alert("Error while saving");

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

    <div className="modal-box">

      <div className="modal-header">

        <h2>
          Pension Processing
        </h2>

      </div>

      <div className="modal-body">

        <div className="info-grid">

          <div className="info-card">
            <span>Employee Code</span>
            <h4>{selectedEmp.emp_code}</h4>
          </div>

          <div className="info-card">
            <span>Employee Name</span>
            <h4>{selectedEmp.name}</h4>
          </div>

          <div className="info-card">
            <span>Class</span>
            <h4>{selectedEmp.class}</h4>
          </div>

          <div className="info-card">
            <span>Date of Birth</span>
            <h4>{selectedEmp.birth_date}</h4>
          </div>

          <div className="info-card">
            <span>Retirement Date</span>
            <h4>{selectedEmp.retirement_date}</h4>
          </div>

          <div className="info-card">
            <span>Last Basic</span>
            <h4>₹ {selectedEmp.last_basic}</h4>
          </div>

        </div>

        <div className="form-section">

          <h3>
            Pension Inputs
          </h3>

          <div className="form-grid">

            <input
              type="number"
              placeholder="No Pay Days"
              value={formData.noPayDays}
              style={{color:"black"}}
              onChange={(e) =>
                setFormData({
                  ...formData,
                  noPayDays: e.target.value,
                })
              }
            />

            <input
              type="number"
              placeholder="Dies Non Days"
              value={formData.diesNonDays}
              style={{color:"black"}}
              onChange={(e) =>
                setFormData({
                  ...formData,
                  diesNonDays: e.target.value,
                })
              }
            />

            <input
              type="number"
              placeholder="Commutation %"
              value={formData.commutationPercent}
              style={{color:"black"}}
              onChange={(e) =>
                setFormData({
                  ...formData,
                  commutationPercent: e.target.value,
                })
              }
            />

            <input
              type="text"
              placeholder="Commutation Reason"
              value={formData.commutationReason}
              style={{color:"black"}}
              onChange={(e) =>
                setFormData({
                  ...formData,
                  commutationReason: e.target.value,
                })
              }
            />

          </div>

          <div className="modal-buttons">

            <button
              className="submit-btn"
              onClick={handleSubmit}
            >
              Submit
            </button>

            <button
              className="close-btn"
              onClick={() =>
                setSelectedEmp(null)
              }
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