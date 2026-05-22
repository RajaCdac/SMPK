import React, { useState } from "react";
import "bootstrap/dist/css/bootstrap.min.css";
import "bootstrap/dist/js/bootstrap.bundle.min.js";
import API from "../services/Api";
import EmployeeProcessTabs from "../components/EmployeeProcessTabs";

const SearchEmployee = () => {
  const [employeeId, setEmployeeId] = useState("");
  const [employee, setEmployee] = useState(null);
  const [message, setMessage] = useState("");

  const handleSearch = async (e) => {
    e.preventDefault();

    if (!employeeId) {
      setMessage("Please enter Employee ID");
      return;
    }

    try {
      const response = await API.get(`first-pension/employees/${employeeId}/`);
      console.log(response.data);
      setEmployee(response.data);
      setMessage("");
    } catch (error) {
      setEmployee(null);
      setMessage("Employee not found");
      console.error(error);
    }
  };

  return (
    <div className="container-fluid px-4 mt-4" style={{ maxWidth: "1520px" }}>
      <div className="card shadow">
        <div className="card-header bg-primary text-white">
          <h4 className="mb-0">Search Employee</h4>
        </div>

        <div className="card-body">
          <form onSubmit={handleSearch}>
            <div className="row align-items-end">
              <div className="col-md-8">
                <label className="form-label">Employee ID</label>

                <input
                  type="text"
                  className="form-control"
                  placeholder="Enter Employee ID"
                  value={employeeId}
                  onChange={(e) => setEmployeeId(e.target.value)}
                />
              </div>

              <div className="col-md-4">
                <button type="submit" className="btn btn-primary w-100">
                  Search
                </button>
              </div>
            </div>
          </form>

          {message && (
            <div className="alert alert-danger mt-3">
              {message}
            </div>
          )}

          {employee && (
            <div className="mt-4">
              <EmployeeProcessTabs employee={employee} idPrefix="first-pension" />
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default SearchEmployee;
