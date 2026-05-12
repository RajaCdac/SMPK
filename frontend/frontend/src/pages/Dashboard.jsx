import "../styles/Dashboard.css";
import { useEffect, useState } from "react";
import API from "../services/Api";

export default function Dashboard() {
  const [data, setData] = useState({
    total_employees: 0,
    retirement_count: 0,
    retirement_list: [],
  });

  const [selectedEmp, setSelectedEmp] = useState(null);
    const [formData, setFormData] = useState({
    noPayDays: "",
    diesNonDays: "",
    commutationPercent: "",
    commutationReason: "",
  });

  const handleProcess = (emp) => {
    setSelectedEmp(emp);
    // temporary
    alert(`Processing ${emp.emp_code}`);
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

      //  alert(
      //    `Pension: ${res.data.pension_amount}
      //     Commutation: ${res.data.commutation_amount}
      //     Gratuity: ${res.data.gratuity_amount}`
      //  );

       setSelectedEmp(null);
     } catch (err) {
       console.error(err);
       alert("Error while saving");
     }
  };

  useEffect(() => {
    API.get("dashboard/")
      .then((res) => {
        console.log(res.data);   // 🔍 debug
        setData(res.data);
      })
      .catch((err) => console.error(err));
  }, []);

  return (
    <div>

      {/* 🔹 CARDS */}
      <div style={{ display: "flex", gap: "20px" }}>
        
        <div style={cardStyle}>
          <h3>Total Employees</h3>
          <h2>{data.total_employees}</h2>
        </div>

        <div style={cardStyle}>
          <h3>This Month Retirements</h3>
          <h2>{data.retirement_count}</h2>
        </div>

      </div>

      {/* 🔹 TABLE */}
      <h3 style={{ marginTop: "20px" }}>
        Employees Retiring This Month
      </h3>

      <table border="1" width="100%">
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
          {data.retirement_list.map((e, i) => (
            <tr key={i}>
              <td>{e.emp_code}</td>
              <td>{e.name}</td>
              <td>{e.class}</td>
              <td>{e.joining_date}</td>
              <td>{e.retirement_date}</td>
              <td>{e.birth_date}</td>
              <td>{e.age_on_appointment?.years !== null ? `${e.age_on_appointment.years} yrs` : 'N/A'}{e.age_on_appointment?.months !== null ? ` ${e.age_on_appointment.months} mn` : ''}{e.age_on_appointment?.days !== null ? ` ${e.age_on_appointment.days} days` : ''}  </td>
              <td>{e.age_on_retirement?.years !== null ? `${e.age_on_retirement.years} yrs` : 'N/A'}{e.age_on_retirement?.months !== null ? ` ${e.age_on_retirement.months} mn` : ''}{e.age_on_retirement?.days !== null ? ` ${e.age_on_retirement.days} days` : ''}  </td>
              <td>{e.designation}</td>
              <td>{e.scale}</td>
              <td>{e.last_basic}</td>
              <td><button className="process-btn" onClick={() => handleProcess(e)}> Process</button></td>
            </tr>
          ))}
        </tbody>
      </table>

      {selectedEmp && (

        <div className="modal-overlay">

          <div className="modal-box">

            <h2>Pension Processing</h2>

            <div className="modal-section">

              <h3>Employee Information</h3>

              <p><b>Emp Code:</b> {selectedEmp.emp_code}</p>

              <p><b>Name:</b> {selectedEmp.name}</p>

              <p><b>Class:</b> {selectedEmp.class}</p>

              <p><b>DOB:</b> {selectedEmp.birth_date}</p>

              <p><b>DOR:</b> {selectedEmp.retirement_date}</p>

              <p><b>Basic:</b> {selectedEmp.last_basic}</p>

              <p><b>Scale:</b> {selectedEmp.scale}</p>

            </div>

            <div className="modal-section">

              <h3>Pension Inputs</h3>

              <input type="number" placeholder="No Pay Days" value={formData.noPayDays} onChange={(e) =>
                setFormData({
                  ...formData,
                  noPayDays: e.target.value,
                })
              } />

              <input type="number" placeholder="Dies Non Days" value={formData.diesNonDays} onChange={(e) =>
                setFormData({
                  ...formData,
                  diesNonDays: e.target.value,
                })
              } />

              <input type="number" placeholder="Commutation %" value={formData.commutationPercent} onChange={(e) =>
                setFormData({
                  ...formData,
                  commutationPercent: e.target.value,
                })
              } />

              <input type="text" placeholder="Commutation Reason" value={formData.commutationReason} onChange={(e) =>
                  setFormData({
                    ...formData,
                    commutationReason: e.target.value,
                  })
                }
              />

            </div>

            <div className="modal-buttons">

              <button onClick={handleSubmit}> Submit</button>

              <button onClick={() => setSelectedEmp(null)}>
                Close
              </button>

            </div>

          </div>

        </div>

      )}

    </div>
    
  );
  
}

const cardStyle = {
  background: "#1976d2",
  color: "white",
  padding: "20px",
  borderRadius: "10px",
  width: "220px",
  textAlign: "center",
};

