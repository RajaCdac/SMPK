import goiLogo from "../assets/images/goi_logo.png";
import smpLogo from "../assets/images/SMP_Logo.png";

export default function PensionCalculationSheet({ data }) {
  if (!data) return null;

  return (
    <div className="sheet">
      <div className="top-header">
        <div className="logo-box">
          <img src={goiLogo} alt="GOI Logo" className="top-logo" />
        </div>
        <div className="header-text">
          <h1>Syama Prasad Mookerjee Port</h1>
          <h2>Kolkata Port Trust</h2>
          <h3>PENSION CALCULATION SHEET</h3>
        </div>
        <div className="logo-box">
          <img src={smpLogo} alt="SMP Logo" className="top-logo" />
        </div>
      </div>

      <div className="section-title">Employee Information</div>
      <div className="details-grid">
        <div className="detail-card">
          <span>Name</span>
          <h4>{data.name}</h4>
        </div>
        <div className="detail-card">
          <span>Case No</span>
          <h4>{data.case_no}</h4>
        </div>
        <div className="detail-card">
          <span>Date of Appointment</span>
          <h4>{data.joining_date}</h4>
        </div>
        <div className="detail-card">
          <span>Age on Appointment</span>
          <h4>{data.age_on_appointment}</h4>
        </div>
        <div className="detail-card">
          <span>Date of Retirement</span>
          <h4>{data.retirement_date}</h4>
        </div>
        <div className="detail-card">
          <span>Age on Retirement</span>
          <h4>{data.age_on_retirement}</h4>
        </div>
        <div className="detail-card">
          <span>Date of Birth</span>
          <h4>{data.birth_date}</h4>
        </div>
        <div className="detail-card">
          <span>Retirement Reason</span>
          <h4>Superannuation</h4>
        </div>
        <div className="detail-card">
          <span>No Pay Days</span>
          <h4>{data.no_pay_days}</h4>
        </div>
        <div className="detail-card">
          <span>Dies Non Days</span>
          <h4>{data.dies_non_days}</h4>
        </div>
      </div>

      <div className="section-title">Pension Calculation</div>
      <table className="calc-table">
        <tbody>
          <tr>
            <td>Last Basic Pay</td>
            <td>₹ {data.last_basic}</td>
          </tr>
          <tr>
            <td>Pension Amount</td>
            <td>₹ {data.pension_amount}</td>
          </tr>
          <tr>
            <td>Commutation Percentage</td>
            <td>40%</td>
          </tr>
          <tr>
            <td>Commutation Payable</td>
            <td>₹ {data.commutation_amount}</td>
          </tr>
        </tbody>
      </table>

      <div className="section-title">Service Details</div>
      <table className="calc-table">
        <tbody>
          <tr>
            <td>Total Service</td>
            <td>{data.total_service}</td>
          </tr>
          <tr>
            <td>TCCS</td>
            <td>{data.tccs}</td>
          </tr>
          <tr>
            <td>TQS</td>
            <td>{data.tqs}</td>
          </tr>
        </tbody>
      </table>

      <div className="section-title">Gratuity Calculation</div>
      <table className="calc-table">
        <tbody>
          <tr>
            <td>Last Basic Pay</td>
            <td>₹ {data.last_basic}</td>
          </tr>
          <tr>
            <td>DA Amount</td>
            <td>₹ {data.da_amount}</td>
          </tr>
          <tr>
            <td>Gratuity Amount</td>
            <td>₹ {data.gratuity_amount}</td>
          </tr>
        </tbody>
      </table>

      <div className="signature-section">
        <div className="sign-box">
          <div className="sign-line" />
          <p>Prepared By</p>
        </div>
        <div className="sign-box">
          <div className="sign-line" />
          <p>Checked By</p>
        </div>
        <div className="sign-box">
          <div className="sign-line" />
          <p>Sanctioning Authority</p>
        </div>
      </div>
    </div>
  );
}
