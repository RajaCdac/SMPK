const ADMIN_CODES = new Set(["ADMIN", "PENSION_ADMIN", "ADMINISTRATOR"]);

export const ROLE = {
  ADMIN: "ADMIN",
  FIRST_PENSION_USER: "FIRST_PENSION_USER",
  FAMILY_PENSION_USER: "FAMILY_PENSION_USER",
  BILL_GENERATION_USER: "BILL_GENERATION_USER",
  LIC_SECTION_USER: "LIC_SECTION_USER",
  /** Legacy catch-all from older role names */
  PENSION_USER: "PENSION_USER",
};

export function getStoredUser() {
  try {
    return JSON.parse(localStorage.getItem("user") || "null");
  } catch {
    return null;
  }
}

export function normalizeRoleCode(user) {
  if (user?.is_superuser) {
    const code = (user?.role_code || "").toString().trim().toUpperCase();
    if (code && ADMIN_CODES.has(code)) {
      return ROLE.ADMIN;
    }
    if (!code || ADMIN_CODES.has(code)) {
      return ROLE.ADMIN;
    }
  }

  const code = (user?.role_code || "").toString().trim().toUpperCase();
  if (ADMIN_CODES.has(code)) {
    return ROLE.ADMIN;
  }

  const roleName = (user?.role || "").toString().toLowerCase().trim();
  if (roleName.includes("family pension")) {
    return ROLE.FAMILY_PENSION_USER;
  }
  if (roleName.includes("first pension")) {
    return ROLE.FIRST_PENSION_USER;
  }
  if (roleName.includes("bill generation")) {
    return ROLE.BILL_GENERATION_USER;
  }
  if (roleName.includes("lic section")) {
    return ROLE.LIC_SECTION_USER;
  }
  if (roleName.includes("admin") && !roleName.includes("pension user")) {
    return ROLE.ADMIN;
  }
  if (
    roleName === "admin" ||
    roleName === "administrator" ||
    roleName === "pension admin"
  ) {
    return ROLE.ADMIN;
  }

  if (code) {
    return code;
  }

  if (user?.is_superuser) {
    return ROLE.ADMIN;
  }

  if (roleName) {
    return ROLE.PENSION_USER;
  }

  return ROLE.PENSION_USER;
}

export function isAdminUser(user = getStoredUser()) {
  if (user?.is_superuser && !user?.role_code) {
    return true;
  }
  return normalizeRoleCode(user) === ROLE.ADMIN;
}

export function isFirstPensionUser(user = getStoredUser()) {
  const code = normalizeRoleCode(user);
  return (
    code === ROLE.FIRST_PENSION_USER || code === ROLE.PENSION_USER
  );
}

export function isFamilyPensionUser(user = getStoredUser()) {
  return normalizeRoleCode(user) === ROLE.FAMILY_PENSION_USER;
}

export function isBillGenerationUser(user = getStoredUser()) {
  return normalizeRoleCode(user) === ROLE.BILL_GENERATION_USER;
}

export function isLicSectionUser(user = getStoredUser()) {
  return normalizeRoleCode(user) === ROLE.LIC_SECTION_USER;
}

/** @deprecated Prefer role-specific helpers; kept for older imports. */
export function isPensionUser(user = getStoredUser()) {
  return !isAdminUser(user) && normalizeRoleCode(user) !== "";
}

/** @deprecated Prefer getNavItemsForUser / role-specific helpers. */
export function isPensionOnlyUser(user = getStoredUser()) {
  return isFirstPensionUser(user);
}

const ADMIN_NAV = [
  { to: "/dashboard/admin", label: "Admin Home", end: false },
  { to: "/dashboard/users", label: "User Management" },
  { to: "/dashboard/roles", label: "Role Management" },
  { to: "/dashboard/logs", label: "Audit Logs" },
  { to: "/dashboard/workflow", label: "Workflow" },
  { to: "/dashboard/master-data", label: "Master Data" },
  { to: "/dashboard/oracle-transfer", label: "Oracle Transfer" },
];

const ESR_NAV = {
  key: "esr",
  label: "ESR",
  children: [
    { to: "/dashboard/esr/personal", label: "Personal" },
    { to: "/dashboard/esr/admin", label: "Admin" },
    { to: "/dashboard/esr/finance", label: "Finance" },
    { to: "/dashboard/esr/salary", label: "Salary" },
    { to: "/dashboard/nominee", label: "Nominee" },
  ],
};

const FIRST_PENSION_NAV = [
  { to: "/dashboard", label: "Dashboard", end: true },
  { to: "/dashboard/cases", label: "Pension Cases" },
  {
    key: "first-pension",
    label: "First Pension",
    children: [
      { to: "/dashboard/firstpension/esr-check", label: "ESR Check", end: true },
      { to: "/dashboard/firstpension/nopay", label: "No-pay" },
      { to: "/dashboard/firstpension/commutation", label: "Commutation" },
      { to: "/dashboard/firstpension/proposal", label: "Proposal" },
      { to: "/dashboard/firstpension/amount", label: "Amount" },
      { to: "/dashboard/firstpension/bill", label: "Bill & Journal" },
      { to: "/dashboard/firstpension/reports", label: "Reports" },
    ],
  },
  ESR_NAV,
  {
    key: "fp-report",
    label: "Report",
    children: [
      {
        to: "/dashboard/fp-reports/sanction",
        label: "Pension Sanction",
        end: true,
      },
      {
        to: "/dashboard/fp-reports/firstpensionadvice",
        label: "First Pension Advice",
      },
      { to: "/dashboard/fp-reports/lic", label: "LIC Report" },
      {
        to: "/dashboard/fp-reports/combill",
        label: "Commutation Sanction",
      },
      {
        to: "/dashboard/fp-reports/sepcombill",
        label: "Sep. Commutation Bill",
      },
      { to: "/dashboard/fp-reports/billabstract", label: "Bill Abstract" },
      { to: "/dashboard/fp-reports/journalsummary", label: "Journal Summary" },
    ],
  },
  { to: "/dashboard/archive", label: "Archive" },
  { to: "/dashboard/methodology2", label: "Methodology 2" },
];

const FAMILY_PENSION_NAV = [
  {
    to: "/dashboard/familypensioncases",
    label: "Dashboard",
    end: true,
  },
  ESR_NAV,
  {
    key: "die-in-harness",
    label: "Die-in-Harness",
    children: [
      {
        to: "/dashboard/die-in-harness",
        label: "No-pay Entry",
        end: true,
      },
      {
        to: "/dashboard/die-in-harness/proposal",
        label: "Pension Proposal",
      },
      {
        to: "/dashboard/die-in-harness/claim",
        label: "Pension Application",
      },
    ],
  },
  {
    key: "family-pension",
    label: "Family Pension",
    children: [
      { to: "/dashboard/familypension", label: "Claim Entry", end: true },
      {
        to: "/dashboard/familypension/recovery-deduction",
        label: "Recovery/Deduction",
      },
      { to: "/dashboard/methodology1", label: "Methodology I" },
    ],
  },
  {
    key: "report",
    label: "Report",
    children: [
      {
        to: "/dashboard/reports/first-pension-generation",
        label: "Sanction Of Family Pension (Normal)",
      },
      {
        to: "/dashboard/reports/fp-dih-application",
        label: "Application for FP(DIH)",
      },
      {
        to: "/dashboard/reports/bill-generation",
        label: "Bill Generation",
      },
      {
        to: "/dashboard/reports/bill-abstract",
        label: "Bill Abstract",
      },
      {
        to: "/dashboard/reports/journal-voucher",
        label: "Journal Voucher",
      },
      {
        to: "/dashboard/reports/first-fp-bill-lic",
        label: "First FP Bill (LIC)",
      },
      { to: "/dashboard/reports/arrear", label: "Arrear" },
      { to: "/dashboard/reports/cpi-upgrade", label: "CPI-Upgrade" },
    ],
  },
];

const BILL_GENERATION_NAV = [];
const LIC_SECTION_NAV = [];

export function getNavItemsForUser(user = getStoredUser()) {
  if (isAdminUser(user)) {
    return ADMIN_NAV;
  }
  const code = normalizeRoleCode(user);
  if (code === ROLE.FAMILY_PENSION_USER) {
    return FAMILY_PENSION_NAV;
  }
  if (
    code === ROLE.FIRST_PENSION_USER ||
    code === ROLE.PENSION_USER
  ) {
    return FIRST_PENSION_NAV;
  }
  if (code === ROLE.BILL_GENERATION_USER) {
    return BILL_GENERATION_NAV;
  }
  if (code === ROLE.LIC_SECTION_USER) {
    return LIC_SECTION_NAV;
  }
  return [];
}

export function defaultDashboardPath(user = getStoredUser()) {
  if (isAdminUser(user)) {
    return "/dashboard/admin";
  }
  if (isFamilyPensionUser(user)) {
    return "/dashboard/familypensioncases";
  }
  if (isFirstPensionUser(user)) {
    return "/dashboard";
  }
  return "/dashboard";
}

/**
 * Route guard helper.
 * @param {"admin"|"first_pension"|"family_pension"|string[]} allow
 */
export function roleAllows(allow, user = getStoredUser()) {
  const code = normalizeRoleCode(user);
  if (Array.isArray(allow)) {
    return allow.map((c) => String(c).toUpperCase()).includes(code);
  }
  if (allow === "admin") {
    return isAdminUser(user);
  }
  if (allow === "first_pension") {
    return isFirstPensionUser(user);
  }
  if (allow === "family_pension") {
    return isFamilyPensionUser(user);
  }
  return code === String(allow).toUpperCase();
}
