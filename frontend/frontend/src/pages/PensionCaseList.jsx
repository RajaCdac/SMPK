import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import API from "../services/Api";
import "../styles/PensionCaseList.css";

export default function PensionCaseList() {

  const [cases, setCases] = useState([]);

  useEffect(() => {

    API.get("first-pension/cases/")
      .then((res) => {
        setCases(res.data);
      })
      .catch((err) => console.error(err));

  }, []);

  return (

    <div className="case-page">
      <div className="case-header">

        <div>

          <h1>Pension Cases</h1>

          <p>
            View and manage all processed pension cases
          </p>

        </div>

        <div className="case-count">

          <span>Total Cases</span>

          <h2>{cases.length}</h2>

        </div>

      </div>

      <div className="case-table-container">

        <table className="case-table">

          <thead>

            <tr>

              <th>Emp Code</th>

              <th>Name</th>

              <th>Designation</th>

              <th>Retirement Date</th>

              <th>Status</th>

              <th>Last Basic</th>

              <th>Action</th>

            </tr>

          </thead>

          <tbody>

            {cases.length > 0 ? (

              cases.map((c) => (

                <tr key={c.id}>

                  <td>{c.emp_code}</td>

                  <td>{c.name}</td>

                  <td>{c.designation}</td>

                  <td>{c.retirement_date}</td>

                  <td>

                    <span className="status-badge">
                      {c.status}
                    </span>

                  </td>

                  <td>
                    ₹ {c.last_basic}
                  </td>

                  <td>

                    <Link
                      to={`/pension-report/${c.id}`}
                      className="details-btn"
                    >
                      View Details
                    </Link>

                  </td>

                </tr>

              ))

            ) : (

              <tr>

                <td
                  colSpan="7"
                  className="no-data"
                >
                  No Pension Cases Found
                </td>

              </tr>

            )}

          </tbody>

        </table>

      </div>

    </div>

  );

}