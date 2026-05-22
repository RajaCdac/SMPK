-- Run in MySQL database: smpk_pension
-- Use only if python manage.py migrate did not create the table.

CREATE TABLE IF NOT EXISTS `first_pension_pensionproposal` (
  `id` bigint AUTO_INCREMENT NOT NULL PRIMARY KEY,
  `emp_cd` varchar(20) NOT NULL UNIQUE,
  `emp_name` varchar(200) NOT NULL,
  `employee_status` varchar(50) NOT NULL,
  `ca_number` varchar(50) NOT NULL,
  `pension_type` varchar(50) NOT NULL,
  `pension_proposal_no` varchar(50) NOT NULL,
  `eligible_double_family_pension` bool NOT NULL,
  `separation_type` varchar(50) NOT NULL,
  `separation_date` date NULL,
  `implemented_year` integer NULL,
  `implemented_month` integer NULL,
  `service_tenure` varchar(100) NOT NULL,
  `pension_option` varchar(50) NOT NULL,
  `option_given_by` varchar(50) NOT NULL,
  `regn_no` varchar(50) NOT NULL,
  `regn_date` date NULL,
  `start_month` integer NULL,
  `start_year` integer NULL,
  `pension_roll_no` varchar(50) NOT NULL,
  `pension_proposal_date` date NULL,
  `double_family_pension_upto_date` date NULL,
  `provisional_pension_pct` numeric(7, 2) NULL,
  `bank_cd` varchar(20) NOT NULL,
  `bank_name` varchar(200) NOT NULL,
  `account_no` varchar(50) NOT NULL,
  `vigilance_clearance_ref_no` varchar(100) NOT NULL,
  `vigilance_clearance_ref_dt` date NULL,
  `lic_bank_cd` varchar(20) NOT NULL,
  `lic_bank_name` varchar(200) NOT NULL,
  `vr_ref_no` varchar(100) NOT NULL,
  `vr_ref_dt` date NULL,
  `compassionate_allowance` varchar(50) NOT NULL,
  `quarter_status` varchar(50) NOT NULL,
  `nominee_eform` varchar(50) NOT NULL,
  `compassionate_allowance_amt` numeric(12, 2) NULL,
  `port_city_resident` varchar(50) NOT NULL,
  `gratuity_option` varchar(50) NOT NULL,
  `retirement_cpi` numeric(10, 2) NULL,
  `id_card_submitted` bool NOT NULL,
  `vigilance_cleared` bool NOT NULL,
  `incentive_holder` varchar(50) NOT NULL,
  `held_up_flag` varchar(50) NOT NULL,
  `held_gratuity_amt` numeric(12, 2) NULL,
  `extra_tccs_enabled` bool NOT NULL,
  `extra_tccs_years` integer NOT NULL,
  `extra_tccs_months` integer NOT NULL,
  `extra_tccs_days` integer NOT NULL,
  `earning_deductions` json NOT NULL,
  `created_at` datetime(6) NOT NULL,
  `updated_at` datetime(6) NOT NULL,
  `created_by_id` bigint NULL,
  `updated_by_id` bigint NULL
);

ALTER TABLE `first_pension_pensionproposal`
  ADD CONSTRAINT `first_pension_pensio_created_by_id_fk`
  FOREIGN KEY (`created_by_id`) REFERENCES `accounts_user` (`id`);

ALTER TABLE `first_pension_pensionproposal`
  ADD CONSTRAINT `first_pension_pensio_updated_by_id_fk`
  FOREIGN KEY (`updated_by_id`) REFERENCES `accounts_user` (`id`);

-- Record migration (run only if missing from django_migrations):
-- INSERT INTO django_migrations (app, name, applied)
-- VALUES ('first_pension', '0003_pensionproposal', NOW());
