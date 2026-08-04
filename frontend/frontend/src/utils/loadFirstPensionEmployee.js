import API from "../services/Api";
import { mergeEmployeeDetail } from "./dashboardEmployee";

/**
 * Load employee for pension processing (dashboard row + intake + full employee API).
 */
export async function loadFirstPensionEmployee(dashboardRow) {
  const empCode = dashboardRow.emp_code;
  let intakeData = null;
  let empApi = null;
  let loadWarning = "";

  try {
    const intakeRes = await API.get(
      `first-pension/process-intake/employee/${empCode}/`
    );
    intakeData = intakeRes.data;
  } catch (err) {
    console.error(err);
  }

  try {
    const empRes = await API.get(`first-pension/employees/${empCode}/`);
    empApi = empRes.data;
  } catch (err) {
    console.error(err);
    empApi = err.response?.data ?? null;
    if (empApi) {
      loadWarning =
        "Some data could not be loaded from Oracle; you can continue with available fields.";
    } else {
      loadWarning =
        "Oracle employee lookup failed; using dashboard data for processing.";
    }
  }

  const detail = mergeEmployeeDetail(dashboardRow, empApi, intakeData);
  return { detail, loadWarning };
}

/** Load by employee code only (First Pension page / deep link from dashboard). */
export async function loadFirstPensionEmployeeByCode(empCode) {
  const code = String(empCode || "").trim();
  if (!code) {
    throw new Error("Employee code is required");
  }
  return loadFirstPensionEmployee({ emp_code: code });
}
