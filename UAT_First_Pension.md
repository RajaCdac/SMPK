# User Acceptance Testing (UAT) Document
### Web-based Pension Management System for SMPK

**Document Type:** UAT Test Case & Sign-Off Report for Prototype Development of First Pension / Superannuation Pension using Methodology 1

**Purpose:** To formally record User Acceptance Testing activities, results and approval for the prototype development of First / Superannuation Pension using Methodology 1.

---

## 1. Document Control

| Field | Details |
| --- | --- |
| Document Title | UAT Test Case & Sign-Off Report – First / Superannuation Pension |
| Application | Web-based Pension Management System for SMPK |
| Module | First / Superannuation Pension (Methodology 1) |
| Version | 1.0 |
| Prepared By | |
| Reviewed By | |
| Date of Issue | |

---

## 2. Scope of Testing

**In Scope**
- End-to-end generation of First / Superannuation Pension for all categories of employees (Category 1 & 2 and Category 3 & 4).
- Pension Proposal data entry, calculation of Pension amount and Gratuity amount, and generation of the related output.

**Out of Scope**
- Standalone Methodology 1 and Methodology 2 calculator modules (covered under separate UAT).

---

## 3. UAT Test Case

| Sl. No. | Field | Details |
| --- | --- | --- |
| 1 | Test Case ID | UAT-Methodology1-First-Pension |
| 2 | Module Name | Prototype development of First / Superannuation Pension using Methodology 1 for all categories of employee |
| 3 | Test Scenario | Generation of First / Superannuation Pension using Methodology 1 for all categories of employee |
| 4 | Preconditions | 1. Authorized user is logged in with valid credentials and role; application and database are up and reachable.<br>2. The selected employee's master record exists with Date of Birth, Date of Joining, pay scale and last pay drawn available.<br>3. No First Pension has already been sanctioned for the same employee (no duplicate proposal).<br>4. Separation date is a valid calendar date and not earlier than the Date of Joining.<br>5. For Superannuation, the separation/retirement date corresponds to the date of attaining superannuation age (date of superannuation) and does not exceed it.<br>6. No-pay / Dies-non periods, if any, fall within the service period (between Date of Joining and Separation date).<br>7. Commutation percentage is within the permissible limit (≤ 40%).<br>8. A valid pension disbursing bank is selectable from the bank master. |
| 5 | Test Steps | 1. Select employee.<br>2. Enter separation type and date.<br>3. Enter No-pays, Dies-non details.<br>4. Enter commutation percentage and bank.<br>5. Fill up Pension Proposal form.<br>6. Click on the **'Calculate'** button to calculate Pension amount and Gratuity amount. |
| 6 | Category of Employee Data Tested | All categories — both 1 & 2 and 3 & 4 |
| 7 | Functional Performance | Option:<br>a) Not Satisfactory<br>b) Poor<br>c) Average<br>d) Almost as per expectation<br>e) Better than expectation<br><br>Comments / Observation: |
| 8 | Tested By | |
| 9 | Test Date | |
| 10 | Remarks, if any | |

---

## 4. Detailed Test Steps & Expected Results

| Step | Action | Expected Result | Actual Result | Status (Pass/Fail) |
| --- | --- | --- | --- | --- |
| 1 | Select employee | Employee details (name, code, scale, last pay, service details) are fetched and displayed correctly. | | |
| 2 | Enter separation type and date | Separation type and separation date are accepted and validated. | | |
| 3 | Enter No-pays and Dies-non details | No-pay / Dies-non periods are accepted and reflected in qualifying service. | | |
| 4 | Enter commutation percentage and bank | Commutation percentage is accepted; bank is selectable from the bank list. | | |
| 5 | Fill up Pension Proposal form | All mandatory proposal fields are captured and validated. | | |
| 6 | Click on 'Calculate' | Pension amount and Gratuity amount are computed correctly as per Methodology 1 for the employee's category. | | |

---

## 5. Functional Performance Rating

Mark the option that best describes the overall functional performance:

| Option | Rating | Selected (✓) |
| --- | --- | --- |
| a) | Not Satisfactory | |
| b) | Poor | |
| c) | Average | |
| d) | Almost as per expectation | |
| e) | Better than expectation | |

**Comments / Observation:**

_______________________________________________________________________

_______________________________________________________________________

---

## 6. Declaration

- The application has been tested against the agreed business requirements.
- The undersigned formally approve completion of UAT for the prototype development.

---

## 7. Approvals

| Organization | Name & Designation | Signature & Date | Approval (Y/N) |
| --- | --- | --- | --- |
| | | | |
| | | | |
| | | | |
| | | | |
| | | | |
| | | | |
| | | | |
| | | | |
