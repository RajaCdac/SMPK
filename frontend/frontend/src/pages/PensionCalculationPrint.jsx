
import React, { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import API from "../services/Api";
import "../styles/PensionPrint.css";

export default function PensionCalculationPrint() {

  const { id } = useParams();

  const [data, setData] = useState(null);

  useEffect(() => {

    API.get(`first-pension/report/${id}/`)
      .then((res) => {
        setData(res.data);
      })
      .catch((err) => console.error(err));

  }, [id]);

  const handlePrint = () => {
    window.print();
  };

  if (!data) {
    return <div>Loading...</div>;
  }

  return (
    <div className="print-page">

      <div className="no-print">
        <button onClick={handlePrint}>
          Print
        </button>
      </div>

      <div className="sheet">

        <div className="header">
          <h2>Kolkata Port Trust</h2>
          <h3>CALCULATION SHEET</h3>
        </div>

        <div className="row">
          <div>
            <b>Name :</b> {data.name}
          </div>

          <div>
            <b>Case No :</b> {data.case_no}
          </div>
        </div>

        <div className="row">
          <div>
            <b>Date of Appointment :</b>
            {data.joining_date}
          </div>

          <div>
            <b>Age on Appointment :</b>
            {data.age_on_appointment}
          </div>
        </div>

        <div className="row">
          <div>
            <b>Date of Retirement :</b>
            {data.retirement_date}
          </div>

          <div>
            <b>Age on Retirement :</b>
            {data.age_on_retirement}
          </div>
        </div>

        <div className="row">
          <div>
            <b>Date of Birth :</b>
            {data.birth_date}
          </div>

          <div>
            <b>Reason for Retirement :</b>
            Superannuation
          </div>
        </div>

        <div className="row">
          <div>
            <b>No Pay :</b>
            {data.no_pay_days}
          </div>

          <div>
            <b>Dies Non :</b>
            {data.dies_non_days}
          </div>
        </div>

        <hr />

        <div className="calc-section">

          <p>
            <b>Last Basic Pay :</b>
            Rs. {data.last_basic}
          </p>

          <p>
            <b>Pension :</b>
            50% of Pay = Rs. {data.pension_amount}
          </p>

          <p>
            <b>Commutation :</b>
            40% of Pension
          </p>

          <p>
            <b>Commutation Payable :</b>
            Rs. {data.commutation_amount}
          </p>

        </div>

        <div className="service-box">

          <p>
            <b>Total Service :</b>
            {data.total_service}
          </p>

          <p>
            <b>TCCS :</b>
            {data.tccs}
          </p>

          <p>
            <b>TQS :</b>
            {data.tqs}
          </p>

        </div>

        <hr />

        <div className="gratuity-section">

          <h3>GRATUITY CALCULATION</h3>

          <p>
            <b>Last Basic Pay :</b>
            Rs. {data.last_basic}
          </p>

          <p>
            <b>DA :</b>
            Rs. {data.da_amount}
          </p>

          <p>
            <b>Gratuity Amount :</b>
            Rs. {data.gratuity_amount}
          </p>

        </div>

        <div className="signature">
          <p>Prepared By</p>
          <p>Checked By</p>
          <p>Sanctioning Authority</p>
        </div>

      </div>

    </div>
  );
}
