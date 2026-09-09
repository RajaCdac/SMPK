-- Copy SMPK application + missing master tables: smpk_pension -> finance (localhost:3306).
--
-- Usage (PowerShell):
--   mysql --user=root --password=root123 --host=127.0.0.1 --port=3306 finance < "d:\SMPK\SMPK\backend\config\scripts\import_smpk_tables_to_finance_3306.sql"
--
-- Notes:
-- - fi_pn_mh_pension_proposal is NOT copied (6,712 Oracle rows already in finance).
-- - first_pension_pensionproposal is SMPK workflow data (36 rows in smpk_pension).
-- - If a table already exists in finance, it is dropped and recreated from smpk_pension structure, then rows copied.

SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS = 0;

-- === 1. First Pension workflow ===============================================
DROP TABLE IF EXISTS finance.first_pension_pensionsummary;
DROP TABLE IF EXISTS finance.first_pension_commutationapplication;
DROP TABLE IF EXISTS finance.first_pension_pensionproposal;
DROP TABLE IF EXISTS finance.first_pension_pensioncase;

CREATE TABLE finance.first_pension_pensioncase LIKE smpk_pension.first_pension_pensioncase;
INSERT INTO finance.first_pension_pensioncase SELECT * FROM smpk_pension.first_pension_pensioncase;

CREATE TABLE finance.first_pension_pensionproposal LIKE smpk_pension.first_pension_pensionproposal;
INSERT INTO finance.first_pension_pensionproposal SELECT * FROM smpk_pension.first_pension_pensionproposal;

CREATE TABLE finance.first_pension_commutationapplication LIKE smpk_pension.first_pension_commutationapplication;
INSERT INTO finance.first_pension_commutationapplication SELECT * FROM smpk_pension.first_pension_commutationapplication;

CREATE TABLE finance.first_pension_pensionsummary LIKE smpk_pension.first_pension_pensionsummary;
INSERT INTO finance.first_pension_pensionsummary SELECT * FROM smpk_pension.first_pension_pensionsummary;

-- === 2. Methodology 2 ======================================================
DROP TABLE IF EXISTS finance.methodology2_consolidation;
CREATE TABLE finance.methodology2_consolidation LIKE smpk_pension.methodology2_consolidation;
INSERT INTO finance.methodology2_consolidation SELECT * FROM smpk_pension.methodology2_consolidation;

-- === 3. Missing finance masters ============================================
DROP TABLE IF EXISTS finance.fi_pn_cpi_consolidation;
CREATE TABLE finance.fi_pn_cpi_consolidation LIKE smpk_pension.fi_pn_cpi_consolidation;
INSERT INTO finance.fi_pn_cpi_consolidation SELECT * FROM smpk_pension.fi_pn_cpi_consolidation;

DROP TABLE IF EXISTS finance.fi_pn_md_edbilltype_map;
CREATE TABLE finance.fi_pn_md_edbilltype_map LIKE smpk_pension.fi_pn_md_edbilltype_map;
INSERT INTO finance.fi_pn_md_edbilltype_map SELECT * FROM smpk_pension.fi_pn_md_edbilltype_map;

DROP TABLE IF EXISTS finance.fi_pn_mh_base_cpi;
CREATE TABLE finance.fi_pn_mh_base_cpi LIKE smpk_pension.fi_pn_mh_base_cpi;
INSERT INTO finance.fi_pn_mh_base_cpi SELECT * FROM smpk_pension.fi_pn_mh_base_cpi;

DROP TABLE IF EXISTS finance.fi_pn_mh_billtype;
CREATE TABLE finance.fi_pn_mh_billtype LIKE smpk_pension.fi_pn_mh_billtype;
INSERT INTO finance.fi_pn_mh_billtype SELECT * FROM smpk_pension.fi_pn_mh_billtype;

DROP TABLE IF EXISTS finance.fi_pn_mh_consolidation;
CREATE TABLE finance.fi_pn_mh_consolidation LIKE smpk_pension.fi_pn_mh_consolidation;
INSERT INTO finance.fi_pn_mh_consolidation SELECT * FROM smpk_pension.fi_pn_mh_consolidation;

DROP TABLE IF EXISTS finance.fi_pr_mh_ada_rate_vw;
CREATE TABLE finance.fi_pr_mh_ada_rate_vw LIKE smpk_pension.fi_pr_mh_ada_rate_vw;
INSERT INTO finance.fi_pr_mh_ada_rate_vw SELECT * FROM smpk_pension.fi_pr_mh_ada_rate_vw;

DROP TABLE IF EXISTS finance.fi_pr_mh_erndednmap;
CREATE TABLE finance.fi_pr_mh_erndednmap LIKE smpk_pension.fi_pr_mh_erndednmap;
INSERT INTO finance.fi_pr_mh_erndednmap SELECT * FROM smpk_pension.fi_pr_mh_erndednmap;

-- === 4. Optional cache / workflow ==========================================
DROP TABLE IF EXISTS finance.first_pension_cached_retirement_emp;
CREATE TABLE finance.first_pension_cached_retirement_emp LIKE smpk_pension.first_pension_cached_retirement_emp;
INSERT INTO finance.first_pension_cached_retirement_emp SELECT * FROM smpk_pension.first_pension_cached_retirement_emp;

DROP TABLE IF EXISTS finance.first_pension_cached_employee_oracle;
CREATE TABLE finance.first_pension_cached_employee_oracle LIKE smpk_pension.first_pension_cached_employee_oracle;
INSERT INTO finance.first_pension_cached_employee_oracle SELECT * FROM smpk_pension.first_pension_cached_employee_oracle;

DROP TABLE IF EXISTS finance.first_pension_dashboard_snapshot;
CREATE TABLE finance.first_pension_dashboard_snapshot LIKE smpk_pension.first_pension_dashboard_snapshot;
INSERT INTO finance.first_pension_dashboard_snapshot SELECT * FROM smpk_pension.first_pension_dashboard_snapshot;

DROP TABLE IF EXISTS finance.workflow_workflowhistory;
DROP TABLE IF EXISTS finance.workflow_workflowinstance;
DROP TABLE IF EXISTS finance.workflow_workflowstep;
DROP TABLE IF EXISTS finance.workflow_workflowmaster;

CREATE TABLE finance.workflow_workflowmaster LIKE smpk_pension.workflow_workflowmaster;
INSERT INTO finance.workflow_workflowmaster SELECT * FROM smpk_pension.workflow_workflowmaster;

CREATE TABLE finance.workflow_workflowstep LIKE smpk_pension.workflow_workflowstep;
INSERT INTO finance.workflow_workflowstep SELECT * FROM smpk_pension.workflow_workflowstep;

CREATE TABLE finance.workflow_workflowinstance LIKE smpk_pension.workflow_workflowinstance;
INSERT INTO finance.workflow_workflowinstance SELECT * FROM smpk_pension.workflow_workflowinstance;

CREATE TABLE finance.workflow_workflowhistory LIKE smpk_pension.workflow_workflowhistory;
INSERT INTO finance.workflow_workflowhistory SELECT * FROM smpk_pension.workflow_workflowhistory;

SET FOREIGN_KEY_CHECKS = 1;

SELECT 'first_pension_pensioncase' AS tbl, COUNT(*) AS rows_in_finance FROM finance.first_pension_pensioncase
UNION ALL SELECT 'first_pension_pensionproposal', COUNT(*) FROM finance.first_pension_pensionproposal
UNION ALL SELECT 'fi_pn_mh_pension_proposal (oracle)', COUNT(*) FROM finance.fi_pn_mh_pension_proposal;
