import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import API from "../services/Api";

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
    <div>

      <h2>Pension Cases</h2>

      <table border="1" width="100%">

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

          {cases.map((c) => (

            <tr key={c.id}>

              <td>{c.emp_code}</td>
              <td>{c.name}</td>
              <td>{c.designation}</td>
              <td>{c.retirement_date}</td>
              <td>{c.status}</td>
              <td>{c.last_basic}</td>

              <td>
                <Link to={`/pension-report/${c.id}`}>
                  Details
                </Link>
              </td>

            </tr>
          ))}

        </tbody>

      </table>

    </div>
  );
}