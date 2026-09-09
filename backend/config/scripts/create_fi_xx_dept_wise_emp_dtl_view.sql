-- Oracle FINANCE.FI_XX_DEPT_WISE_EMP_DTL as MySQL view on finance:3306.
--
-- Prerequisites (import from Oracle if missing):
--   fi_xx_mh_emp_per, fi_xx_mh_emp_fin, fi_pm_mh_emplink,
--   fi_xx_mh_fixabs, fi_xx_md_dept, fi_xx_mh_dept, fi_ma_md_budcntr
--
-- Sync base tables:
--   set MYSQL_PORT=3306
--   python scripts/oracle_table_to_mysql.py FI_PM_MH_EMPLINK --drop
--   python scripts/oracle_table_to_mysql.py FI_XX_MD_DEPT --drop
--   python scripts/oracle_table_to_mysql.py FI_MA_MD_BUDCNTR --drop

DROP VIEW IF EXISTS fi_xx_dept_wise_emp_dtl;

CREATE VIEW fi_xx_dept_wise_emp_dtl AS
SELECT
    a.EMP_CD,
    a.FIRST_NAME,
    a.MIDDLE_NAME,
    a.LAST_NAME,
    b.FA_NO,
    d.FA_DESC,
    c.SRF_NO,
    c.PF_NO,
    c.LEAVE_AC_NO,
    c.OLD_EMP_NO,
    e.BUDCNTR_CD,
    g.ALLOC_DESC,
    e.DEPT_CD,
    f.DEPT_DESC
FROM fi_xx_mh_emp_per a
INNER JOIN fi_xx_mh_emp_fin b
    ON (a.EMP_CD) COLLATE utf8mb4_unicode_ci = (b.EMP_CD) COLLATE utf8mb4_unicode_ci
INNER JOIN fi_pm_mh_emplink c
    ON (b.EMP_CD) COLLATE utf8mb4_unicode_ci = (c.EMP_CD) COLLATE utf8mb4_unicode_ci
INNER JOIN fi_xx_mh_fixabs d
    ON (TRIM(b.FA_NO)) COLLATE utf8mb4_unicode_ci = (TRIM(d.FA_NO)) COLLATE utf8mb4_unicode_ci
INNER JOIN fi_xx_md_dept e
    ON (d.BUDCNTR_CD) COLLATE utf8mb4_unicode_ci = (e.BUDCNTR_CD) COLLATE utf8mb4_unicode_ci
INNER JOIN fi_xx_mh_dept f
    ON (e.DEPT_CD) COLLATE utf8mb4_unicode_ci = (f.DEPT_CD) COLLATE utf8mb4_unicode_ci
INNER JOIN fi_ma_md_budcntr g
    ON (e.BUDCNTR_CD) COLLATE utf8mb4_unicode_ci = (g.ALLOC_CD) COLLATE utf8mb4_unicode_ci;
