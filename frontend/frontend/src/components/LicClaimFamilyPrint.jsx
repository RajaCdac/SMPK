import "../styles/LicClaimNormalPrint.css";
import "../styles/LicClaimFamilyPrint.css";

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

function PensionTable({ title, block, daPct }) {
  const drLabel =
    daPct != null && daPct !== ""
      ? `Initial D.R.(${Number(daPct).toFixed(2)})`
      : "Initial D.R.";
  return (
    <div className="lic-claim-family__block">
      <div className="lic-claim-family__block-title">{title}</div>
      <table className="lic-claim-family__table">
        <thead>
          <tr>
            <th />
            <th>Basic Pension</th>
            <th>Dearness Pension</th>
            <th>{drLabel}</th>
            <th>Total</th>
          </tr>
        </thead>
        <tbody>
          <tr>
            <td />
            <td>{money(block?.basic_pension)}</td>
            <td>{money(block?.dearness_pension)}</td>
            <td>{money(block?.initial_dr)}</td>
            <td>{money(block?.total)}</td>
          </tr>
        </tbody>
      </table>
    </div>
  );
}

/**
 * Oracle FI_PN_LIC_FAMILY_PEN_DTLS — matched to live family LIC claim print.
 */
export default function LicClaimFamilyPrint({ report }) {
  if (!report) return null;

  return (
    <div className="lic-claim-print lic-claim-family" id="lic-claim-family-print-root">
      <div className="lic-claim-print__page">
          <div className="lic-claim-print__head">
            <div className="lic-claim-print__scheme">{report.org_scheme}</div>
            <div className="lic-claim-print__policy">
              MASTER POLICY NO. {report.master_policy_no}
            </div>
            <div className="lic-claim-print__sub">
              {report.subtitle}{" "}
              <strong>{report.payable_from || "____________"}</strong>
            </div>
            <div className="lic-claim-print__dock">{report.dock_system}</div>
          </div>

        <div className="lic-claim-print__fields">
          <Field no={1} label="LIC Sr. No." value={report.lic_sl_no} />
          <Field no={2} label="Pension Roll No." value={report.pen_roll_no} />
          <Field no={3} label="Aadhar No." value={report.aadhar_no || ""} />
          <Field
            no={4}
            label="Name of the Widow/Widower"
            value={report.applicant_name}
          />
          <Field no={5} label="Sex" value={report.gender} />
          <Field
            no={6}
            label="Date Of Birth of the annuitant"
            value={report.birth_dt}
          />
          <Field
            no={7}
            label="Due Date of First Month Pension"
            value={report.due_date_first_pension}
          />
          <Field
            no={8}
            label="Due Date Of Vesting Of Pension"
            value={report.due_date_vesting}
          />
          <Field
            no={9}
            label="Age(Last Birthday on the annuitant on the date of vesting)"
            value={
              report.age_on_vesting != null ? report.age_on_vesting : ""
            }
          />

          <div className="lic-claim-family__section">
            <div className="lic-claim-print__comm-title">
              10. Ordinary Pension Payable upto death/remarriage (after
              commutation) :
            </div>
            <PensionTable
              title=""
              block={report.ordinary}
              daPct={report.da_pct}
            />
          </div>

          <div className="lic-claim-family__section">
            <div className="lic-claim-print__comm-title">
              11. Extra pension payable for a limited period (after
              commutation) :
            </div>
            <PensionTable title="" block={report.extra} daPct={report.da_pct} />
          </div>

          <div className="lic-claim-family__section">
            <div className="lic-claim-print__comm-title">
              12. Total amount of pension payable (after commutation) :
            </div>
            <PensionTable
              title=""
              block={report.total_pension}
              daPct={report.da_pct}
            />
          </div>

          <div className="lic-claim-print__field lic-claim-print__field--wide">
            <span className="lic-claim-print__no">13.</span>
            <span className="lic-claim-print__lbl">
              Date upto which extra pension is payable
            </span>
            <span className="lic-claim-print__colon">:</span>
            <span className="lic-claim-print__val lic-claim-print__val--wrap">
              {report.extra_pension_upto_text || ""}
            </span>
          </div>

          <Field
            no={14}
            label="Initial Purchase price"
            value={report.purchase_price || ""}
          />
          <Field
            no={15}
            label="Rate of Income Tax Deduction"
            value={report.income_tax_note || ""}
            wide
          />
          <Field
            no={16}
            label="Residential address of the Annuitant"
            value={report.address}
            wide
          />

          <div className="lic-claim-print__bank">
            <div className="lic-claim-print__comm-title">
              17. Particulars of the Annuitant Bank Account :
            </div>
            <div className="lic-claim-print__comm-row">
              <span>a) Bank Account No</span>
              <span>:</span>
              <span>{report.account_no}</span>
            </div>
            <div className="lic-claim-print__comm-row">
              <span>b) Name of the Bank and Branch</span>
              <span>:</span>
              <span>{report.bank_name_branch}</span>
            </div>
            <div className="lic-claim-print__comm-row">
              <span>c) Address of the Bank</span>
              <span>:</span>
              <span>{report.bank_address}</span>
            </div>
          </div>

          <Field
            no={18}
            label="Name of the deceased employee"
            value={report.emp_name}
          />
          <Field no={19} label="Office Code" value={report.office_code} />
          <Field no={20} label="Salary Roll No" value={report.emp_cd} />
          <Field
            no={21}
            label="LIC Annuity number of the deceased employee"
            value={report.deceased_lic_annuity_no || ""}
          />
          <Field
            no={22}
            label="Date of death of the deceased employee"
            value={report.date_of_death}
          />
          <Field
            no={23}
            label="Whether post dated cheques issued (if any) against the deceased employee are returned"
            value={report.post_dated_cheques_note || ""}
            wide
          />
          <Field no={24} label="Remarks, if any" value={report.remarks || ""} wide />
        </div>

        <div className="lic-claim-print__note">
          NOTE : TWO SPECIMAN SIGNATURE OF THE ANNUITANT ARE GIVEN BELOW
        </div>
        <div className="lic-claim-family__sign-area">
          <div>
            <div>1) _______________________________</div>
            <div className="mt-2">2) _______________________________</div>
            <div className="mt-3">DATE : _______________</div>
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
