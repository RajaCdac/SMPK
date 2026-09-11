import "../styles/LicClaimNormalPrint.css";

function money(value) {
  if (value == null || value === "") return "";
  const n = Number(value);
  if (Number.isNaN(n)) return String(value);
  return n.toLocaleString("en-IN", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
}

function Field({ no, label, value, wide }) {
  return (
    <div
      className={`lic-claim-print__field${wide ? " lic-claim-print__field--wide" : ""}`}
    >
      <span className="lic-claim-print__no">{no}.</span>
      <span className="lic-claim-print__lbl">{label}</span>
      <span className="lic-claim-print__colon">:</span>
      <span className="lic-claim-print__val">{value ?? ""}</span>
    </div>
  );
}

/**
 * Oracle FI_PN_LIC_NORMAL_PEN_DTLS — LIC Claim Form-Normal
 */
export default function LicClaimNormalPrint({ report }) {
  if (!report) return null;

  const daPct =
    report.da_pct != null && report.da_pct !== ""
      ? Number(report.da_pct).toFixed(2)
      : "";

  return (
    <div className="lic-claim-print" id="lic-claim-normal-print-root">
      <div className="lic-claim-print__page">
        <div className="lic-claim-print__head">
          <div className="lic-claim-print__scheme">{report.org_scheme}</div>
          <div className="lic-claim-print__policy">
            MASTER POLICY NO. {report.master_policy_no}
          </div>
          <div className="lic-claim-print__sub">
            {report.subtitle} {report.installment_label}{" "}
            <strong>{report.payable_from || "____________"}</strong>
          </div>
          <div className="lic-claim-print__dock">{report.dock_system}</div>
        </div>

        <div className="lic-claim-print__fields">
          <Field no={1} label="LIC Sr. No." value={report.lic_sl_no} />
          <Field no={2} label="Pension Roll No." value={report.pen_roll_no} />
          <Field no={3} label="Aadhar No." value={report.aadhar_no || ""} />
          <Field no={4} label="Name of the Employee" value={report.emp_name} />
          <Field no={5} label="Sex" value={report.gender} />
          <Field no={6} label="Office Code" value={report.office_code} />
          <Field no={7} label="Salary Roll No." value={report.emp_cd} />
          <Field
            no={8}
            label="Class of Employee"
            value={report.emp_class_roman || report.emp_class}
          />
          <Field no={9} label="Date of Birth" value={report.birth_dt} />
          <Field no={10} label="Date of Retirement" value={report.retirement_dt} />
          <Field
            no={11}
            label="Age(Last Birthday on DOR)"
            value={
              report.age_last_birthday != null ? report.age_last_birthday : ""
            }
          />

          <div className="lic-claim-print__comm">
            <div className="lic-claim-print__comm-title">12. Commutation :</div>
            <div className="lic-claim-print__comm-row">
              <span>Pension amount commuted per month</span>
              <span>:</span>
              <span>{money(report.commuted_portion)}</span>
            </div>
            <div className="lic-claim-print__comm-row">
              <span>Commuted value of Pension</span>
              <span>:</span>
              <span>{money(report.commutation_value)}</span>
            </div>
          </div>

          <div className="lic-claim-print__item13">
            <div className="lic-claim-print__comm-title">
              13. Initial monthly pension after commutation :
            </div>
            <div className="lic-claim-print__pension-box">
              <div className="lic-claim-print__pension-row">
                <span>Basic Pension:</span>
                <span>{money(report.basic_pension)}</span>
              </div>
              <div className="lic-claim-print__pension-row">
                <span>Dearness Pension(50%):</span>
                <span>{money(report.dearness_pension)}</span>
              </div>
              <div className="lic-claim-print__pension-row">
                <span>Initial DA({daPct}):</span>
                <span>{money(report.initial_da)}</span>
              </div>
              <div className="lic-claim-print__pension-row lic-claim-print__pension-row--total">
                <span />
                <span>{money(report.initial_monthly_pension)}</span>
              </div>
            </div>
          </div>

          <Field
            no={14}
            label="Due date of 1st monthly Pension"
            value={report.due_date_first_pension}
          />
          <Field
            no={15}
            label="Initial Purchase price(to be filled by the LIC)"
            value={report.purchase_price || ""}
          />
          <div className="lic-claim-print__field lic-claim-print__field--wide">
            <span className="lic-claim-print__no">16.</span>
            <span className="lic-claim-print__lbl">
              Rate of Income Tax Deduction up to
            </span>
            <span className="lic-claim-print__colon">:</span>
            <span className="lic-claim-print__val lic-claim-print__val--note">
              {report.income_tax_note ||
                "Tax to be paid by the Annuitant Directly."}
            </span>
          </div>
          <Field
            no={17}
            label="Residential address of the Annuitant"
            value={report.address}
            wide
          />

          <div className="lic-claim-print__bank">
            <div className="lic-claim-print__comm-title">
              18. Particulars of the Annuitant Bank Account :
            </div>
            <div className="lic-claim-print__comm-row">
              <span>a) Bank Account No</span>
              <span>-</span>
              <span>{report.account_no}</span>
            </div>
            <div className="lic-claim-print__pan">
              PAN No &nbsp;-&nbsp; {report.pan_no || ""}
            </div>
            <div className="lic-claim-print__comm-row">
              <span>b) Name of the Bank and Branch</span>
              <span>-</span>
              <span>{report.bank_name_branch}</span>
            </div>
            <div className="lic-claim-print__comm-row">
              <span>c) Address of the Bank</span>
              <span>-</span>
              <span>{report.bank_address}</span>
            </div>
          </div>

          <Field no={19} label="Remarks, if any" value={report.remarks || ""} wide />
        </div>

        <div className="lic-claim-print__note">
          NOTE : TWO SPECIMAN SIGNATURE OF THE ANNUITANT ARE GIVEN BELOW
        </div>
        <div className="lic-claim-print__sign-boxes">
          <div className="lic-claim-print__sign-box" />
          <div className="lic-claim-print__sign-box" />
        </div>

        <div className="lic-claim-print__footer">
          <div>
            <div>DATE : _______________</div>
          </div>
          <div className="lic-claim-print__trustee">
            <div>(Office Seal)</div>
            <div>For self and Co-Trustees of Superannuation Fund</div>
            <div className="lic-claim-print__sig-line">
              (Signature of the Trustees)
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
