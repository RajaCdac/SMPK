/*
SQLyog Community v13.3.1 (64 bit)
MySQL - 8.0.45 : Database - smpk_pension
*********************************************************************
*/

/*!40101 SET NAMES utf8 */;

/*!40101 SET SQL_MODE=''*/;

/*!40014 SET @OLD_UNIQUE_CHECKS=@@UNIQUE_CHECKS, UNIQUE_CHECKS=0 */;
/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;
/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;
/*!40111 SET @OLD_SQL_NOTES=@@SQL_NOTES, SQL_NOTES=0 */;
CREATE DATABASE /*!32312 IF NOT EXISTS*/`smpk_pension` /*!40100 DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci */ /*!80016 DEFAULT ENCRYPTION='N' */;

USE `smpk_pension`;

/*Table structure for table `accounts_diesnon` */

DROP TABLE IF EXISTS `accounts_diesnon`;

CREATE TABLE `accounts_diesnon` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `start_dt` date NOT NULL,
  `description` varchar(255) COLLATE utf8mb4_unicode_ci NOT NULL,
  `is_active` tinyint(1) NOT NULL,
  `end_date` date DEFAULT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

/*Table structure for table `accounts_role` */

DROP TABLE IF EXISTS `accounts_role`;

CREATE TABLE `accounts_role` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `name` varchar(50) NOT NULL,
  `is_active` tinyint(1) NOT NULL,
  `code` varchar(30) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `accounts_role_code_31e05c3f_uniq` (`code`)
) ENGINE=InnoDB AUTO_INCREMENT=7 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

/*Table structure for table `accounts_user` */

DROP TABLE IF EXISTS `accounts_user`;

CREATE TABLE `accounts_user` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `password` varchar(128) NOT NULL,
  `last_login` datetime(6) DEFAULT NULL,
  `is_superuser` tinyint(1) NOT NULL,
  `username` varchar(150) NOT NULL,
  `first_name` varchar(150) NOT NULL,
  `last_name` varchar(150) NOT NULL,
  `email` varchar(254) NOT NULL,
  `is_staff` tinyint(1) NOT NULL,
  `is_active` tinyint(1) NOT NULL,
  `date_joined` datetime(6) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `username` (`username`)
) ENGINE=InnoDB AUTO_INCREMENT=7 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

/*Table structure for table `accounts_user_groups` */

DROP TABLE IF EXISTS `accounts_user_groups`;

CREATE TABLE `accounts_user_groups` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `user_id` bigint NOT NULL,
  `group_id` int NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `accounts_user_groups_user_id_group_id_59c0b32f_uniq` (`user_id`,`group_id`),
  KEY `accounts_user_groups_group_id_bd11a704_fk_auth_group_id` (`group_id`),
  CONSTRAINT `accounts_user_groups_group_id_bd11a704_fk_auth_group_id` FOREIGN KEY (`group_id`) REFERENCES `auth_group` (`id`),
  CONSTRAINT `accounts_user_groups_user_id_52b62117_fk_accounts_user_id` FOREIGN KEY (`user_id`) REFERENCES `accounts_user` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

/*Table structure for table `accounts_user_user_permissions` */

DROP TABLE IF EXISTS `accounts_user_user_permissions`;

CREATE TABLE `accounts_user_user_permissions` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `user_id` bigint NOT NULL,
  `permission_id` int NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `accounts_user_user_permi_user_id_permission_id_2ab516c2_uniq` (`user_id`,`permission_id`),
  KEY `accounts_user_user_p_permission_id_113bb443_fk_auth_perm` (`permission_id`),
  CONSTRAINT `accounts_user_user_p_permission_id_113bb443_fk_auth_perm` FOREIGN KEY (`permission_id`) REFERENCES `auth_permission` (`id`),
  CONSTRAINT `accounts_user_user_p_user_id_e4f0a161_fk_accounts_` FOREIGN KEY (`user_id`) REFERENCES `accounts_user` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

/*Table structure for table `accounts_userprofile` */

DROP TABLE IF EXISTS `accounts_userprofile`;

CREATE TABLE `accounts_userprofile` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `emp_code` varchar(50) COLLATE utf8mb4_unicode_ci NOT NULL,
  `designation` varchar(100) COLLATE utf8mb4_unicode_ci NOT NULL,
  `department` varchar(100) COLLATE utf8mb4_unicode_ci NOT NULL,
  `mobile_no` varchar(20) COLLATE utf8mb4_unicode_ci NOT NULL,
  `user_id` bigint NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `user_id` (`user_id`),
  CONSTRAINT `accounts_userprofile_user_id_92240672_fk_accounts_user_id` FOREIGN KEY (`user_id`) REFERENCES `accounts_user` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=5 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

/*Table structure for table `accounts_userrole` */

DROP TABLE IF EXISTS `accounts_userrole`;

CREATE TABLE `accounts_userrole` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `is_active` tinyint(1) NOT NULL,
  `role_id` bigint NOT NULL,
  `user_id` bigint NOT NULL,
  PRIMARY KEY (`id`),
  KEY `accounts_userrole_role_id_9448d870_fk_accounts_role_id` (`role_id`),
  KEY `accounts_userrole_user_id_eba3c754_fk_accounts_user_id` (`user_id`),
  CONSTRAINT `accounts_userrole_role_id_9448d870_fk_accounts_role_id` FOREIGN KEY (`role_id`) REFERENCES `accounts_role` (`id`),
  CONSTRAINT `accounts_userrole_user_id_eba3c754_fk_accounts_user_id` FOREIGN KEY (`user_id`) REFERENCES `accounts_user` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=5 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

/*Table structure for table `audit_auditlog` */

DROP TABLE IF EXISTS `audit_auditlog`;

CREATE TABLE `audit_auditlog` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `table_name` varchar(100) NOT NULL,
  `record_id` varchar(100) NOT NULL,
  `action` varchar(10) NOT NULL,
  `old_data` json DEFAULT NULL,
  `new_data` json DEFAULT NULL,
  `changed_at` datetime(6) NOT NULL,
  `ip_address` char(39) DEFAULT NULL,
  `user_agent` longtext,
  `module` varchar(50) NOT NULL,
  `changed_by_id` bigint DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `audit_auditlog_changed_by_id_a72ece1d_fk_accounts_user_id` (`changed_by_id`),
  CONSTRAINT `audit_auditlog_changed_by_id_a72ece1d_fk_accounts_user_id` FOREIGN KEY (`changed_by_id`) REFERENCES `accounts_user` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=207 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

/*Table structure for table `auth_group` */

DROP TABLE IF EXISTS `auth_group`;

CREATE TABLE `auth_group` (
  `id` int NOT NULL AUTO_INCREMENT,
  `name` varchar(150) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `name` (`name`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

/*Table structure for table `auth_group_permissions` */

DROP TABLE IF EXISTS `auth_group_permissions`;

CREATE TABLE `auth_group_permissions` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `group_id` int NOT NULL,
  `permission_id` int NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `auth_group_permissions_group_id_permission_id_0cd325b0_uniq` (`group_id`,`permission_id`),
  KEY `auth_group_permissio_permission_id_84c5c92e_fk_auth_perm` (`permission_id`),
  CONSTRAINT `auth_group_permissio_permission_id_84c5c92e_fk_auth_perm` FOREIGN KEY (`permission_id`) REFERENCES `auth_permission` (`id`),
  CONSTRAINT `auth_group_permissions_group_id_b120cbf9_fk_auth_group_id` FOREIGN KEY (`group_id`) REFERENCES `auth_group` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

/*Table structure for table `auth_permission` */

DROP TABLE IF EXISTS `auth_permission`;

CREATE TABLE `auth_permission` (
  `id` int NOT NULL AUTO_INCREMENT,
  `name` varchar(255) NOT NULL,
  `content_type_id` int NOT NULL,
  `codename` varchar(100) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `auth_permission_content_type_id_codename_01ab375a_uniq` (`content_type_id`,`codename`),
  CONSTRAINT `auth_permission_content_type_id_2f476e4b_fk_django_co` FOREIGN KEY (`content_type_id`) REFERENCES `django_content_type` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=273 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

/*Table structure for table `django_admin_log` */

DROP TABLE IF EXISTS `django_admin_log`;

CREATE TABLE `django_admin_log` (
  `id` int NOT NULL AUTO_INCREMENT,
  `action_time` datetime(6) NOT NULL,
  `object_id` longtext,
  `object_repr` varchar(200) NOT NULL,
  `action_flag` smallint unsigned NOT NULL,
  `change_message` longtext NOT NULL,
  `content_type_id` int DEFAULT NULL,
  `user_id` bigint NOT NULL,
  PRIMARY KEY (`id`),
  KEY `django_admin_log_content_type_id_c4bce8eb_fk_django_co` (`content_type_id`),
  KEY `django_admin_log_user_id_c564eba6_fk_accounts_user_id` (`user_id`),
  CONSTRAINT `django_admin_log_content_type_id_c4bce8eb_fk_django_co` FOREIGN KEY (`content_type_id`) REFERENCES `django_content_type` (`id`),
  CONSTRAINT `django_admin_log_user_id_c564eba6_fk_accounts_user_id` FOREIGN KEY (`user_id`) REFERENCES `accounts_user` (`id`),
  CONSTRAINT `django_admin_log_chk_1` CHECK ((`action_flag` >= 0))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

/*Table structure for table `django_content_type` */

DROP TABLE IF EXISTS `django_content_type`;

CREATE TABLE `django_content_type` (
  `id` int NOT NULL AUTO_INCREMENT,
  `app_label` varchar(100) NOT NULL,
  `model` varchar(100) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `django_content_type_app_label_model_76bd3d3b_uniq` (`app_label`,`model`)
) ENGINE=InnoDB AUTO_INCREMENT=69 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

/*Table structure for table `django_migrations` */

DROP TABLE IF EXISTS `django_migrations`;

CREATE TABLE `django_migrations` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `app` varchar(255) NOT NULL,
  `name` varchar(255) NOT NULL,
  `applied` datetime(6) NOT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=61 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

/*Table structure for table `django_session` */

DROP TABLE IF EXISTS `django_session`;

CREATE TABLE `django_session` (
  `session_key` varchar(40) NOT NULL,
  `session_data` longtext NOT NULL,
  `expire_date` datetime(6) NOT NULL,
  PRIMARY KEY (`session_key`),
  KEY `django_session_expire_date_a5c62663` (`expire_date`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

/*Table structure for table `employee_department` */

DROP TABLE IF EXISTS `employee_department`;

CREATE TABLE `employee_department` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `name` varchar(100) NOT NULL,
  `is_active` tinyint(1) NOT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

/*Table structure for table `employee_employee` */

DROP TABLE IF EXISTS `employee_employee`;

CREATE TABLE `employee_employee` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `employee_code` varchar(20) NOT NULL,
  `name` varchar(100) NOT NULL,
  `email` varchar(254) NOT NULL,
  `mobile` varchar(15) NOT NULL,
  `designation` varchar(100) NOT NULL,
  `is_pension_user` tinyint(1) NOT NULL,
  `department_id` bigint DEFAULT NULL,
  `user_id` bigint NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `employee_code` (`employee_code`),
  UNIQUE KEY `user_id` (`user_id`),
  KEY `employee_employee_department_id_8fce1a05_fk_employee_` (`department_id`),
  CONSTRAINT `employee_employee_department_id_8fce1a05_fk_employee_` FOREIGN KEY (`department_id`) REFERENCES `employee_department` (`id`),
  CONSTRAINT `employee_employee_user_id_2dd26fdc_fk_accounts_user_id` FOREIGN KEY (`user_id`) REFERENCES `accounts_user` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

/*Table structure for table `fi_pm_mh_bank` */

DROP TABLE IF EXISTS `fi_pm_mh_bank`;

CREATE TABLE `fi_pm_mh_bank` (
  `BANK_CD` varchar(6) COLLATE utf8mb4_unicode_ci NOT NULL,
  `BANK_DESC` varchar(50) COLLATE utf8mb4_unicode_ci NOT NULL,
  `BANK_ID` varchar(7) COLLATE utf8mb4_unicode_ci NOT NULL,
  `CONTROL_BANK_CD` varchar(6) COLLATE utf8mb4_unicode_ci NOT NULL,
  `ADDR1` varchar(25) COLLATE utf8mb4_unicode_ci NOT NULL,
  `ADDR2` varchar(25) COLLATE utf8mb4_unicode_ci NOT NULL,
  `PS` varchar(30) COLLATE utf8mb4_unicode_ci NOT NULL,
  `CITY` varchar(20) COLLATE utf8mb4_unicode_ci NOT NULL,
  `DIST` varchar(20) COLLATE utf8mb4_unicode_ci NOT NULL,
  `STATE` varchar(20) COLLATE utf8mb4_unicode_ci NOT NULL,
  `PIN` int DEFAULT NULL,
  `COUNTRY` varchar(20) COLLATE utf8mb4_unicode_ci NOT NULL,
  `CONTACT1` varchar(15) COLLATE utf8mb4_unicode_ci NOT NULL,
  `CONTACT2` varchar(15) COLLATE utf8mb4_unicode_ci NOT NULL,
  `FAX_NO` varchar(15) COLLATE utf8mb4_unicode_ci NOT NULL,
  `EMAIL_ID` varchar(30) COLLATE utf8mb4_unicode_ci NOT NULL,
  `DATE_CREATED` date DEFAULT NULL,
  `DATE_MODIFIED` date DEFAULT NULL,
  `MODIFIED_BY` varchar(5) COLLATE utf8mb4_unicode_ci NOT NULL,
  `CREATED_BY` varchar(5) COLLATE utf8mb4_unicode_ci NOT NULL,
  `RBI_CD` varchar(9) COLLATE utf8mb4_unicode_ci NOT NULL,
  `OLD_BANK_CD` varchar(6) COLLATE utf8mb4_unicode_ci NOT NULL,
  PRIMARY KEY (`BANK_CD`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

/*Table structure for table `fi_pm_mh_bankabbr` */

DROP TABLE IF EXISTS `fi_pm_mh_bankabbr`;

CREATE TABLE `fi_pm_mh_bankabbr` (
  `BANK_TYPE` varchar(2) COLLATE utf8mb4_unicode_ci NOT NULL,
  `BANK_NAME` varchar(60) COLLATE utf8mb4_unicode_ci NOT NULL,
  `CREATED_BY` varchar(5) COLLATE utf8mb4_unicode_ci NOT NULL,
  `MODIFIED_BY` varchar(5) COLLATE utf8mb4_unicode_ci NOT NULL,
  `DATE_CREATED` date DEFAULT NULL,
  `DATE_MODIFIED` date DEFAULT NULL,
  `BANK_ID` varchar(3) COLLATE utf8mb4_unicode_ci NOT NULL,
  `BANK_SHORT_NAME` varchar(10) COLLATE utf8mb4_unicode_ci NOT NULL,
  PRIMARY KEY (`BANK_TYPE`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

/*Table structure for table `fi_pn_md_commrate_rupee` */

DROP TABLE IF EXISTS `fi_pn_md_commrate_rupee`;

CREATE TABLE `fi_pn_md_commrate_rupee` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `DATE_CREATED` date DEFAULT NULL,
  `DATE_MODIFIED` date DEFAULT NULL,
  `MODIFIED_BY` varchar(5) COLLATE utf8mb4_unicode_ci NOT NULL,
  `CREATED_BY` varchar(5) COLLATE utf8mb4_unicode_ci NOT NULL,
  `AGE_YRS` int NOT NULL,
  `WEF_DT` date NOT NULL,
  `AMT_PER_RUPEE` decimal(14,6) DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uniq_commrate_rupee_key` (`AGE_YRS`,`WEF_DT`)
) ENGINE=InnoDB AUTO_INCREMENT=119 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

/*Table structure for table `fi_pn_md_death_gratchart` */

DROP TABLE IF EXISTS `fi_pn_md_death_gratchart`;

CREATE TABLE `fi_pn_md_death_gratchart` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `DATE_CREATED` date DEFAULT NULL,
  `DATE_MODIFIED` date DEFAULT NULL,
  `MODIFIED_BY` varchar(5) COLLATE utf8mb4_unicode_ci NOT NULL,
  `CREATED_BY` varchar(5) COLLATE utf8mb4_unicode_ci NOT NULL,
  `WEF_DT` date NOT NULL,
  `GRATUITY_TYPE` int NOT NULL,
  `TQS_START_YRS` int NOT NULL,
  `TQS_END_YRS` int NOT NULL,
  `MULTIPLE_FACTOR` decimal(14,4) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uniq_md_death_gratchart_key` (`TQS_START_YRS`,`WEF_DT`,`GRATUITY_TYPE`)
) ENGINE=InnoDB AUTO_INCREMENT=14 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

/*Table structure for table `fi_pn_md_jrnltype` */

DROP TABLE IF EXISTS `fi_pn_md_jrnltype`;

CREATE TABLE `fi_pn_md_jrnltype` (
  `DATE_CREATED` date DEFAULT NULL,
  `DATE_MODIFIED` date DEFAULT NULL,
  `MODIFIED_BY` varchar(5) COLLATE utf8mb4_unicode_ci NOT NULL,
  `CREATED_BY` varchar(5) COLLATE utf8mb4_unicode_ci NOT NULL,
  `id` bigint NOT NULL AUTO_INCREMENT,
  `JRNAL_SRL_NO` int NOT NULL,
  `ZONAL_CD` int NOT NULL,
  `DR_CR_FLG` varchar(1) COLLATE utf8mb4_unicode_ci NOT NULL,
  `ALOC_CD1` varchar(4) COLLATE utf8mb4_unicode_ci NOT NULL,
  `ALOC_CD2` varchar(4) COLLATE utf8mb4_unicode_ci NOT NULL,
  `ALOC_CD3` varchar(7) COLLATE utf8mb4_unicode_ci NOT NULL,
  `MAP_CD` varchar(15) COLLATE utf8mb4_unicode_ci NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uniq_pn_md_jrnltype_key` (`JRNAL_SRL_NO`,`ZONAL_CD`,`DR_CR_FLG`,`ALOC_CD1`,`ALOC_CD2`,`ALOC_CD3`),
  KEY `fi_pn_md_jrnltype_JRNAL_SRL_NO_4abb32bd` (`JRNAL_SRL_NO`)
) ENGINE=InnoDB AUTO_INCREMENT=83 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

/*Table structure for table `fi_pn_md_maxadm_gratuity` */

DROP TABLE IF EXISTS `fi_pn_md_maxadm_gratuity`;

CREATE TABLE `fi_pn_md_maxadm_gratuity` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `DATE_CREATED` date DEFAULT NULL,
  `DATE_MODIFIED` date DEFAULT NULL,
  `MODIFIED_BY` varchar(5) COLLATE utf8mb4_unicode_ci NOT NULL,
  `CREATED_BY` varchar(5) COLLATE utf8mb4_unicode_ci NOT NULL,
  `WEF_DT` date NOT NULL,
  `GRATUITY_TYPE` int NOT NULL,
  `RET_DT_FROM` date NOT NULL,
  `RET_DT_TO` date DEFAULT NULL,
  `MAX_EMOLUMENT` decimal(14,2) DEFAULT NULL,
  `MAX_ADM_GRATUITY` decimal(14,2) DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uniq_maxadm_gratuity_key` (`WEF_DT`,`GRATUITY_TYPE`,`RET_DT_FROM`)
) ENGINE=InnoDB AUTO_INCREMENT=13 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

/*Table structure for table `fi_pn_md_pension_proposal` */

DROP TABLE IF EXISTS `fi_pn_md_pension_proposal`;

CREATE TABLE `fi_pn_md_pension_proposal` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `ca_number` varchar(22) COLLATE utf8mb4_unicode_ci NOT NULL,
  `earndedn_cd` varchar(3) COLLATE utf8mb4_unicode_ci NOT NULL,
  `earn_dedn_type` varchar(1) COLLATE utf8mb4_unicode_ci NOT NULL,
  `amount` decimal(14,2) DEFAULT NULL,
  `e_d_priority` smallint unsigned DEFAULT NULL,
  `deducted_amt` decimal(14,2) DEFAULT NULL,
  `line_order` smallint unsigned NOT NULL,
  `date_created` date DEFAULT NULL,
  `created_by` varchar(5) COLLATE utf8mb4_unicode_ci NOT NULL,
  `date_modified` date DEFAULT NULL,
  `modified_by` varchar(5) COLLATE utf8mb4_unicode_ci NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uniq_ca_earndedn_cd_type` (`ca_number`,`earndedn_cd`,`earn_dedn_type`),
  KEY `fi_pn_md_pension_proposal_ca_number_00d81e08` (`ca_number`),
  CONSTRAINT `fi_pn_md_pension_proposal_chk_1` CHECK ((`e_d_priority` >= 0)),
  CONSTRAINT `fi_pn_md_pension_proposal_chk_2` CHECK ((`line_order` >= 0))
) ENGINE=InnoDB AUTO_INCREMENT=27521 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

/*Table structure for table `fi_pn_mh_ada_rate` */

DROP TABLE IF EXISTS `fi_pn_mh_ada_rate`;

CREATE TABLE `fi_pn_mh_ada_rate` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `DATE_CREATED` date DEFAULT NULL,
  `DATE_MODIFIED` date DEFAULT NULL,
  `MODIFIED_BY` varchar(5) COLLATE utf8mb4_unicode_ci NOT NULL,
  `CREATED_BY` varchar(5) COLLATE utf8mb4_unicode_ci NOT NULL,
  `EMP_TYPE` varchar(3) COLLATE utf8mb4_unicode_ci NOT NULL,
  `WEF_DT` date NOT NULL,
  `BASE_CPI_NO` int NOT NULL,
  `INDEX_PTS` decimal(14,4) DEFAULT NULL,
  `DA_PCT` decimal(14,4) DEFAULT NULL,
  `CPI_NO` decimal(14,4) DEFAULT NULL,
  `WET_DT` date DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uniq_ada_rate_key` (`WEF_DT`,`EMP_TYPE`,`BASE_CPI_NO`)
) ENGINE=InnoDB AUTO_INCREMENT=798 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

/*Table structure for table `fi_pn_mh_application` */

DROP TABLE IF EXISTS `fi_pn_mh_application`;

CREATE TABLE `fi_pn_mh_application` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `emp_cd` varchar(5) COLLATE utf8mb4_unicode_ci NOT NULL,
  `appcn_no` varchar(22) COLLATE utf8mb4_unicode_ci NOT NULL,
  `appcn_dt` date NOT NULL,
  `ref_no` varchar(22) COLLATE utf8mb4_unicode_ci NOT NULL,
  `pen_amt` decimal(14,2) DEFAULT NULL,
  `commutation_per` decimal(14,4) DEFAULT NULL,
  `sanction_particulars` varchar(500) COLLATE utf8mb4_unicode_ci NOT NULL,
  `commutation_reasons` varchar(500) COLLATE utf8mb4_unicode_ci NOT NULL,
  `prev_comm_particulars` varchar(500) COLLATE utf8mb4_unicode_ci NOT NULL,
  `avg_expected_life` varchar(240) COLLATE utf8mb4_unicode_ci NOT NULL,
  `date_created` date DEFAULT NULL,
  `created_by` varchar(5) COLLATE utf8mb4_unicode_ci NOT NULL,
  `date_modified` date DEFAULT NULL,
  `modified_by` varchar(5) COLLATE utf8mb4_unicode_ci NOT NULL,
  `comm_start_mnth` int DEFAULT NULL,
  `comm_start_yr` int DEFAULT NULL,
  `impl_bill_no` varchar(22) COLLATE utf8mb4_unicode_ci NOT NULL,
  `mo_certificate_ref` varchar(20) COLLATE utf8mb4_unicode_ci NOT NULL,
  `mo_certification_dt` date DEFAULT NULL,
  `application_rcvd_dt` date DEFAULT NULL,
  `commutation_date` date DEFAULT NULL,
  `commutation_amt` decimal(14,2) DEFAULT NULL,
  `impl_fpen_combill` varchar(3) COLLATE utf8mb4_unicode_ci NOT NULL,
  `bank_cd` varchar(6) COLLATE utf8mb4_unicode_ci NOT NULL,
  `ca_no` varchar(22) COLLATE utf8mb4_unicode_ci NOT NULL,
  `restoration_dt` date DEFAULT NULL,
  `restoration_flg` int DEFAULT NULL,
  `application_time` int DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uniq_pn_application_key` (`emp_cd`,`appcn_no`,`appcn_dt`),
  KEY `fi_pn_mh_application_emp_cd_ed73f65a` (`emp_cd`)
) ENGINE=InnoDB AUTO_INCREMENT=5686 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

/*Table structure for table `fi_pn_mh_base_cpi` */

DROP TABLE IF EXISTS `fi_pn_mh_base_cpi`;

CREATE TABLE `fi_pn_mh_base_cpi` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `DATE_CREATED` date DEFAULT NULL,
  `DATE_MODIFIED` date DEFAULT NULL,
  `MODIFIED_BY` varchar(5) COLLATE utf8mb4_unicode_ci NOT NULL,
  `CREATED_BY` varchar(5) COLLATE utf8mb4_unicode_ci NOT NULL,
  `EMP_TYPE` varchar(2) COLLATE utf8mb4_unicode_ci NOT NULL,
  `WEF_DT` date NOT NULL,
  `BASE_CPI` decimal(14,4) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uniq_base_cpi_key` (`EMP_TYPE`,`WEF_DT`)
) ENGINE=InnoDB AUTO_INCREMENT=3 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

/*Table structure for table `fi_pn_mh_death_gratchart` */

DROP TABLE IF EXISTS `fi_pn_mh_death_gratchart`;

CREATE TABLE `fi_pn_mh_death_gratchart` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `DATE_CREATED` date DEFAULT NULL,
  `DATE_MODIFIED` date DEFAULT NULL,
  `MODIFIED_BY` varchar(5) COLLATE utf8mb4_unicode_ci NOT NULL,
  `CREATED_BY` varchar(5) COLLATE utf8mb4_unicode_ci NOT NULL,
  `WEF_DT` date NOT NULL,
  `GRATUITY_TYPE` int NOT NULL,
  `INCEPTION_DT` date NOT NULL,
  `BEFORE_INCEPTION_MAX_LT` int NOT NULL,
  `AFTER_INCEPTION_MAX_LT` int NOT NULL,
  `CIRCULAR_REF_NO` varchar(22) COLLATE utf8mb4_unicode_ci NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uniq_mh_death_gratchart_key` (`WEF_DT`,`GRATUITY_TYPE`)
) ENGINE=InnoDB AUTO_INCREMENT=11 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

/*Table structure for table `fi_pn_mh_earndedn` */

DROP TABLE IF EXISTS `fi_pn_mh_earndedn`;

CREATE TABLE `fi_pn_mh_earndedn` (
  `EARNDEDN_CD` varchar(3) COLLATE utf8mb4_unicode_ci NOT NULL,
  `EARNDEDN_TYPE` varchar(1) COLLATE utf8mb4_unicode_ci NOT NULL,
  `EARNDEDN_DESC` varchar(100) COLLATE utf8mb4_unicode_ci NOT NULL,
  `DATE_CREATED` date DEFAULT NULL,
  `DATE_MODIFIED` date DEFAULT NULL,
  `MODIFIED_BY` varchar(5) COLLATE utf8mb4_unicode_ci NOT NULL,
  `CREATED_BY` varchar(5) COLLATE utf8mb4_unicode_ci NOT NULL,
  `ALLOC_CD` varchar(4) COLLATE utf8mb4_unicode_ci NOT NULL,
  `ZONAL_CD` int DEFAULT NULL,
  PRIMARY KEY (`EARNDEDN_CD`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

/*Table structure for table `fi_pn_mh_erndednmap` */

DROP TABLE IF EXISTS `fi_pn_mh_erndednmap`;

CREATE TABLE `fi_pn_mh_erndednmap` (
  `DATE_CREATED` date DEFAULT NULL,
  `DATE_MODIFIED` date DEFAULT NULL,
  `MODIFIED_BY` varchar(5) COLLATE utf8mb4_unicode_ci NOT NULL,
  `CREATED_BY` varchar(5) COLLATE utf8mb4_unicode_ci NOT NULL,
  `MAP_CD` int NOT NULL,
  `E_D_TYPE` varchar(1) COLLATE utf8mb4_unicode_ci NOT NULL,
  `MAP_DESC` varchar(50) COLLATE utf8mb4_unicode_ci NOT NULL,
  `EARNDEDN_CD` varchar(3) COLLATE utf8mb4_unicode_ci NOT NULL,
  `DEDN_PRIORITY` int DEFAULT NULL,
  PRIMARY KEY (`MAP_CD`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

/*Table structure for table `fi_pn_mh_jrnltype` */

DROP TABLE IF EXISTS `fi_pn_mh_jrnltype`;

CREATE TABLE `fi_pn_mh_jrnltype` (
  `DATE_CREATED` date DEFAULT NULL,
  `DATE_MODIFIED` date DEFAULT NULL,
  `MODIFIED_BY` varchar(5) COLLATE utf8mb4_unicode_ci NOT NULL,
  `CREATED_BY` varchar(5) COLLATE utf8mb4_unicode_ci NOT NULL,
  `JRNAL_SRL_NO` int NOT NULL,
  `TYPE` varchar(6) COLLATE utf8mb4_unicode_ci NOT NULL,
  `JRNAL_DESC` varchar(30) COLLATE utf8mb4_unicode_ci NOT NULL,
  PRIMARY KEY (`JRNAL_SRL_NO`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

/*Table structure for table `fi_pn_mh_oldbill_param` */

DROP TABLE IF EXISTS `fi_pn_mh_oldbill_param`;

CREATE TABLE `fi_pn_mh_oldbill_param` (
  `emp_cd` varchar(5) COLLATE utf8mb4_unicode_ci NOT NULL,
  `appointment_dt` date DEFAULT NULL,
  `retirement_dt` date DEFAULT NULL,
  `boy_serv_days` int DEFAULT NULL,
  `birth_dt` date DEFAULT NULL,
  `dnon_days` int DEFAULT NULL,
  `edn_lv_days` int DEFAULT NULL,
  `npay_prior_10mth` int DEFAULT NULL,
  `susp_days` int DEFAULT NULL,
  `npay_morethan_240_dys` int DEFAULT NULL,
  PRIMARY KEY (`emp_cd`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

/*Table structure for table `fi_pn_mh_pension_proposal` */

DROP TABLE IF EXISTS `fi_pn_mh_pension_proposal`;

CREATE TABLE `fi_pn_mh_pension_proposal` (
  `ca_number` varchar(22) COLLATE utf8mb4_unicode_ci NOT NULL,
  `emp_cd` varchar(5) COLLATE utf8mb4_unicode_ci NOT NULL,
  `pension_type` varchar(1) COLLATE utf8mb4_unicode_ci NOT NULL,
  `pension_proposal_no` varchar(30) COLLATE utf8mb4_unicode_ci NOT NULL,
  `pension_proposal_dt` date NOT NULL,
  `impl_month` int DEFAULT NULL,
  `impl_yr` int DEFAULT NULL,
  `start_month` int DEFAULT NULL,
  `start_yr` int DEFAULT NULL,
  `employee_status` varchar(1) COLLATE utf8mb4_unicode_ci NOT NULL,
  `vigilance_clearance_tag` varchar(1) COLLATE utf8mb4_unicode_ci NOT NULL,
  `vigilance_clearance_ref_no` varchar(22) COLLATE utf8mb4_unicode_ci NOT NULL,
  `vigilance_clearance_ref_dt` date DEFAULT NULL,
  `prov_pen_percentage` decimal(14,4) DEFAULT NULL,
  `quarter_status` varchar(1) COLLATE utf8mb4_unicode_ci NOT NULL,
  `pension_option` varchar(1) COLLATE utf8mb4_unicode_ci NOT NULL,
  `pension_roll_no` varchar(22) COLLATE utf8mb4_unicode_ci NOT NULL,
  `id_card_submitted` varchar(1) COLLATE utf8mb4_unicode_ci NOT NULL,
  `port_city_resident` varchar(1) COLLATE utf8mb4_unicode_ci NOT NULL,
  `separation_type` varchar(3) COLLATE utf8mb4_unicode_ci NOT NULL,
  `separation_dt` date NOT NULL,
  `date_created` date DEFAULT NULL,
  `created_by` varchar(5) COLLATE utf8mb4_unicode_ci NOT NULL,
  `date_modified` date DEFAULT NULL,
  `modified_by` varchar(5) COLLATE utf8mb4_unicode_ci NOT NULL,
  `comp_allowance_check_tag` int DEFAULT NULL,
  `comp_allowance` decimal(14,2) DEFAULT NULL,
  `gratuity_option` int DEFAULT NULL,
  `bank_cd` varchar(6) COLLATE utf8mb4_unicode_ci NOT NULL,
  `double_fpen_eligibility` int DEFAULT NULL,
  `double_fpen_upto` date DEFAULT NULL,
  `base_cpi` decimal(14,4) DEFAULT NULL,
  `extra_grat_tccs_flg` varchar(1) COLLATE utf8mb4_unicode_ci NOT NULL,
  `extra_grat_tccs_days` int DEFAULT NULL,
  `extra_grat_tccs_mon` int DEFAULT NULL,
  `extra_grat_tccs_yr` int DEFAULT NULL,
  `incentive_holder_flg` varchar(1) COLLATE utf8mb4_unicode_ci NOT NULL,
  `held_grat_flg` varchar(1) COLLATE utf8mb4_unicode_ci NOT NULL,
  `held_grat_amt` decimal(14,2) DEFAULT NULL,
  `lic_bank_cd` varchar(6) COLLATE utf8mb4_unicode_ci NOT NULL,
  `regn_no` varchar(22) COLLATE utf8mb4_unicode_ci NOT NULL,
  `regn_date` date DEFAULT NULL,
  `account_no` varchar(20) COLLATE utf8mb4_unicode_ci NOT NULL,
  `opt_given_by` varchar(1) COLLATE utf8mb4_unicode_ci NOT NULL,
  `nomin_eform_grat_flg` varchar(1) COLLATE utf8mb4_unicode_ci NOT NULL,
  `vr_ref_no` varchar(30) COLLATE utf8mb4_unicode_ci NOT NULL,
  `vr_ref_dt` date DEFAULT NULL,
  `letter_no` varchar(15) COLLATE utf8mb4_unicode_ci NOT NULL,
  `acepted_dt` date DEFAULT NULL,
  `dcr_type` varchar(10) COLLATE utf8mb4_unicode_ci NOT NULL,
  `held_commu_amt` decimal(14,2) DEFAULT NULL,
  PRIMARY KEY (`ca_number`),
  KEY `fi_pn_mh_pension_proposal_emp_cd_1dc00b72` (`emp_cd`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

/*Table structure for table `fi_pn_mh_pensioner` */

DROP TABLE IF EXISTS `fi_pn_mh_pensioner`;

CREATE TABLE `fi_pn_mh_pensioner` (
  `ca_number` varchar(22) COLLATE utf8mb4_unicode_ci NOT NULL,
  `emp_cd` varchar(5) COLLATE utf8mb4_unicode_ci NOT NULL,
  `original_pension_amt` decimal(14,2) DEFAULT NULL,
  `effective_stdt_pension` date DEFAULT NULL,
  `commuted_portion` decimal(14,2) DEFAULT NULL,
  `payable_pension` decimal(14,2) DEFAULT NULL,
  `gratuity` decimal(14,2) DEFAULT NULL,
  `commutation_per` decimal(7,2) DEFAULT NULL,
  `relief` decimal(14,2) DEFAULT NULL,
  `pension_emoluments` decimal(14,2) DEFAULT NULL,
  `gratuity_emoluments` decimal(14,2) DEFAULT NULL,
  `tccs_yr` int DEFAULT NULL,
  `tccs_month` int DEFAULT NULL,
  `tccs_days` int DEFAULT NULL,
  `tqs_yr` int DEFAULT NULL,
  `tqs_month` int DEFAULT NULL,
  `tqs_days` int DEFAULT NULL,
  `name` varchar(62) COLLATE utf8mb4_unicode_ci NOT NULL,
  `pension_option` varchar(1) COLLATE utf8mb4_unicode_ci NOT NULL,
  `base_cpi` decimal(14,4) DEFAULT NULL,
  `bank_cd` varchar(6) COLLATE utf8mb4_unicode_ci NOT NULL,
  `lic_bank_cd` varchar(6) COLLATE utf8mb4_unicode_ci NOT NULL,
  `account_no` varchar(20) COLLATE utf8mb4_unicode_ci NOT NULL,
  `pension_roll_no` varchar(22) COLLATE utf8mb4_unicode_ci NOT NULL,
  `sex` varchar(1) COLLATE utf8mb4_unicode_ci NOT NULL,
  `dob` date DEFAULT NULL,
  `desig_cd` int DEFAULT NULL,
  `emp_ret_dt` date DEFAULT NULL,
  `app_class` int DEFAULT NULL,
  `date_commutation` date DEFAULT NULL,
  `date_created` date DEFAULT NULL,
  `created_by` varchar(5) COLLATE utf8mb4_unicode_ci NOT NULL,
  `date_modified` date DEFAULT NULL,
  `modified_by` varchar(5) COLLATE utf8mb4_unicode_ci NOT NULL,
  PRIMARY KEY (`ca_number`),
  KEY `fi_pn_mh_pensioner_emp_cd_94055150` (`emp_cd`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

/*Table structure for table `fi_pn_mh_pmthsetup` */

DROP TABLE IF EXISTS `fi_pn_mh_pmthsetup`;

CREATE TABLE `fi_pn_mh_pmthsetup` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `bill_type` varchar(3) COLLATE utf8mb4_unicode_ci NOT NULL,
  `bill_mth` int NOT NULL,
  `bill_yr` int NOT NULL,
  `bill_process_flg` int NOT NULL,
  `bill_close_flg` int NOT NULL,
  `date_created` date DEFAULT NULL,
  `created_by` varchar(5) COLLATE utf8mb4_unicode_ci NOT NULL,
  `date_modified` date DEFAULT NULL,
  `modified_by` varchar(5) COLLATE utf8mb4_unicode_ci NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uniq_pmthsetup_key` (`bill_type`,`bill_mth`,`bill_yr`)
) ENGINE=InnoDB AUTO_INCREMENT=14 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

/*Table structure for table `fi_pn_mh_service_gratchart` */

DROP TABLE IF EXISTS `fi_pn_mh_service_gratchart`;

CREATE TABLE `fi_pn_mh_service_gratchart` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `DATE_CREATED` date DEFAULT NULL,
  `DATE_MODIFIED` date DEFAULT NULL,
  `MODIFIED_BY` varchar(5) COLLATE utf8mb4_unicode_ci NOT NULL,
  `CREATED_BY` varchar(5) COLLATE utf8mb4_unicode_ci NOT NULL,
  `WEF_DT` date NOT NULL,
  `INTERVAL_SRL` int NOT NULL,
  `DURATION_MONTH` int NOT NULL,
  `BASE_DOC` varchar(15) COLLATE utf8mb4_unicode_ci NOT NULL,
  `NUMERATOR_AMT` decimal(14,4) DEFAULT NULL,
  `DENOMINATOR_AMT` decimal(14,4) DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uniq_service_gratchart_key` (`WEF_DT`,`INTERVAL_SRL`)
) ENGINE=InnoDB AUTO_INCREMENT=20 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

/*Table structure for table `fi_pn_td_first_month_pension` */

DROP TABLE IF EXISTS `fi_pn_td_first_month_pension`;

CREATE TABLE `fi_pn_td_first_month_pension` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `fmpen_id` varchar(22) COLLATE utf8mb4_unicode_ci NOT NULL,
  `earn_dedn_type` varchar(1) COLLATE utf8mb4_unicode_ci NOT NULL,
  `earn_dedn_cd` varchar(3) COLLATE utf8mb4_unicode_ci NOT NULL,
  `amount` decimal(14,2) DEFAULT NULL,
  `emp_cd` varchar(5) COLLATE utf8mb4_unicode_ci NOT NULL,
  `original_amt` decimal(14,2) DEFAULT NULL,
  `arrear_amt` decimal(14,2) DEFAULT NULL,
  `date_created` date DEFAULT NULL,
  `created_by` varchar(5) COLLATE utf8mb4_unicode_ci NOT NULL,
  `date_modified` date DEFAULT NULL,
  `modified_by` varchar(5) COLLATE utf8mb4_unicode_ci NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uniq_fmpen_earndedn_type` (`fmpen_id`,`earn_dedn_cd`,`earn_dedn_type`),
  KEY `fi_pn_td_first_month_pension_fmpen_id_b9a060b1` (`fmpen_id`),
  KEY `fi_pn_td_first_month_pension_emp_cd_83699ed9` (`emp_cd`)
) ENGINE=InnoDB AUTO_INCREMENT=55 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

/*Table structure for table `fi_pn_td_jv` */

DROP TABLE IF EXISTS `fi_pn_td_jv`;

CREATE TABLE `fi_pn_td_jv` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `voucher_no` varchar(25) COLLATE utf8mb4_unicode_ci NOT NULL,
  `voucher_dt` date NOT NULL,
  `yr` int NOT NULL,
  `mth` int NOT NULL,
  `sl_no` int NOT NULL,
  `zonal_cd` int NOT NULL,
  `aloc_cd1` varchar(4) COLLATE utf8mb4_unicode_ci NOT NULL,
  `aloc_cd2` varchar(4) COLLATE utf8mb4_unicode_ci NOT NULL,
  `aloc_cd3` varchar(7) COLLATE utf8mb4_unicode_ci NOT NULL,
  `dr_cr_flag` varchar(1) COLLATE utf8mb4_unicode_ci NOT NULL,
  `type_cd` int NOT NULL,
  `amount` decimal(14,2) NOT NULL,
  `ref` varchar(25) COLLATE utf8mb4_unicode_ci NOT NULL,
  `remarks` varchar(60) COLLATE utf8mb4_unicode_ci NOT NULL,
  `created_by` varchar(5) COLLATE utf8mb4_unicode_ci NOT NULL,
  `created_on` date DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uniq_pn_td_jv_line` (`voucher_no`,`sl_no`),
  KEY `fi_pn_td_jv_voucher_no_4b5a4223` (`voucher_no`)
) ENGINE=InnoDB AUTO_INCREMENT=30 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

/*Table structure for table `fi_pn_td_salout` */

DROP TABLE IF EXISTS `fi_pn_td_salout`;

CREATE TABLE `fi_pn_td_salout` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `emp_cd` varchar(5) COLLATE utf8mb4_unicode_ci NOT NULL,
  `sal_mth` int NOT NULL,
  `sal_yr` int NOT NULL,
  `earndedn_cd` varchar(3) COLLATE utf8mb4_unicode_ci NOT NULL,
  `earndedn_type` varchar(1) COLLATE utf8mb4_unicode_ci NOT NULL,
  `no_of_units` decimal(14,4) DEFAULT NULL,
  `rate` decimal(14,4) DEFAULT NULL,
  `rate_pct_flg` int DEFAULT NULL,
  `act_earndedn_amt` decimal(14,2) DEFAULT NULL,
  `adj_earndedn_amt` decimal(14,2) DEFAULT NULL,
  `arr_earn_amt` decimal(14,2) DEFAULT NULL,
  `date_created` date DEFAULT NULL,
  `date_modified` date DEFAULT NULL,
  `modified_by` varchar(5) COLLATE utf8mb4_unicode_ci NOT NULL,
  `created_by` varchar(5) COLLATE utf8mb4_unicode_ci NOT NULL,
  `spl_pay` decimal(14,2) DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uniq_pn_td_salout_key` (`emp_cd`,`sal_mth`,`sal_yr`,`earndedn_cd`),
  KEY `fi_pn_td_sa_emp_cd_0736fd_idx` (`emp_cd`,`sal_yr`,`sal_mth`),
  KEY `fi_pn_td_salout_emp_cd_eb49a069` (`emp_cd`)
) ENGINE=InnoDB AUTO_INCREMENT=65485 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

/*Table structure for table `fi_pn_td_sepcom` */

DROP TABLE IF EXISTS `fi_pn_td_sepcom`;

CREATE TABLE `fi_pn_td_sepcom` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `earn_dedn_type` varchar(1) COLLATE utf8mb4_unicode_ci NOT NULL,
  `earn_dedn_cd` varchar(3) COLLATE utf8mb4_unicode_ci NOT NULL,
  `amount` decimal(14,2) NOT NULL,
  `date_created` date DEFAULT NULL,
  `created_by` varchar(5) COLLATE utf8mb4_unicode_ci NOT NULL,
  `date_modified` date DEFAULT NULL,
  `modified_by` varchar(5) COLLATE utf8mb4_unicode_ci NOT NULL,
  `sepcom_id` varchar(22) COLLATE utf8mb4_unicode_ci NOT NULL,
  `emp_cd` varchar(5) COLLATE utf8mb4_unicode_ci NOT NULL,
  `original_amt` decimal(14,2) DEFAULT NULL,
  `arrear_amt` decimal(14,2) DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `fi_pn_td_sepcom_sepcom_id_3019f810` (`sepcom_id`),
  KEY `fi_pn_td_sepcom_emp_cd_05636cf0` (`emp_cd`)
) ENGINE=InnoDB AUTO_INCREMENT=2 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

/*Table structure for table `fi_pn_th_first_month_pension` */

DROP TABLE IF EXISTS `fi_pn_th_first_month_pension`;

CREATE TABLE `fi_pn_th_first_month_pension` (
  `fmpen_id` varchar(22) COLLATE utf8mb4_unicode_ci NOT NULL,
  `pension_type` varchar(3) COLLATE utf8mb4_unicode_ci NOT NULL,
  `pension_month` int NOT NULL,
  `pension_yr` int NOT NULL,
  `ca_no` varchar(22) COLLATE utf8mb4_unicode_ci NOT NULL,
  `ca_date` date DEFAULT NULL,
  `original_fpension_amt` decimal(14,2) DEFAULT NULL,
  `payable_pension` decimal(14,2) DEFAULT NULL,
  `date_of_execution` date DEFAULT NULL,
  `bill_no` varchar(22) COLLATE utf8mb4_unicode_ci NOT NULL,
  `paid_month` int DEFAULT NULL,
  `paid_year` int DEFAULT NULL,
  `date_created` date DEFAULT NULL,
  `created_by` varchar(5) COLLATE utf8mb4_unicode_ci NOT NULL,
  `date_modified` date DEFAULT NULL,
  `modified_by` varchar(5) COLLATE utf8mb4_unicode_ci NOT NULL,
  `emp_cd` varchar(5) COLLATE utf8mb4_unicode_ci NOT NULL,
  `bank_cd` varchar(6) COLLATE utf8mb4_unicode_ci NOT NULL,
  `sys_man_tag` varchar(1) COLLATE utf8mb4_unicode_ci NOT NULL,
  `cpi_no` decimal(14,4) DEFAULT NULL,
  `nomin_type` varchar(2) COLLATE utf8mb4_unicode_ci NOT NULL,
  `pen_proc_tag` varchar(1) COLLATE utf8mb4_unicode_ci NOT NULL,
  `nomin_srl_no` int DEFAULT NULL,
  `base_cpi` decimal(14,4) DEFAULT NULL,
  `payment_tag` varchar(2) COLLATE utf8mb4_unicode_ci NOT NULL,
  `lic_bank_cd` varchar(6) COLLATE utf8mb4_unicode_ci NOT NULL,
  PRIMARY KEY (`fmpen_id`),
  KEY `fi_pn_th_first_month_pension_ca_no_0ef45336` (`ca_no`),
  KEY `fi_pn_th_first_month_pension_emp_cd_75fa50aa` (`emp_cd`),
  KEY `fi_pn_th_fi_emp_cd_0e2c2e_idx` (`emp_cd`,`pension_yr`,`pension_month`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

/*Table structure for table `fi_pn_th_jv` */

DROP TABLE IF EXISTS `fi_pn_th_jv`;

CREATE TABLE `fi_pn_th_jv` (
  `voucher_no` varchar(25) COLLATE utf8mb4_unicode_ci NOT NULL,
  `yr` int NOT NULL,
  `mth` int NOT NULL,
  `voucher_dt` date NOT NULL,
  `tran_type` varchar(10) COLLATE utf8mb4_unicode_ci NOT NULL,
  `ref_no` varchar(25) COLLATE utf8mb4_unicode_ci NOT NULL,
  `ref_dt` date DEFAULT NULL,
  `narration` varchar(500) COLLATE utf8mb4_unicode_ci NOT NULL,
  `tot_amt` decimal(14,2) DEFAULT NULL,
  `created_by` varchar(5) COLLATE utf8mb4_unicode_ci NOT NULL,
  `created_on` date DEFAULT NULL,
  `voucher_for` varchar(1) COLLATE utf8mb4_unicode_ci NOT NULL,
  PRIMARY KEY (`voucher_no`),
  KEY `fi_pn_th_jv_ref_no_fc4e2942` (`ref_no`),
  KEY `fi_pn_th_jv_yr_8e8695_idx` (`yr`,`mth`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

/*Table structure for table `fi_pn_th_pension_bill` */

DROP TABLE IF EXISTS `fi_pn_th_pension_bill`;

CREATE TABLE `fi_pn_th_pension_bill` (
  `bill_no` varchar(22) COLLATE utf8mb4_unicode_ci NOT NULL,
  `bill_type` varchar(3) COLLATE utf8mb4_unicode_ci NOT NULL,
  `bill_month` int NOT NULL,
  `bill_yr` int NOT NULL,
  `bank_cd` varchar(6) COLLATE utf8mb4_unicode_ci NOT NULL,
  `total_amt_earned` decimal(14,2) DEFAULT NULL,
  `total_amt_deducted` decimal(14,2) DEFAULT NULL,
  `bill_abstract_no` varchar(22) COLLATE utf8mb4_unicode_ci NOT NULL,
  `abstract_type` varchar(2) COLLATE utf8mb4_unicode_ci NOT NULL,
  `cheque_no` int DEFAULT NULL,
  `cheque_dt` date DEFAULT NULL,
  `cheque_amt` decimal(14,2) DEFAULT NULL,
  `date_created` date DEFAULT NULL,
  `created_by` varchar(5) COLLATE utf8mb4_unicode_ci NOT NULL,
  `date_modified` date DEFAULT NULL,
  `modified_by` varchar(5) COLLATE utf8mb4_unicode_ci NOT NULL,
  `remarks` varchar(100) COLLATE utf8mb4_unicode_ci NOT NULL,
  `voucher_no` varchar(25) COLLATE utf8mb4_unicode_ci NOT NULL,
  `abstract_date` date DEFAULT NULL,
  `gen_lic_tag` varchar(1) COLLATE utf8mb4_unicode_ci NOT NULL,
  `posted` varchar(1) COLLATE utf8mb4_unicode_ci NOT NULL,
  `posted_on` date DEFAULT NULL,
  `posted_by` varchar(5) COLLATE utf8mb4_unicode_ci NOT NULL,
  PRIMARY KEY (`bill_no`),
  KEY `fi_pn_th_pe_bill_yr_1edf39_idx` (`bill_yr`,`bill_month`,`bill_type`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

/*Table structure for table `fi_pn_th_salout` */

DROP TABLE IF EXISTS `fi_pn_th_salout`;

CREATE TABLE `fi_pn_th_salout` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `emp_cd` varchar(5) COLLATE utf8mb4_unicode_ci NOT NULL,
  `sal_mth` int NOT NULL,
  `sal_yr` int NOT NULL,
  `fa_no` varchar(10) COLLATE utf8mb4_unicode_ci NOT NULL,
  `sal_bill_no` varchar(22) COLLATE utf8mb4_unicode_ci NOT NULL,
  `gross_earn_amt` decimal(14,2) DEFAULT NULL,
  `gross_dedn_amt` decimal(14,2) DEFAULT NULL,
  `net_earn_amt` decimal(14,2) DEFAULT NULL,
  `scale_desc` varchar(100) COLLATE utf8mb4_unicode_ci NOT NULL,
  `basic_rate` decimal(14,2) DEFAULT NULL,
  `wg_st_dt` date DEFAULT NULL,
  `wg_end_dt` date DEFAULT NULL,
  `date_created` date DEFAULT NULL,
  `date_modified` date DEFAULT NULL,
  `modified_by` varchar(5) COLLATE utf8mb4_unicode_ci NOT NULL,
  `created_by` varchar(5) COLLATE utf8mb4_unicode_ci NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uniq_pn_th_salout_key` (`emp_cd`,`sal_mth`,`sal_yr`),
  KEY `fi_pn_th_salout_emp_cd_7f7d8ac6` (`emp_cd`),
  KEY `fi_pn_th_sa_emp_cd_b467a9_idx` (`emp_cd`,`sal_yr`,`sal_mth`)
) ENGINE=InnoDB AUTO_INCREMENT=64 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

/*Table structure for table `fi_pn_th_sepcom` */

DROP TABLE IF EXISTS `fi_pn_th_sepcom`;

CREATE TABLE `fi_pn_th_sepcom` (
  `sepcom_id` varchar(22) COLLATE utf8mb4_unicode_ci NOT NULL,
  `sepcom_month` int NOT NULL,
  `sepcom_yr` int NOT NULL,
  `ca_no` varchar(22) COLLATE utf8mb4_unicode_ci NOT NULL,
  `original_com_amt` decimal(14,2) DEFAULT NULL,
  `bill_no` varchar(22) COLLATE utf8mb4_unicode_ci NOT NULL,
  `paid_month` int DEFAULT NULL,
  `paid_year` int DEFAULT NULL,
  `emp_cd` varchar(5) COLLATE utf8mb4_unicode_ci NOT NULL,
  `nomin_type` varchar(2) COLLATE utf8mb4_unicode_ci NOT NULL,
  `com_proc_tag` varchar(1) COLLATE utf8mb4_unicode_ci NOT NULL,
  `nomin_srl_no` int NOT NULL,
  `date_created` date DEFAULT NULL,
  `created_by` varchar(5) COLLATE utf8mb4_unicode_ci NOT NULL,
  `date_modified` date DEFAULT NULL,
  `modified_by` varchar(5) COLLATE utf8mb4_unicode_ci NOT NULL,
  `bank_cd` varchar(6) COLLATE utf8mb4_unicode_ci NOT NULL,
  `pen_dedn_amt` decimal(14,2) DEFAULT NULL,
  `appcn_no` varchar(22) COLLATE utf8mb4_unicode_ci NOT NULL,
  `appcn_dt` date DEFAULT NULL,
  PRIMARY KEY (`sepcom_id`),
  KEY `fi_pn_th_sepcom_emp_cd_778a1901` (`emp_cd`),
  KEY `fi_pn_th_se_emp_cd_5744e3_idx` (`emp_cd`,`sepcom_yr`,`sepcom_month`),
  KEY `fi_pn_th_se_bill_no_962362_idx` (`bill_no`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

/*Table structure for table `fi_pr_mh_ada_rate_vw` */

DROP TABLE IF EXISTS `fi_pr_mh_ada_rate_vw`;

CREATE TABLE `fi_pr_mh_ada_rate_vw` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `wef_dt` date NOT NULL,
  `emp_type` varchar(2) COLLATE utf8mb4_unicode_ci NOT NULL,
  `emp_class_grp` int NOT NULL,
  `da_pct` decimal(10,4) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uniq_ada_rate_wef_type_grp` (`wef_dt`,`emp_type`,`emp_class_grp`)
) ENGINE=InnoDB AUTO_INCREMENT=78 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

/*Table structure for table `fi_pr_mh_erndednmap` */

DROP TABLE IF EXISTS `fi_pr_mh_erndednmap`;

CREATE TABLE `fi_pr_mh_erndednmap` (
  `DATE_CREATED` date DEFAULT NULL,
  `DATE_MODIFIED` date DEFAULT NULL,
  `MODIFIED_BY` varchar(5) COLLATE utf8mb4_unicode_ci NOT NULL,
  `CREATED_BY` varchar(5) COLLATE utf8mb4_unicode_ci NOT NULL,
  `MAP_CD` int NOT NULL,
  `GROUP_TYPE` varchar(1) COLLATE utf8mb4_unicode_ci NOT NULL,
  `MAP_DESC` varchar(50) COLLATE utf8mb4_unicode_ci NOT NULL,
  `EARNDEDN_CD` varchar(3) COLLATE utf8mb4_unicode_ci NOT NULL,
  `DEDN_PRIORITY` int DEFAULT NULL,
  PRIMARY KEY (`MAP_CD`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

/*Table structure for table `fi_pr_td_salout` */

DROP TABLE IF EXISTS `fi_pr_td_salout`;

CREATE TABLE `fi_pr_td_salout` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `emp_cd` varchar(5) COLLATE utf8mb4_unicode_ci NOT NULL,
  `sal_mth` int NOT NULL,
  `sal_yr` int NOT NULL,
  `earndedn_cd` varchar(3) COLLATE utf8mb4_unicode_ci NOT NULL,
  `earndedn_type` varchar(1) COLLATE utf8mb4_unicode_ci NOT NULL,
  `no_of_units` decimal(14,4) DEFAULT NULL,
  `rate` decimal(14,4) DEFAULT NULL,
  `rate_pct_flg` int DEFAULT NULL,
  `act_earndedn_amt` decimal(14,2) DEFAULT NULL,
  `adj_earndedn_amt` decimal(14,2) DEFAULT NULL,
  `arr_earn_amt` decimal(14,2) DEFAULT NULL,
  `notional_amount` decimal(14,2) DEFAULT NULL,
  `date_created` date DEFAULT NULL,
  `date_modified` date DEFAULT NULL,
  `modified_by` varchar(5) COLLATE utf8mb4_unicode_ci NOT NULL,
  `created_by` varchar(5) COLLATE utf8mb4_unicode_ci NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uniq_pr_td_salout_key` (`emp_cd`,`sal_mth`,`sal_yr`,`earndedn_cd`),
  KEY `fi_pr_td_salout_emp_cd_412af77d` (`emp_cd`),
  KEY `fi_pr_td_sa_emp_cd_52b82d_idx` (`emp_cd`,`sal_yr`,`sal_mth`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

/*Table structure for table `fi_pr_th_salout` */

DROP TABLE IF EXISTS `fi_pr_th_salout`;

CREATE TABLE `fi_pr_th_salout` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `emp_cd` varchar(5) COLLATE utf8mb4_unicode_ci NOT NULL,
  `sal_mth` int NOT NULL,
  `sal_yr` int NOT NULL,
  `fa_no` varchar(5) COLLATE utf8mb4_unicode_ci NOT NULL,
  `sal_bill_no` varchar(20) COLLATE utf8mb4_unicode_ci NOT NULL,
  `gross_earn_amt` decimal(14,2) DEFAULT NULL,
  `gross_dedn_amt` decimal(14,2) DEFAULT NULL,
  `net_earn_amt` decimal(14,2) DEFAULT NULL,
  `scale_desc` varchar(40) COLLATE utf8mb4_unicode_ci NOT NULL,
  `basic_rate` decimal(14,2) DEFAULT NULL,
  `wg_st_dt` date DEFAULT NULL,
  `wg_end_dt` date DEFAULT NULL,
  `date_created` date DEFAULT NULL,
  `date_modified` date DEFAULT NULL,
  `modified_by` varchar(5) COLLATE utf8mb4_unicode_ci NOT NULL,
  `created_by` varchar(5) COLLATE utf8mb4_unicode_ci NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uniq_pr_th_salout_key` (`emp_cd`,`sal_mth`,`sal_yr`),
  KEY `fi_pr_th_salout_emp_cd_907d761a` (`emp_cd`),
  KEY `fi_pr_th_sa_emp_cd_c19652_idx` (`emp_cd`,`sal_yr`,`sal_mth`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

/*Table structure for table `fi_xx_md_finscale` */

DROP TABLE IF EXISTS `fi_xx_md_finscale`;

CREATE TABLE `fi_xx_md_finscale` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `emp_cd` varchar(5) COLLATE utf8mb4_unicode_ci NOT NULL,
  `scale_sl` varchar(14) COLLATE utf8mb4_unicode_ci NOT NULL,
  `wef_dt` date NOT NULL,
  `sl_no` int NOT NULL,
  `date_created` date DEFAULT NULL,
  `date_modified` date DEFAULT NULL,
  `modified_by` varchar(30) COLLATE utf8mb4_unicode_ci NOT NULL,
  `created_by` varchar(30) COLLATE utf8mb4_unicode_ci NOT NULL,
  `history_flg` int DEFAULT NULL,
  `basic_amt` decimal(14,2) DEFAULT NULL,
  `stag_pay_amt` decimal(14,2) DEFAULT NULL,
  `ref_no` varchar(10) COLLATE utf8mb4_unicode_ci NOT NULL,
  `tran_flg` varchar(1) COLLATE utf8mb4_unicode_ci NOT NULL,
  `active_rec` varchar(1) COLLATE utf8mb4_unicode_ci NOT NULL,
  `remarks` varchar(500) COLLATE utf8mb4_unicode_ci NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uniq_xx_md_finscale_key` (`emp_cd`,`wef_dt`,`sl_no`),
  KEY `fi_xx_md_finscale_emp_cd_955a0722` (`emp_cd`),
  KEY `fi_xx_md_fi_emp_cd_edb1b2_idx` (`emp_cd`,`wef_dt`)
) ENGINE=InnoDB AUTO_INCREMENT=152250 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

/*Table structure for table `fi_xx_mh_dept` */

DROP TABLE IF EXISTS `fi_xx_mh_dept`;

CREATE TABLE `fi_xx_mh_dept` (
  `DEPT_CD` varchar(2) COLLATE utf8mb4_unicode_ci NOT NULL,
  `dept_desc` varchar(100) COLLATE utf8mb4_unicode_ci NOT NULL,
  `dept_short_desc` varchar(7) COLLATE utf8mb4_unicode_ci NOT NULL,
  `date_created` date DEFAULT NULL,
  `date_modified` date DEFAULT NULL,
  `created_by` varchar(5) COLLATE utf8mb4_unicode_ci NOT NULL,
  `modified_by` varchar(5) COLLATE utf8mb4_unicode_ci NOT NULL,
  PRIMARY KEY (`DEPT_CD`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

/*Table structure for table `fi_xx_mh_desig` */

DROP TABLE IF EXISTS `fi_xx_mh_desig`;

CREATE TABLE `fi_xx_mh_desig` (
  `DATE_CREATED` date DEFAULT NULL,
  `DATE_MODIFIED` date DEFAULT NULL,
  `MODIFIED_BY` varchar(5) COLLATE utf8mb4_unicode_ci NOT NULL,
  `CREATED_BY` varchar(5) COLLATE utf8mb4_unicode_ci NOT NULL,
  `DESIG_CD` int NOT NULL,
  `DESIG_DESC` varchar(60) COLLATE utf8mb4_unicode_ci NOT NULL,
  `ACTIVE_FLG` int NOT NULL,
  PRIMARY KEY (`DESIG_CD`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

/*Table structure for table `fi_xx_mh_emp_adm` */

DROP TABLE IF EXISTS `fi_xx_mh_emp_adm`;

CREATE TABLE `fi_xx_mh_emp_adm` (
  `emp_cd` varchar(5) COLLATE utf8mb4_unicode_ci NOT NULL,
  `mo_cert_ref` varchar(30) COLLATE utf8mb4_unicode_ci NOT NULL,
  `join_dt` date DEFAULT NULL,
  `emp_origin_tag` varchar(1) COLLATE utf8mb4_unicode_ci NOT NULL,
  `confirm_dt` date DEFAULT NULL,
  `app_quota` varchar(3) COLLATE utf8mb4_unicode_ci NOT NULL,
  `separation_type` varchar(3) COLLATE utf8mb4_unicode_ci NOT NULL,
  `separation_dt` date DEFAULT NULL,
  `termin_remark` varchar(800) COLLATE utf8mb4_unicode_ci NOT NULL,
  `exp_ret_dt` date DEFAULT NULL,
  `pf_type` varchar(1) COLLATE utf8mb4_unicode_ci NOT NULL,
  `hindi_flg` int DEFAULT NULL,
  `dlypaid_years` int DEFAULT NULL,
  `date_created` date DEFAULT NULL,
  `date_modified` date DEFAULT NULL,
  `modified_by` varchar(5) COLLATE utf8mb4_unicode_ci NOT NULL,
  `created_by` varchar(5) COLLATE utf8mb4_unicode_ci NOT NULL,
  `vig_cert_no` varchar(20) COLLATE utf8mb4_unicode_ci NOT NULL,
  `vig_cert_dt` date DEFAULT NULL,
  `order_no` varchar(20) COLLATE utf8mb4_unicode_ci NOT NULL,
  `order_dt` date DEFAULT NULL,
  `order_issued_by` varchar(20) COLLATE utf8mb4_unicode_ci NOT NULL,
  `desig_cd` int DEFAULT NULL,
  `union_cd` int DEFAULT NULL,
  `mc_reg_no` varchar(5) COLLATE utf8mb4_unicode_ci NOT NULL,
  `mc_reg_dt` date DEFAULT NULL,
  `known_flg` int DEFAULT NULL,
  `known_details` varchar(100) COLLATE utf8mb4_unicode_ci NOT NULL,
  `pan_no` varchar(10) COLLATE utf8mb4_unicode_ci NOT NULL,
  PRIMARY KEY (`emp_cd`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

/*Table structure for table `fi_xx_mh_emp_data` */

DROP TABLE IF EXISTS `fi_xx_mh_emp_data`;

CREATE TABLE `fi_xx_mh_emp_data` (
  `emp_cd` varchar(5) COLLATE utf8mb4_unicode_ci NOT NULL,
  `dept_cd` varchar(2) COLLATE utf8mb4_unicode_ci NOT NULL,
  `dept_desc` varchar(100) COLLATE utf8mb4_unicode_ci NOT NULL,
  `budcntr_cd` varchar(3) COLLATE utf8mb4_unicode_ci NOT NULL,
  `alloc_desc` varchar(100) COLLATE utf8mb4_unicode_ci NOT NULL,
  `fa_no` varchar(5) COLLATE utf8mb4_unicode_ci NOT NULL,
  `fa_desc` varchar(50) COLLATE utf8mb4_unicode_ci NOT NULL,
  `srf_no` varchar(7) COLLATE utf8mb4_unicode_ci NOT NULL,
  `class` varchar(15) COLLATE utf8mb4_unicode_ci NOT NULL,
  `name` varchar(62) COLLATE utf8mb4_unicode_ci NOT NULL,
  `desig` varchar(30) COLLATE utf8mb4_unicode_ci NOT NULL,
  `dob_text` varchar(10) COLLATE utf8mb4_unicode_ci NOT NULL,
  `age` int DEFAULT NULL,
  `join_dt_text` varchar(10) COLLATE utf8mb4_unicode_ci NOT NULL,
  `ret_dt_text` varchar(10) COLLATE utf8mb4_unicode_ci NOT NULL,
  PRIMARY KEY (`emp_cd`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

/*Table structure for table `fi_xx_mh_emp_fin` */

DROP TABLE IF EXISTS `fi_xx_mh_emp_fin`;

CREATE TABLE `fi_xx_mh_emp_fin` (
  `emp_cd` varchar(5) COLLATE utf8mb4_unicode_ci NOT NULL,
  `bank_cd` varchar(6) COLLATE utf8mb4_unicode_ci NOT NULL,
  `paymode_cd` varchar(2) COLLATE utf8mb4_unicode_ci NOT NULL,
  `bank_ac_no` varchar(20) COLLATE utf8mb4_unicode_ci NOT NULL,
  `last_gi_dt` date DEFAULT NULL,
  `next_gi_dt` date DEFAULT NULL,
  `suspend_flg` varchar(1) COLLATE utf8mb4_unicode_ci NOT NULL,
  `suspend_wef_dt` date DEFAULT NULL,
  `qtr_flg` int DEFAULT NULL,
  `transport_flg` int DEFAULT NULL,
  `tel_flg` int DEFAULT NULL,
  `past_serv_days` int DEFAULT NULL,
  `dues_clr_flg` int DEFAULT NULL,
  `remarks` varchar(150) COLLATE utf8mb4_unicode_ci NOT NULL,
  `date_created` date DEFAULT NULL,
  `date_modified` date DEFAULT NULL,
  `modified_by` varchar(5) COLLATE utf8mb4_unicode_ci NOT NULL,
  `created_by` varchar(5) COLLATE utf8mb4_unicode_ci NOT NULL,
  `pay_pct` decimal(14,4) DEFAULT NULL,
  `final_stlmt_status` varchar(1) COLLATE utf8mb4_unicode_ci NOT NULL,
  `fa_no` varchar(5) COLLATE utf8mb4_unicode_ci NOT NULL,
  `scale_sl` varchar(14) COLLATE utf8mb4_unicode_ci NOT NULL,
  `scale_wef_dt` date DEFAULT NULL,
  `scale_optfor` varchar(1) COLLATE utf8mb4_unicode_ci NOT NULL,
  `inland_cert_class` varchar(1) COLLATE utf8mb4_unicode_ci NOT NULL,
  `emp_class` int DEFAULT NULL,
  PRIMARY KEY (`emp_cd`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

/*Table structure for table `fi_xx_mh_emp_per` */

DROP TABLE IF EXISTS `fi_xx_mh_emp_per`;

CREATE TABLE `fi_xx_mh_emp_per` (
  `emp_cd` varchar(5) COLLATE utf8mb4_unicode_ci NOT NULL,
  `title` varchar(8) COLLATE utf8mb4_unicode_ci NOT NULL,
  `first_name` varchar(20) COLLATE utf8mb4_unicode_ci NOT NULL,
  `middle_name` varchar(20) COLLATE utf8mb4_unicode_ci NOT NULL,
  `last_name` varchar(20) COLLATE utf8mb4_unicode_ci NOT NULL,
  `perm_addr1` varchar(25) COLLATE utf8mb4_unicode_ci NOT NULL,
  `perm_addr2` varchar(25) COLLATE utf8mb4_unicode_ci NOT NULL,
  `perm_ps` varchar(30) COLLATE utf8mb4_unicode_ci NOT NULL,
  `perm_city` varchar(20) COLLATE utf8mb4_unicode_ci NOT NULL,
  `perm_dist` varchar(20) COLLATE utf8mb4_unicode_ci NOT NULL,
  `perm_state` varchar(20) COLLATE utf8mb4_unicode_ci NOT NULL,
  `perm_pin` int DEFAULT NULL,
  `perm_country` varchar(20) COLLATE utf8mb4_unicode_ci NOT NULL,
  `perm_contact1` varchar(15) COLLATE utf8mb4_unicode_ci NOT NULL,
  `perm_contact2` varchar(15) COLLATE utf8mb4_unicode_ci NOT NULL,
  `perm_fax_no` varchar(15) COLLATE utf8mb4_unicode_ci NOT NULL,
  `perm_email_id` varchar(30) COLLATE utf8mb4_unicode_ci NOT NULL,
  `pres_addr1` varchar(25) COLLATE utf8mb4_unicode_ci NOT NULL,
  `pres_addr2` varchar(25) COLLATE utf8mb4_unicode_ci NOT NULL,
  `pres_ps` varchar(30) COLLATE utf8mb4_unicode_ci NOT NULL,
  `pres_city` varchar(20) COLLATE utf8mb4_unicode_ci NOT NULL,
  `pres_dist` varchar(20) COLLATE utf8mb4_unicode_ci NOT NULL,
  `pres_state` varchar(20) COLLATE utf8mb4_unicode_ci NOT NULL,
  `pres_pin` int DEFAULT NULL,
  `pres_country` varchar(20) COLLATE utf8mb4_unicode_ci NOT NULL,
  `pres_contact1` varchar(15) COLLATE utf8mb4_unicode_ci NOT NULL,
  `pres_contact2` varchar(15) COLLATE utf8mb4_unicode_ci NOT NULL,
  `pres_fax_no` varchar(15) COLLATE utf8mb4_unicode_ci NOT NULL,
  `pres_email_id` varchar(30) COLLATE utf8mb4_unicode_ci NOT NULL,
  `f_h_flg` varchar(1) COLLATE utf8mb4_unicode_ci NOT NULL,
  `f_h_name` varchar(50) COLLATE utf8mb4_unicode_ci NOT NULL,
  `birth_dt` date DEFAULT NULL,
  `dob_evidence` varchar(100) COLLATE utf8mb4_unicode_ci NOT NULL,
  `sex` varchar(1) COLLATE utf8mb4_unicode_ci NOT NULL,
  `edu_qual` varchar(80) COLLATE utf8mb4_unicode_ci NOT NULL,
  `prof_qual` varchar(80) COLLATE utf8mb4_unicode_ci NOT NULL,
  `other_qual` varchar(80) COLLATE utf8mb4_unicode_ci NOT NULL,
  `awards` varchar(80) COLLATE utf8mb4_unicode_ci NOT NULL,
  `religion` varchar(15) COLLATE utf8mb4_unicode_ci NOT NULL,
  `nationality` varchar(15) COLLATE utf8mb4_unicode_ci NOT NULL,
  `height_cm` int DEFAULT NULL,
  `id_marks` varchar(100) COLLATE utf8mb4_unicode_ci NOT NULL,
  `category` varchar(3) COLLATE utf8mb4_unicode_ci NOT NULL,
  `handicap_flg` int DEFAULT NULL,
  `marital_status` varchar(1) COLLATE utf8mb4_unicode_ci NOT NULL,
  `date_created` date DEFAULT NULL,
  `date_modified` date DEFAULT NULL,
  `modified_by` varchar(5) COLLATE utf8mb4_unicode_ci NOT NULL,
  `created_by` varchar(5) COLLATE utf8mb4_unicode_ci NOT NULL,
  `status` varchar(2) COLLATE utf8mb4_unicode_ci NOT NULL,
  `f_h_addr` varchar(140) COLLATE utf8mb4_unicode_ci NOT NULL,
  `doctor_flg` int DEFAULT NULL,
  `remarks` varchar(300) COLLATE utf8mb4_unicode_ci NOT NULL,
  PRIMARY KEY (`emp_cd`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

/*Table structure for table `fi_xx_xx_m_d_fin_ctrl` */

DROP TABLE IF EXISTS `fi_xx_xx_m_d_fin_ctrl`;

CREATE TABLE `fi_xx_xx_m_d_fin_ctrl` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `FIN_YR` int NOT NULL,
  `DOC_ABV` varchar(4) COLLATE utf8mb4_unicode_ci NOT NULL,
  `DOC_DESC` varchar(60) COLLATE utf8mb4_unicode_ci NOT NULL,
  `L_TRN_NO` int NOT NULL,
  `CREATED_BY` varchar(5) COLLATE utf8mb4_unicode_ci NOT NULL,
  `CREATED_ON` date NOT NULL,
  `L_MODIFIED_BY` varchar(5) COLLATE utf8mb4_unicode_ci NOT NULL,
  `L_MODIFIED_ON` date DEFAULT NULL,
  `AUTHORITY` varchar(300) COLLATE utf8mb4_unicode_ci NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uniq_fin_ctrl_detail_key` (`FIN_YR`,`DOC_ABV`)
) ENGINE=InnoDB AUTO_INCREMENT=1059 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

/*Table structure for table `fi_xx_xx_m_h_fin_ctrl` */

DROP TABLE IF EXISTS `fi_xx_xx_m_h_fin_ctrl`;

CREATE TABLE `fi_xx_xx_m_h_fin_ctrl` (
  `FIN_YR` int NOT NULL,
  `YR_ST_DT` date NOT NULL,
  `YR_END_DT` date NOT NULL,
  `YEAR_PD` varchar(9) COLLATE utf8mb4_unicode_ci NOT NULL,
  `FIN_STAT` int NOT NULL,
  `L_TRN_NO` int NOT NULL,
  `CREATED_BY` varchar(5) COLLATE utf8mb4_unicode_ci NOT NULL,
  `CREATED_ON` date NOT NULL,
  `L_MODIFIED_BY` varchar(5) COLLATE utf8mb4_unicode_ci NOT NULL,
  `L_MODIFIED_ON` date DEFAULT NULL,
  PRIMARY KEY (`FIN_YR`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

/*Table structure for table `first_pension_cached_employee_oracle` */

DROP TABLE IF EXISTS `first_pension_cached_employee_oracle`;

CREATE TABLE `first_pension_cached_employee_oracle` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `emp_code` varchar(20) COLLATE utf8mb4_unicode_ci NOT NULL,
  `payload` json NOT NULL,
  `synced_at` datetime(6) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `emp_code` (`emp_code`)
) ENGINE=InnoDB AUTO_INCREMENT=21 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

/*Table structure for table `first_pension_cached_retirement_emp` */

DROP TABLE IF EXISTS `first_pension_cached_retirement_emp`;

CREATE TABLE `first_pension_cached_retirement_emp` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `emp_code` varchar(20) COLLATE utf8mb4_unicode_ci NOT NULL,
  `retirement_month` smallint unsigned NOT NULL,
  `retirement_year` int unsigned NOT NULL,
  `name` varchar(300) COLLATE utf8mb4_unicode_ci NOT NULL,
  `joining_date` varchar(20) COLLATE utf8mb4_unicode_ci NOT NULL,
  `retirement_date` varchar(20) COLLATE utf8mb4_unicode_ci NOT NULL,
  `birth_date` varchar(20) COLLATE utf8mb4_unicode_ci NOT NULL,
  `age_on_appointment` json DEFAULT NULL,
  `age_on_retirement` json DEFAULT NULL,
  `designation` varchar(300) COLLATE utf8mb4_unicode_ci NOT NULL,
  `scale` varchar(100) COLLATE utf8mb4_unicode_ci NOT NULL,
  `last_basic` decimal(12,2) DEFAULT NULL,
  `emp_class` varchar(20) COLLATE utf8mb4_unicode_ci NOT NULL,
  `row_payload` json NOT NULL,
  `synced_at` datetime(6) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `first_pension_cached_ret_emp_code_retirement_mont_3f4034bc_uniq` (`emp_code`,`retirement_month`,`retirement_year`),
  KEY `first_pension_cached_retirement_emp_emp_code_2e99d85d` (`emp_code`),
  KEY `first_pensi_retirem_b547a8_idx` (`retirement_year`,`retirement_month`),
  CONSTRAINT `first_pension_cached_retirement_emp_chk_1` CHECK ((`retirement_month` >= 0)),
  CONSTRAINT `first_pension_cached_retirement_emp_chk_2` CHECK ((`retirement_year` >= 0))
) ENGINE=InnoDB AUTO_INCREMENT=3635 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

/*Table structure for table `first_pension_commutationapplication` */

DROP TABLE IF EXISTS `first_pension_commutationapplication`;

CREATE TABLE `first_pension_commutationapplication` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `emp_cd` varchar(20) COLLATE utf8mb4_unicode_ci NOT NULL,
  `appcn_no` int NOT NULL,
  `application_time` int NOT NULL,
  `comm_start_mnth` int DEFAULT NULL,
  `appcn_dt` date DEFAULT NULL,
  `application_rcvd_dt` date DEFAULT NULL,
  `impl_fpen_combill` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `commutation_dt` date DEFAULT NULL,
  `restoration_dt` date DEFAULT NULL,
  `commutation_per` int DEFAULT NULL,
  `mo_certificate_dt` date DEFAULT NULL,
  `mo_certificate_ref` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `commutation_reasons` varchar(200) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `created_at` datetime(6) DEFAULT NULL,
  `status` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `current_stage` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `updated_at` datetime(6) DEFAULT NULL,
  `created_by_id` bigint DEFAULT NULL,
  `updated_by_id` bigint DEFAULT NULL,
  `bank_cd` varchar(6) COLLATE utf8mb4_unicode_ci NOT NULL,
  `bank_desc` varchar(50) COLLATE utf8mb4_unicode_ci NOT NULL,
  `ca_no` varchar(50) COLLATE utf8mb4_unicode_ci NOT NULL,
  `ref_no` varchar(100) COLLATE utf8mb4_unicode_ci NOT NULL,
  `bill_no` varchar(50) COLLATE utf8mb4_unicode_ci NOT NULL,
  `sanction_parameter` varchar(200) COLLATE utf8mb4_unicode_ci NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `emp_cd` (`emp_cd`),
  KEY `first_pension_commut_created_by_id_ea40f5fb_fk_accounts_` (`created_by_id`),
  KEY `first_pension_commut_updated_by_id_2097d29d_fk_accounts_` (`updated_by_id`),
  CONSTRAINT `first_pension_commut_created_by_id_ea40f5fb_fk_accounts_` FOREIGN KEY (`created_by_id`) REFERENCES `accounts_user` (`id`),
  CONSTRAINT `first_pension_commut_updated_by_id_2097d29d_fk_accounts_` FOREIGN KEY (`updated_by_id`) REFERENCES `accounts_user` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=17 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

/*Table structure for table `first_pension_dashboard_snapshot` */

DROP TABLE IF EXISTS `first_pension_dashboard_snapshot`;

CREATE TABLE `first_pension_dashboard_snapshot` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `month` smallint unsigned NOT NULL,
  `year` int unsigned NOT NULL,
  `total_employees` int DEFAULT NULL,
  `prev_month_count` int NOT NULL,
  `retirement_count` int NOT NULL,
  `next_month_count` int NOT NULL,
  `prev_month_label` varchar(64) COLLATE utf8mb4_unicode_ci NOT NULL,
  `this_month_label` varchar(64) COLLATE utf8mb4_unicode_ci NOT NULL,
  `next_month_label` varchar(64) COLLATE utf8mb4_unicode_ci NOT NULL,
  `synced_at` datetime(6) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `first_pension_dashboard_snapshot_month_year_055922d6_uniq` (`month`,`year`),
  KEY `first_pensi_year_d88318_idx` (`year`,`month`),
  CONSTRAINT `first_pension_dashboard_snapshot_chk_1` CHECK ((`month` >= 0)),
  CONSTRAINT `first_pension_dashboard_snapshot_chk_2` CHECK ((`year` >= 0))
) ENGINE=InnoDB AUTO_INCREMENT=6 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

/*Table structure for table `first_pension_pensioncase` */

DROP TABLE IF EXISTS `first_pension_pensioncase`;

CREATE TABLE `first_pension_pensioncase` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `emp_code` varchar(20) COLLATE utf8mb4_unicode_ci NOT NULL,
  `name` varchar(200) COLLATE utf8mb4_unicode_ci NOT NULL,
  `emp_class` varchar(20) COLLATE utf8mb4_unicode_ci NOT NULL,
  `birth_date` date NOT NULL,
  `joining_date` date NOT NULL,
  `retirement_date` date NOT NULL,
  `designation` varchar(200) COLLATE utf8mb4_unicode_ci NOT NULL,
  `scale` varchar(100) COLLATE utf8mb4_unicode_ci NOT NULL,
  `last_basic` decimal(12,2) NOT NULL,
  `no_pay_days` int NOT NULL,
  `dies_non_days` int NOT NULL,
  `commutation_percent` decimal(5,2) NOT NULL,
  `commutation_reason` varchar(200) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `status` varchar(50) COLLATE utf8mb4_unicode_ci NOT NULL,
  `current_stage` varchar(50) COLLATE utf8mb4_unicode_ci NOT NULL,
  `created_at` datetime(6) NOT NULL,
  `updated_at` datetime(6) NOT NULL,
  `created_by_id` bigint DEFAULT NULL,
  `updated_by_id` bigint DEFAULT NULL,
  `no_pay_more_than_240_days` int NOT NULL,
  `suspension_days` int NOT NULL,
  `separation_type` varchar(50) COLLATE utf8mb4_unicode_ci NOT NULL,
  `separation_date` date DEFAULT NULL,
  `process_remarks` longtext COLLATE utf8mb4_unicode_ci NOT NULL,
  `boys_serv_days` int NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `emp_code` (`emp_code`),
  KEY `first_pension_pensio_created_by_id_1ead96e1_fk_accounts_` (`created_by_id`),
  KEY `first_pension_pensio_updated_by_id_ed04a933_fk_accounts_` (`updated_by_id`),
  CONSTRAINT `first_pension_pensio_created_by_id_1ead96e1_fk_accounts_` FOREIGN KEY (`created_by_id`) REFERENCES `accounts_user` (`id`),
  CONSTRAINT `first_pension_pensio_updated_by_id_ed04a933_fk_accounts_` FOREIGN KEY (`updated_by_id`) REFERENCES `accounts_user` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=38 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

/*Table structure for table `first_pension_pensionproposal` */

DROP TABLE IF EXISTS `first_pension_pensionproposal`;

CREATE TABLE `first_pension_pensionproposal` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `emp_cd` varchar(20) COLLATE utf8mb4_unicode_ci NOT NULL,
  `emp_name` varchar(200) COLLATE utf8mb4_unicode_ci NOT NULL,
  `employee_status` varchar(50) COLLATE utf8mb4_unicode_ci NOT NULL,
  `ca_number` varchar(50) COLLATE utf8mb4_unicode_ci NOT NULL,
  `pension_type` varchar(50) COLLATE utf8mb4_unicode_ci NOT NULL,
  `pension_proposal_no` varchar(50) COLLATE utf8mb4_unicode_ci NOT NULL,
  `eligible_double_family_pension` tinyint(1) NOT NULL,
  `separation_type` varchar(50) COLLATE utf8mb4_unicode_ci NOT NULL,
  `separation_date` date DEFAULT NULL,
  `implemented_year` int DEFAULT NULL,
  `implemented_month` int DEFAULT NULL,
  `service_tenure` varchar(100) COLLATE utf8mb4_unicode_ci NOT NULL,
  `pension_option` varchar(50) COLLATE utf8mb4_unicode_ci NOT NULL,
  `option_given_by` varchar(50) COLLATE utf8mb4_unicode_ci NOT NULL,
  `regn_no` varchar(50) COLLATE utf8mb4_unicode_ci NOT NULL,
  `regn_date` date DEFAULT NULL,
  `start_month` int DEFAULT NULL,
  `start_year` int DEFAULT NULL,
  `pension_roll_no` varchar(50) COLLATE utf8mb4_unicode_ci NOT NULL,
  `pension_proposal_date` date DEFAULT NULL,
  `double_family_pension_upto_date` date DEFAULT NULL,
  `provisional_pension_pct` decimal(7,2) DEFAULT NULL,
  `bank_cd` varchar(20) COLLATE utf8mb4_unicode_ci NOT NULL,
  `bank_name` varchar(200) COLLATE utf8mb4_unicode_ci NOT NULL,
  `account_no` varchar(50) COLLATE utf8mb4_unicode_ci NOT NULL,
  `vigilance_clearance_ref_no` varchar(100) COLLATE utf8mb4_unicode_ci NOT NULL,
  `vigilance_clearance_ref_dt` date DEFAULT NULL,
  `lic_bank_cd` varchar(20) COLLATE utf8mb4_unicode_ci NOT NULL,
  `lic_bank_name` varchar(200) COLLATE utf8mb4_unicode_ci NOT NULL,
  `vr_ref_no` varchar(100) COLLATE utf8mb4_unicode_ci NOT NULL,
  `vr_ref_dt` date DEFAULT NULL,
  `compassionate_allowance` varchar(50) COLLATE utf8mb4_unicode_ci NOT NULL,
  `quarter_status` varchar(50) COLLATE utf8mb4_unicode_ci NOT NULL,
  `nominee_eform` varchar(50) COLLATE utf8mb4_unicode_ci NOT NULL,
  `compassionate_allowance_amt` decimal(12,2) DEFAULT NULL,
  `port_city_resident` varchar(50) COLLATE utf8mb4_unicode_ci NOT NULL,
  `gratuity_option` varchar(50) COLLATE utf8mb4_unicode_ci NOT NULL,
  `retirement_cpi` decimal(10,2) DEFAULT NULL,
  `id_card_submitted` tinyint(1) NOT NULL,
  `vigilance_cleared` tinyint(1) NOT NULL,
  `incentive_holder` varchar(50) COLLATE utf8mb4_unicode_ci NOT NULL,
  `held_up_flag` varchar(50) COLLATE utf8mb4_unicode_ci NOT NULL,
  `held_gratuity_amt` decimal(12,2) DEFAULT NULL,
  `extra_tccs_enabled` tinyint(1) NOT NULL,
  `extra_tccs_years` int NOT NULL,
  `extra_tccs_months` int NOT NULL,
  `extra_tccs_days` int NOT NULL,
  `earning_deductions` json NOT NULL,
  `created_at` datetime(6) NOT NULL,
  `updated_at` datetime(6) NOT NULL,
  `created_by_id` bigint DEFAULT NULL,
  `updated_by_id` bigint DEFAULT NULL,
  `held_recovery_amt` decimal(12,2) DEFAULT NULL,
  `held_recovery_date` date DEFAULT NULL,
  `held_recovery_ref_no` varchar(30) COLLATE utf8mb4_unicode_ci NOT NULL,
  `held_recovery_remarks` varchar(500) COLLATE utf8mb4_unicode_ci NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `emp_cd` (`emp_cd`),
  KEY `first_pension_pensio_created_by_id_817d31dc_fk_accounts_` (`created_by_id`),
  KEY `first_pension_pensio_updated_by_id_3389263b_fk_accounts_` (`updated_by_id`),
  CONSTRAINT `first_pension_pensio_created_by_id_817d31dc_fk_accounts_` FOREIGN KEY (`created_by_id`) REFERENCES `accounts_user` (`id`),
  CONSTRAINT `first_pension_pensio_updated_by_id_3389263b_fk_accounts_` FOREIGN KEY (`updated_by_id`) REFERENCES `accounts_user` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=18 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

/*Table structure for table `first_pension_pensionsummary` */

DROP TABLE IF EXISTS `first_pension_pensionsummary`;

CREATE TABLE `first_pension_pensionsummary` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `total_service_years` int NOT NULL,
  `total_service_months` int NOT NULL,
  `total_service_days` int NOT NULL,
  `tccs_years` int NOT NULL,
  `tccs_months` int NOT NULL,
  `tccs_days` int NOT NULL,
  `tqs_years` int NOT NULL,
  `tqs_months` int NOT NULL,
  `tqs_days` int NOT NULL,
  `pension_amount` decimal(12,2) NOT NULL,
  `commutation_amount` decimal(15,2) NOT NULL,
  `gratuity_amount` decimal(15,2) NOT NULL,
  `pension_start_date` date NOT NULL,
  `created_at` datetime(6) NOT NULL,
  `updated_at` datetime(6) NOT NULL,
  `pension_case_id` bigint NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `pension_case_id` (`pension_case_id`),
  CONSTRAINT `first_pension_pensio_pension_case_id_5eb76817_fk_first_pen` FOREIGN KEY (`pension_case_id`) REFERENCES `first_pension_pensioncase` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=22 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

/*Table structure for table `workflow_workflowhistory` */

DROP TABLE IF EXISTS `workflow_workflowhistory`;

CREATE TABLE `workflow_workflowhistory` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `action` varchar(50) NOT NULL,
  `remarks` longtext,
  `performed_at` datetime(6) NOT NULL,
  `from_step` int DEFAULT NULL,
  `to_step` int DEFAULT NULL,
  `performed_by_id` bigint DEFAULT NULL,
  `instance_id` bigint NOT NULL,
  `step_id` bigint NOT NULL,
  PRIMARY KEY (`id`),
  KEY `workflow_workflowhis_performed_by_id_f91043b4_fk_accounts_` (`performed_by_id`),
  KEY `workflow_workflowhis_instance_id_c5c65b54_fk_workflow_` (`instance_id`),
  KEY `workflow_workflowhis_step_id_b6b2e1cd_fk_workflow_` (`step_id`),
  CONSTRAINT `workflow_workflowhis_instance_id_c5c65b54_fk_workflow_` FOREIGN KEY (`instance_id`) REFERENCES `workflow_workflowinstance` (`id`),
  CONSTRAINT `workflow_workflowhis_performed_by_id_f91043b4_fk_accounts_` FOREIGN KEY (`performed_by_id`) REFERENCES `accounts_user` (`id`),
  CONSTRAINT `workflow_workflowhis_step_id_b6b2e1cd_fk_workflow_` FOREIGN KEY (`step_id`) REFERENCES `workflow_workflowstep` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

/*Table structure for table `workflow_workflowinstance` */

DROP TABLE IF EXISTS `workflow_workflowinstance`;

CREATE TABLE `workflow_workflowinstance` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `object_id` varchar(100) NOT NULL,
  `module` varchar(50) NOT NULL,
  `status` varchar(20) NOT NULL,
  `created_at` datetime(6) NOT NULL,
  `workflow_id` bigint NOT NULL,
  `current_step_id` bigint DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `workflow_workflowins_workflow_id_1cc77802_fk_workflow_` (`workflow_id`),
  KEY `workflow_workflowins_current_step_id_9110ee8b_fk_workflow_` (`current_step_id`),
  CONSTRAINT `workflow_workflowins_current_step_id_9110ee8b_fk_workflow_` FOREIGN KEY (`current_step_id`) REFERENCES `workflow_workflowstep` (`id`),
  CONSTRAINT `workflow_workflowins_workflow_id_1cc77802_fk_workflow_` FOREIGN KEY (`workflow_id`) REFERENCES `workflow_workflowmaster` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

/*Table structure for table `workflow_workflowmaster` */

DROP TABLE IF EXISTS `workflow_workflowmaster`;

CREATE TABLE `workflow_workflowmaster` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `name` varchar(100) NOT NULL,
  `module` varchar(50) NOT NULL,
  `is_active` tinyint(1) NOT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

/*Table structure for table `workflow_workflowstep` */

DROP TABLE IF EXISTS `workflow_workflowstep`;

CREATE TABLE `workflow_workflowstep` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `step_order` int NOT NULL,
  `action_name` varchar(50) NOT NULL,
  `is_final` tinyint(1) NOT NULL,
  `is_active` tinyint(1) NOT NULL,
  `role_id` bigint NOT NULL,
  `workflow_id` bigint NOT NULL,
  PRIMARY KEY (`id`),
  KEY `workflow_workflowstep_role_id_63bf12fb_fk_accounts_role_id` (`role_id`),
  KEY `workflow_workflowste_workflow_id_7d7883a2_fk_workflow_` (`workflow_id`),
  CONSTRAINT `workflow_workflowste_workflow_id_7d7883a2_fk_workflow_` FOREIGN KEY (`workflow_id`) REFERENCES `workflow_workflowmaster` (`id`),
  CONSTRAINT `workflow_workflowstep_role_id_63bf12fb_fk_accounts_role_id` FOREIGN KEY (`role_id`) REFERENCES `accounts_role` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;
