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

/*Data for the table `accounts_diesnon` */

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

/*Data for the table `accounts_role` */

insert  into `accounts_role`(`id`,`name`,`is_active`,`code`) values 
(1,'Test',0,'TEST'),
(2,'First Pension User',1,'FIRST_PENSION_USER'),
(3,'Family Pension User',1,'FAMILY_PENSION_USER'),
(4,'Bill Generation User',1,'BILL_GENERATION_USER'),
(5,'LIC Section User',1,'LIC_SECTION_USER'),
(6,'Pension Admin',1,'PENSION_ADMIN');

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

/*Data for the table `accounts_user` */

insert  into `accounts_user`(`id`,`password`,`last_login`,`is_superuser`,`username`,`first_name`,`last_name`,`email`,`is_staff`,`is_active`,`date_joined`) values 
(1,'pbkdf2_sha256$1000000$2XqUWvgkrvTFqm98EHxC88$a1XZ2kt1IqzkKeBP3jnckl9+Rwd3kfcmYMC3YIthTiA=','2026-04-24 07:49:54.476500',1,'admin_smpk','','','smpk@cdac.in',1,1,'2026-04-24 07:24:55.777679'),
(2,'pbkdf2_sha256$1000000$ra5Hg45bpUKGz2aGOWVyve$3T+pXKgZDcbWbmm0X3Ma2ZlEzzIyIVxsWXNSaRgbuEw=',NULL,0,'x','','','',0,0,'2026-05-28 17:11:14.603891'),
(3,'pbkdf2_sha256$1000000$EnrH1L22aliyKcYPchR7aX$Gh76JyLDwMPvPw1NE4DLDpP5GeULiAmcqGhM+VUKsQY=',NULL,0,'pension_user','Pension','User','raja.gupta@cdac.in',0,1,'2026-05-28 17:14:13.794328');

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

/*Data for the table `accounts_user_groups` */

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

/*Data for the table `accounts_user_user_permissions` */

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

/*Data for the table `accounts_userprofile` */

insert  into `accounts_userprofile`(`id`,`emp_code`,`designation`,`department`,`mobile_no`,`user_id`) values 
(1,'','','','',1),
(2,'','','','',2),
(3,'100317','Accounts Officer','Pension Department','9830298259',3);

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

/*Data for the table `accounts_userrole` */

insert  into `accounts_userrole`(`id`,`is_active`,`role_id`,`user_id`) values 
(1,1,6,1),
(2,1,2,2),
(3,1,2,3);

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
) ENGINE=InnoDB AUTO_INCREMENT=74 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

/*Data for the table `audit_auditlog` */

insert  into `audit_auditlog`(`id`,`table_name`,`record_id`,`action`,`old_data`,`new_data`,`changed_at`,`ip_address`,`user_agent`,`module`,`changed_by_id`) values 
(1,'PensionCase','12','CREATE',NULL,'{\"name\": \"Mr. RAVI SHANKAR RAJHANS\", \"status\": \"INITIATED\", \"emp_code\": \"48330\"}','2026-05-11 06:54:24.413207','127.0.0.1','Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36','FIRST_PENSION',1),
(2,'PensionCase','13','CREATE',NULL,'{\"name\": \"Mr. SWAPAN KUMAR NASKAR\", \"status\": \"INITIATED\", \"emp_code\": \"42230\"}','2026-05-11 08:12:40.513182','127.0.0.1','Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36','FIRST_PENSION',1),
(4,'PensionCase','15','CREATE',NULL,'{\"name\": \"Mr. AMAL KUMAR MAITI\", \"status\": \"INITIATED\", \"emp_code\": \"43443\"}','2026-05-11 09:16:47.063627','127.0.0.1','Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36','FIRST_PENSION',1),
(5,'PensionCase','16','CREATE',NULL,'{\"name\": \"Mr. DASARATH  YADAV\", \"status\": \"INITIATED\", \"emp_code\": \"45996\"}','2026-05-12 09:29:23.865902','127.0.0.1','Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36','FIRST_PENSION',1),
(6,'PensionCase','17','CREATE',NULL,'{\"name\": \"Mrs. KRISHNA  MINZ\", \"status\": \"INITIATED\", \"emp_code\": \"43694\"}','2026-05-15 05:53:24.525710','127.0.0.1','Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36','FIRST_PENSION',1),
(7,'CommutationApplication','1','CREATE',NULL,'{\"id\": 1, \"emp_cd\": \"42230\", \"status\": \"COMMUTATION INITIATED\", \"appcn_dt\": \"2026-06-01\", \"appcn_no\": \"5688\", \"commutation_dt\": \"2026-06-01\", \"restoration_dt\": \"2026-06-01\", \"comm_start_mnth\": \"06\", \"commutation_per\": \"40\", \"application_time\": \"1\", \"impl_fpen_combill\": \"PEN\", \"mo_certificate_dt\": \"2026-05-21\", \"mo_certificate_ref\": \"MO/25-26/1\", \"application_rcvd_dt\": \"2026-06-01\", \"commutation_reasons\": \"House Renovotation\"}','2026-05-21 07:26:43.267299','127.0.0.1','Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36','FIRST_PENSION',1),
(8,'CommutationApplication','1','UPDATE','{\"id\": 1, \"emp_cd\": \"42230\", \"status\": \"COMMUTATION INITIATED\", \"appcn_dt\": \"2026-06-01\", \"appcn_no\": 5688, \"commutation_dt\": \"2026-06-01\", \"restoration_dt\": \"2026-06-01\", \"comm_start_mnth\": 6, \"commutation_per\": 40, \"application_time\": 1, \"impl_fpen_combill\": \"PEN\", \"mo_certificate_dt\": \"2026-05-21\", \"mo_certificate_ref\": \"MO/25-26/1\", \"application_rcvd_dt\": \"2026-06-01\", \"commutation_reasons\": \"House Renovotation\"}','{\"id\": 1, \"emp_cd\": \"42230\", \"status\": \"COMMUTATION INITIATED\", \"appcn_dt\": \"2026-06-01\", \"appcn_no\": 5688, \"commutation_dt\": \"2026-06-01\", \"restoration_dt\": \"2026-06-01\", \"comm_start_mnth\": 6, \"commutation_per\": 40, \"application_time\": 1, \"impl_fpen_combill\": \"PEN\", \"mo_certificate_dt\": \"2026-05-21\", \"mo_certificate_ref\": \"MO/25-26/1\", \"application_rcvd_dt\": \"2026-06-01\", \"commutation_reasons\": \"House Repairing\"}','2026-05-21 07:28:14.565526','127.0.0.1','Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36','FIRST_PENSION',1),
(9,'PensionCase','13','UPDATE','{\"id\": 13, \"emp_code\": \"42230\", \"no_pay_days\": 0, \"dies_non_days\": 0}','{\"id\": 13, \"emp_code\": \"42230\", \"no_pay_days\": 10, \"dies_non_days\": 7}','2026-05-21 07:48:10.182986','127.0.0.1','Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36','FIRST_PENSION',1),
(10,'PensionProposal','1','CREATE',NULL,'{\"id\": 1, \"emp_cd\": \"42230\", \"bank_cd\": \"160061\", \"regn_no\": \"\", \"emp_name\": \"Mr. SWAPAN KUMAR NASKAR\", \"bank_name\": \"KOLKATA PORT TRUST(SUBHASH BHABAN)\", \"ca_number\": \"\", \"regn_date\": \"\", \"vr_ref_dt\": \"\", \"vr_ref_no\": \"\", \"account_no\": \"158201000002144\", \"start_year\": 2026, \"lic_bank_cd\": \"\", \"start_month\": 6, \"held_up_flag\": \"\", \"pension_type\": \"\", \"lic_bank_name\": \"\", \"nominee_eform\": \"\", \"pension_option\": \"\", \"quarter_status\": \"\", \"retirement_cpi\": null, \"service_tenure\": \"From 26-05-1988 to 01-06-2026\", \"employee_status\": \"EMPLOYEE\", \"extra_tccs_days\": 0, \"gratuity_option\": \"\", \"option_given_by\": \"\", \"pension_roll_no\": \"\", \"separation_date\": \"2026-06-01\", \"separation_type\": \"\", \"extra_tccs_years\": 0, \"implemented_year\": 2026, \"incentive_holder\": \"\", \"extra_tccs_months\": 0, \"held_gratuity_amt\": null, \"id_card_submitted\": false, \"implemented_month\": 6, \"vigilance_cleared\": false, \"earning_deductions\": [{\"code\": \"200\", \"desc\": \"\", \"type\": \"EARN\", \"amount\": \"\", \"deduction_priority\": \"\"}, {\"code\": \"\", \"desc\": \"\", \"type\": \"EARN\", \"amount\": \"\", \"deduction_priority\": \"\"}, {\"code\": \"\", \"desc\": \"\", \"type\": \"EARN\", \"amount\": \"\", \"deduction_priority\": \"\"}], \"extra_tccs_enabled\": false, \"port_city_resident\": \"\", \"pension_proposal_no\": \"\", \"pension_proposal_date\": \"\", \"compassionate_allowance\": \"\", \"provisional_pension_pct\": null, \"vigilance_clearance_ref_dt\": \"\", \"vigilance_clearance_ref_no\": \"\", \"compassionate_allowance_amt\": null, \"eligible_double_family_pension\": false, \"double_family_pension_upto_date\": \"\"}','2026-05-21 11:39:00.431432','127.0.0.1','Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36','FIRST_PENSION',1),
(11,'CommutationApplication','2','CREATE',NULL,'{\"id\": 2, \"emp_cd\": \"46299\", \"status\": \"COMMUTATION INITIATED\", \"appcn_dt\": \"2026-06-01\", \"appcn_no\": \"5688\", \"commutation_dt\": \"2026-06-01\", \"restoration_dt\": \"2026-06-01\", \"comm_start_mnth\": \"06\", \"commutation_per\": \"40\", \"application_time\": 1, \"impl_fpen_combill\": \"PEN\", \"mo_certificate_dt\": \"\", \"mo_certificate_ref\": \"\", \"application_rcvd_dt\": \"2026-06-01\", \"commutation_reasons\": \"House Renovation\"}','2026-05-21 12:04:05.503309','127.0.0.1','Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36','FIRST_PENSION',1),
(12,'PensionCase','18','CREATE',NULL,'{\"id\": 18, \"emp_code\": \"46299\", \"no_pay_days\": 0, \"dies_non_days\": 0, \"suspension_days\": 0, \"no_pay_more_than_240_days\": 0}','2026-05-21 12:04:33.777159','127.0.0.1','Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36','FIRST_PENSION',1),
(13,'PensionProposal','1','CREATE',NULL,'{\"id\": 1, \"emp_cd\": \"46299\", \"bank_cd\": \"010127\", \"regn_no\": \"X/REG/1\", \"emp_name\": \"Mrs. RAHIMA  KHATOON\", \"bank_name\": \"GARDEN REACH (GAR)\", \"ca_number\": \"38562\", \"regn_date\": \"2026-05-21\", \"vr_ref_dt\": \"\", \"vr_ref_no\": \"\", \"account_no\": \"10320782829\", \"start_year\": 2026, \"lic_bank_cd\": \"700001\", \"start_month\": 6, \"held_up_flag\": \"\", \"pension_type\": \"PN\", \"lic_bank_name\": \"\", \"nominee_eform\": \"\", \"pension_option\": \"G\", \"quarter_status\": \"\", \"retirement_cpi\": null, \"service_tenure\": \"From 11-05-1994 to 01-06-2026\", \"employee_status\": \"EMPLOYEE\", \"extra_tccs_days\": 0, \"gratuity_option\": \"\", \"option_given_by\": \"E\", \"pension_roll_no\": \"ROLL1\", \"separation_date\": \"2026-06-01\", \"separation_type\": \"RT\", \"extra_tccs_years\": 0, \"implemented_year\": 2026, \"incentive_holder\": \"\", \"extra_tccs_months\": 0, \"held_gratuity_amt\": null, \"id_card_submitted\": false, \"implemented_month\": 6, \"vigilance_cleared\": false, \"earning_deductions\": [{\"code\": \"200\", \"desc\": \"PENSION(RETIRING)\", \"type\": \"EARN\", \"amount\": \"\", \"deduction_priority\": \"\"}, {\"code\": \"203\", \"desc\": \"COMMUTATION\", \"type\": \"EARN\", \"amount\": \"\", \"deduction_priority\": \"\"}, {\"code\": \"208\", \"desc\": \"RELIEF\", \"type\": \"EARN\", \"amount\": \"\", \"deduction_priority\": \"\"}, {\"code\": \"205\", \"desc\": \"RET. GRATUITY OPT- I\", \"type\": \"EARN\", \"amount\": \"\", \"deduction_priority\": \"\"}], \"extra_tccs_enabled\": false, \"port_city_resident\": \"\", \"pension_proposal_no\": \"PP/ABC/1\", \"pension_proposal_date\": \"2026-06-01\", \"compassionate_allowance\": \"\", \"provisional_pension_pct\": null, \"vigilance_clearance_ref_dt\": \"2026-05-21\", \"vigilance_clearance_ref_no\": \"VIG/25-26/1\", \"compassionate_allowance_amt\": null, \"eligible_double_family_pension\": false, \"double_family_pension_upto_date\": \"\"}','2026-05-21 12:08:14.634697','127.0.0.1','Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36','FIRST_PENSION',1),
(14,'PensionCase','18','CREATE',NULL,'{\"tqs\": \"32Y 0M 21D\", \"tccs\": \"32Y 0M 21D\", \"case_id\": 18, \"emp_code\": \"46299\", \"calculated\": true, \"last_basic\": 76800.0, \"no_pay_days\": 0, \"inputs_ready\": true, \"dies_non_days\": 0, \"total_service\": \"32Y 0M 21D\", \"pension_amount\": 38400.0, \"gratuity_amount\": 1688229.42, \"commutation_amount\": 1510318.08, \"commutation_percent\": 40.0, \"has_commutation_application\": true, \"commutation_percent_from_app\": 40.0}','2026-05-21 12:14:15.722735','127.0.0.1','Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36','FIRST_PENSION',1),
(15,'PensionCase','18','UPDATE','{\"tqs\": \"32Y 0M 21D\", \"tccs\": \"32Y 0M 21D\", \"case_id\": 18, \"emp_code\": \"46299\", \"calculated\": true, \"last_basic\": 76800.0, \"no_pay_days\": 0, \"inputs_ready\": true, \"dies_non_days\": 0, \"total_service\": \"32Y 0M 21D\", \"pension_amount\": 38400.0, \"gratuity_amount\": 1688229.42, \"commutation_amount\": 1510318.08, \"commutation_percent\": 40.0, \"has_commutation_application\": true, \"commutation_percent_from_app\": 40.0}','{\"tqs\": \"32Y 0M 21D\", \"tccs\": \"32Y 0M 21D\", \"case_id\": 18, \"emp_code\": \"46299\", \"calculated\": true, \"last_basic\": 76800.0, \"no_pay_days\": 0, \"inputs_ready\": true, \"dies_non_days\": 0, \"total_service\": \"32Y 0M 21D\", \"pension_amount\": 38400.0, \"gratuity_amount\": 1688229.42, \"commutation_amount\": 1510318.08, \"commutation_percent\": 40.0, \"has_commutation_application\": true, \"commutation_percent_from_app\": 40.0}','2026-05-21 12:22:06.520176','127.0.0.1','Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36','FIRST_PENSION',1),
(16,'PensionCase','18','UPDATE','{\"id\": 18, \"emp_code\": \"46299\", \"no_pay_days\": 0, \"dies_non_days\": 0, \"suspension_days\": 0, \"no_pay_more_than_240_days\": 0}','{\"id\": 18, \"emp_code\": \"46299\", \"no_pay_days\": 0, \"dies_non_days\": 0, \"suspension_days\": 0, \"no_pay_more_than_240_days\": 0}','2026-05-21 12:23:28.102018','127.0.0.1','Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36','FIRST_PENSION',1),
(17,'CommutationApplication','2','UPDATE','{\"id\": 2, \"emp_cd\": \"46299\", \"status\": \"COMMUTATION INITIATED\", \"appcn_dt\": \"2026-06-01\", \"appcn_no\": 5688, \"commutation_dt\": \"2026-06-01\", \"restoration_dt\": \"2026-06-01\", \"comm_start_mnth\": 6, \"commutation_per\": 40, \"application_time\": 1, \"impl_fpen_combill\": \"PEN\", \"mo_certificate_dt\": \"\", \"mo_certificate_ref\": \"\", \"application_rcvd_dt\": \"2026-06-01\", \"commutation_reasons\": \"House Renovation\"}','{\"id\": 2, \"emp_cd\": \"46299\", \"status\": \"COMMUTATION INITIATED\", \"appcn_dt\": \"2026-06-01\", \"appcn_no\": 5688, \"commutation_dt\": \"2026-06-01\", \"restoration_dt\": \"2026-06-01\", \"comm_start_mnth\": 6, \"commutation_per\": \"40\", \"application_time\": 1, \"impl_fpen_combill\": \"PEN\", \"mo_certificate_dt\": \"\", \"mo_certificate_ref\": \"\", \"application_rcvd_dt\": \"2026-06-01\", \"commutation_reasons\": \"House Renovation\"}','2026-05-21 12:23:36.958833','127.0.0.1','Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36','FIRST_PENSION',1),
(18,'PensionProposal','1','UPDATE','{\"id\": 1, \"emp_cd\": \"46299\", \"bank_cd\": \"010127\", \"regn_no\": \"X/REG/1\", \"emp_name\": \"Mrs. RAHIMA  KHATOON\", \"bank_name\": \"GARDEN REACH (GAR)\", \"ca_number\": \"38562\", \"regn_date\": \"2026-05-21\", \"vr_ref_dt\": \"\", \"vr_ref_no\": \"\", \"account_no\": \"10320782829\", \"start_year\": 2026, \"lic_bank_cd\": \"700001\", \"start_month\": 6, \"held_up_flag\": \"\", \"pension_type\": \"PN\", \"lic_bank_name\": \"\", \"nominee_eform\": \"\", \"pension_option\": \"G\", \"quarter_status\": \"\", \"retirement_cpi\": null, \"service_tenure\": \"From 11-05-1994 to 01-06-2026\", \"employee_status\": \"EMPLOYEE\", \"extra_tccs_days\": 0, \"gratuity_option\": \"\", \"option_given_by\": \"E\", \"pension_roll_no\": \"ROLL1\", \"separation_date\": \"2026-06-01\", \"separation_type\": \"RT\", \"extra_tccs_years\": 0, \"implemented_year\": 2026, \"incentive_holder\": \"\", \"extra_tccs_months\": 0, \"held_gratuity_amt\": null, \"id_card_submitted\": false, \"implemented_month\": 6, \"vigilance_cleared\": false, \"earning_deductions\": [{\"code\": \"200\", \"desc\": \"PENSION(RETIRING)\", \"type\": \"EARN\", \"amount\": \"\", \"deduction_priority\": \"\"}, {\"code\": \"203\", \"desc\": \"COMMUTATION\", \"type\": \"EARN\", \"amount\": \"\", \"deduction_priority\": \"\"}, {\"code\": \"208\", \"desc\": \"RELIEF\", \"type\": \"EARN\", \"amount\": \"\", \"deduction_priority\": \"\"}, {\"code\": \"205\", \"desc\": \"RET. GRATUITY OPT- I\", \"type\": \"EARN\", \"amount\": \"\", \"deduction_priority\": \"\"}], \"extra_tccs_enabled\": false, \"port_city_resident\": \"\", \"pension_proposal_no\": \"PP/ABC/1\", \"pension_proposal_date\": \"2026-06-01\", \"compassionate_allowance\": \"\", \"provisional_pension_pct\": null, \"vigilance_clearance_ref_dt\": \"2026-05-21\", \"vigilance_clearance_ref_no\": \"VIG/25-26/1\", \"compassionate_allowance_amt\": null, \"eligible_double_family_pension\": false, \"double_family_pension_upto_date\": \"\"}','{\"id\": 1, \"emp_cd\": \"46299\", \"bank_cd\": \"010127\", \"regn_no\": \"X/REG/1\", \"emp_name\": \"Mrs. RAHIMA  KHATOON\", \"bank_name\": \"GARDEN REACH (GAR)\", \"ca_number\": \"38562\", \"regn_date\": \"2026-05-21\", \"vr_ref_dt\": \"\", \"vr_ref_no\": \"\", \"account_no\": \"10320782829\", \"start_year\": 2026, \"lic_bank_cd\": \"700001\", \"start_month\": 6, \"held_up_flag\": \"\", \"pension_type\": \"PN\", \"lic_bank_name\": \"\", \"nominee_eform\": \"\", \"pension_option\": \"G\", \"quarter_status\": \"\", \"retirement_cpi\": null, \"service_tenure\": \"From 11-05-1994 to 01-06-2026\", \"employee_status\": \"EMPLOYEE\", \"extra_tccs_days\": 0, \"gratuity_option\": \"\", \"option_given_by\": \"E\", \"pension_roll_no\": \"ROLL1\", \"separation_date\": \"2026-06-01\", \"separation_type\": \"RT\", \"extra_tccs_years\": 0, \"implemented_year\": 2026, \"incentive_holder\": \"\", \"extra_tccs_months\": 0, \"held_gratuity_amt\": null, \"id_card_submitted\": false, \"implemented_month\": 6, \"vigilance_cleared\": false, \"earning_deductions\": [{\"code\": \"200\", \"desc\": \"PENSION(RETIRING)\", \"type\": \"EARN\", \"amount\": \"\", \"deduction_priority\": \"\"}, {\"code\": \"203\", \"desc\": \"COMMUTATION\", \"type\": \"EARN\", \"amount\": \"\", \"deduction_priority\": \"\"}, {\"code\": \"208\", \"desc\": \"RELIEF\", \"type\": \"EARN\", \"amount\": \"\", \"deduction_priority\": \"\"}, {\"code\": \"205\", \"desc\": \"RET. GRATUITY OPT- I\", \"type\": \"EARN\", \"amount\": \"\", \"deduction_priority\": \"\"}], \"extra_tccs_enabled\": false, \"port_city_resident\": \"\", \"pension_proposal_no\": \"PP/ABC/1\", \"pension_proposal_date\": \"2026-06-01\", \"compassionate_allowance\": \"\", \"provisional_pension_pct\": null, \"vigilance_clearance_ref_dt\": \"2026-05-21\", \"vigilance_clearance_ref_no\": \"VIG/25-26/1\", \"compassionate_allowance_amt\": null, \"eligible_double_family_pension\": false, \"double_family_pension_upto_date\": \"\"}','2026-05-21 12:23:53.986202','127.0.0.1','Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36','FIRST_PENSION',1),
(19,'PensionCase','18','CREATE',NULL,'{\"tqs\": \"32Y 0M 21D\", \"tccs\": \"32Y 0M 21D\", \"case_id\": 18, \"emp_code\": \"46299\", \"calculated\": true, \"last_basic\": 76800.0, \"no_pay_days\": 0, \"inputs_ready\": true, \"dies_non_days\": 0, \"total_service\": \"32Y 0M 21D\", \"pension_amount\": 38400.0, \"gratuity_amount\": 1688229.42, \"commutation_amount\": 1510318.08, \"commutation_percent\": 40.0, \"has_commutation_application\": true, \"commutation_percent_from_app\": 40.0}','2026-05-21 12:24:07.684473','127.0.0.1','Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36','FIRST_PENSION',1),
(20,'CommutationApplication','2','UPDATE','{\"id\": 2, \"emp_cd\": \"46299\", \"status\": \"COMMUTATION INITIATED\", \"appcn_dt\": \"2026-06-01\", \"appcn_no\": 5688, \"commutation_dt\": \"2026-06-01\", \"restoration_dt\": \"2026-06-01\", \"comm_start_mnth\": 6, \"commutation_per\": 40, \"application_time\": 1, \"impl_fpen_combill\": \"PEN\", \"mo_certificate_dt\": \"\", \"mo_certificate_ref\": \"\", \"application_rcvd_dt\": \"2026-06-01\", \"commutation_reasons\": \"House Renovation\"}','{\"id\": 2, \"emp_cd\": \"46299\", \"status\": \"COMMUTATION INITIATED\", \"appcn_dt\": \"2026-06-01\", \"appcn_no\": 5688, \"commutation_dt\": \"2026-06-01\", \"restoration_dt\": \"2026-06-01\", \"comm_start_mnth\": 6, \"commutation_per\": 40, \"application_time\": 1, \"impl_fpen_combill\": \"PEN\", \"mo_certificate_dt\": \"\", \"mo_certificate_ref\": \"\", \"application_rcvd_dt\": \"2026-06-01\", \"commutation_reasons\": \"House Renovation\"}','2026-05-21 12:32:20.506300','127.0.0.1','Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36','FIRST_PENSION',1),
(21,'PensionCase','18','UPDATE','{\"id\": 18, \"emp_code\": \"46299\", \"no_pay_days\": 0, \"dies_non_days\": 0, \"suspension_days\": 0, \"no_pay_more_than_240_days\": 0}','{\"id\": 18, \"emp_code\": \"46299\", \"no_pay_days\": 0, \"dies_non_days\": 0, \"suspension_days\": 0, \"no_pay_more_than_240_days\": 0}','2026-05-21 12:32:25.898315','127.0.0.1','Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36','FIRST_PENSION',1),
(22,'PensionCase','18','UPDATE','{\"tqs\": \"32Y 0M 21D\", \"tccs\": \"32Y 0M 21D\", \"case_id\": 18, \"emp_code\": \"46299\", \"calculated\": true, \"last_basic\": 76800.0, \"no_pay_days\": 0, \"inputs_ready\": true, \"dies_non_days\": 0, \"total_service\": \"32Y 0M 21D\", \"pension_amount\": 38400.0, \"gratuity_amount\": 1688229.42, \"commutation_amount\": 1510318.08, \"commutation_percent\": 40.0, \"has_commutation_application\": true, \"commutation_percent_from_app\": 40.0}','{\"tqs\": \"32Y 0M 21D\", \"tccs\": \"32Y 0M 21D\", \"case_id\": 18, \"emp_code\": \"46299\", \"calculated\": true, \"last_basic\": 76800.0, \"no_pay_days\": 0, \"inputs_ready\": true, \"dies_non_days\": 0, \"total_service\": \"32Y 0M 21D\", \"pension_amount\": 38400.0, \"gratuity_amount\": 1688230.0, \"commutation_amount\": 1510318.08, \"commutation_percent\": 40.0, \"has_commutation_application\": true, \"commutation_percent_from_app\": 40.0}','2026-05-21 12:32:35.607478','127.0.0.1','Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36','FIRST_PENSION',1),
(23,'PensionCase','18','UPDATE','{\"tqs\": \"32Y 0M 21D\", \"tccs\": \"32Y 0M 21D\", \"case_id\": 18, \"emp_code\": \"46299\", \"calculated\": true, \"last_basic\": 76800.0, \"no_pay_days\": 0, \"inputs_ready\": true, \"dies_non_days\": 0, \"total_service\": \"32Y 0M 21D\", \"pension_amount\": 38400.0, \"gratuity_amount\": 1688230.0, \"commutation_amount\": 1510318.08, \"commutation_percent\": 40.0, \"has_commutation_application\": true, \"commutation_percent_from_app\": 40.0}','{\"tqs\": \"32Y 0M 21D\", \"tccs\": \"32Y 0M 21D\", \"case_id\": 18, \"emp_code\": \"46299\", \"calculated\": true, \"last_basic\": 76800.0, \"no_pay_days\": 0, \"inputs_ready\": true, \"dies_non_days\": 0, \"total_service\": \"32Y 0M 21D\", \"pension_amount\": 38400.0, \"gratuity_amount\": 1688230.0, \"commutation_amount\": 1510319.0, \"commutation_percent\": 40.0, \"has_commutation_application\": true, \"commutation_percent_from_app\": 40.0}','2026-05-21 12:33:40.735449','127.0.0.1','Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36','FIRST_PENSION',1),
(24,'CommutationApplication','3','CREATE',NULL,'{\"id\": 3, \"emp_cd\": \"41158\", \"status\": \"COMMUTATION INITIATED\", \"appcn_dt\": \"2005-02-01\", \"appcn_no\": \"5688\", \"commutation_dt\": \"2005-02-01\", \"restoration_dt\": \"2026-05-01\", \"comm_start_mnth\": \"02\", \"commutation_per\": \"40\", \"application_time\": 1, \"impl_fpen_combill\": \"PEN\", \"mo_certificate_dt\": \"\", \"mo_certificate_ref\": \"\", \"application_rcvd_dt\": \"2005-02-01\", \"commutation_reasons\": \"hnbjmnk\"}','2026-05-25 09:05:09.935822','127.0.0.1','Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36','FIRST_PENSION',1),
(25,'PensionCase','19','CREATE',NULL,'{\"id\": 19, \"emp_code\": \"41158\", \"no_pay_days\": 0, \"dies_non_days\": 41, \"suspension_days\": 0, \"no_pay_more_than_240_days\": 0}','2026-05-25 09:05:45.358857','127.0.0.1','Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36','FIRST_PENSION',1),
(26,'PensionProposal','2','CREATE',NULL,'{\"id\": 2, \"emp_cd\": \"41158\", \"bank_cd\": \"210013\", \"regn_no\": \"\", \"emp_name\": \"Mr. DEB KUMAR GUHA\", \"bank_name\": \"BEHALA (BHL)\", \"ca_number\": \"34543\", \"regn_date\": \"\", \"vr_ref_dt\": \"\", \"vr_ref_no\": \"\", \"account_no\": \"268933\", \"start_year\": 2005, \"lic_bank_cd\": \"\", \"start_month\": 2, \"held_up_flag\": \"\", \"pension_type\": \"\", \"lic_bank_name\": \"\", \"nominee_eform\": \"NOMINEE\", \"pension_option\": \"\", \"quarter_status\": \"\", \"retirement_cpi\": null, \"service_tenure\": \"From 09-06-1967 to 01-02-2005\", \"employee_status\": \"EMPLOYEE\", \"extra_tccs_days\": 0, \"gratuity_option\": \"\", \"option_given_by\": \"\", \"pension_roll_no\": \"X/ghj\", \"separation_date\": \"2005-02-01\", \"separation_type\": \"RT\", \"extra_tccs_years\": 0, \"implemented_year\": 2005, \"incentive_holder\": \"\", \"extra_tccs_months\": 0, \"held_gratuity_amt\": null, \"id_card_submitted\": false, \"implemented_month\": 2, \"vigilance_cleared\": false, \"earning_deductions\": [{\"code\": \"200\", \"desc\": \"PENSION(RETIRING)\", \"type\": \"EARN\", \"amount\": \"\", \"deduction_priority\": \"\"}, {\"code\": \"203\", \"desc\": \"COMMUTATION\", \"type\": \"EARN\", \"amount\": \"\", \"deduction_priority\": \"\"}, {\"code\": \"205\", \"desc\": \"RET. GRATUITY OPT- I\", \"type\": \"EARN\", \"amount\": \"\", \"deduction_priority\": \"\"}, {\"code\": \"208\", \"desc\": \"RELIEF\", \"type\": \"EARN\", \"amount\": \"\", \"deduction_priority\": \"\"}], \"extra_tccs_enabled\": false, \"port_city_resident\": \"\", \"pension_proposal_no\": \"\", \"pension_proposal_date\": \"\", \"compassionate_allowance\": \"\", \"provisional_pension_pct\": null, \"vigilance_clearance_ref_dt\": \"\", \"vigilance_clearance_ref_no\": \"\", \"compassionate_allowance_amt\": null, \"eligible_double_family_pension\": false, \"double_family_pension_upto_date\": \"\"}','2026-05-25 09:06:49.369909','127.0.0.1','Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36','FIRST_PENSION',1),
(27,'PensionProposal','2','UPDATE','{\"id\": 2, \"emp_cd\": \"41158\", \"bank_cd\": \"210013\", \"regn_no\": \"\", \"emp_name\": \"Mr. DEB KUMAR GUHA\", \"bank_name\": \"BEHALA (BHL)\", \"ca_number\": \"34543\", \"regn_date\": \"\", \"vr_ref_dt\": \"\", \"vr_ref_no\": \"\", \"account_no\": \"268933\", \"start_year\": 2005, \"lic_bank_cd\": \"\", \"start_month\": 2, \"held_up_flag\": \"\", \"pension_type\": \"\", \"lic_bank_name\": \"\", \"nominee_eform\": \"NOMINEE\", \"pension_option\": \"\", \"quarter_status\": \"\", \"retirement_cpi\": null, \"service_tenure\": \"From 09-06-1967 to 01-02-2005\", \"employee_status\": \"EMPLOYEE\", \"extra_tccs_days\": 0, \"gratuity_option\": \"\", \"option_given_by\": \"\", \"pension_roll_no\": \"X/ghj\", \"separation_date\": \"2005-02-01\", \"separation_type\": \"RT\", \"extra_tccs_years\": 0, \"implemented_year\": 2005, \"incentive_holder\": \"\", \"extra_tccs_months\": 0, \"held_gratuity_amt\": null, \"id_card_submitted\": false, \"implemented_month\": 2, \"vigilance_cleared\": false, \"earning_deductions\": [{\"code\": \"200\", \"desc\": \"PENSION(RETIRING)\", \"type\": \"EARN\", \"amount\": \"\", \"deduction_priority\": \"\"}, {\"code\": \"203\", \"desc\": \"COMMUTATION\", \"type\": \"EARN\", \"amount\": \"\", \"deduction_priority\": \"\"}, {\"code\": \"205\", \"desc\": \"RET. GRATUITY OPT- I\", \"type\": \"EARN\", \"amount\": \"\", \"deduction_priority\": \"\"}, {\"code\": \"208\", \"desc\": \"RELIEF\", \"type\": \"EARN\", \"amount\": \"\", \"deduction_priority\": \"\"}], \"extra_tccs_enabled\": false, \"port_city_resident\": \"\", \"pension_proposal_no\": \"\", \"pension_proposal_date\": \"\", \"compassionate_allowance\": \"\", \"provisional_pension_pct\": null, \"vigilance_clearance_ref_dt\": \"\", \"vigilance_clearance_ref_no\": \"\", \"compassionate_allowance_amt\": null, \"eligible_double_family_pension\": false, \"double_family_pension_upto_date\": \"\"}','{\"id\": 2, \"emp_cd\": \"41158\", \"bank_cd\": \"210013\", \"regn_no\": \"X/fg/yu\", \"emp_name\": \"Mr. DEB KUMAR GUHA\", \"bank_name\": \"BEHALA (BHL)\", \"ca_number\": \"34543\", \"regn_date\": \"\", \"vr_ref_dt\": \"\", \"vr_ref_no\": \"\", \"account_no\": \"268933\", \"start_year\": 2005, \"lic_bank_cd\": \"\", \"start_month\": 2, \"held_up_flag\": \"\", \"pension_type\": \"\", \"lic_bank_name\": \"\", \"nominee_eform\": \"NOMINEE\", \"pension_option\": \"G\", \"quarter_status\": \"\", \"retirement_cpi\": null, \"service_tenure\": \"From 09-06-1967 to 01-02-2005\", \"employee_status\": \"EMPLOYEE\", \"extra_tccs_days\": 0, \"gratuity_option\": \"\", \"option_given_by\": \"E\", \"pension_roll_no\": \"LIC-567\", \"separation_date\": \"2005-02-01\", \"separation_type\": \"RT\", \"extra_tccs_years\": 0, \"implemented_year\": 2005, \"incentive_holder\": \"\", \"extra_tccs_months\": 0, \"held_gratuity_amt\": null, \"id_card_submitted\": false, \"implemented_month\": 2, \"vigilance_cleared\": false, \"earning_deductions\": [{\"code\": \"200\", \"desc\": \"PENSION(RETIRING)\", \"type\": \"EARN\", \"amount\": \"\", \"deduction_priority\": \"\"}, {\"code\": \"203\", \"desc\": \"COMMUTATION\", \"type\": \"EARN\", \"amount\": \"\", \"deduction_priority\": \"\"}, {\"code\": \"205\", \"desc\": \"RET. GRATUITY OPT- I\", \"type\": \"EARN\", \"amount\": \"\", \"deduction_priority\": \"\"}, {\"code\": \"208\", \"desc\": \"RELIEF\", \"type\": \"EARN\", \"amount\": \"\", \"deduction_priority\": \"\"}], \"extra_tccs_enabled\": false, \"port_city_resident\": \"\", \"pension_proposal_no\": \"\", \"pension_proposal_date\": \"\", \"compassionate_allowance\": \"\", \"provisional_pension_pct\": null, \"vigilance_clearance_ref_dt\": \"\", \"vigilance_clearance_ref_no\": \"\", \"compassionate_allowance_amt\": null, \"eligible_double_family_pension\": false, \"double_family_pension_upto_date\": \"\"}','2026-05-25 09:08:44.264485','127.0.0.1','Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36','FIRST_PENSION',1),
(28,'PensionCase','19','CREATE',NULL,'{\"tqs\": \"37Y 6M 13D\", \"tccs\": \"37Y 6M 13D\", \"case_id\": 19, \"emp_code\": \"41158\", \"calculated\": true, \"last_basic\": 8480.0, \"no_pay_days\": 0, \"inputs_ready\": true, \"dies_non_days\": 41, \"total_service\": \"37Y 7M 23D\", \"pension_amount\": 4240.0, \"gratuity_amount\": 221361.0, \"commutation_amount\": 166765.0, \"commutation_percent\": 40.0, \"has_commutation_application\": true, \"commutation_percent_from_app\": 40.0}','2026-05-25 09:08:49.011396','127.0.0.1','Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36','FIRST_PENSION',1),
(29,'PensionCase','19','UPDATE','{\"id\": 19, \"emp_code\": \"41158\", \"no_pay_days\": 0, \"dies_non_days\": 41, \"suspension_days\": 0, \"no_pay_more_than_240_days\": 0}','{\"id\": 19, \"emp_code\": \"41158\", \"no_pay_days\": 810, \"dies_non_days\": 41, \"suspension_days\": 0, \"no_pay_more_than_240_days\": 0}','2026-05-25 09:12:54.642866','127.0.0.1','Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36','FIRST_PENSION',1),
(30,'PensionCase','19','UPDATE','{\"tqs\": \"37Y 6M 13D\", \"tccs\": \"37Y 6M 13D\", \"case_id\": 19, \"emp_code\": \"41158\", \"calculated\": true, \"last_basic\": 8480.0, \"no_pay_days\": 810, \"inputs_ready\": true, \"dies_non_days\": 41, \"total_service\": \"37Y 7M 23D\", \"pension_amount\": 4240.0, \"gratuity_amount\": 221361.0, \"commutation_amount\": 166765.0, \"commutation_percent\": 40.0, \"has_commutation_application\": true, \"commutation_percent_from_app\": 40.0}','{\"tqs\": \"35Y 3M 25D\", \"tccs\": \"37Y 6M 13D\", \"case_id\": 19, \"emp_code\": \"41158\", \"calculated\": true, \"last_basic\": 8480.0, \"no_pay_days\": 810, \"inputs_ready\": true, \"dies_non_days\": 41, \"total_service\": \"37Y 7M 23D\", \"pension_amount\": 4240.0, \"gratuity_amount\": 221361.0, \"commutation_amount\": 166765.0, \"commutation_percent\": 40.0, \"has_commutation_application\": true, \"commutation_percent_from_app\": 40.0}','2026-05-25 09:13:10.901733','127.0.0.1','Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36','FIRST_PENSION',1),
(31,'FI_XX_MH_EMP_ADM','42230','UPDATE','{\"remarks\": \"SUSPEND ON 15/06/07(AFTRNOON) VIDE ORDER NO Lab/E/Cl/III/IV/593 dt-15/06/07.REVOKED WITH IMMEDIATE EFFECT  NO-LAB/E/CL.III/IV/234A-1-V DT-27/03/08.\", \"separation_date\": \"2026-06-01\", \"separation_type\": \"RT\"}','{\"remarks\": \"SUSPEND ON 15/06/07(AFTRNOON) VIDE ORDER NO Lab/E/Cl/III/IV/593 dt-15/06/07.REVOKED WITH IMMEDIATE EFFECT  NO-LAB/E/CL.III/IV/234A-1-V DT-27/03/08.\", \"separation_date\": \"2026-06-01\", \"separation_type\": \"RT\"}','2026-05-26 11:38:49.292799','127.0.0.1','Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36','FIRST_PENSION',1),
(32,'FI_XX_MH_EMP_ADM','43694','UPDATE','{\"remarks\": \"Superannuation\", \"separation_date\": \"2026-06-01\", \"separation_type\": \"RT\"}','{\"remarks\": \"Superannuation\", \"separation_date\": \"2026-06-01\", \"separation_type\": \"RT\"}','2026-05-26 11:42:00.524069','127.0.0.1','Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36','FIRST_PENSION',1),
(33,'PensionCase','15','UPDATE','{\"remarks\": \"\", \"separation_date\": \"\", \"separation_type\": \"\"}','{\"remarks\": \"Superannuation\", \"separation_date\": \"2026-06-01\", \"separation_type\": \"RT\"}','2026-05-26 11:59:35.244289','127.0.0.1','Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36','FIRST_PENSION',1),
(34,'PensionProposal','3','CREATE',NULL,'{\"id\": 3, \"emp_cd\": \"46689\", \"bank_cd\": \"210149\", \"regn_no\": \"\", \"emp_name\": \"Mr. MRITUNJOY  BISWAS\", \"bank_name\": \"WATGANJ (WTG)\", \"ca_number\": \"\", \"regn_date\": \"\", \"vr_ref_dt\": \"\", \"vr_ref_no\": \"\", \"account_no\": \"10467\", \"start_year\": 2004, \"lic_bank_cd\": \"\", \"start_month\": 5, \"held_up_flag\": \"\", \"pension_type\": \"\", \"lic_bank_name\": \"\", \"nominee_eform\": \"\", \"pension_option\": \"\", \"quarter_status\": \"\", \"retirement_cpi\": null, \"service_tenure\": \"From 12-08-1968 to 01-05-2004\", \"employee_status\": \"EMPLOYEE\", \"extra_tccs_days\": 0, \"gratuity_option\": \"\", \"option_given_by\": \"\", \"pension_roll_no\": \"\", \"separation_date\": \"2004-05-01\", \"separation_type\": \"RT\", \"extra_tccs_years\": 0, \"implemented_year\": 2004, \"incentive_holder\": \"\", \"extra_tccs_months\": 0, \"held_gratuity_amt\": null, \"id_card_submitted\": false, \"implemented_month\": 5, \"vigilance_cleared\": false, \"earning_deductions\": [{\"code\": \"\", \"desc\": \"\", \"type\": \"EARN\", \"amount\": \"\", \"deduction_priority\": \"\"}, {\"code\": \"\", \"desc\": \"\", \"type\": \"EARN\", \"amount\": \"\", \"deduction_priority\": \"\"}, {\"code\": \"\", \"desc\": \"\", \"type\": \"EARN\", \"amount\": \"\", \"deduction_priority\": \"\"}], \"extra_tccs_enabled\": false, \"port_city_resident\": \"\", \"pension_proposal_no\": \"\", \"pension_proposal_date\": \"\", \"compassionate_allowance\": \"\", \"provisional_pension_pct\": null, \"vigilance_clearance_ref_dt\": \"\", \"vigilance_clearance_ref_no\": \"\", \"compassionate_allowance_amt\": null, \"eligible_double_family_pension\": false, \"double_family_pension_upto_date\": \"\"}','2026-05-27 08:38:31.575216','127.0.0.1','Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36','FIRST_PENSION',1),
(35,'PensionCase','13','UPDATE','{\"tqs\": \"38Y 0M 6D\", \"tccs\": \"38Y 0M 6D\", \"case_id\": 13, \"emp_code\": \"42230\", \"calculated\": true, \"last_basic\": 86300.0, \"no_pay_days\": 10, \"inputs_ready\": true, \"dies_non_days\": 7, \"total_service\": \"38Y 0M 6D\", \"pension_amount\": 43150.0, \"gratuity_amount\": 2000000.0, \"commutation_amount\": 1697141.28, \"commutation_percent\": 40.0, \"has_commutation_application\": true, \"commutation_percent_from_app\": 40.0}','{\"tqs\": \"37Y 11M 19D\", \"tccs\": \"37Y 11M 29D\", \"case_id\": 13, \"emp_code\": \"42230\", \"calculated\": true, \"last_basic\": 86300.0, \"no_pay_days\": 10, \"inputs_ready\": true, \"dies_non_days\": 7, \"total_service\": \"38Y 0M 6D\", \"pension_amount\": 43150.0, \"gratuity_amount\": 2000000.0, \"commutation_amount\": 1697142.0, \"commutation_percent\": 40.0, \"has_commutation_application\": true, \"commutation_percent_from_app\": 40.0}','2026-05-27 08:50:25.701906','127.0.0.1','Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36','FIRST_PENSION',1),
(36,'CommutationApplication','1','UPDATE','{\"id\": 1, \"emp_cd\": \"42230\", \"status\": \"COMMUTATION INITIATED\", \"appcn_dt\": \"2026-06-01\", \"appcn_no\": 5688, \"commutation_dt\": \"2026-06-01\", \"restoration_dt\": \"2026-06-01\", \"comm_start_mnth\": 6, \"commutation_per\": 40, \"application_time\": 1, \"impl_fpen_combill\": \"PEN\", \"mo_certificate_dt\": \"2026-05-21\", \"mo_certificate_ref\": \"MO/25-26/1\", \"application_rcvd_dt\": \"2026-06-01\", \"commutation_reasons\": \"House Repairing\"}','{\"id\": 1, \"emp_cd\": \"42230\", \"status\": \"COMMUTATION INITIATED\", \"appcn_dt\": \"2026-06-01\", \"appcn_no\": 5688, \"commutation_dt\": \"2026-06-01\", \"restoration_dt\": \"2026-06-01\", \"comm_start_mnth\": 6, \"commutation_per\": 40, \"application_time\": 1, \"impl_fpen_combill\": \"PEN\", \"mo_certificate_dt\": \"2026-05-21\", \"mo_certificate_ref\": \"MO/25-26/1\", \"application_rcvd_dt\": \"2026-06-01\", \"commutation_reasons\": \"House Repairing\"}','2026-05-27 09:21:42.124792','127.0.0.1','Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36','FIRST_PENSION',1),
(37,'PensionCase','13','UPDATE','{\"id\": 13, \"emp_code\": \"42230\", \"no_pay_days\": 10, \"dies_non_days\": 7, \"suspension_days\": 0, \"no_pay_more_than_240_days\": 0}','{\"id\": 13, \"emp_code\": \"42230\", \"no_pay_days\": 10, \"dies_non_days\": 7, \"suspension_days\": 0, \"no_pay_more_than_240_days\": 0}','2026-05-27 09:25:54.030167','127.0.0.1','Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36','FIRST_PENSION',1),
(38,'PensionProposal','4','CREATE',NULL,'{\"id\": 4, \"emp_cd\": \"42230\", \"bank_cd\": \"160061\", \"regn_no\": \"\", \"emp_name\": \"Mr. SWAPAN KUMAR NASKAR\", \"bank_name\": \"KOLKATA PORT TRUST(SUBHASH BHABAN)\", \"ca_number\": \"39999\", \"regn_date\": \"\", \"vr_ref_dt\": \"\", \"vr_ref_no\": \"\", \"account_no\": \"158201000002144\", \"start_year\": 2026, \"lic_bank_cd\": \"700001\", \"start_month\": 6, \"held_up_flag\": \"\", \"pension_type\": \"N\", \"lic_bank_name\": \"\", \"nominee_eform\": \"\", \"pension_option\": \"G\", \"quarter_status\": \"\", \"retirement_cpi\": \"359\", \"service_tenure\": \"From 26-05-1988 to 01-06-2026\", \"employee_status\": \"EMPLOYEE\", \"extra_tccs_days\": 0, \"gratuity_option\": \"1\", \"option_given_by\": \"E\", \"pension_roll_no\": \"LIC-9999\", \"separation_date\": \"2026-06-01\", \"separation_type\": \"RT\", \"extra_tccs_years\": 0, \"implemented_year\": 2026, \"incentive_holder\": \"\", \"extra_tccs_months\": 0, \"held_gratuity_amt\": null, \"id_card_submitted\": false, \"implemented_month\": 6, \"vigilance_cleared\": false, \"earning_deductions\": [{\"code\": \"200\", \"desc\": \"PENSION(RETIRING)\", \"type\": \"EARN\", \"amount\": \"\", \"deduction_priority\": \"\"}, {\"code\": \"203\", \"desc\": \"COMMUTATION\", \"type\": \"EARN\", \"amount\": \"\", \"deduction_priority\": \"\"}, {\"code\": \"205\", \"desc\": \"RET. GRATUITY OPT- I\", \"type\": \"EARN\", \"amount\": \"\", \"deduction_priority\": \"\"}, {\"code\": \"208\", \"desc\": \"RELIEF\", \"type\": \"EARN\", \"amount\": \"\", \"deduction_priority\": \"\"}], \"extra_tccs_enabled\": false, \"port_city_resident\": \"YES\", \"pension_proposal_no\": \"ABC/TEST/01\", \"pension_proposal_date\": \"2026-05-27\", \"compassionate_allowance\": \"\", \"provisional_pension_pct\": null, \"vigilance_clearance_ref_dt\": \"2026-05-20\", \"vigilance_clearance_ref_no\": \"VIG/99/2026/001\", \"compassionate_allowance_amt\": null, \"eligible_double_family_pension\": false, \"double_family_pension_upto_date\": \"\"}','2026-05-27 10:55:10.724470','127.0.0.1','Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36','FIRST_PENSION',1),
(39,'PensionProposal','4','UPDATE','{\"id\": 4, \"emp_cd\": \"42230\", \"bank_cd\": \"160061\", \"regn_no\": \"\", \"emp_name\": \"Mr. SWAPAN KUMAR NASKAR\", \"bank_name\": \"KOLKATA PORT TRUST(SUBHASH BHABAN)\", \"ca_number\": \"39999\", \"regn_date\": \"\", \"vr_ref_dt\": \"\", \"vr_ref_no\": \"\", \"account_no\": \"158201000002144\", \"start_year\": 2026, \"lic_bank_cd\": \"700001\", \"start_month\": 6, \"held_up_flag\": \"\", \"pension_type\": \"N\", \"lic_bank_name\": \"\", \"nominee_eform\": \"\", \"pension_option\": \"G\", \"quarter_status\": \"\", \"retirement_cpi\": 359.0, \"service_tenure\": \"From 26-05-1988 to 01-06-2026\", \"employee_status\": \"EMPLOYEE\", \"extra_tccs_days\": 0, \"gratuity_option\": \"1\", \"option_given_by\": \"E\", \"pension_roll_no\": \"LIC-9999\", \"separation_date\": \"2026-06-01\", \"separation_type\": \"RT\", \"extra_tccs_years\": 0, \"implemented_year\": 2026, \"incentive_holder\": \"\", \"extra_tccs_months\": 0, \"held_gratuity_amt\": null, \"id_card_submitted\": false, \"implemented_month\": 6, \"vigilance_cleared\": false, \"earning_deductions\": [{\"code\": \"200\", \"desc\": \"PENSION(RETIRING)\", \"type\": \"EARN\", \"amount\": \"\", \"deduction_priority\": \"\"}, {\"code\": \"203\", \"desc\": \"COMMUTATION\", \"type\": \"EARN\", \"amount\": \"\", \"deduction_priority\": \"\"}, {\"code\": \"205\", \"desc\": \"RET. GRATUITY OPT- I\", \"type\": \"EARN\", \"amount\": \"\", \"deduction_priority\": \"\"}, {\"code\": \"208\", \"desc\": \"RELIEF\", \"type\": \"EARN\", \"amount\": \"\", \"deduction_priority\": \"\"}], \"extra_tccs_enabled\": false, \"port_city_resident\": \"YES\", \"pension_proposal_no\": \"ABC/TEST/01\", \"pension_proposal_date\": \"2026-05-27\", \"compassionate_allowance\": \"\", \"provisional_pension_pct\": null, \"vigilance_clearance_ref_dt\": \"2026-05-20\", \"vigilance_clearance_ref_no\": \"VIG/99/2026/001\", \"compassionate_allowance_amt\": null, \"eligible_double_family_pension\": false, \"double_family_pension_upto_date\": \"\"}','{\"id\": 4, \"emp_cd\": \"42230\", \"bank_cd\": \"160061\", \"regn_no\": \"\", \"emp_name\": \"Mr. SWAPAN KUMAR NASKAR\", \"bank_name\": \"KOLKATA PORT TRUST(SUBHASH BHABAN)\", \"ca_number\": \"39999\", \"regn_date\": \"\", \"vr_ref_dt\": \"\", \"vr_ref_no\": \"\", \"account_no\": \"158201000002144\", \"start_year\": 2026, \"lic_bank_cd\": \"700001\", \"start_month\": 6, \"held_up_flag\": \"\", \"pension_type\": \"N\", \"lic_bank_name\": \"\", \"nominee_eform\": \"\", \"pension_option\": \"G\", \"quarter_status\": \"\", \"retirement_cpi\": 359, \"service_tenure\": \"From 26-05-1988 to 01-06-2026\", \"employee_status\": \"EMPLOYEE\", \"extra_tccs_days\": 0, \"gratuity_option\": \"1\", \"option_given_by\": \"E\", \"pension_roll_no\": \"LIC-9999\", \"separation_date\": \"2026-06-01\", \"separation_type\": \"RT\", \"extra_tccs_years\": 0, \"implemented_year\": 2026, \"incentive_holder\": \"\", \"extra_tccs_months\": 0, \"held_gratuity_amt\": null, \"id_card_submitted\": false, \"implemented_month\": 6, \"vigilance_cleared\": true, \"earning_deductions\": [{\"code\": \"200\", \"desc\": \"PENSION(RETIRING)\", \"type\": \"EARN\", \"amount\": \"\", \"deduction_priority\": \"\"}, {\"code\": \"203\", \"desc\": \"COMMUTATION\", \"type\": \"EARN\", \"amount\": \"\", \"deduction_priority\": \"\"}, {\"code\": \"205\", \"desc\": \"RET. GRATUITY OPT- I\", \"type\": \"EARN\", \"amount\": \"\", \"deduction_priority\": \"\"}, {\"code\": \"208\", \"desc\": \"RELIEF\", \"type\": \"EARN\", \"amount\": \"\", \"deduction_priority\": \"\"}], \"extra_tccs_enabled\": false, \"port_city_resident\": \"YES\", \"pension_proposal_no\": \"ABC/TEST/01\", \"pension_proposal_date\": \"2026-05-27\", \"compassionate_allowance\": \"\", \"provisional_pension_pct\": null, \"vigilance_clearance_ref_dt\": \"2026-05-20\", \"vigilance_clearance_ref_no\": \"VIG/99/2026/001\", \"compassionate_allowance_amt\": null, \"eligible_double_family_pension\": false, \"double_family_pension_upto_date\": \"\"}','2026-05-27 11:14:56.760908','127.0.0.1','Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36','FIRST_PENSION',1),
(40,'PensionProposal','4','UPDATE','{\"id\": 4, \"emp_cd\": \"42230\", \"bank_cd\": \"160061\", \"regn_no\": \"\", \"emp_name\": \"Mr. SWAPAN KUMAR NASKAR\", \"bank_name\": \"KOLKATA PORT TRUST(SUBHASH BHABAN)\", \"ca_number\": \"39999\", \"regn_date\": \"\", \"vr_ref_dt\": \"\", \"vr_ref_no\": \"\", \"account_no\": \"158201000002144\", \"start_year\": 2026, \"lic_bank_cd\": \"700001\", \"start_month\": 6, \"held_up_flag\": \"\", \"pension_type\": \"N\", \"lic_bank_name\": \"\", \"nominee_eform\": \"\", \"pension_option\": \"G\", \"quarter_status\": \"\", \"retirement_cpi\": 359.0, \"service_tenure\": \"From 26-05-1988 to 01-06-2026\", \"employee_status\": \"EMPLOYEE\", \"extra_tccs_days\": 0, \"gratuity_option\": \"1\", \"option_given_by\": \"E\", \"pension_roll_no\": \"LIC-9999\", \"separation_date\": \"2026-06-01\", \"separation_type\": \"RT\", \"extra_tccs_years\": 0, \"implemented_year\": 2026, \"incentive_holder\": \"\", \"extra_tccs_months\": 0, \"held_gratuity_amt\": null, \"id_card_submitted\": false, \"implemented_month\": 6, \"vigilance_cleared\": true, \"earning_deductions\": [{\"code\": \"200\", \"desc\": \"PENSION(RETIRING)\", \"type\": \"EARN\", \"amount\": \"\", \"deduction_priority\": \"\"}, {\"code\": \"203\", \"desc\": \"COMMUTATION\", \"type\": \"EARN\", \"amount\": \"\", \"deduction_priority\": \"\"}, {\"code\": \"205\", \"desc\": \"RET. GRATUITY OPT- I\", \"type\": \"EARN\", \"amount\": \"\", \"deduction_priority\": \"\"}, {\"code\": \"208\", \"desc\": \"RELIEF\", \"type\": \"EARN\", \"amount\": \"\", \"deduction_priority\": \"\"}], \"extra_tccs_enabled\": false, \"port_city_resident\": \"YES\", \"pension_proposal_no\": \"ABC/TEST/01\", \"pension_proposal_date\": \"2026-05-27\", \"compassionate_allowance\": \"\", \"provisional_pension_pct\": null, \"vigilance_clearance_ref_dt\": \"2026-05-20\", \"vigilance_clearance_ref_no\": \"VIG/99/2026/001\", \"compassionate_allowance_amt\": null, \"eligible_double_family_pension\": false, \"double_family_pension_upto_date\": \"\"}','{\"id\": 4, \"emp_cd\": \"42230\", \"bank_cd\": \"160061\", \"regn_no\": \"\", \"emp_name\": \"Mr. SWAPAN KUMAR NASKAR\", \"bank_name\": \"KOLKATA PORT TRUST(SUBHASH BHABAN)\", \"ca_number\": \"39999\", \"regn_date\": \"\", \"vr_ref_dt\": \"\", \"vr_ref_no\": \"\", \"account_no\": \"158201000002144\", \"start_year\": 2026, \"lic_bank_cd\": \"700001\", \"start_month\": 6, \"held_up_flag\": \"\", \"pension_type\": \"N\", \"lic_bank_name\": \"\", \"nominee_eform\": \"\", \"pension_option\": \"G\", \"quarter_status\": \"\", \"retirement_cpi\": 359, \"service_tenure\": \"From 26-05-1988 to 01-06-2026\", \"employee_status\": \"EMPLOYEE\", \"extra_tccs_days\": 0, \"gratuity_option\": \"1\", \"option_given_by\": \"E\", \"pension_roll_no\": \"LIC-9999\", \"separation_date\": \"2026-06-01\", \"separation_type\": \"RT\", \"extra_tccs_years\": 0, \"implemented_year\": 2026, \"incentive_holder\": \"\", \"extra_tccs_months\": 0, \"held_gratuity_amt\": null, \"id_card_submitted\": true, \"implemented_month\": 6, \"vigilance_cleared\": true, \"earning_deductions\": [{\"code\": \"200\", \"desc\": \"PENSION(RETIRING)\", \"type\": \"EARN\", \"amount\": \"\", \"deduction_priority\": \"\"}, {\"code\": \"203\", \"desc\": \"COMMUTATION\", \"type\": \"EARN\", \"amount\": \"\", \"deduction_priority\": \"\"}, {\"code\": \"205\", \"desc\": \"RET. GRATUITY OPT- I\", \"type\": \"EARN\", \"amount\": \"\", \"deduction_priority\": \"\"}, {\"code\": \"208\", \"desc\": \"RELIEF\", \"type\": \"EARN\", \"amount\": \"\", \"deduction_priority\": \"\"}], \"extra_tccs_enabled\": false, \"port_city_resident\": \"YES\", \"pension_proposal_no\": \"ABC/TEST/01\", \"pension_proposal_date\": \"2026-05-27\", \"compassionate_allowance\": \"\", \"provisional_pension_pct\": null, \"vigilance_clearance_ref_dt\": \"2026-05-20\", \"vigilance_clearance_ref_no\": \"VIG/99/2026/001\", \"compassionate_allowance_amt\": null, \"eligible_double_family_pension\": false, \"double_family_pension_upto_date\": \"\"}','2026-05-27 11:15:18.136687','127.0.0.1','Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36','FIRST_PENSION',1),
(41,'PensionProposal','4','UPDATE','{\"id\": 4, \"emp_cd\": \"42230\", \"bank_cd\": \"160061\", \"regn_no\": \"\", \"emp_name\": \"Mr. SWAPAN KUMAR NASKAR\", \"bank_name\": \"KOLKATA PORT TRUST(SUBHASH BHABAN)\", \"ca_number\": \"39999\", \"regn_date\": \"\", \"vr_ref_dt\": \"\", \"vr_ref_no\": \"\", \"account_no\": \"158201000002144\", \"start_year\": 2026, \"lic_bank_cd\": \"700001\", \"start_month\": 6, \"held_up_flag\": \"\", \"pension_type\": \"N\", \"lic_bank_name\": \"\", \"nominee_eform\": \"\", \"pension_option\": \"G\", \"quarter_status\": \"\", \"retirement_cpi\": 359.0, \"service_tenure\": \"From 26-05-1988 to 01-06-2026\", \"employee_status\": \"EMPLOYEE\", \"extra_tccs_days\": 0, \"gratuity_option\": \"1\", \"option_given_by\": \"E\", \"pension_roll_no\": \"LIC-9999\", \"separation_date\": \"2026-06-01\", \"separation_type\": \"RT\", \"extra_tccs_years\": 0, \"implemented_year\": 2026, \"incentive_holder\": \"\", \"extra_tccs_months\": 0, \"held_gratuity_amt\": null, \"id_card_submitted\": true, \"implemented_month\": 6, \"vigilance_cleared\": true, \"earning_deductions\": [{\"code\": \"200\", \"desc\": \"PENSION(RETIRING)\", \"type\": \"EARN\", \"amount\": \"\", \"deduction_priority\": \"\"}, {\"code\": \"203\", \"desc\": \"COMMUTATION\", \"type\": \"EARN\", \"amount\": \"\", \"deduction_priority\": \"\"}, {\"code\": \"205\", \"desc\": \"RET. GRATUITY OPT- I\", \"type\": \"EARN\", \"amount\": \"\", \"deduction_priority\": \"\"}, {\"code\": \"208\", \"desc\": \"RELIEF\", \"type\": \"EARN\", \"amount\": \"\", \"deduction_priority\": \"\"}], \"extra_tccs_enabled\": false, \"port_city_resident\": \"YES\", \"pension_proposal_no\": \"ABC/TEST/01\", \"pension_proposal_date\": \"2026-05-27\", \"compassionate_allowance\": \"\", \"provisional_pension_pct\": null, \"vigilance_clearance_ref_dt\": \"2026-05-20\", \"vigilance_clearance_ref_no\": \"VIG/99/2026/001\", \"compassionate_allowance_amt\": null, \"eligible_double_family_pension\": false, \"double_family_pension_upto_date\": \"\"}','{\"id\": 4, \"emp_cd\": \"42230\", \"bank_cd\": \"160061\", \"regn_no\": \"\", \"emp_name\": \"Mr. SWAPAN KUMAR NASKAR\", \"bank_name\": \"KOLKATA PORT TRUST(SUBHASH BHABAN)\", \"ca_number\": \"39999\", \"regn_date\": \"\", \"vr_ref_dt\": \"\", \"vr_ref_no\": \"\", \"account_no\": \"158201000002144\", \"start_year\": 2026, \"lic_bank_cd\": \"700001\", \"start_month\": 6, \"held_up_flag\": \"\", \"pension_type\": \"N\", \"lic_bank_name\": \"\", \"nominee_eform\": \"\", \"pension_option\": \"G\", \"quarter_status\": \"\", \"retirement_cpi\": 359, \"service_tenure\": \"38Y 0M 6D\", \"employee_status\": \"EMPLOYEE\", \"extra_tccs_days\": 0, \"gratuity_option\": \"1\", \"option_given_by\": \"E\", \"pension_roll_no\": \"LIC-9999\", \"separation_date\": \"2026-06-01\", \"separation_type\": \"RT\", \"extra_tccs_years\": 0, \"implemented_year\": 2026, \"incentive_holder\": \"\", \"extra_tccs_months\": 0, \"held_gratuity_amt\": null, \"id_card_submitted\": true, \"implemented_month\": 6, \"vigilance_cleared\": true, \"earning_deductions\": [{\"code\": \"200\", \"desc\": \"PENSION(RETIRING)\", \"type\": \"EARN\", \"amount\": \"\", \"deduction_priority\": \"\"}, {\"code\": \"203\", \"desc\": \"COMMUTATION\", \"type\": \"EARN\", \"amount\": \"\", \"deduction_priority\": \"\"}, {\"code\": \"205\", \"desc\": \"RET. GRATUITY OPT- I\", \"type\": \"EARN\", \"amount\": \"\", \"deduction_priority\": \"\"}, {\"code\": \"208\", \"desc\": \"RELIEF\", \"type\": \"EARN\", \"amount\": \"\", \"deduction_priority\": \"\"}], \"extra_tccs_enabled\": false, \"port_city_resident\": \"YES\", \"pension_proposal_no\": \"ABC/TEST/01\", \"pension_proposal_date\": \"2026-05-27\", \"compassionate_allowance\": \"\", \"provisional_pension_pct\": null, \"vigilance_clearance_ref_dt\": \"2026-05-20\", \"vigilance_clearance_ref_no\": \"VIG/99/2026/001\", \"compassionate_allowance_amt\": null, \"eligible_double_family_pension\": false, \"double_family_pension_upto_date\": \"\"}','2026-05-27 11:20:19.968839','127.0.0.1','Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36','FIRST_PENSION',1),
(42,'PensionCase','13','UPDATE','{\"tqs\": \"37Y 11M 19D\", \"tccs\": \"37Y 11M 29D\", \"case_id\": 13, \"emp_code\": \"42230\", \"calculated\": true, \"last_basic\": 86300.0, \"no_pay_days\": 10, \"inputs_ready\": true, \"dies_non_days\": 7, \"total_service\": \"38Y 0M 6D\", \"pension_amount\": 43150.0, \"gratuity_amount\": 2000000.0, \"commutation_amount\": 1697142.0, \"commutation_percent\": 40.0, \"has_commutation_application\": true, \"commutation_percent_from_app\": 40.0}','{\"tqs\": \"37Y 11M 19D\", \"tccs\": \"37Y 11M 29D\", \"case_id\": 13, \"emp_code\": \"42230\", \"calculated\": true, \"last_basic\": 86300.0, \"no_pay_days\": 10, \"inputs_ready\": true, \"dies_non_days\": 7, \"total_service\": \"38Y 0M 6D\", \"pension_amount\": 43150.0, \"gratuity_amount\": 2000000.0, \"commutation_amount\": 1697142.0, \"commutation_percent\": 40.0, \"has_commutation_application\": true, \"commutation_percent_from_app\": 40.0}','2026-05-27 11:20:29.664769','127.0.0.1','Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36','FIRST_PENSION',1),
(43,'accounts_user','6','CREATE',NULL,'{\"id\": 6, \"email\": \"audit@test.com\", \"profile\": {\"emp_code\": \"E001\", \"mobile_no\": \"\", \"department\": \"\", \"designation\": \"\"}, \"role_id\": 2, \"username\": \"audit_test_user\", \"is_active\": true, \"last_name\": \"Test\", \"role_code\": \"FIRST_PENSION_USER\", \"role_name\": \"First Pension User\", \"first_name\": \"Audit\", \"date_joined\": \"2026-05-28T17:30:54.539827Z\", \"display_name\": \"Audit Test\"}','2026-05-28 17:30:54.856920','127.0.0.1',NULL,'USER_MANAGEMENT',1),
(44,'accounts_user','6','UPDATE','{\"id\": 6, \"email\": \"audit@test.com\", \"profile\": {\"emp_code\": \"E001\", \"mobile_no\": \"\", \"department\": \"\", \"designation\": \"\"}, \"role_id\": 2, \"username\": \"audit_test_user\", \"is_active\": true, \"last_name\": \"Test\", \"role_code\": \"FIRST_PENSION_USER\", \"role_name\": \"First Pension User\", \"first_name\": \"Audit\", \"date_joined\": \"2026-05-28T17:30:54.539827Z\", \"display_name\": \"Audit Test\"}','{\"id\": 6, \"email\": \"audit@test.com\", \"profile\": {\"emp_code\": \"E001\", \"mobile_no\": \"\", \"department\": \"\", \"designation\": \"\"}, \"role_id\": 2, \"username\": \"audit_test_user\", \"is_active\": false, \"last_name\": \"Test\", \"role_code\": \"FIRST_PENSION_USER\", \"role_name\": \"First Pension User\", \"first_name\": \"Audit\", \"date_joined\": \"2026-05-28T17:30:54.539827Z\", \"display_name\": \"Audit Test\"}','2026-05-28 17:30:54.873300','127.0.0.1',NULL,'USER_MANAGEMENT',1),
(45,'CommutationApplication','4','CREATE',NULL,'{\"id\": 4, \"emp_cd\": \"44391\", \"status\": \"COMMUTATION INITIATED\", \"appcn_dt\": \"2007-02-01\", \"appcn_no\": \"5689\", \"commutation_dt\": \"2007-02-01\", \"restoration_dt\": \"2007-02-01\", \"comm_start_mnth\": \"02\", \"commutation_per\": 40.0, \"application_time\": 1, \"impl_fpen_combill\": \"PEN\", \"mo_certificate_dt\": \"\", \"mo_certificate_ref\": \"\", \"application_rcvd_dt\": \"2007-02-01\", \"commutation_reasons\": \"Urgent need of money\"}','2026-06-01 07:26:00.817193','127.0.0.1','Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36','FIRST_PENSION',3),
(46,'PensionCase','20','CREATE',NULL,'{\"id\": 20, \"emp_code\": \"44391\", \"no_pay_days\": 5, \"dies_non_days\": 32, \"suspension_days\": 0, \"no_pay_more_than_240_days\": 0}','2026-06-01 07:26:25.279853','127.0.0.1','Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36','FIRST_PENSION',3),
(47,'PensionProposal','5','CREATE',NULL,'{\"id\": 5, \"emp_cd\": \"44391\", \"bank_cd\": \"010129\", \"regn_no\": \"VI/K/89\", \"emp_name\": \"Mr. KASHINATH  PAUL\", \"bank_name\": \"HOWRAH RLY. STN. (HRS)\", \"ca_number\": \"33051\", \"regn_date\": \"1994-07-29\", \"vr_ref_dt\": \"\", \"vr_ref_no\": \"\", \"account_no\": \"01190008042\", \"start_year\": 2007, \"lic_bank_cd\": \"700001\", \"start_month\": 2, \"held_up_flag\": \"N\", \"pension_type\": \"N\", \"lic_bank_name\": \"LIC\", \"nominee_eform\": \"\", \"pension_option\": \"G\", \"quarter_status\": \"\", \"retirement_cpi\": \"1708\", \"service_tenure\": \"23Y 1M 1D\", \"employee_status\": \"EMPLOYEE\", \"extra_tccs_days\": 0, \"gratuity_option\": \"1\", \"option_given_by\": \"E\", \"pension_roll_no\": \"LIC-1177\", \"separation_date\": \"2007-02-01\", \"separation_type\": \"RT\", \"extra_tccs_years\": 0, \"implemented_year\": 2007, \"incentive_holder\": \"\", \"extra_tccs_months\": 0, \"held_gratuity_amt\": null, \"id_card_submitted\": true, \"implemented_month\": 2, \"vigilance_cleared\": true, \"earning_deductions\": [{\"code\": \"200\", \"desc\": \"PENSION(RETIRING)\", \"type\": \"EARN\", \"amount\": \"\", \"deduction_priority\": \"\"}, {\"code\": \"203\", \"desc\": \"COMMUTATION\", \"type\": \"EARN\", \"amount\": \"\", \"deduction_priority\": \"\"}, {\"code\": \"205\", \"desc\": \"RET. GRATUITY OPT- I\", \"type\": \"EARN\", \"amount\": \"\", \"deduction_priority\": \"\"}, {\"code\": \"208\", \"desc\": \"RELIEF\", \"type\": \"EARN\", \"amount\": \"\", \"deduction_priority\": \"\"}], \"extra_tccs_enabled\": false, \"port_city_resident\": \"NO\", \"pension_proposal_no\": \"MRN/CH/1860/1276\", \"pension_proposal_date\": \"2006-06-30\", \"compassionate_allowance\": \"\", \"provisional_pension_pct\": null, \"vigilance_clearance_ref_dt\": \"2006-08-10\", \"vigilance_clearance_ref_no\": \"VIG/SARO/30/2006/878\", \"compassionate_allowance_amt\": null, \"eligible_double_family_pension\": false, \"double_family_pension_upto_date\": \"\"}','2026-06-01 07:31:35.793656','127.0.0.1','Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36','FIRST_PENSION',3),
(48,'PensionCase','20','CREATE',NULL,'{\"tqs\": \"22Y 11M 26D\", \"tccs\": \"23Y 0M 0D\", \"case_id\": 20, \"emp_code\": \"44391\", \"calculated\": true, \"last_basic\": 16090.0, \"no_pay_days\": 5, \"inputs_ready\": true, \"dies_non_days\": 32, \"total_service\": \"23Y 1M 1D\", \"pension_amount\": 8045.0, \"gratuity_amount\": 254217.0, \"commutation_amount\": 316420.0, \"commutation_percent\": 40.0, \"has_commutation_application\": true, \"commutation_percent_from_app\": 40.0}','2026-06-01 07:31:52.303661','127.0.0.1','Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36','FIRST_PENSION',3),
(49,'PensionProposal','4','UPDATE','{\"id\": 4, \"emp_cd\": \"42230\", \"bank_cd\": \"160061\", \"regn_no\": \"\", \"emp_name\": \"Mr. SWAPAN KUMAR NASKAR\", \"bank_name\": \"KOLKATA PORT TRUST(SUBHASH BHABAN)\", \"ca_number\": \"39999\", \"regn_date\": \"\", \"vr_ref_dt\": \"\", \"vr_ref_no\": \"\", \"account_no\": \"158201000002144\", \"start_year\": 2026, \"lic_bank_cd\": \"700001\", \"start_month\": 6, \"held_up_flag\": \"\", \"pension_type\": \"N\", \"lic_bank_name\": \"\", \"nominee_eform\": \"\", \"pension_option\": \"G\", \"quarter_status\": \"\", \"retirement_cpi\": 359.0, \"service_tenure\": \"38Y 0M 6D\", \"employee_status\": \"EMPLOYEE\", \"extra_tccs_days\": 0, \"gratuity_option\": \"1\", \"option_given_by\": \"E\", \"pension_roll_no\": \"LIC-9999\", \"separation_date\": \"2026-06-01\", \"separation_type\": \"RT\", \"extra_tccs_years\": 0, \"implemented_year\": 2026, \"incentive_holder\": \"\", \"extra_tccs_months\": 0, \"held_gratuity_amt\": null, \"id_card_submitted\": true, \"implemented_month\": 6, \"vigilance_cleared\": true, \"earning_deductions\": [{\"code\": \"200\", \"desc\": \"PENSION(RETIRING)\", \"type\": \"EARN\", \"amount\": \"\", \"deduction_priority\": \"\"}, {\"code\": \"203\", \"desc\": \"COMMUTATION\", \"type\": \"EARN\", \"amount\": \"\", \"deduction_priority\": \"\"}, {\"code\": \"205\", \"desc\": \"RET. GRATUITY OPT- I\", \"type\": \"EARN\", \"amount\": \"\", \"deduction_priority\": \"\"}, {\"code\": \"208\", \"desc\": \"RELIEF\", \"type\": \"EARN\", \"amount\": \"\", \"deduction_priority\": \"\"}], \"extra_tccs_enabled\": false, \"port_city_resident\": \"YES\", \"pension_proposal_no\": \"ABC/TEST/01\", \"pension_proposal_date\": \"2026-05-27\", \"compassionate_allowance\": \"\", \"provisional_pension_pct\": null, \"vigilance_clearance_ref_dt\": \"2026-05-20\", \"vigilance_clearance_ref_no\": \"VIG/99/2026/001\", \"compassionate_allowance_amt\": null, \"eligible_double_family_pension\": false, \"double_family_pension_upto_date\": \"\"}','{\"id\": 4, \"emp_cd\": \"42230\", \"bank_cd\": \"160061\", \"regn_no\": \"\", \"emp_name\": \"Mr. SWAPAN KUMAR NASKAR\", \"bank_name\": \"KOLKATA PORT TRUST(SUBHASH BHABAN)\", \"ca_number\": \"39999\", \"regn_date\": \"\", \"vr_ref_dt\": \"\", \"vr_ref_no\": \"\", \"account_no\": \"158201000002144\", \"start_year\": 2026, \"lic_bank_cd\": \"700001\", \"start_month\": 6, \"held_up_flag\": \"\", \"pension_type\": \"N\", \"lic_bank_name\": \"\", \"nominee_eform\": \"\", \"pension_option\": \"G\", \"quarter_status\": \"\", \"retirement_cpi\": 359, \"service_tenure\": \"38Y 0M 6D\", \"employee_status\": \"P\", \"extra_tccs_days\": 0, \"gratuity_option\": \"1\", \"option_given_by\": \"E\", \"pension_roll_no\": \"LIC-9999\", \"separation_date\": \"2026-06-01\", \"separation_type\": \"RT\", \"extra_tccs_years\": 0, \"implemented_year\": 2026, \"incentive_holder\": \"\", \"extra_tccs_months\": 0, \"held_gratuity_amt\": null, \"id_card_submitted\": true, \"implemented_month\": 6, \"vigilance_cleared\": true, \"earning_deductions\": [{\"code\": \"200\", \"desc\": \"PENSION(RETIRING)\", \"type\": \"EARN\", \"amount\": \"\", \"deduction_priority\": \"\"}, {\"code\": \"203\", \"desc\": \"COMMUTATION\", \"type\": \"EARN\", \"amount\": \"\", \"deduction_priority\": \"\"}, {\"code\": \"205\", \"desc\": \"RET. GRATUITY OPT- I\", \"type\": \"EARN\", \"amount\": \"\", \"deduction_priority\": \"\"}, {\"code\": \"208\", \"desc\": \"RELIEF\", \"type\": \"EARN\", \"amount\": \"\", \"deduction_priority\": \"\"}], \"extra_tccs_enabled\": false, \"port_city_resident\": \"YES\", \"pension_proposal_no\": \"ABC/TEST/01\", \"pension_proposal_date\": \"2026-05-27\", \"compassionate_allowance\": \"\", \"provisional_pension_pct\": null, \"vigilance_clearance_ref_dt\": \"2026-05-20\", \"vigilance_clearance_ref_no\": \"VIG/99/2026/001\", \"compassionate_allowance_amt\": null, \"eligible_double_family_pension\": false, \"double_family_pension_upto_date\": \"\"}','2026-06-01 09:43:23.130346','127.0.0.1','Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36','FIRST_PENSION',3),
(50,'PensionCase','13','UPDATE','{\"tqs\": \"37Y 11M 19D\", \"tccs\": \"37Y 11M 29D\", \"case_id\": 13, \"emp_code\": \"42230\", \"calculated\": true, \"last_basic\": 86300.0, \"no_pay_days\": 10, \"inputs_ready\": true, \"dies_non_days\": 7, \"total_service\": \"38Y 0M 6D\", \"pension_amount\": 43150.0, \"gratuity_amount\": 2000000.0, \"commutation_amount\": 1697142.0, \"commutation_percent\": 40.0, \"has_commutation_application\": true, \"commutation_percent_from_app\": 40.0}','{\"tqs\": \"37Y 11M 19D\", \"tccs\": \"37Y 11M 29D\", \"case_id\": 13, \"emp_code\": \"42230\", \"calculated\": true, \"last_basic\": 86300.0, \"no_pay_days\": 10, \"inputs_ready\": true, \"dies_non_days\": 7, \"total_service\": \"38Y 0M 6D\", \"pension_amount\": 43150.0, \"gratuity_amount\": 2000000.0, \"commutation_amount\": 1697142.0, \"commutation_percent\": 40.0, \"has_commutation_application\": true, \"commutation_percent_from_app\": 40.0}','2026-06-02 06:34:17.200193','192.168.4.102','Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36','FIRST_PENSION',3),
(51,'PensionProposal','4','UPDATE','{\"id\": 4, \"emp_cd\": \"42230\", \"bank_cd\": \"160061\", \"regn_no\": \"\", \"emp_name\": \"Mr. SWAPAN KUMAR NASKAR\", \"bank_name\": \"KOLKATA PORT TRUST(SUBHASH BHABAN)\", \"ca_number\": \"39999\", \"regn_date\": \"\", \"vr_ref_dt\": \"\", \"vr_ref_no\": \"\", \"account_no\": \"158201000002144\", \"start_year\": 2026, \"lic_bank_cd\": \"700001\", \"start_month\": 6, \"held_up_flag\": \"\", \"pension_type\": \"N\", \"lic_bank_name\": \"\", \"nominee_eform\": \"\", \"pension_option\": \"G\", \"quarter_status\": \"\", \"retirement_cpi\": 359.0, \"service_tenure\": \"38Y 0M 6D\", \"employee_status\": \"P\", \"extra_tccs_days\": 0, \"gratuity_option\": \"1\", \"option_given_by\": \"E\", \"pension_roll_no\": \"LIC-9999\", \"separation_date\": \"2026-06-01\", \"separation_type\": \"RT\", \"extra_tccs_years\": 0, \"implemented_year\": 2026, \"incentive_holder\": \"\", \"extra_tccs_months\": 0, \"held_gratuity_amt\": null, \"id_card_submitted\": true, \"implemented_month\": 6, \"vigilance_cleared\": true, \"earning_deductions\": [{\"code\": \"200\", \"desc\": \"PENSION(RETIRING)\", \"type\": \"EARN\", \"amount\": \"\", \"deduction_priority\": \"\"}, {\"code\": \"203\", \"desc\": \"COMMUTATION\", \"type\": \"EARN\", \"amount\": \"\", \"deduction_priority\": \"\"}, {\"code\": \"205\", \"desc\": \"RET. GRATUITY OPT- I\", \"type\": \"EARN\", \"amount\": \"\", \"deduction_priority\": \"\"}, {\"code\": \"208\", \"desc\": \"RELIEF\", \"type\": \"EARN\", \"amount\": \"\", \"deduction_priority\": \"\"}], \"extra_tccs_enabled\": false, \"port_city_resident\": \"YES\", \"pension_proposal_no\": \"ABC/TEST/01\", \"pension_proposal_date\": \"2026-05-27\", \"compassionate_allowance\": \"\", \"provisional_pension_pct\": null, \"vigilance_clearance_ref_dt\": \"2026-05-20\", \"vigilance_clearance_ref_no\": \"VIG/99/2026/001\", \"compassionate_allowance_amt\": null, \"eligible_double_family_pension\": false, \"double_family_pension_upto_date\": \"\"}','{\"id\": 4, \"emp_cd\": \"42230\", \"bank_cd\": \"160061\", \"regn_no\": \"X/S-543\", \"emp_name\": \"Mr. SWAPAN KUMAR NASKAR\", \"bank_name\": \"KOLKATA PORT TRUST(SUBHASH BHABAN)\", \"ca_number\": \"39999\", \"regn_date\": \"2026-05-28\", \"vr_ref_dt\": \"\", \"vr_ref_no\": \"\", \"account_no\": \"158201000002144\", \"start_year\": 2026, \"lic_bank_cd\": \"700001\", \"start_month\": 6, \"held_up_flag\": \"\", \"pension_type\": \"N\", \"lic_bank_name\": \"\", \"nominee_eform\": \"\", \"pension_option\": \"G\", \"quarter_status\": \"\", \"retirement_cpi\": 359, \"service_tenure\": \"38Y 0M 6D\", \"employee_status\": \"P\", \"extra_tccs_days\": 0, \"gratuity_option\": \"1\", \"option_given_by\": \"E\", \"pension_roll_no\": \"LIC-9999\", \"separation_date\": \"2026-06-01\", \"separation_type\": \"RT\", \"extra_tccs_years\": 0, \"implemented_year\": 2026, \"incentive_holder\": \"\", \"extra_tccs_months\": 0, \"held_gratuity_amt\": null, \"id_card_submitted\": true, \"implemented_month\": 6, \"vigilance_cleared\": true, \"earning_deductions\": [{\"code\": \"200\", \"desc\": \"PENSION(RETIRING)\", \"type\": \"EARN\", \"amount\": \"\", \"deduction_priority\": \"\"}, {\"code\": \"203\", \"desc\": \"COMMUTATION\", \"type\": \"EARN\", \"amount\": \"\", \"deduction_priority\": \"\"}, {\"code\": \"205\", \"desc\": \"RET. GRATUITY OPT- I\", \"type\": \"EARN\", \"amount\": \"\", \"deduction_priority\": \"\"}, {\"code\": \"208\", \"desc\": \"RELIEF\", \"type\": \"EARN\", \"amount\": \"\", \"deduction_priority\": \"\"}], \"extra_tccs_enabled\": false, \"port_city_resident\": \"YES\", \"pension_proposal_no\": \"ABC/TEST/01\", \"pension_proposal_date\": \"2026-05-27\", \"compassionate_allowance\": \"\", \"provisional_pension_pct\": null, \"vigilance_clearance_ref_dt\": \"2026-05-20\", \"vigilance_clearance_ref_no\": \"VIG/99/2026/001\", \"compassionate_allowance_amt\": null, \"eligible_double_family_pension\": false, \"double_family_pension_upto_date\": \"\"}','2026-06-02 07:44:59.067928','192.168.4.102','Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36','FIRST_PENSION',3),
(52,'CommutationApplication','5','CREATE',NULL,'{\"id\": 5, \"emp_cd\": \"43694\", \"status\": \"COMMUTATION INITIATED\", \"appcn_dt\": \"2026-06-01\", \"appcn_no\": \"5690\", \"commutation_dt\": \"2026-06-01\", \"restoration_dt\": \"2026-05-21\", \"comm_start_mnth\": \"06\", \"commutation_per\": 40.0, \"application_time\": 1, \"impl_fpen_combill\": \"PEN\", \"mo_certificate_dt\": \"\", \"mo_certificate_ref\": \"\", \"application_rcvd_dt\": \"2026-06-01\", \"commutation_reasons\": \"gfjhgk\"}','2026-06-02 07:47:56.142319','192.168.4.102','Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36','FIRST_PENSION',3),
(53,'PensionCase','18','UPDATE','{\"remarks\": \"\", \"separation_date\": \"\", \"separation_type\": \"\"}','{\"remarks\": \"Superannuation\", \"separation_date\": \"2026-06-01\", \"separation_type\": \"RT\"}','2026-06-02 09:46:14.982986','192.168.4.102','Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36','FIRST_PENSION',3),
(54,'PensionProposal','1','UPDATE','{\"id\": 1, \"emp_cd\": \"46299\", \"bank_cd\": \"010127\", \"regn_no\": \"X/REG/1\", \"emp_name\": \"Mrs. RAHIMA  KHATOON\", \"bank_name\": \"GARDEN REACH (GAR)\", \"ca_number\": \"38562\", \"regn_date\": \"2026-05-21\", \"vr_ref_dt\": \"\", \"vr_ref_no\": \"\", \"account_no\": \"10320782829\", \"start_year\": 2026, \"lic_bank_cd\": \"700001\", \"start_month\": 6, \"held_up_flag\": \"\", \"pension_type\": \"PN\", \"lic_bank_name\": \"\", \"nominee_eform\": \"\", \"pension_option\": \"G\", \"quarter_status\": \"\", \"retirement_cpi\": null, \"service_tenure\": \"From 11-05-1994 to 01-06-2026\", \"employee_status\": \"EMPLOYEE\", \"extra_tccs_days\": 0, \"gratuity_option\": \"\", \"option_given_by\": \"E\", \"pension_roll_no\": \"ROLL1\", \"separation_date\": \"2026-06-01\", \"separation_type\": \"RT\", \"extra_tccs_years\": 0, \"implemented_year\": 2026, \"incentive_holder\": \"\", \"extra_tccs_months\": 0, \"held_gratuity_amt\": null, \"id_card_submitted\": false, \"implemented_month\": 6, \"vigilance_cleared\": false, \"earning_deductions\": [{\"code\": \"200\", \"desc\": \"PENSION(RETIRING)\", \"type\": \"EARN\", \"amount\": \"\", \"deduction_priority\": \"\"}, {\"code\": \"203\", \"desc\": \"COMMUTATION\", \"type\": \"EARN\", \"amount\": \"\", \"deduction_priority\": \"\"}, {\"code\": \"208\", \"desc\": \"RELIEF\", \"type\": \"EARN\", \"amount\": \"\", \"deduction_priority\": \"\"}, {\"code\": \"205\", \"desc\": \"RET. GRATUITY OPT- I\", \"type\": \"EARN\", \"amount\": \"\", \"deduction_priority\": \"\"}], \"extra_tccs_enabled\": false, \"port_city_resident\": \"\", \"pension_proposal_no\": \"PP/ABC/1\", \"pension_proposal_date\": \"2026-06-01\", \"compassionate_allowance\": \"\", \"provisional_pension_pct\": null, \"vigilance_clearance_ref_dt\": \"2026-05-21\", \"vigilance_clearance_ref_no\": \"VIG/25-26/1\", \"compassionate_allowance_amt\": null, \"eligible_double_family_pension\": false, \"double_family_pension_upto_date\": \"\"}','{\"id\": 1, \"emp_cd\": \"46299\", \"bank_cd\": \"010127\", \"regn_no\": \"X/REG/1\", \"emp_name\": \"Mrs. RAHIMA  KHATOON\", \"bank_name\": \"GARDEN REACH (GAR)\", \"ca_number\": \"38562\", \"regn_date\": \"2026-05-21\", \"vr_ref_dt\": \"\", \"vr_ref_no\": \"\", \"account_no\": \"10320782829\", \"start_year\": 2026, \"lic_bank_cd\": \"700001\", \"start_month\": 6, \"held_up_flag\": \"\", \"pension_type\": \"N\", \"lic_bank_name\": \"\", \"nominee_eform\": \"E\", \"pension_option\": \"G\", \"quarter_status\": \"\", \"retirement_cpi\": null, \"service_tenure\": \"32Y 0M 21D\", \"employee_status\": \"EMPLOYEE\", \"extra_tccs_days\": 0, \"gratuity_option\": \"1\", \"option_given_by\": \"E\", \"pension_roll_no\": \"ROLL1\", \"separation_date\": \"2026-06-01\", \"separation_type\": \"RT\", \"extra_tccs_years\": 0, \"implemented_year\": 2026, \"incentive_holder\": \"\", \"extra_tccs_months\": 0, \"held_gratuity_amt\": null, \"id_card_submitted\": true, \"implemented_month\": 6, \"vigilance_cleared\": true, \"earning_deductions\": [{\"code\": \"200\", \"desc\": \"PENSION(RETIRING)\", \"type\": \"EARN\", \"amount\": \"\", \"deduction_priority\": \"\"}, {\"code\": \"203\", \"desc\": \"COMMUTATION\", \"type\": \"EARN\", \"amount\": \"\", \"deduction_priority\": \"\"}, {\"code\": \"208\", \"desc\": \"RELIEF\", \"type\": \"EARN\", \"amount\": \"\", \"deduction_priority\": \"\"}, {\"code\": \"205\", \"desc\": \"RET. GRATUITY OPT- I\", \"type\": \"EARN\", \"amount\": \"\", \"deduction_priority\": \"\"}], \"extra_tccs_enabled\": false, \"port_city_resident\": \"YES\", \"pension_proposal_no\": \"PP/ABC/1\", \"pension_proposal_date\": \"2026-06-01\", \"compassionate_allowance\": \"\", \"provisional_pension_pct\": null, \"vigilance_clearance_ref_dt\": \"2026-05-21\", \"vigilance_clearance_ref_no\": \"VIG/25-26/1\", \"compassionate_allowance_amt\": null, \"eligible_double_family_pension\": false, \"double_family_pension_upto_date\": \"\"}','2026-06-02 09:48:16.244243','192.168.4.102','Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36','FIRST_PENSION',3),
(55,'PensionCase','18','UPDATE','{\"tqs\": \"32Y 0M 21D\", \"tccs\": \"32Y 0M 21D\", \"case_id\": 18, \"emp_code\": \"46299\", \"calculated\": true, \"last_basic\": 76800.0, \"no_pay_days\": 0, \"inputs_ready\": true, \"dies_non_days\": 0, \"total_service\": \"32Y 0M 21D\", \"pension_amount\": 38400.0, \"gratuity_amount\": 1688230.0, \"commutation_amount\": 1510319.0, \"commutation_percent\": 40.0, \"has_commutation_application\": true, \"commutation_percent_from_app\": 40.0}','{\"tqs\": \"32Y 0M 21D\", \"tccs\": \"32Y 0M 21D\", \"case_id\": 18, \"emp_code\": \"46299\", \"calculated\": true, \"last_basic\": 76800.0, \"no_pay_days\": 0, \"inputs_ready\": true, \"dies_non_days\": 0, \"total_service\": \"32Y 0M 21D\", \"pension_amount\": 38400.0, \"gratuity_amount\": 1688230.0, \"commutation_amount\": 1510319.0, \"commutation_percent\": 40.0, \"has_commutation_application\": true, \"commutation_percent_from_app\": 40.0}','2026-06-02 09:48:24.009223','192.168.4.102','Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36','FIRST_PENSION',3),
(56,'PensionProposal','1','UPDATE','{\"id\": 1, \"emp_cd\": \"46299\", \"bank_cd\": \"010127\", \"regn_no\": \"X/REG/1\", \"emp_name\": \"Mrs. RAHIMA  KHATOON\", \"bank_name\": \"GARDEN REACH (GAR)\", \"ca_number\": \"38562\", \"regn_date\": \"2026-05-21\", \"vr_ref_dt\": \"\", \"vr_ref_no\": \"\", \"account_no\": \"10320782829\", \"start_year\": 2026, \"lic_bank_cd\": \"700001\", \"start_month\": 6, \"held_up_flag\": \"\", \"pension_type\": \"N\", \"lic_bank_name\": \"\", \"nominee_eform\": \"E\", \"pension_option\": \"G\", \"quarter_status\": \"\", \"retirement_cpi\": null, \"service_tenure\": \"32Y 0M 21D\", \"employee_status\": \"EMPLOYEE\", \"extra_tccs_days\": 0, \"gratuity_option\": \"1\", \"option_given_by\": \"E\", \"pension_roll_no\": \"ROLL1\", \"separation_date\": \"2026-06-01\", \"separation_type\": \"RT\", \"extra_tccs_years\": 0, \"implemented_year\": 2026, \"incentive_holder\": \"\", \"extra_tccs_months\": 0, \"held_gratuity_amt\": null, \"id_card_submitted\": true, \"implemented_month\": 6, \"vigilance_cleared\": true, \"earning_deductions\": [{\"code\": \"200\", \"desc\": \"PENSION(RETIRING)\", \"type\": \"EARN\", \"amount\": \"\", \"deduction_priority\": \"\"}, {\"code\": \"203\", \"desc\": \"COMMUTATION\", \"type\": \"EARN\", \"amount\": \"\", \"deduction_priority\": \"\"}, {\"code\": \"208\", \"desc\": \"RELIEF\", \"type\": \"EARN\", \"amount\": \"\", \"deduction_priority\": \"\"}, {\"code\": \"205\", \"desc\": \"RET. GRATUITY OPT- I\", \"type\": \"EARN\", \"amount\": \"\", \"deduction_priority\": \"\"}], \"extra_tccs_enabled\": false, \"port_city_resident\": \"YES\", \"pension_proposal_no\": \"PP/ABC/1\", \"pension_proposal_date\": \"2026-06-01\", \"compassionate_allowance\": \"\", \"provisional_pension_pct\": null, \"vigilance_clearance_ref_dt\": \"2026-05-21\", \"vigilance_clearance_ref_no\": \"VIG/25-26/1\", \"compassionate_allowance_amt\": null, \"eligible_double_family_pension\": false, \"double_family_pension_upto_date\": \"\"}','{\"id\": 1, \"emp_cd\": \"46299\", \"bank_cd\": \"010127\", \"regn_no\": \"X/REG/1\", \"emp_name\": \"Mrs. RAHIMA  KHATOON\", \"bank_name\": \"GARDEN REACH (GAR)\", \"ca_number\": \"38562\", \"regn_date\": \"2026-05-21\", \"vr_ref_dt\": \"\", \"vr_ref_no\": \"\", \"account_no\": \"10320782829\", \"start_year\": 2026, \"lic_bank_cd\": \"700001\", \"start_month\": 6, \"held_up_flag\": \"\", \"pension_type\": \"N\", \"lic_bank_name\": \"\", \"nominee_eform\": \"E\", \"pension_option\": \"G\", \"quarter_status\": \"\", \"retirement_cpi\": null, \"service_tenure\": \"32Y 0M 21D\", \"employee_status\": \"F\", \"extra_tccs_days\": 0, \"gratuity_option\": \"1\", \"option_given_by\": \"E\", \"pension_roll_no\": \"ROLL1\", \"separation_date\": \"2026-06-01\", \"separation_type\": \"RT\", \"extra_tccs_years\": 0, \"implemented_year\": 2026, \"incentive_holder\": \"\", \"extra_tccs_months\": 0, \"held_gratuity_amt\": null, \"id_card_submitted\": true, \"implemented_month\": 6, \"vigilance_cleared\": true, \"earning_deductions\": [{\"code\": \"200\", \"desc\": \"PENSION(RETIRING)\", \"type\": \"EARN\", \"amount\": \"\", \"deduction_priority\": \"\"}, {\"code\": \"203\", \"desc\": \"COMMUTATION\", \"type\": \"EARN\", \"amount\": \"\", \"deduction_priority\": \"\"}, {\"code\": \"208\", \"desc\": \"RELIEF\", \"type\": \"EARN\", \"amount\": \"\", \"deduction_priority\": \"\"}, {\"code\": \"205\", \"desc\": \"RET. GRATUITY OPT- I\", \"type\": \"EARN\", \"amount\": \"\", \"deduction_priority\": \"\"}], \"extra_tccs_enabled\": false, \"port_city_resident\": \"YES\", \"pension_proposal_no\": \"PP/ABC/1\", \"pension_proposal_date\": \"2026-06-01\", \"compassionate_allowance\": \"\", \"provisional_pension_pct\": null, \"vigilance_clearance_ref_dt\": \"2026-05-21\", \"vigilance_clearance_ref_no\": \"VIG/25-26/1\", \"compassionate_allowance_amt\": null, \"eligible_double_family_pension\": false, \"double_family_pension_upto_date\": \"\"}','2026-06-02 09:58:05.573726','192.168.4.102','Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36','FIRST_PENSION',3),
(57,'PensionProposal','1','UPDATE','{\"id\": 1, \"emp_cd\": \"46299\", \"bank_cd\": \"010127\", \"regn_no\": \"X/REG/1\", \"emp_name\": \"Mrs. RAHIMA  KHATOON\", \"bank_name\": \"GARDEN REACH (GAR)\", \"ca_number\": \"38562\", \"regn_date\": \"2026-05-21\", \"vr_ref_dt\": \"\", \"vr_ref_no\": \"\", \"account_no\": \"10320782829\", \"start_year\": 2026, \"lic_bank_cd\": \"700001\", \"start_month\": 6, \"held_up_flag\": \"\", \"pension_type\": \"N\", \"lic_bank_name\": \"\", \"nominee_eform\": \"E\", \"pension_option\": \"G\", \"quarter_status\": \"\", \"retirement_cpi\": null, \"service_tenure\": \"32Y 0M 21D\", \"employee_status\": \"F\", \"extra_tccs_days\": 0, \"gratuity_option\": \"1\", \"option_given_by\": \"E\", \"pension_roll_no\": \"ROLL1\", \"separation_date\": \"2026-06-01\", \"separation_type\": \"RT\", \"extra_tccs_years\": 0, \"implemented_year\": 2026, \"incentive_holder\": \"\", \"extra_tccs_months\": 0, \"held_gratuity_amt\": null, \"id_card_submitted\": true, \"implemented_month\": 6, \"vigilance_cleared\": true, \"earning_deductions\": [{\"code\": \"200\", \"desc\": \"PENSION(RETIRING)\", \"type\": \"EARN\", \"amount\": \"\", \"deduction_priority\": \"\"}, {\"code\": \"203\", \"desc\": \"COMMUTATION\", \"type\": \"EARN\", \"amount\": \"\", \"deduction_priority\": \"\"}, {\"code\": \"208\", \"desc\": \"RELIEF\", \"type\": \"EARN\", \"amount\": \"\", \"deduction_priority\": \"\"}, {\"code\": \"205\", \"desc\": \"RET. GRATUITY OPT- I\", \"type\": \"EARN\", \"amount\": \"\", \"deduction_priority\": \"\"}], \"extra_tccs_enabled\": false, \"port_city_resident\": \"YES\", \"pension_proposal_no\": \"PP/ABC/1\", \"pension_proposal_date\": \"2026-06-01\", \"compassionate_allowance\": \"\", \"provisional_pension_pct\": null, \"vigilance_clearance_ref_dt\": \"2026-05-21\", \"vigilance_clearance_ref_no\": \"VIG/25-26/1\", \"compassionate_allowance_amt\": null, \"eligible_double_family_pension\": false, \"double_family_pension_upto_date\": \"\"}','{\"id\": 1, \"emp_cd\": \"46299\", \"bank_cd\": \"010127\", \"regn_no\": \"X/REG/1\", \"emp_name\": \"Mrs. RAHIMA  KHATOON\", \"bank_name\": \"GARDEN REACH (GAR)\", \"ca_number\": \"38562\", \"regn_date\": \"2026-05-21\", \"vr_ref_dt\": \"\", \"vr_ref_no\": \"\", \"account_no\": \"10320782829\", \"start_year\": 2026, \"lic_bank_cd\": \"700001\", \"start_month\": 6, \"held_up_flag\": \"\", \"pension_type\": \"N\", \"lic_bank_name\": \"\", \"nominee_eform\": \"E\", \"pension_option\": \"G\", \"quarter_status\": \"\", \"retirement_cpi\": null, \"service_tenure\": \"32Y 0M 21D\", \"employee_status\": \"P\", \"extra_tccs_days\": 0, \"gratuity_option\": \"1\", \"option_given_by\": \"E\", \"pension_roll_no\": \"ROLL1\", \"separation_date\": \"2026-06-01\", \"separation_type\": \"RT\", \"extra_tccs_years\": 0, \"implemented_year\": 2026, \"incentive_holder\": \"\", \"extra_tccs_months\": 0, \"held_gratuity_amt\": null, \"id_card_submitted\": true, \"implemented_month\": 6, \"vigilance_cleared\": true, \"earning_deductions\": [{\"code\": \"200\", \"desc\": \"PENSION(RETIRING)\", \"type\": \"EARN\", \"amount\": \"\", \"deduction_priority\": \"\"}, {\"code\": \"203\", \"desc\": \"COMMUTATION\", \"type\": \"EARN\", \"amount\": \"\", \"deduction_priority\": \"\"}, {\"code\": \"208\", \"desc\": \"RELIEF\", \"type\": \"EARN\", \"amount\": \"\", \"deduction_priority\": \"\"}, {\"code\": \"205\", \"desc\": \"RET. GRATUITY OPT- I\", \"type\": \"EARN\", \"amount\": \"\", \"deduction_priority\": \"\"}], \"extra_tccs_enabled\": false, \"port_city_resident\": \"YES\", \"pension_proposal_no\": \"PP/ABC/1\", \"pension_proposal_date\": \"2026-06-01\", \"compassionate_allowance\": \"\", \"provisional_pension_pct\": null, \"vigilance_clearance_ref_dt\": \"2026-05-21\", \"vigilance_clearance_ref_no\": \"VIG/25-26/1\", \"compassionate_allowance_amt\": null, \"eligible_double_family_pension\": false, \"double_family_pension_upto_date\": \"\"}','2026-06-02 09:58:25.090897','192.168.4.102','Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36','FIRST_PENSION',3),
(58,'PensionProposal','1','UPDATE','{\"id\": 1, \"emp_cd\": \"46299\", \"bank_cd\": \"010127\", \"regn_no\": \"X/REG/1\", \"emp_name\": \"Mrs. RAHIMA  KHATOON\", \"bank_name\": \"GARDEN REACH (GAR)\", \"ca_number\": \"38562\", \"regn_date\": \"2026-05-21\", \"vr_ref_dt\": \"\", \"vr_ref_no\": \"\", \"account_no\": \"10320782829\", \"start_year\": 2026, \"lic_bank_cd\": \"700001\", \"start_month\": 6, \"held_up_flag\": \"\", \"pension_type\": \"N\", \"lic_bank_name\": \"\", \"nominee_eform\": \"E\", \"pension_option\": \"G\", \"quarter_status\": \"\", \"retirement_cpi\": null, \"service_tenure\": \"32Y 0M 21D\", \"employee_status\": \"P\", \"extra_tccs_days\": 0, \"gratuity_option\": \"1\", \"option_given_by\": \"E\", \"pension_roll_no\": \"ROLL1\", \"separation_date\": \"2026-06-01\", \"separation_type\": \"RT\", \"extra_tccs_years\": 0, \"implemented_year\": 2026, \"incentive_holder\": \"\", \"extra_tccs_months\": 0, \"held_gratuity_amt\": null, \"id_card_submitted\": true, \"implemented_month\": 6, \"vigilance_cleared\": true, \"earning_deductions\": [{\"code\": \"200\", \"desc\": \"PENSION(RETIRING)\", \"type\": \"EARN\", \"amount\": \"\", \"deduction_priority\": \"\"}, {\"code\": \"203\", \"desc\": \"COMMUTATION\", \"type\": \"EARN\", \"amount\": \"\", \"deduction_priority\": \"\"}, {\"code\": \"208\", \"desc\": \"RELIEF\", \"type\": \"EARN\", \"amount\": \"\", \"deduction_priority\": \"\"}, {\"code\": \"205\", \"desc\": \"RET. GRATUITY OPT- I\", \"type\": \"EARN\", \"amount\": \"\", \"deduction_priority\": \"\"}], \"extra_tccs_enabled\": false, \"port_city_resident\": \"YES\", \"pension_proposal_no\": \"PP/ABC/1\", \"pension_proposal_date\": \"2026-06-01\", \"compassionate_allowance\": \"\", \"provisional_pension_pct\": null, \"vigilance_clearance_ref_dt\": \"2026-05-21\", \"vigilance_clearance_ref_no\": \"VIG/25-26/1\", \"compassionate_allowance_amt\": null, \"eligible_double_family_pension\": false, \"double_family_pension_upto_date\": \"\"}','{\"id\": 1, \"emp_cd\": \"46299\", \"bank_cd\": \"010127\", \"regn_no\": \"X/REG/1\", \"emp_name\": \"Mrs. RAHIMA  KHATOON\", \"bank_name\": \"GARDEN REACH (GAR)\", \"ca_number\": \"38562\", \"regn_date\": \"2026-05-21\", \"vr_ref_dt\": \"\", \"vr_ref_no\": \"\", \"account_no\": \"10320782829\", \"start_year\": 2026, \"lic_bank_cd\": \"700001\", \"start_month\": 6, \"held_up_flag\": \"\", \"pension_type\": \"N\", \"lic_bank_name\": \"\", \"nominee_eform\": \"E\", \"pension_option\": \"G\", \"quarter_status\": \"\", \"retirement_cpi\": null, \"service_tenure\": \"32Y 0M 21D\", \"employee_status\": \"P\", \"extra_tccs_days\": 0, \"gratuity_option\": \"1\", \"option_given_by\": \"E\", \"pension_roll_no\": \"ROLL1\", \"separation_date\": \"2026-06-01\", \"separation_type\": \"RT\", \"extra_tccs_years\": 0, \"implemented_year\": null, \"incentive_holder\": \"\", \"extra_tccs_months\": 0, \"held_gratuity_amt\": null, \"id_card_submitted\": true, \"implemented_month\": null, \"vigilance_cleared\": true, \"earning_deductions\": [{\"code\": \"200\", \"desc\": \"PENSION(RETIRING)\", \"type\": \"EARN\", \"amount\": \"\", \"deduction_priority\": \"\"}, {\"code\": \"203\", \"desc\": \"COMMUTATION\", \"type\": \"EARN\", \"amount\": \"\", \"deduction_priority\": \"\"}, {\"code\": \"208\", \"desc\": \"RELIEF\", \"type\": \"EARN\", \"amount\": \"\", \"deduction_priority\": \"\"}, {\"code\": \"205\", \"desc\": \"RET. GRATUITY OPT- I\", \"type\": \"EARN\", \"amount\": \"\", \"deduction_priority\": \"\"}], \"extra_tccs_enabled\": false, \"port_city_resident\": \"YES\", \"pension_proposal_no\": \"PP/ABC/1\", \"pension_proposal_date\": \"2026-06-01\", \"compassionate_allowance\": \"\", \"provisional_pension_pct\": null, \"vigilance_clearance_ref_dt\": \"2026-05-21\", \"vigilance_clearance_ref_no\": \"VIG/25-26/1\", \"compassionate_allowance_amt\": null, \"eligible_double_family_pension\": false, \"double_family_pension_upto_date\": \"\"}','2026-06-02 09:58:53.747458','192.168.4.102','Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36','FIRST_PENSION',3),
(59,'PensionCase','17','UPDATE','{\"tqs\": \"32Y 5M 1D\", \"tccs\": \"32Y 5M 11D\", \"case_id\": 17, \"emp_code\": \"43694\", \"calculated\": true, \"last_basic\": 98700.0, \"no_pay_days\": 10, \"inputs_ready\": true, \"dies_non_days\": 0, \"total_service\": \"32Y 5M 11D\", \"pension_amount\": 49350.0, \"gratuity_amount\": 2000000.0, \"commutation_amount\": 1940994.72, \"commutation_percent\": 40.0, \"has_commutation_application\": true, \"commutation_percent_from_app\": 40.0}','{\"tqs\": \"32Y 5M 1D\", \"tccs\": \"32Y 5M 11D\", \"case_id\": 17, \"emp_code\": \"43694\", \"calculated\": true, \"last_basic\": 98700.0, \"no_pay_days\": 10, \"inputs_ready\": true, \"dies_non_days\": 0, \"total_service\": \"32Y 5M 11D\", \"pension_amount\": 49350.0, \"gratuity_amount\": 2000000.0, \"commutation_amount\": 1940995.0, \"commutation_percent\": 40.0, \"has_commutation_application\": true, \"commutation_percent_from_app\": 40.0}','2026-06-02 11:30:24.473549','192.168.4.102','Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36','FIRST_PENSION',3),
(60,'PensionProposal','6','CREATE',NULL,'{\"id\": 6, \"emp_cd\": \"43694\", \"bank_cd\": \"160059\", \"regn_no\": \"X/K-45\", \"emp_name\": \"Mrs. KRISHNA  MINZ\", \"bank_name\": \"Ko.P.T. FAIRLIE PLACE BRANCH\", \"ca_number\": \"38565\", \"regn_date\": \"2026-05-27\", \"vr_ref_dt\": \"\", \"vr_ref_no\": \"\", \"account_no\": \"227001000001244\", \"start_year\": 2026, \"lic_bank_cd\": \"700001\", \"start_month\": 6, \"held_up_flag\": \"\", \"pension_type\": \"N\", \"lic_bank_name\": \"\", \"nominee_eform\": \"E\", \"pension_option\": \"G\", \"quarter_status\": \"\", \"retirement_cpi\": \"359\", \"service_tenure\": \"32Y 5M 11D\", \"employee_status\": \"EMPLOYEE\", \"extra_tccs_days\": 0, \"gratuity_option\": \"1\", \"option_given_by\": \"E\", \"pension_roll_no\": \"LIC-6504\", \"separation_date\": \"2026-06-01\", \"separation_type\": \"RT\", \"extra_tccs_years\": 0, \"implemented_year\": null, \"incentive_holder\": \"\", \"extra_tccs_months\": 0, \"held_gratuity_amt\": null, \"id_card_submitted\": true, \"implemented_month\": null, \"vigilance_cleared\": true, \"earning_deductions\": [{\"code\": \"200\", \"desc\": \"PENSION(RETIRING)\", \"type\": \"EARN\", \"amount\": \"\", \"deduction_priority\": \"\"}, {\"code\": \"203\", \"desc\": \"COMMUTATION\", \"type\": \"EARN\", \"amount\": \"\", \"deduction_priority\": \"\"}, {\"code\": \"205\", \"desc\": \"RET. GRATUITY OPT- I\", \"type\": \"EARN\", \"amount\": \"\", \"deduction_priority\": \"\"}, {\"code\": \"208\", \"desc\": \"RELIEF\", \"type\": \"EARN\", \"amount\": \"\", \"deduction_priority\": \"\"}], \"extra_tccs_enabled\": false, \"port_city_resident\": \"YES\", \"pension_proposal_no\": \"ABC/Test/9\", \"pension_proposal_date\": \"2026-05-22\", \"compassionate_allowance\": \"\", \"provisional_pension_pct\": null, \"vigilance_clearance_ref_dt\": \"2026-05-15\", \"vigilance_clearance_ref_no\": \"VIG/26/001\", \"compassionate_allowance_amt\": null, \"eligible_double_family_pension\": false, \"double_family_pension_upto_date\": \"\"}','2026-06-02 11:37:34.437018','192.168.4.102','Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36','FIRST_PENSION',3),
(61,'PensionCase','17','UPDATE','{\"tqs\": \"32Y 5M 1D\", \"tccs\": \"32Y 5M 11D\", \"case_id\": 17, \"emp_code\": \"43694\", \"calculated\": true, \"last_basic\": 98700.0, \"no_pay_days\": 10, \"inputs_ready\": true, \"dies_non_days\": 0, \"total_service\": \"32Y 5M 11D\", \"pension_amount\": 49350.0, \"gratuity_amount\": 2000000.0, \"commutation_amount\": 1940995.0, \"commutation_percent\": 40.0, \"has_commutation_application\": true, \"commutation_percent_from_app\": 40.0}','{\"tqs\": \"32Y 5M 1D\", \"tccs\": \"32Y 5M 11D\", \"case_id\": 17, \"emp_code\": \"43694\", \"calculated\": true, \"last_basic\": 98700.0, \"no_pay_days\": 10, \"inputs_ready\": true, \"dies_non_days\": 0, \"total_service\": \"32Y 5M 11D\", \"pension_amount\": 49350.0, \"gratuity_amount\": 2000000.0, \"commutation_amount\": 1940995.0, \"commutation_percent\": 40.0, \"has_commutation_application\": true, \"commutation_percent_from_app\": 40.0}','2026-06-02 11:37:43.301050','192.168.4.102','Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36','FIRST_PENSION',3),
(62,'PensionCase','21','CREATE','{\"remarks\": \"\", \"separation_date\": \"\", \"separation_type\": \"\"}','{\"remarks\": \"Superannuation\", \"separation_date\": \"2026-07-01\", \"separation_type\": \"RT\"}','2026-06-03 04:40:25.077028','192.168.4.102','Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36','FIRST_PENSION',3),
(63,'CommutationApplication','6','CREATE',NULL,'{\"id\": 6, \"emp_cd\": \"41783\", \"status\": \"COMMUTATION INITIATED\", \"appcn_dt\": \"2026-07-01\", \"appcn_no\": \"5691\", \"commutation_dt\": \"2026-07-01\", \"restoration_dt\": \"2026-06-03\", \"comm_start_mnth\": \"07\", \"commutation_per\": 40.0, \"application_time\": 1, \"impl_fpen_combill\": \"PEN\", \"mo_certificate_dt\": \"\", \"mo_certificate_ref\": \"\", \"application_rcvd_dt\": \"2026-07-01\", \"commutation_reasons\": \"Personal Work\"}','2026-06-03 04:41:04.585737','192.168.4.102','Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36','FIRST_PENSION',3),
(64,'PensionCase','21','UPDATE','{\"id\": 21, \"emp_code\": \"41783\", \"no_pay_days\": 0, \"dies_non_days\": 0, \"suspension_days\": 0, \"no_pay_more_than_240_days\": 0}','{\"id\": 21, \"emp_code\": \"41783\", \"no_pay_days\": 5, \"dies_non_days\": 32, \"suspension_days\": 0, \"no_pay_more_than_240_days\": 0}','2026-06-03 04:41:31.038390','192.168.4.102','Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36','FIRST_PENSION',3),
(65,'PensionCase','21','CREATE',NULL,'{\"tqs\": \"30Y 9M 29D\", \"tccs\": \"30Y 10M 4D\", \"case_id\": 21, \"emp_code\": \"41783\", \"calculated\": true, \"last_basic\": 79000.0, \"no_pay_days\": 5, \"inputs_ready\": true, \"dies_non_days\": 32, \"total_service\": \"30Y 11M 5D\", \"pension_amount\": 39500.0, \"gratuity_amount\": 1682322.0, \"commutation_amount\": 1553583.0, \"commutation_percent\": 40.0, \"has_commutation_application\": true, \"commutation_percent_from_app\": 40.0}','2026-06-03 04:52:53.722685','192.168.4.102','Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36','FIRST_PENSION',3),
(66,'PensionCase','17','UPDATE','{\"remarks\": \"\", \"separation_date\": \"\", \"separation_type\": \"\"}','{\"remarks\": \"Superannuation\", \"separation_date\": \"2026-05-01\", \"separation_type\": \"RT\"}','2026-06-03 06:24:10.215170','192.168.4.102','Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36','FIRST_PENSION',3),
(67,'PensionCase','22','CREATE',NULL,'{\"remarks\": \"Superannuation\", \"separation_date\": \"2026-07-01\", \"separation_type\": \"RT\"}','2026-06-03 07:14:38.847788','192.168.4.102','Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36','FIRST_PENSION',3),
(68,'CommutationApplication','7','CREATE',NULL,'{\"id\": 7, \"emp_cd\": \"42063\", \"status\": \"COMMUTATION INITIATED\", \"appcn_dt\": \"2026-07-01\", \"appcn_no\": 5692, \"commutation_dt\": \"2026-07-01\", \"restoration_dt\": \"2026-07-01\", \"comm_start_mnth\": \"07\", \"commutation_per\": 40.0, \"application_time\": 1, \"impl_fpen_combill\": \"PEN\", \"mo_certificate_dt\": \"\", \"mo_certificate_ref\": \"\", \"application_rcvd_dt\": \"2026-07-01\", \"commutation_reasons\": \"House Repairing\"}','2026-06-03 07:20:33.659327','192.168.4.102','Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36','FIRST_PENSION',3),
(69,'PensionCase','12','UPDATE','{\"remarks\": \"AS PER ORDER OF MOPSW VIDE NO.A-12023/23/2021-PR-I DATED 29.09.2021, SRI RAJHANS JOINED AT KDS ON 30.09.2021. HE HAS BEEN TRANSFERRED FROM HDC.\", \"separation_date\": \"\", \"separation_type\": \"\"}','{\"remarks\": \"AS PER ORDER OF MOPSW VIDE NO.A-12023/23/2021-PR-I DATED 29.09.2021, SRI RAJHANS JOINED AT KDS ON 30.09.2021. HE HAS BEEN TRANSFERRED FROM HDC.\", \"separation_date\": \"2026-06-01\", \"separation_type\": \"RT\"}','2026-06-03 07:30:49.604620','192.168.4.102','Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36','FIRST_PENSION',3),
(70,'CommutationApplication','8','CREATE',NULL,'{\"id\": 8, \"emp_cd\": \"48330\", \"status\": \"COMMUTATION INITIATED\", \"appcn_dt\": \"2026-06-01\", \"appcn_no\": 5692, \"commutation_dt\": \"2026-06-01\", \"restoration_dt\": \"\", \"comm_start_mnth\": \"06\", \"commutation_per\": 40.0, \"application_time\": 1, \"impl_fpen_combill\": \"\", \"mo_certificate_dt\": \"\", \"mo_certificate_ref\": \"\", \"application_rcvd_dt\": \"2026-06-01\", \"commutation_reasons\": \"\"}','2026-06-03 07:31:15.870722','192.168.4.102','Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36','FIRST_PENSION',3),
(71,'PensionCase','13','UPDATE','{\"remarks\": \"\", \"separation_date\": \"\", \"separation_type\": \"\"}','{\"remarks\": \"Superannuation\", \"separation_date\": \"2026-05-01\", \"separation_type\": \"RT\"}','2026-06-03 08:23:48.472482','192.168.4.102','Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36','FIRST_PENSION',3),
(72,'PensionCase','23','CREATE',NULL,'{\"remarks\": \"Superannuation\", \"separation_date\": \"2026-07-01\", \"separation_type\": \"RT\"}','2026-06-03 08:28:37.617161','192.168.4.102','Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36','FIRST_PENSION',3),
(73,'CommutationApplication','9','CREATE',NULL,'{\"id\": 9, \"emp_cd\": \"43626\", \"status\": \"COMMUTATION INITIATED\", \"appcn_dt\": \"2026-07-01\", \"appcn_no\": 5693, \"commutation_dt\": \"2026-07-01\", \"restoration_dt\": \"\", \"comm_start_mnth\": \"07\", \"commutation_per\": 40.0, \"application_time\": 1, \"impl_fpen_combill\": \"PEN\", \"mo_certificate_dt\": \"\", \"mo_certificate_ref\": \"\", \"application_rcvd_dt\": \"2026-07-01\", \"commutation_reasons\": \"Home Renovation\"}','2026-06-03 08:53:26.674949','192.168.4.102','Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36','FIRST_PENSION',3);

/*Table structure for table `auth_group` */

DROP TABLE IF EXISTS `auth_group`;

CREATE TABLE `auth_group` (
  `id` int NOT NULL AUTO_INCREMENT,
  `name` varchar(150) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `name` (`name`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

/*Data for the table `auth_group` */

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

/*Data for the table `auth_group_permissions` */

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
) ENGINE=InnoDB AUTO_INCREMENT=101 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

/*Data for the table `auth_permission` */

insert  into `auth_permission`(`id`,`name`,`content_type_id`,`codename`) values 
(1,'Can add log entry',1,'add_logentry'),
(2,'Can change log entry',1,'change_logentry'),
(3,'Can delete log entry',1,'delete_logentry'),
(4,'Can view log entry',1,'view_logentry'),
(5,'Can add permission',2,'add_permission'),
(6,'Can change permission',2,'change_permission'),
(7,'Can delete permission',2,'delete_permission'),
(8,'Can view permission',2,'view_permission'),
(9,'Can add group',3,'add_group'),
(10,'Can change group',3,'change_group'),
(11,'Can delete group',3,'delete_group'),
(12,'Can view group',3,'view_group'),
(13,'Can add content type',4,'add_contenttype'),
(14,'Can change content type',4,'change_contenttype'),
(15,'Can delete content type',4,'delete_contenttype'),
(16,'Can view content type',4,'view_contenttype'),
(17,'Can add session',5,'add_session'),
(18,'Can change session',5,'change_session'),
(19,'Can delete session',5,'delete_session'),
(20,'Can view session',5,'view_session'),
(21,'Can add role',6,'add_role'),
(22,'Can change role',6,'change_role'),
(23,'Can delete role',6,'delete_role'),
(24,'Can view role',6,'view_role'),
(25,'Can add user',7,'add_user'),
(26,'Can change user',7,'change_user'),
(27,'Can delete user',7,'delete_user'),
(28,'Can view user',7,'view_user'),
(29,'Can add user role',8,'add_userrole'),
(30,'Can change user role',8,'change_userrole'),
(31,'Can delete user role',8,'delete_userrole'),
(32,'Can view user role',8,'view_userrole'),
(33,'Can add department',9,'add_department'),
(34,'Can change department',9,'change_department'),
(35,'Can delete department',9,'delete_department'),
(36,'Can view department',9,'view_department'),
(37,'Can add employee',10,'add_employee'),
(38,'Can change employee',10,'change_employee'),
(39,'Can delete employee',10,'delete_employee'),
(40,'Can view employee',10,'view_employee'),
(41,'Can add workflow master',11,'add_workflowmaster'),
(42,'Can change workflow master',11,'change_workflowmaster'),
(43,'Can delete workflow master',11,'delete_workflowmaster'),
(44,'Can view workflow master',11,'view_workflowmaster'),
(45,'Can add workflow step',12,'add_workflowstep'),
(46,'Can change workflow step',12,'change_workflowstep'),
(47,'Can delete workflow step',12,'delete_workflowstep'),
(48,'Can view workflow step',12,'view_workflowstep'),
(49,'Can add workflow instance',13,'add_workflowinstance'),
(50,'Can change workflow instance',13,'change_workflowinstance'),
(51,'Can delete workflow instance',13,'delete_workflowinstance'),
(52,'Can view workflow instance',13,'view_workflowinstance'),
(53,'Can add workflow history',14,'add_workflowhistory'),
(54,'Can change workflow history',14,'change_workflowhistory'),
(55,'Can delete workflow history',14,'delete_workflowhistory'),
(56,'Can view workflow history',14,'view_workflowhistory'),
(57,'Can add audit log',15,'add_auditlog'),
(58,'Can change audit log',15,'change_auditlog'),
(59,'Can delete audit log',15,'delete_auditlog'),
(60,'Can view audit log',15,'view_auditlog'),
(61,'Can add dies non',16,'add_diesnon'),
(62,'Can change dies non',16,'change_diesnon'),
(63,'Can delete dies non',16,'delete_diesnon'),
(64,'Can view dies non',16,'view_diesnon'),
(65,'Can add pension case',17,'add_pensioncase'),
(66,'Can change pension case',17,'change_pensioncase'),
(67,'Can delete pension case',17,'delete_pensioncase'),
(68,'Can view pension case',17,'view_pensioncase'),
(69,'Can add pension case',18,'add_pensioncase'),
(70,'Can change pension case',18,'change_pensioncase'),
(71,'Can delete pension case',18,'delete_pensioncase'),
(72,'Can view pension case',18,'view_pensioncase'),
(73,'Can add pension summary',19,'add_pensionsummary'),
(74,'Can change pension summary',19,'change_pensionsummary'),
(75,'Can delete pension summary',19,'delete_pensionsummary'),
(76,'Can view pension summary',19,'view_pensionsummary'),
(77,'Can add commutation application',20,'add_commutationapplication'),
(78,'Can change commutation application',20,'change_commutationapplication'),
(79,'Can delete commutation application',20,'delete_commutationapplication'),
(80,'Can view commutation application',20,'view_commutationapplication'),
(81,'Can add pension proposal',21,'add_pensionproposal'),
(82,'Can change pension proposal',21,'change_pensionproposal'),
(83,'Can delete pension proposal',21,'delete_pensionproposal'),
(84,'Can view pension proposal',21,'view_pensionproposal'),
(85,'Can add user profile',22,'add_userprofile'),
(86,'Can change user profile',22,'change_userprofile'),
(87,'Can delete user profile',22,'delete_userprofile'),
(88,'Can view user profile',22,'view_userprofile'),
(89,'Can add dashboard month snapshot',23,'add_dashboardmonthsnapshot'),
(90,'Can change dashboard month snapshot',23,'change_dashboardmonthsnapshot'),
(91,'Can delete dashboard month snapshot',23,'delete_dashboardmonthsnapshot'),
(92,'Can view dashboard month snapshot',23,'view_dashboardmonthsnapshot'),
(93,'Can add cached retirement employee',24,'add_cachedretirementemployee'),
(94,'Can change cached retirement employee',24,'change_cachedretirementemployee'),
(95,'Can delete cached retirement employee',24,'delete_cachedretirementemployee'),
(96,'Can view cached retirement employee',24,'view_cachedretirementemployee'),
(97,'Can add cached employee oracle detail',25,'add_cachedemployeeoracledetail'),
(98,'Can change cached employee oracle detail',25,'change_cachedemployeeoracledetail'),
(99,'Can delete cached employee oracle detail',25,'delete_cachedemployeeoracledetail'),
(100,'Can view cached employee oracle detail',25,'view_cachedemployeeoracledetail');

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

/*Data for the table `django_admin_log` */

/*Table structure for table `django_content_type` */

DROP TABLE IF EXISTS `django_content_type`;

CREATE TABLE `django_content_type` (
  `id` int NOT NULL AUTO_INCREMENT,
  `app_label` varchar(100) NOT NULL,
  `model` varchar(100) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `django_content_type_app_label_model_76bd3d3b_uniq` (`app_label`,`model`)
) ENGINE=InnoDB AUTO_INCREMENT=26 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

/*Data for the table `django_content_type` */

insert  into `django_content_type`(`id`,`app_label`,`model`) values 
(16,'accounts','diesnon'),
(6,'accounts','role'),
(7,'accounts','user'),
(22,'accounts','userprofile'),
(8,'accounts','userrole'),
(1,'admin','logentry'),
(15,'audit','auditlog'),
(3,'auth','group'),
(2,'auth','permission'),
(4,'contenttypes','contenttype'),
(9,'employee','department'),
(10,'employee','employee'),
(17,'employee','pensioncase'),
(25,'first_pension','cachedemployeeoracledetail'),
(24,'first_pension','cachedretirementemployee'),
(20,'first_pension','commutationapplication'),
(23,'first_pension','dashboardmonthsnapshot'),
(18,'first_pension','pensioncase'),
(21,'first_pension','pensionproposal'),
(19,'first_pension','pensionsummary'),
(5,'sessions','session'),
(14,'workflow','workflowhistory'),
(13,'workflow','workflowinstance'),
(11,'workflow','workflowmaster'),
(12,'workflow','workflowstep');

/*Table structure for table `django_migrations` */

DROP TABLE IF EXISTS `django_migrations`;

CREATE TABLE `django_migrations` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `app` varchar(255) NOT NULL,
  `name` varchar(255) NOT NULL,
  `applied` datetime(6) NOT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=34 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

/*Data for the table `django_migrations` */

insert  into `django_migrations`(`id`,`app`,`name`,`applied`) values 
(1,'contenttypes','0001_initial','2026-04-24 07:21:58.291903'),
(2,'contenttypes','0002_remove_content_type_name','2026-04-24 07:21:58.358446'),
(3,'auth','0001_initial','2026-04-24 07:21:58.536797'),
(4,'auth','0002_alter_permission_name_max_length','2026-04-24 07:21:58.596814'),
(5,'auth','0003_alter_user_email_max_length','2026-04-24 07:21:58.601479'),
(6,'auth','0004_alter_user_username_opts','2026-04-24 07:21:58.611244'),
(7,'auth','0005_alter_user_last_login_null','2026-04-24 07:21:58.614584'),
(8,'auth','0006_require_contenttypes_0002','2026-04-24 07:21:58.614584'),
(9,'auth','0007_alter_validators_add_error_messages','2026-04-24 07:21:58.614584'),
(10,'auth','0008_alter_user_username_max_length','2026-04-24 07:21:58.630139'),
(11,'auth','0009_alter_user_last_name_max_length','2026-04-24 07:21:58.636138'),
(12,'auth','0010_alter_group_name_max_length','2026-04-24 07:21:58.649945'),
(13,'auth','0011_update_proxy_permissions','2026-04-24 07:21:58.658461'),
(14,'auth','0012_alter_user_first_name_max_length','2026-04-24 07:21:58.663819'),
(15,'accounts','0001_initial','2026-04-24 07:21:59.065203'),
(16,'admin','0001_initial','2026-04-24 07:21:59.174370'),
(17,'admin','0002_logentry_remove_auto_add','2026-04-24 07:21:59.191574'),
(18,'admin','0003_logentry_add_action_flag_choices','2026-04-24 07:21:59.200226'),
(19,'audit','0001_initial','2026-04-24 07:21:59.274292'),
(20,'employee','0001_initial','2026-04-24 07:21:59.532197'),
(21,'sessions','0001_initial','2026-04-24 07:21:59.558132'),
(22,'workflow','0001_initial','2026-04-24 07:21:59.914385'),
(23,'accounts','0002_diesnon','2026-05-06 07:26:01.142687'),
(24,'accounts','0003_diesnon_end_date','2026-05-06 07:28:17.550935'),
(25,'employee','0002_pensioncase','2026-05-10 15:25:28.742175'),
(26,'first_pension','0001_initial','2026-05-10 16:46:24.471195'),
(27,'first_pension','0002_commutationapplication','2026-05-19 06:19:00.159595'),
(28,'first_pension','0003_pensionproposal','2026-05-21 09:17:02.273710'),
(29,'first_pension','0004_pensioncase_no_pay_more_than_240_days_and_more','2026-05-21 10:28:45.368809'),
(30,'first_pension','0005_pensioncase_separation_fields','2026-05-26 11:58:59.987587'),
(31,'accounts','0004_userprofile_role_code','2026-05-28 16:46:03.020381'),
(32,'accounts','0005_remove_userprofile_full_name','2026-05-28 17:00:04.748597'),
(33,'first_pension','0006_oracle_local_cache','2026-06-02 17:01:02.433055');

/*Table structure for table `django_session` */

DROP TABLE IF EXISTS `django_session`;

CREATE TABLE `django_session` (
  `session_key` varchar(40) NOT NULL,
  `session_data` longtext NOT NULL,
  `expire_date` datetime(6) NOT NULL,
  PRIMARY KEY (`session_key`),
  KEY `django_session_expire_date_a5c62663` (`expire_date`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

/*Data for the table `django_session` */

/*Table structure for table `employee_department` */

DROP TABLE IF EXISTS `employee_department`;

CREATE TABLE `employee_department` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `name` varchar(100) NOT NULL,
  `is_active` tinyint(1) NOT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

/*Data for the table `employee_department` */

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

/*Data for the table `employee_employee` */

/*Table structure for table `first_pension_cached_employee_oracle` */

DROP TABLE IF EXISTS `first_pension_cached_employee_oracle`;

CREATE TABLE `first_pension_cached_employee_oracle` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `emp_code` varchar(20) COLLATE utf8mb4_unicode_ci NOT NULL,
  `payload` json NOT NULL,
  `synced_at` datetime(6) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `emp_code` (`emp_code`)
) ENGINE=InnoDB AUTO_INCREMENT=7 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

/*Data for the table `first_pension_cached_employee_oracle` */

insert  into `first_pension_cached_employee_oracle`(`id`,`emp_code`,`payload`,`synced_at`) values 
(1,'42230','{\"name\": \"Mr. SWAPAN KUMAR NASKAR\", \"class\": \"III\", \"scale\": \"2022/RE/006/31\", \"emp_id\": \"42230\", \"partial\": false, \"join_date\": \"26-05-1988\", \"birth_date\": \"06-05-1966\", \"designation\": \"L.D. CLERK\", \"basic_amount\": 86300.0, \"age_on_retirement\": {\"days\": 26, \"years\": 60, \"months\": 0}, \"proposal_defaults\": {\"bank_cd\": \"160061\", \"bank_name\": \"KOLKATA PORT TRUST(SUBHASH BHABAN)\", \"account_no\": \"158201000002144\", \"start_year\": 2026, \"start_month\": 6, \"service_tenure\": \"38Y 0M 6D\", \"separation_date\": \"2026-06-01\", \"separation_type\": \"RT\", \"implemented_year\": null, \"implemented_month\": null}, \"age_on_appointment\": {\"days\": 20, \"years\": 22, \"months\": 0}, \"expected_retirement_date\": \"01-06-2026\"}','2026-06-03 07:28:27.163900'),
(2,'41783','{\"name\": \"Mr. SK.  NIZAM\", \"class\": \"III\", \"scale\": \"2022/RE/006/28\", \"emp_id\": \"41783\", \"partial\": false, \"join_date\": \"26-07-1995\", \"birth_date\": \"07-06-1966\", \"designation\": \"G.C.P.O\", \"basic_amount\": 79000.0, \"age_on_retirement\": {\"days\": 24, \"years\": 60, \"months\": 0}, \"proposal_defaults\": {\"bank_cd\": \"110008\", \"bank_name\": \"NEW ALIPORE (NAL)\", \"account_no\": \"20032324043\", \"start_year\": 2026, \"start_month\": 7, \"service_tenure\": \"30Y 11M 5D\", \"separation_date\": \"2026-07-01\", \"separation_type\": \"RT\", \"implemented_year\": null, \"implemented_month\": null}, \"age_on_appointment\": {\"days\": 19, \"years\": 29, \"months\": 1}, \"expected_retirement_date\": \"01-07-2026\"}','2026-06-03 07:28:00.226540'),
(3,'42063','{\"name\": \"Mr. PINTU  GHOSH\", \"class\": \"III\", \"scale\": \"2022/RE/008/31\", \"emp_id\": \"42063\", \"partial\": false, \"join_date\": \"05-09-1985\", \"birth_date\": \"07-06-1966\", \"designation\": \"U.D.CLERK (S/G)\", \"basic_amount\": 101600.0, \"age_on_retirement\": {\"days\": 24, \"years\": 60, \"months\": 0}, \"proposal_defaults\": {\"bank_cd\": \"320139\", \"bank_name\": \"RISHRA\", \"account_no\": \"95352200014172\", \"start_year\": 2026, \"start_month\": 7, \"service_tenure\": \"40Y 9M 26D\", \"separation_date\": \"2026-07-01\", \"separation_type\": \"\", \"implemented_year\": null, \"implemented_month\": null}, \"age_on_appointment\": {\"days\": 29, \"years\": 19, \"months\": 2}, \"expected_retirement_date\": \"01-07-2026\"}','2026-06-03 07:27:27.104420'),
(4,'43694','{\"name\": \"Mrs. KRISHNA  MINZ\", \"class\": \"III\", \"scale\": \"2022/RE/009/27\", \"emp_id\": \"43694\", \"partial\": false, \"join_date\": \"21-12-1993\", \"birth_date\": \"01-06-1966\", \"designation\": \"U.D.CLERK (S/G)\", \"basic_amount\": 98700.0, \"age_on_retirement\": {\"days\": 0, \"years\": 60, \"months\": 0}, \"proposal_defaults\": {\"bank_cd\": \"160059\", \"bank_name\": \"Ko.P.T. FAIRLIE PLACE BRANCH\", \"account_no\": \"227001000001244\", \"start_year\": 2026, \"start_month\": 6, \"service_tenure\": \"32Y 5M 11D\", \"separation_date\": \"2026-06-01\", \"separation_type\": \"RT\", \"implemented_year\": null, \"implemented_month\": null}, \"age_on_appointment\": {\"days\": 20, \"years\": 27, \"months\": 6}, \"expected_retirement_date\": \"01-06-2026\"}','2026-06-03 06:22:14.541370'),
(5,'43626','{\"name\": \"Mr. SUSHIL  BARLA\", \"class\": \"III\", \"scale\": \"2017/RE/018\", \"emp_id\": \"43626\", \"partial\": false, \"join_date\": \"11-04-1992\", \"birth_date\": \"16-06-1966\", \"designation\": \"I.O. STAFF CUM LIBRARIAN\", \"basic_amount\": 121190.0, \"age_on_retirement\": {\"days\": 15, \"years\": 60, \"months\": 0}, \"proposal_defaults\": {\"bank_cd\": \"160059\", \"bank_name\": \"Ko.P.T. FAIRLIE PLACE BRANCH\", \"account_no\": \"227001000001063\", \"start_year\": 2026, \"start_month\": 7, \"service_tenure\": \"\", \"separation_date\": \"2026-07-01\", \"separation_type\": \"\", \"implemented_year\": null, \"implemented_month\": null}, \"age_on_appointment\": {\"days\": 26, \"years\": 25, \"months\": 9}, \"expected_retirement_date\": \"01-07-2026\"}','2026-06-03 06:50:49.440534'),
(6,'48330','{\"name\": \"Mr. RAVI SHANKAR RAJHANS\", \"class\": \"I\", \"scale\": \"2017/RE/012\", \"emp_id\": \"48330\", \"partial\": false, \"join_date\": \"01-01-1992\", \"birth_date\": \"01-06-1966\", \"designation\": \"TRAFFIC MANAGER\", \"basic_amount\": 180070.0, \"age_on_retirement\": {\"days\": 0, \"years\": 60, \"months\": 0}, \"proposal_defaults\": {\"bank_cd\": \"160061\", \"bank_name\": \"KOLKATA PORT TRUST(SUBHASH BHABAN)\", \"account_no\": \"158201000009222\", \"start_year\": 2026, \"start_month\": 6, \"service_tenure\": \"34Y 5M 0D\", \"separation_date\": \"2026-06-01\", \"separation_type\": \"\", \"implemented_year\": null, \"implemented_month\": null}, \"age_on_appointment\": {\"days\": 0, \"years\": 25, \"months\": 7}, \"expected_retirement_date\": \"01-06-2026\"}','2026-06-03 07:30:24.734752');

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
  KEY `first_pensi_retire_6b2c8e_idx` (`retirement_year`,`retirement_month`),
  CONSTRAINT `first_pension_cached_retirement_emp_chk_1` CHECK ((`retirement_month` >= 0)),
  CONSTRAINT `first_pension_cached_retirement_emp_chk_2` CHECK ((`retirement_year` >= 0))
) ENGINE=InnoDB AUTO_INCREMENT=842 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

/*Data for the table `first_pension_cached_retirement_emp` */

insert  into `first_pension_cached_retirement_emp`(`id`,`emp_code`,`retirement_month`,`retirement_year`,`name`,`joining_date`,`retirement_date`,`birth_date`,`age_on_appointment`,`age_on_retirement`,`designation`,`scale`,`last_basic`,`emp_class`,`row_payload`,`synced_at`) values 
(755,'42230',5,2026,'Mr. SWAPAN KUMAR NASKAR','26-05-1988','01-06-2026','06-05-1966','{\"days\": 20, \"years\": 22, \"months\": 0}','{\"days\": 26, \"years\": 60, \"months\": 0}','L.D. CLERK','2022/RE/006/31',86300.00,'III','{\"name\": \"Mr. SWAPAN KUMAR NASKAR\", \"class\": \"III\", \"scale\": \"2022/RE/006/31\", \"emp_code\": \"42230\", \"birth_date\": \"06-05-1966\", \"last_basic\": 86300, \"designation\": \"L.D. CLERK\", \"joining_date\": \"26-05-1988\", \"retirement_date\": \"01-06-2026\", \"age_on_retirement\": {\"days\": 26, \"years\": 60, \"months\": 0}, \"age_on_appointment\": {\"days\": 20, \"years\": 22, \"months\": 0}}','2026-06-03 07:31:33.333865'),
(756,'43443',5,2026,'Mr. AMAL KUMAR MAITI','25-05-1988','01-06-2026','02-05-1966','{\"days\": 23, \"years\": 22, \"months\": 0}','{\"days\": 30, \"years\": 60, \"months\": 0}','PHARMACIST GR. I','2022/RE/010/32',128400.00,'III','{\"name\": \"Mr. AMAL KUMAR MAITI\", \"class\": \"III\", \"scale\": \"2022/RE/010/32\", \"emp_code\": \"43443\", \"birth_date\": \"02-05-1966\", \"last_basic\": 128400, \"designation\": \"PHARMACIST GR. I\", \"joining_date\": \"25-05-1988\", \"retirement_date\": \"01-06-2026\", \"age_on_retirement\": {\"days\": 30, \"years\": 60, \"months\": 0}, \"age_on_appointment\": {\"days\": 23, \"years\": 22, \"months\": 0}}','2026-06-03 07:31:33.333865'),
(757,'43694',5,2026,'Mrs. KRISHNA  MINZ','21-12-1993','01-06-2026','01-06-1966','{\"days\": 20, \"years\": 27, \"months\": 6}','{\"days\": 0, \"years\": 60, \"months\": 0}','U.D.CLERK (S/G)','2022/RE/009/27',98700.00,'III','{\"name\": \"Mrs. KRISHNA  MINZ\", \"class\": \"III\", \"scale\": \"2022/RE/009/27\", \"emp_code\": \"43694\", \"birth_date\": \"01-06-1966\", \"last_basic\": 98700, \"designation\": \"U.D.CLERK (S/G)\", \"joining_date\": \"21-12-1993\", \"retirement_date\": \"01-06-2026\", \"age_on_retirement\": {\"days\": 0, \"years\": 60, \"months\": 0}, \"age_on_appointment\": {\"days\": 20, \"years\": 27, \"months\": 6}}','2026-06-03 07:31:33.333865'),
(758,'45996',5,2026,'Mr. DASARATH  YADAV','13-01-1993','01-06-2026','13-05-1966','{\"days\": 0, \"years\": 26, \"months\": 8}','{\"days\": 19, \"years\": 60, \"months\": 0}','CARGO OVERSEAR','2022/RE/005/31',82900.00,'III','{\"name\": \"Mr. DASARATH  YADAV\", \"class\": \"III\", \"scale\": \"2022/RE/005/31\", \"emp_code\": \"45996\", \"birth_date\": \"13-05-1966\", \"last_basic\": 82900, \"designation\": \"CARGO OVERSEAR\", \"joining_date\": \"13-01-1993\", \"retirement_date\": \"01-06-2026\", \"age_on_retirement\": {\"days\": 19, \"years\": 60, \"months\": 0}, \"age_on_appointment\": {\"days\": 0, \"years\": 26, \"months\": 8}}','2026-06-03 07:31:33.333865'),
(759,'46007',5,2026,'Mr. SK. ATAUR RAHAMAN','15-01-1993','01-06-2026','11-05-1966','{\"days\": 4, \"years\": 26, \"months\": 8}','{\"days\": 21, \"years\": 60, \"months\": 0}','A. CATAGORY PORTER','2022/RE/005/27',73700.00,'IV','{\"name\": \"Mr. SK. ATAUR RAHAMAN\", \"class\": \"IV\", \"scale\": \"2022/RE/005/27\", \"emp_code\": \"46007\", \"birth_date\": \"11-05-1966\", \"last_basic\": 73700, \"designation\": \"A. CATAGORY PORTER\", \"joining_date\": \"15-01-1993\", \"retirement_date\": \"01-06-2026\", \"age_on_retirement\": {\"days\": 21, \"years\": 60, \"months\": 0}, \"age_on_appointment\": {\"days\": 4, \"years\": 26, \"months\": 8}}','2026-06-03 07:31:33.333865'),
(760,'46299',5,2026,'Mrs. RAHIMA  KHATOON','11-05-1994','01-06-2026','02-05-1966','{\"days\": 9, \"years\": 28, \"months\": 0}','{\"days\": 30, \"years\": 60, \"months\": 0}','SR. ATTENDANT (FEMALE)','2022/RE/004/30',76800.00,'IV','{\"name\": \"Mrs. RAHIMA  KHATOON\", \"class\": \"IV\", \"scale\": \"2022/RE/004/30\", \"emp_code\": \"46299\", \"birth_date\": \"02-05-1966\", \"last_basic\": 76800, \"designation\": \"SR. ATTENDANT (FEMALE)\", \"joining_date\": \"11-05-1994\", \"retirement_date\": \"01-06-2026\", \"age_on_retirement\": {\"days\": 30, \"years\": 60, \"months\": 0}, \"age_on_appointment\": {\"days\": 9, \"years\": 28, \"months\": 0}}','2026-06-03 07:31:33.333865'),
(761,'47862',5,2026,'Mr. KARUNA NIDHAN KARMAKAR','04-09-1995','01-06-2026','05-05-1966','{\"days\": 30, \"years\": 29, \"months\": 3}','{\"days\": 27, \"years\": 60, \"months\": 0}','2ND CLASS DRIVER','2022/RE/008/26',87600.00,'III','{\"name\": \"Mr. KARUNA NIDHAN KARMAKAR\", \"class\": \"III\", \"scale\": \"2022/RE/008/26\", \"emp_code\": \"47862\", \"birth_date\": \"05-05-1966\", \"last_basic\": 87600, \"designation\": \"2ND CLASS DRIVER\", \"joining_date\": \"04-09-1995\", \"retirement_date\": \"01-06-2026\", \"age_on_retirement\": {\"days\": 27, \"years\": 60, \"months\": 0}, \"age_on_appointment\": {\"days\": 30, \"years\": 29, \"months\": 3}}','2026-06-03 07:31:33.333865'),
(762,'48330',5,2026,'Mr. RAVI SHANKAR RAJHANS','01-01-1992','01-06-2026','01-06-1966','{\"days\": 0, \"years\": 25, \"months\": 7}','{\"days\": 0, \"years\": 60, \"months\": 0}','TRAFFIC MANAGER','2017/RE/012',180070.00,'I','{\"name\": \"Mr. RAVI SHANKAR RAJHANS\", \"class\": \"I\", \"scale\": \"2017/RE/012\", \"emp_code\": \"48330\", \"birth_date\": \"01-06-1966\", \"last_basic\": 180070, \"designation\": \"TRAFFIC MANAGER\", \"joining_date\": \"01-01-1992\", \"retirement_date\": \"01-06-2026\", \"age_on_retirement\": {\"days\": 0, \"years\": 60, \"months\": 0}, \"age_on_appointment\": {\"days\": 0, \"years\": 25, \"months\": 7}}','2026-06-03 07:31:33.333865'),
(803,'40323',9,2026,'Mr. GOUTAM  DAS','08-11-1985','01-10-2026','22-09-1966','{\"days\": 17, \"years\": 19, \"months\": 1}','{\"days\": 9, \"years\": 60, \"months\": 0}','U.D.CLERK (S/G)','2022/RE/009',121300.00,'III','{\"name\": \"Mr. GOUTAM  DAS\", \"class\": \"III\", \"scale\": \"2022/RE/009\", \"emp_code\": \"40323\", \"birth_date\": \"22-09-1966\", \"last_basic\": 121300, \"designation\": \"U.D.CLERK (S/G)\", \"joining_date\": \"08-11-1985\", \"retirement_date\": \"01-10-2026\", \"age_on_retirement\": {\"days\": 9, \"years\": 60, \"months\": 0}, \"age_on_appointment\": {\"days\": 17, \"years\": 19, \"months\": 1}}','2026-06-03 07:40:38.873670'),
(804,'40443',9,2026,'Mr. SUBRATA  MAITY','08-07-1985','01-10-2026','15-09-1966','{\"days\": 23, \"years\": 18, \"months\": 9}','{\"days\": 16, \"years\": 60, \"months\": 0}','SHED FOREMAN','2022/RE/010/31',124700.00,'III','{\"name\": \"Mr. SUBRATA  MAITY\", \"class\": \"III\", \"scale\": \"2022/RE/010/31\", \"emp_code\": \"40443\", \"birth_date\": \"15-09-1966\", \"last_basic\": 124700, \"designation\": \"SHED FOREMAN\", \"joining_date\": \"08-07-1985\", \"retirement_date\": \"01-10-2026\", \"age_on_retirement\": {\"days\": 16, \"years\": 60, \"months\": 0}, \"age_on_appointment\": {\"days\": 23, \"years\": 18, \"months\": 9}}','2026-06-03 07:40:38.875419'),
(805,'40591',9,2026,'Mr. PROSENJIT  CHOWDHURY','23-08-1991','01-10-2026','26-09-1966','{\"days\": 28, \"years\": 24, \"months\": 10}','{\"days\": 5, \"years\": 60, \"months\": 0}','COMPUTER CENTRE SUPERVISOR','2017/RE/018',128930.00,'III','{\"name\": \"Mr. PROSENJIT  CHOWDHURY\", \"class\": \"III\", \"scale\": \"2017/RE/018\", \"emp_code\": \"40591\", \"birth_date\": \"26-09-1966\", \"last_basic\": 128930, \"designation\": \"COMPUTER CENTRE SUPERVISOR\", \"joining_date\": \"23-08-1991\", \"retirement_date\": \"01-10-2026\", \"age_on_retirement\": {\"days\": 5, \"years\": 60, \"months\": 0}, \"age_on_appointment\": {\"days\": 28, \"years\": 24, \"months\": 10}}','2026-06-03 07:40:38.875419'),
(806,'40893',9,2026,'Mr. BARUN  MITRA','11-03-1991','01-10-2026','08-09-1966','{\"days\": 3, \"years\": 24, \"months\": 6}','{\"days\": 23, \"years\": 60, \"months\": 0}','JR.ENGINEER GR-I','2017/RE/015',152660.00,'III','{\"name\": \"Mr. BARUN  MITRA\", \"class\": \"III\", \"scale\": \"2017/RE/015\", \"emp_code\": \"40893\", \"birth_date\": \"08-09-1966\", \"last_basic\": 152660, \"designation\": \"JR.ENGINEER GR-I\", \"joining_date\": \"11-03-1991\", \"retirement_date\": \"01-10-2026\", \"age_on_retirement\": {\"days\": 23, \"years\": 60, \"months\": 0}, \"age_on_appointment\": {\"days\": 3, \"years\": 24, \"months\": 6}}','2026-06-03 07:40:38.875419'),
(807,'43572',9,2026,'Mr. PRADIP  SEAL SHARMA','16-12-1991','01-10-2026','10-09-1966','{\"days\": 6, \"years\": 25, \"months\": 3}','{\"days\": 21, \"years\": 60, \"months\": 0}','HEAD CLERK','2022/RE/009/30',107900.00,'III','{\"name\": \"Mr. PRADIP  SEAL SHARMA\", \"class\": \"III\", \"scale\": \"2022/RE/009/30\", \"emp_code\": \"43572\", \"birth_date\": \"10-09-1966\", \"last_basic\": 107900, \"designation\": \"HEAD CLERK\", \"joining_date\": \"16-12-1991\", \"retirement_date\": \"01-10-2026\", \"age_on_retirement\": {\"days\": 21, \"years\": 60, \"months\": 0}, \"age_on_appointment\": {\"days\": 6, \"years\": 25, \"months\": 3}}','2026-06-03 07:40:38.875419'),
(808,'43656',9,2026,'Mr. KAJAL KANTI PAL','10-08-1989','01-10-2026','29-09-1966','{\"days\": 12, \"years\": 22, \"months\": 10}','{\"days\": 2, \"years\": 60, \"months\": 0}','INSPECTOR (WELFARE)','2022/RE/010/29',117600.00,'III','{\"name\": \"Mr. KAJAL KANTI PAL\", \"class\": \"III\", \"scale\": \"2022/RE/010/29\", \"emp_code\": \"43656\", \"birth_date\": \"29-09-1966\", \"last_basic\": 117600, \"designation\": \"INSPECTOR (WELFARE)\", \"joining_date\": \"10-08-1989\", \"retirement_date\": \"01-10-2026\", \"age_on_retirement\": {\"days\": 2, \"years\": 60, \"months\": 0}, \"age_on_appointment\": {\"days\": 12, \"years\": 22, \"months\": 10}}','2026-06-03 07:40:38.875419'),
(809,'44122',9,2026,'Mr. BISWANATH  MAZUMDAR','07-08-2001','01-10-2026','03-09-1966','{\"days\": 4, \"years\": 34, \"months\": 11}','{\"days\": 28, \"years\": 60, \"months\": 0}','LASCAR GR.II (T.W.)','2022/RE/004/27',70300.00,'IV','{\"name\": \"Mr. BISWANATH  MAZUMDAR\", \"class\": \"IV\", \"scale\": \"2022/RE/004/27\", \"emp_code\": \"44122\", \"birth_date\": \"03-09-1966\", \"last_basic\": 70300, \"designation\": \"LASCAR GR.II (T.W.)\", \"joining_date\": \"07-08-2001\", \"retirement_date\": \"01-10-2026\", \"age_on_retirement\": {\"days\": 28, \"years\": 60, \"months\": 0}, \"age_on_appointment\": {\"days\": 4, \"years\": 34, \"months\": 11}}','2026-06-03 07:40:38.875419'),
(810,'44303',9,2026,'Mr. SANAT KUMAR NASKAR','30-04-1986','01-10-2026','18-09-1966','{\"days\": 12, \"years\": 19, \"months\": 7}','{\"days\": 13, \"years\": 60, \"months\": 0}','ASSTT. SERANG','2022/RE/006/31',86300.00,'III','{\"name\": \"Mr. SANAT KUMAR NASKAR\", \"class\": \"III\", \"scale\": \"2022/RE/006/31\", \"emp_code\": \"44303\", \"birth_date\": \"18-09-1966\", \"last_basic\": 86300, \"designation\": \"ASSTT. SERANG\", \"joining_date\": \"30-04-1986\", \"retirement_date\": \"01-10-2026\", \"age_on_retirement\": {\"days\": 13, \"years\": 60, \"months\": 0}, \"age_on_appointment\": {\"days\": 12, \"years\": 19, \"months\": 7}}','2026-06-03 07:40:38.875419'),
(811,'44414',9,2026,'Mr. RAJU  HEMBROM','04-09-1995','01-10-2026','07-09-1966','{\"days\": 28, \"years\": 28, \"months\": 11}','{\"days\": 24, \"years\": 60, \"months\": 0}','2ND CLASS DRIVER','2022/RE/007/30',91300.00,'III','{\"name\": \"Mr. RAJU  HEMBROM\", \"class\": \"III\", \"scale\": \"2022/RE/007/30\", \"emp_code\": \"44414\", \"birth_date\": \"07-09-1966\", \"last_basic\": 91300, \"designation\": \"2ND CLASS DRIVER\", \"joining_date\": \"04-09-1995\", \"retirement_date\": \"01-10-2026\", \"age_on_retirement\": {\"days\": 24, \"years\": 60, \"months\": 0}, \"age_on_appointment\": {\"days\": 28, \"years\": 28, \"months\": 11}}','2026-06-03 07:40:38.875419'),
(812,'44452',9,2026,'Mr. RANJIT KUMAR MAJI','15-03-1991','01-10-2026','20-09-1966','{\"days\": 23, \"years\": 24, \"months\": 5}','{\"days\": 11, \"years\": 60, \"months\": 0}','PILOT GR. 1','2017/RE/012',210680.00,'I','{\"name\": \"Mr. RANJIT KUMAR MAJI\", \"class\": \"I\", \"scale\": \"2017/RE/012\", \"emp_code\": \"44452\", \"birth_date\": \"20-09-1966\", \"last_basic\": 210680, \"designation\": \"PILOT GR. 1\", \"joining_date\": \"15-03-1991\", \"retirement_date\": \"01-10-2026\", \"age_on_retirement\": {\"days\": 11, \"years\": 60, \"months\": 0}, \"age_on_appointment\": {\"days\": 23, \"years\": 24, \"months\": 5}}','2026-06-03 07:40:38.877082'),
(813,'44519',9,2026,'Mr. UTPAL  GHOSH','14-05-1994','01-10-2026','14-09-1966','{\"days\": 0, \"years\": 27, \"months\": 8}','{\"days\": 17, \"years\": 60, \"months\": 0}','DY. CHIEF HYD. ENGINEER','2017/RE/014',143820.00,'I','{\"name\": \"Mr. UTPAL  GHOSH\", \"class\": \"I\", \"scale\": \"2017/RE/014\", \"emp_code\": \"44519\", \"birth_date\": \"14-09-1966\", \"last_basic\": 143820, \"designation\": \"DY. CHIEF HYD. ENGINEER\", \"joining_date\": \"14-05-1994\", \"retirement_date\": \"01-10-2026\", \"age_on_retirement\": {\"days\": 17, \"years\": 60, \"months\": 0}, \"age_on_appointment\": {\"days\": 0, \"years\": 27, \"months\": 8}}','2026-06-03 07:40:38.877082'),
(814,'44662',9,2026,'Mr. SANDIP  SIL','24-01-1989','01-10-2026','16-09-1966','{\"days\": 8, \"years\": 22, \"months\": 4}','{\"days\": 15, \"years\": 60, \"months\": 0}','LEADING FIREMAN','2022/RE/006/31',86300.00,'III','{\"name\": \"Mr. SANDIP  SIL\", \"class\": \"III\", \"scale\": \"2022/RE/006/31\", \"emp_code\": \"44662\", \"birth_date\": \"16-09-1966\", \"last_basic\": 86300, \"designation\": \"LEADING FIREMAN\", \"joining_date\": \"24-01-1989\", \"retirement_date\": \"01-10-2026\", \"age_on_retirement\": {\"days\": 15, \"years\": 60, \"months\": 0}, \"age_on_appointment\": {\"days\": 8, \"years\": 22, \"months\": 4}}','2026-06-03 07:40:38.877082'),
(815,'45368',9,2026,'EQBAL  AHMED','07-06-1995','01-10-2026','10-09-1966','{\"days\": 28, \"years\": 28, \"months\": 8}','{\"days\": 21, \"years\": 60, \"months\": 0}','FIREMAN','2022/RE/004/31',79100.00,'IV','{\"name\": \"EQBAL  AHMED\", \"class\": \"IV\", \"scale\": \"2022/RE/004/31\", \"emp_code\": \"45368\", \"birth_date\": \"10-09-1966\", \"last_basic\": 79100, \"designation\": \"FIREMAN\", \"joining_date\": \"07-06-1995\", \"retirement_date\": \"01-10-2026\", \"age_on_retirement\": {\"days\": 21, \"years\": 60, \"months\": 0}, \"age_on_appointment\": {\"days\": 28, \"years\": 28, \"months\": 8}}','2026-06-03 07:40:38.877082'),
(816,'46227',9,2026,'Mrs. INDRANI  ROY','30-07-1998','01-10-2026','24-09-1966','{\"days\": 6, \"years\": 31, \"months\": 10}','{\"days\": 7, \"years\": 60, \"months\": 0}','SR. TYPIST','2022/RE/008/26',87600.00,'III','{\"name\": \"Mrs. INDRANI  ROY\", \"class\": \"III\", \"scale\": \"2022/RE/008/26\", \"emp_code\": \"46227\", \"birth_date\": \"24-09-1966\", \"last_basic\": 87600, \"designation\": \"SR. TYPIST\", \"joining_date\": \"30-07-1998\", \"retirement_date\": \"01-10-2026\", \"age_on_retirement\": {\"days\": 7, \"years\": 60, \"months\": 0}, \"age_on_appointment\": {\"days\": 6, \"years\": 31, \"months\": 10}}','2026-06-03 07:40:38.877082'),
(817,'46381',9,2026,'Mr. KRISHNENDU  DAS','08-10-1996','01-10-2026','25-09-1966','{\"days\": 13, \"years\": 30, \"months\": 0}','{\"days\": 6, \"years\": 60, \"months\": 0}','L.D. CLERK','2022/RE/006/27',76700.00,'III','{\"name\": \"Mr. KRISHNENDU  DAS\", \"class\": \"III\", \"scale\": \"2022/RE/006/27\", \"emp_code\": \"46381\", \"birth_date\": \"25-09-1966\", \"last_basic\": 76700, \"designation\": \"L.D. CLERK\", \"joining_date\": \"08-10-1996\", \"retirement_date\": \"01-10-2026\", \"age_on_retirement\": {\"days\": 6, \"years\": 60, \"months\": 0}, \"age_on_appointment\": {\"days\": 13, \"years\": 30, \"months\": 0}}','2026-06-03 07:40:38.877082'),
(818,'46717',9,2026,'Mr. SANJIB  SARKAR','15-03-1997','01-10-2026','28-09-1966','{\"days\": 15, \"years\": 30, \"months\": 5}','{\"days\": 3, \"years\": 60, \"months\": 0}','SUPERINTENDING ENGINEER (MECH)','2017/RE/015',113950.00,'I','{\"name\": \"Mr. SANJIB  SARKAR\", \"class\": \"I\", \"scale\": \"2017/RE/015\", \"emp_code\": \"46717\", \"birth_date\": \"28-09-1966\", \"last_basic\": 113950, \"designation\": \"SUPERINTENDING ENGINEER (MECH)\", \"joining_date\": \"15-03-1997\", \"retirement_date\": \"01-10-2026\", \"age_on_retirement\": {\"days\": 3, \"years\": 60, \"months\": 0}, \"age_on_appointment\": {\"days\": 15, \"years\": 30, \"months\": 5}}','2026-06-03 07:40:38.877082'),
(819,'47198',9,2026,'Mr. PINAKI KUMAR BASU','02-03-1989','01-10-2026','11-09-1966','{\"days\": 19, \"years\": 22, \"months\": 5}','{\"days\": 20, \"years\": 60, \"months\": 0}','PROGRESS SUPERVISOR','2022/RE/010/31',124700.00,'III','{\"name\": \"Mr. PINAKI KUMAR BASU\", \"class\": \"III\", \"scale\": \"2022/RE/010/31\", \"emp_code\": \"47198\", \"birth_date\": \"11-09-1966\", \"last_basic\": 124700, \"designation\": \"PROGRESS SUPERVISOR\", \"joining_date\": \"02-03-1989\", \"retirement_date\": \"01-10-2026\", \"age_on_retirement\": {\"days\": 20, \"years\": 60, \"months\": 0}, \"age_on_appointment\": {\"days\": 19, \"years\": 22, \"months\": 5}}','2026-06-03 07:40:38.878709'),
(820,'47931',9,2026,'Mr. DIPU  DAS','17-05-2001','01-10-2026','28-07-1966','{\"days\": 19, \"years\": 34, \"months\": 9}','{\"days\": 3, \"years\": 60, \"months\": 2}','LASCAR','2022/RE/004/28',72400.00,'IV','{\"name\": \"Mr. DIPU  DAS\", \"class\": \"IV\", \"scale\": \"2022/RE/004/28\", \"emp_code\": \"47931\", \"birth_date\": \"28-07-1966\", \"last_basic\": 72400, \"designation\": \"LASCAR\", \"joining_date\": \"17-05-2001\", \"retirement_date\": \"01-10-2026\", \"age_on_retirement\": {\"days\": 3, \"years\": 60, \"months\": 2}, \"age_on_appointment\": {\"days\": 19, \"years\": 34, \"months\": 9}}','2026-06-03 07:40:38.878709'),
(821,'48285',9,2026,'Mr. JOYDEEP  GHOSHDASTIDAR','27-08-1992','01-10-2026','06-09-1966','{\"days\": 21, \"years\": 25, \"months\": 11}','{\"days\": 25, \"years\": 60, \"months\": 0}','SR. PERSONNEL OFFICER','2017/RE/014',146960.00,'I','{\"name\": \"Mr. JOYDEEP  GHOSHDASTIDAR\", \"class\": \"I\", \"scale\": \"2017/RE/014\", \"emp_code\": \"48285\", \"birth_date\": \"06-09-1966\", \"last_basic\": 146960, \"designation\": \"SR. PERSONNEL OFFICER\", \"joining_date\": \"27-08-1992\", \"retirement_date\": \"01-10-2026\", \"age_on_retirement\": {\"days\": 25, \"years\": 60, \"months\": 0}, \"age_on_appointment\": {\"days\": 21, \"years\": 25, \"months\": 11}}','2026-06-03 07:40:38.878709'),
(832,'41783',6,2026,'Mr. SK.  NIZAM','26-07-1995','01-07-2026','07-06-1966','{\"days\": 19, \"years\": 29, \"months\": 1}','{\"days\": 24, \"years\": 60, \"months\": 0}','G.C.P.O','2022/RE/006/28',79000.00,'III','{\"name\": \"Mr. SK.  NIZAM\", \"class\": \"III\", \"scale\": \"2022/RE/006/28\", \"emp_code\": \"41783\", \"birth_date\": \"07-06-1966\", \"last_basic\": 79000, \"designation\": \"G.C.P.O\", \"joining_date\": \"26-07-1995\", \"retirement_date\": \"01-07-2026\", \"age_on_retirement\": {\"days\": 24, \"years\": 60, \"months\": 0}, \"age_on_appointment\": {\"days\": 19, \"years\": 29, \"months\": 1}}','2026-06-03 07:42:20.713246'),
(833,'42063',6,2026,'Mr. PINTU  GHOSH','05-09-1985','01-07-2026','07-06-1966','{\"days\": 29, \"years\": 19, \"months\": 2}','{\"days\": 24, \"years\": 60, \"months\": 0}','U.D.CLERK (S/G)','2022/RE/008/31',101600.00,'III','{\"name\": \"Mr. PINTU  GHOSH\", \"class\": \"III\", \"scale\": \"2022/RE/008/31\", \"emp_code\": \"42063\", \"birth_date\": \"07-06-1966\", \"last_basic\": 101600, \"designation\": \"U.D.CLERK (S/G)\", \"joining_date\": \"05-09-1985\", \"retirement_date\": \"01-07-2026\", \"age_on_retirement\": {\"days\": 24, \"years\": 60, \"months\": 0}, \"age_on_appointment\": {\"days\": 29, \"years\": 19, \"months\": 2}}','2026-06-03 07:42:20.713246'),
(834,'43626',6,2026,'Mr. SUSHIL  BARLA','11-04-1992','01-07-2026','16-06-1966','{\"days\": 26, \"years\": 25, \"months\": 9}','{\"days\": 15, \"years\": 60, \"months\": 0}','I.O. STAFF CUM LIBRARIAN','2017/RE/018',121190.00,'III','{\"name\": \"Mr. SUSHIL  BARLA\", \"class\": \"III\", \"scale\": \"2017/RE/018\", \"emp_code\": \"43626\", \"birth_date\": \"16-06-1966\", \"last_basic\": 121190, \"designation\": \"I.O. STAFF CUM LIBRARIAN\", \"joining_date\": \"11-04-1992\", \"retirement_date\": \"01-07-2026\", \"age_on_retirement\": {\"days\": 15, \"years\": 60, \"months\": 0}, \"age_on_appointment\": {\"days\": 26, \"years\": 25, \"months\": 9}}','2026-06-03 07:42:20.713246'),
(835,'44377',6,2026,'Mr. SANJAY  BISWAS','04-11-1988','01-07-2026','13-06-1966','{\"days\": 22, \"years\": 22, \"months\": 4}','{\"days\": 18, \"years\": 60, \"months\": 0}','ASSTT.  DOCK MASTER','2017/RE/014',153950.00,'I','{\"name\": \"Mr. SANJAY  BISWAS\", \"class\": \"I\", \"scale\": \"2017/RE/014\", \"emp_code\": \"44377\", \"birth_date\": \"13-06-1966\", \"last_basic\": 153950, \"designation\": \"ASSTT.  DOCK MASTER\", \"joining_date\": \"04-11-1988\", \"retirement_date\": \"01-07-2026\", \"age_on_retirement\": {\"days\": 18, \"years\": 60, \"months\": 0}, \"age_on_appointment\": {\"days\": 22, \"years\": 22, \"months\": 4}}','2026-06-03 07:42:20.713246'),
(836,'44672',6,2026,'Mr. ASOKE  SANTRA','24-01-1989','01-07-2026','04-06-1966','{\"days\": 20, \"years\": 22, \"months\": 7}','{\"days\": 27, \"years\": 60, \"months\": 0}','SUBEDAR','2022/RE/007/29',88600.00,'III','{\"name\": \"Mr. ASOKE  SANTRA\", \"class\": \"III\", \"scale\": \"2022/RE/007/29\", \"emp_code\": \"44672\", \"birth_date\": \"04-06-1966\", \"last_basic\": 88600, \"designation\": \"SUBEDAR\", \"joining_date\": \"24-01-1989\", \"retirement_date\": \"01-07-2026\", \"age_on_retirement\": {\"days\": 27, \"years\": 60, \"months\": 0}, \"age_on_appointment\": {\"days\": 20, \"years\": 22, \"months\": 7}}','2026-06-03 07:42:20.713246'),
(837,'45115',6,2026,'RAM CHANDRA BIN','14-05-1993','01-07-2026','01-07-1966','{\"days\": 13, \"years\": 26, \"months\": 10}','{\"days\": 0, \"years\": 60, \"months\": 0}','A. CATAGORY PORTER','2022/RE/005/25',69500.00,'IV','{\"name\": \"RAM CHANDRA BIN\", \"class\": \"IV\", \"scale\": \"2022/RE/005/25\", \"emp_code\": \"45115\", \"birth_date\": \"01-07-1966\", \"last_basic\": 69500, \"designation\": \"A. CATAGORY PORTER\", \"joining_date\": \"14-05-1993\", \"retirement_date\": \"01-07-2026\", \"age_on_retirement\": {\"days\": 0, \"years\": 60, \"months\": 0}, \"age_on_appointment\": {\"days\": 13, \"years\": 26, \"months\": 10}}','2026-06-03 07:42:20.713246'),
(838,'45746',6,2026,'Mr. RAM KRIPAL KURMI','12-06-1995','01-07-2026','07-06-1966','{\"days\": 5, \"years\": 29, \"months\": 0}','{\"days\": 24, \"years\": 60, \"months\": 0}','A. CATAGORY PORTER','2022/RE/004/31',79100.00,'IV','{\"name\": \"Mr. RAM KRIPAL KURMI\", \"class\": \"IV\", \"scale\": \"2022/RE/004/31\", \"emp_code\": \"45746\", \"birth_date\": \"07-06-1966\", \"last_basic\": 79100, \"designation\": \"A. CATAGORY PORTER\", \"joining_date\": \"12-06-1995\", \"retirement_date\": \"01-07-2026\", \"age_on_retirement\": {\"days\": 24, \"years\": 60, \"months\": 0}, \"age_on_appointment\": {\"days\": 5, \"years\": 29, \"months\": 0}}','2026-06-03 07:42:20.713246'),
(839,'47020',6,2026,'Mr. GANESH PRASAD RAJAK','16-01-1994','01-07-2026','18-06-1966','{\"days\": 29, \"years\": 27, \"months\": 6}','{\"days\": 13, \"years\": 60, \"months\": 0}','HEAD ATTENDANT','2022/RE/005/31',82900.00,'IV','{\"name\": \"Mr. GANESH PRASAD RAJAK\", \"class\": \"IV\", \"scale\": \"2022/RE/005/31\", \"emp_code\": \"47020\", \"birth_date\": \"18-06-1966\", \"last_basic\": 82900, \"designation\": \"HEAD ATTENDANT\", \"joining_date\": \"16-01-1994\", \"retirement_date\": \"01-07-2026\", \"age_on_retirement\": {\"days\": 13, \"years\": 60, \"months\": 0}, \"age_on_appointment\": {\"days\": 29, \"years\": 27, \"months\": 6}}','2026-06-03 07:42:20.713246'),
(840,'48062',6,2026,'Mr. M KR GHOSH','30-05-1992','01-07-2026','02-06-1968','{\"days\": 28, \"years\": 23, \"months\": 11}','{\"days\": 29, \"years\": 58, \"months\": 0}','PROGRESS  ASSTT.','1997/RE/012/06',9850.00,'II','{\"name\": \"Mr. M KR GHOSH\", \"class\": \"II\", \"scale\": \"1997/RE/012/06\", \"emp_code\": \"48062\", \"birth_date\": \"02-06-1968\", \"last_basic\": 9850, \"designation\": \"PROGRESS  ASSTT.\", \"joining_date\": \"30-05-1992\", \"retirement_date\": \"01-07-2026\", \"age_on_retirement\": {\"days\": 29, \"years\": 58, \"months\": 0}, \"age_on_appointment\": {\"days\": 28, \"years\": 23, \"months\": 11}}','2026-06-03 07:42:20.713246'),
(841,'48137',6,2026,'PROKASH CHANDRA BISWAS','18-08-2011','01-07-2026','05-06-1966','{\"days\": 13, \"years\": 45, \"months\": 2}','{\"days\": 26, \"years\": 60, \"months\": 0}','PILOT GR. III','2007/RE/015',37040.00,'I','{\"name\": \"PROKASH CHANDRA BISWAS\", \"class\": \"I\", \"scale\": \"2007/RE/015\", \"emp_code\": \"48137\", \"birth_date\": \"05-06-1966\", \"last_basic\": 37040, \"designation\": \"PILOT GR. III\", \"joining_date\": \"18-08-2011\", \"retirement_date\": \"01-07-2026\", \"age_on_retirement\": {\"days\": 26, \"years\": 60, \"months\": 0}, \"age_on_appointment\": {\"days\": 13, \"years\": 45, \"months\": 2}}','2026-06-03 07:42:20.713246');

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
  PRIMARY KEY (`id`),
  UNIQUE KEY `emp_cd` (`emp_cd`),
  KEY `first_pension_commut_created_by_id_ea40f5fb_fk_accounts_` (`created_by_id`),
  KEY `first_pension_commut_updated_by_id_2097d29d_fk_accounts_` (`updated_by_id`),
  CONSTRAINT `first_pension_commut_created_by_id_ea40f5fb_fk_accounts_` FOREIGN KEY (`created_by_id`) REFERENCES `accounts_user` (`id`),
  CONSTRAINT `first_pension_commut_updated_by_id_2097d29d_fk_accounts_` FOREIGN KEY (`updated_by_id`) REFERENCES `accounts_user` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=10 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

/*Data for the table `first_pension_commutationapplication` */

insert  into `first_pension_commutationapplication`(`id`,`emp_cd`,`appcn_no`,`application_time`,`comm_start_mnth`,`appcn_dt`,`application_rcvd_dt`,`impl_fpen_combill`,`commutation_dt`,`restoration_dt`,`commutation_per`,`mo_certificate_dt`,`mo_certificate_ref`,`commutation_reasons`,`created_at`,`status`,`current_stage`,`updated_at`,`created_by_id`,`updated_by_id`) values 
(1,'42230',5688,1,6,'2026-06-01','2026-06-01','PEN','2026-06-01','2026-06-01',40,'2026-05-21','MO/25-26/1','House Repairing','2026-05-21 07:26:43.257996','COMMUTATION INITIATED','PENSION USER','2026-05-27 09:21:41.963315',1,1),
(2,'46299',5688,1,6,'2026-06-01','2026-06-01','PEN','2026-06-01','2026-06-01',40,NULL,'','House Renovation','2026-05-21 12:04:05.485963','COMMUTATION INITIATED','PENSION USER','2026-05-21 12:32:20.479680',1,1),
(3,'41158',5688,1,2,'2005-02-01','2005-02-01','PEN','2005-02-01','2026-05-01',40,NULL,'','hnbjmnk','2026-05-25 09:05:09.921767','COMMUTATION INITIATED','PENSION USER','2026-05-25 09:05:09.921767',1,NULL),
(4,'44391',5689,1,2,'2007-02-01','2007-02-01','PEN','2007-02-01','2007-02-01',40,NULL,'','Urgent need of money','2026-06-01 07:26:00.604878','COMMUTATION INITIATED','PENSION USER','2026-06-01 07:26:00.604878',3,NULL),
(5,'43694',5690,1,6,'2026-06-01','2026-06-01','PEN','2026-06-01','2026-05-21',40,NULL,'','gfjhgk','2026-06-02 07:47:55.896219','COMMUTATION INITIATED','PENSION USER','2026-06-02 07:47:55.896219',3,NULL),
(6,'41783',5691,1,7,'2026-07-01','2026-07-01','PEN','2026-07-01','2026-06-03',40,NULL,'','Personal Work','2026-06-03 04:41:04.327425','COMMUTATION INITIATED','PENSION USER','2026-06-03 04:41:04.327425',3,NULL),
(7,'42063',5692,1,7,'2026-07-01','2026-07-01','PEN','2026-07-01','2026-07-01',40,NULL,'','House Repairing','2026-06-03 07:20:33.538076','COMMUTATION INITIATED','PENSION USER','2026-06-03 07:20:33.538076',3,NULL),
(8,'48330',5692,1,6,'2026-06-01','2026-06-01','','2026-06-01',NULL,40,NULL,'','','2026-06-03 07:31:15.622896','COMMUTATION INITIATED','PENSION USER','2026-06-03 07:31:15.622896',3,NULL),
(9,'43626',5693,1,7,'2026-07-01','2026-07-01','PEN','2026-07-01',NULL,40,NULL,'','Home Renovation','2026-06-03 08:53:26.457766','COMMUTATION INITIATED','PENSION USER','2026-06-03 08:53:26.457766',3,NULL);

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
  KEY `first_pensi_year_8a0f0d_idx` (`year`,`month`),
  CONSTRAINT `first_pension_dashboard_snapshot_chk_1` CHECK ((`month` >= 0)),
  CONSTRAINT `first_pension_dashboard_snapshot_chk_2` CHECK ((`year` >= 0))
) ENGINE=InnoDB AUTO_INCREMENT=4 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

/*Data for the table `first_pension_dashboard_snapshot` */

insert  into `first_pension_dashboard_snapshot`(`id`,`month`,`year`,`total_employees`,`prev_month_count`,`retirement_count`,`next_month_count`,`prev_month_label`,`this_month_label`,`next_month_label`,`synced_at`) values 
(1,6,2026,36658,8,10,21,'May 2026','June 2026','July 2026','2026-06-03 07:42:20.713246'),
(2,5,2026,36658,9,8,10,'April 2026','May 2026','June 2026','2026-06-03 07:31:33.333865'),
(3,9,2026,36658,9,19,7,'August 2026','September 2026','October 2026','2026-06-03 07:40:38.857914');

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
  PRIMARY KEY (`id`),
  UNIQUE KEY `emp_code` (`emp_code`),
  KEY `first_pension_pensio_created_by_id_1ead96e1_fk_accounts_` (`created_by_id`),
  KEY `first_pension_pensio_updated_by_id_ed04a933_fk_accounts_` (`updated_by_id`),
  CONSTRAINT `first_pension_pensio_created_by_id_1ead96e1_fk_accounts_` FOREIGN KEY (`created_by_id`) REFERENCES `accounts_user` (`id`),
  CONSTRAINT `first_pension_pensio_updated_by_id_ed04a933_fk_accounts_` FOREIGN KEY (`updated_by_id`) REFERENCES `accounts_user` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=24 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

/*Data for the table `first_pension_pensioncase` */

insert  into `first_pension_pensioncase`(`id`,`emp_code`,`name`,`emp_class`,`birth_date`,`joining_date`,`retirement_date`,`designation`,`scale`,`last_basic`,`no_pay_days`,`dies_non_days`,`commutation_percent`,`commutation_reason`,`status`,`current_stage`,`created_at`,`updated_at`,`created_by_id`,`updated_by_id`,`no_pay_more_than_240_days`,`suspension_days`,`separation_type`,`separation_date`,`process_remarks`) values 
(12,'48330','Mr. RAVI SHANKAR RAJHANS','I','1966-06-01','1992-01-01','2026-06-01','TRAFFIC MANAGER','2017/RE/012',180070.00,10,0,40.00,'House Renovation','INITIATED','CLERK','2026-05-11 06:54:24.379441','2026-06-03 07:30:48.612272',1,3,0,0,'RT','2026-06-01','AS PER ORDER OF MOPSW VIDE NO.A-12023/23/2021-PR-I DATED 29.09.2021, SRI RAJHANS JOINED AT KDS ON 30.09.2021. HE HAS BEEN TRANSFERRED FROM HDC.'),
(13,'42230','Mr. SWAPAN KUMAR NASKAR','III','1966-05-06','1988-05-26','2026-06-01','L.D. CLERK','2022/RE/006/31',86300.00,10,7,40.00,'Home Renovation','INITIATED','CLERK','2026-05-11 08:12:40.497930','2026-06-03 08:23:48.225876',1,3,0,0,'RT','2026-05-01','Superannuation'),
(15,'43443','Mr. AMAL KUMAR MAITI','III','1966-05-02','1988-05-25','2026-06-01','PHARMACIST GR. I','2022/RE/010/32',128400.00,0,0,40.00,'Home Renovation','INITIATED','CLERK','2026-05-11 09:16:47.059621','2026-05-26 11:59:35.229355',1,1,0,0,'RT','2026-06-01','Superannuation'),
(16,'45996','Mr. DASARATH  YADAV','III','1966-05-13','1993-01-13','2026-06-01','CARGO OVERSEAR','2022/RE/005/31',82900.00,10,0,40.00,'House Repairing','INITIATED','CLERK','2026-05-12 09:29:23.852168','2026-05-12 09:29:23.852168',1,NULL,0,0,'',NULL,''),
(17,'43694','Mrs. KRISHNA  MINZ','III','1966-06-01','1993-12-21','2026-06-01','U.D.CLERK (S/G)','2022/RE/009/27',98700.00,10,0,40.00,'Home Repair','INITIATED','CLERK','2026-05-15 05:53:24.519681','2026-06-03 06:24:10.076122',1,3,0,0,'RT','2026-05-01','Superannuation'),
(18,'46299','Mrs. RAHIMA  KHATOON','IV','1966-05-02','1994-05-11','2026-06-01','SR. ATTENDANT (FEMALE)','2022/RE/004/30',76800.00,0,0,40.00,NULL,'INITIATED','CLERK','2026-05-21 12:04:33.766859','2026-06-02 09:48:23.958549',1,3,0,0,'RT','2026-06-01','Superannuation'),
(19,'41158','Mr. DEB KUMAR GUHA','III','1947-01-15','1967-06-09','2005-02-01','S.B. OPER.','1997/RE/016/24',8480.00,810,41,40.00,NULL,'INITIATED','CLERK','2026-05-25 09:05:45.343571','2026-05-25 09:13:10.858321',1,1,0,0,'',NULL,''),
(20,'44391','Mr. KASHINATH  PAUL','III','1949-01-03','1983-12-31','2007-02-01','SERANG','2007/RE/005',16090.00,5,32,40.00,NULL,'INITIATED','CLERK','2026-06-01 07:26:25.080081','2026-06-01 07:31:52.267384',3,3,0,0,'',NULL,''),
(21,'41783','Mr. SK.  NIZAM','III','1966-06-07','1995-07-26','2026-07-01','G.C.P.O','2022/RE/006/28',79000.00,5,32,40.00,NULL,'INITIATED','CLERK','2026-06-03 04:40:25.064790','2026-06-03 04:52:53.682236',3,3,0,0,'RT','2026-07-01','Superannuation'),
(22,'42063','Mr. PINTU  GHOSH','III','1966-06-07','1985-09-05','2026-07-01','U.D.CLERK (S/G)','2022/RE/008/31',101600.00,0,0,40.00,NULL,'INITIATED','CLERK','2026-06-03 07:14:38.723531','2026-06-03 07:14:38.723531',3,NULL,0,0,'RT','2026-07-01','Superannuation'),
(23,'43626','Mr. SUSHIL  BARLA','III','1966-06-16','1992-04-11','2026-07-01','I.O. STAFF CUM LIBRARIAN','2017/RE/018',121190.00,5,32,40.00,NULL,'INITIATED','CLERK','2026-06-03 08:28:37.316170','2026-06-03 08:38:32.888781',3,3,0,0,'RT','2026-07-01','Superannuation');

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
  PRIMARY KEY (`id`),
  UNIQUE KEY `emp_cd` (`emp_cd`),
  KEY `first_pension_pensio_created_by_id_817d31dc_fk_accounts_` (`created_by_id`),
  KEY `first_pension_pensio_updated_by_id_3389263b_fk_accounts_` (`updated_by_id`),
  CONSTRAINT `first_pension_pensio_created_by_id_817d31dc_fk_accounts_` FOREIGN KEY (`created_by_id`) REFERENCES `accounts_user` (`id`),
  CONSTRAINT `first_pension_pensio_updated_by_id_3389263b_fk_accounts_` FOREIGN KEY (`updated_by_id`) REFERENCES `accounts_user` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=8 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

/*Data for the table `first_pension_pensionproposal` */

insert  into `first_pension_pensionproposal`(`id`,`emp_cd`,`emp_name`,`employee_status`,`ca_number`,`pension_type`,`pension_proposal_no`,`eligible_double_family_pension`,`separation_type`,`separation_date`,`implemented_year`,`implemented_month`,`service_tenure`,`pension_option`,`option_given_by`,`regn_no`,`regn_date`,`start_month`,`start_year`,`pension_roll_no`,`pension_proposal_date`,`double_family_pension_upto_date`,`provisional_pension_pct`,`bank_cd`,`bank_name`,`account_no`,`vigilance_clearance_ref_no`,`vigilance_clearance_ref_dt`,`lic_bank_cd`,`lic_bank_name`,`vr_ref_no`,`vr_ref_dt`,`compassionate_allowance`,`quarter_status`,`nominee_eform`,`compassionate_allowance_amt`,`port_city_resident`,`gratuity_option`,`retirement_cpi`,`id_card_submitted`,`vigilance_cleared`,`incentive_holder`,`held_up_flag`,`held_gratuity_amt`,`extra_tccs_enabled`,`extra_tccs_years`,`extra_tccs_months`,`extra_tccs_days`,`earning_deductions`,`created_at`,`updated_at`,`created_by_id`,`updated_by_id`) values 
(1,'46299','Mrs. RAHIMA  KHATOON','P','38562','N','PP/ABC/1',0,'RT','2026-06-01',NULL,NULL,'32Y 0M 21D','G','E','X/REG/1','2026-05-21',6,2026,'ROLL1','2026-06-01',NULL,NULL,'010127','GARDEN REACH (GAR)','10320782829','VIG/25-26/1','2026-05-21','700001','','',NULL,'','','E',NULL,'YES','1',NULL,1,1,'','',NULL,0,0,0,0,'[{\"code\": \"200\", \"desc\": \"PENSION(RETIRING)\", \"type\": \"EARN\", \"amount\": \"\", \"deduction_priority\": \"\"}, {\"code\": \"203\", \"desc\": \"COMMUTATION\", \"type\": \"EARN\", \"amount\": \"\", \"deduction_priority\": \"\"}, {\"code\": \"208\", \"desc\": \"RELIEF\", \"type\": \"EARN\", \"amount\": \"\", \"deduction_priority\": \"\"}, {\"code\": \"205\", \"desc\": \"RET. GRATUITY OPT- I\", \"type\": \"EARN\", \"amount\": \"\", \"deduction_priority\": \"\"}]','2026-05-21 12:08:14.628413','2026-06-02 09:58:53.596781',1,3),
(2,'41158','Mr. DEB KUMAR GUHA','EMPLOYEE','34543','','',0,'RT','2005-02-01',2005,2,'From 09-06-1967 to 01-02-2005','G','E','X/fg/yu',NULL,2,2005,'LIC-567',NULL,NULL,NULL,'210013','BEHALA (BHL)','268933','',NULL,'','','',NULL,'','','NOMINEE',NULL,'','',NULL,0,0,'','',NULL,0,0,0,0,'[{\"code\": \"200\", \"desc\": \"PENSION(RETIRING)\", \"type\": \"EARN\", \"amount\": \"\", \"deduction_priority\": \"\"}, {\"code\": \"203\", \"desc\": \"COMMUTATION\", \"type\": \"EARN\", \"amount\": \"\", \"deduction_priority\": \"\"}, {\"code\": \"205\", \"desc\": \"RET. GRATUITY OPT- I\", \"type\": \"EARN\", \"amount\": \"\", \"deduction_priority\": \"\"}, {\"code\": \"208\", \"desc\": \"RELIEF\", \"type\": \"EARN\", \"amount\": \"\", \"deduction_priority\": \"\"}]','2026-05-25 09:06:49.359067','2026-05-25 09:08:44.250912',1,1),
(3,'46689','Mr. MRITUNJOY  BISWAS','EMPLOYEE','','','',0,'RT','2004-05-01',2004,5,'From 12-08-1968 to 01-05-2004','','','',NULL,5,2004,'',NULL,NULL,NULL,'210149','WATGANJ (WTG)','10467','',NULL,'','','',NULL,'','','',NULL,'','',NULL,0,0,'','',NULL,0,0,0,0,'[{\"code\": \"\", \"desc\": \"\", \"type\": \"EARN\", \"amount\": \"\", \"deduction_priority\": \"\"}, {\"code\": \"\", \"desc\": \"\", \"type\": \"EARN\", \"amount\": \"\", \"deduction_priority\": \"\"}, {\"code\": \"\", \"desc\": \"\", \"type\": \"EARN\", \"amount\": \"\", \"deduction_priority\": \"\"}]','2026-05-27 08:38:31.570210','2026-05-27 08:38:31.570210',1,NULL),
(4,'42230','Mr. SWAPAN KUMAR NASKAR','P','39999','N','ABC/TEST/01',0,'RT','2026-05-01',2026,6,'38Y 0M 6D','G','E','X/S-543','2026-05-28',6,2026,'LIC-9999','2026-05-27',NULL,NULL,'160061','KOLKATA PORT TRUST(SUBHASH BHABAN)','158201000002144','VIG/99/2026/001','2026-05-20','700001','','',NULL,'','','',NULL,'YES','1',359.00,1,1,'','',NULL,0,0,0,0,'[{\"code\": \"200\", \"desc\": \"PENSION(RETIRING)\", \"type\": \"EARN\", \"amount\": \"\", \"deduction_priority\": \"\"}, {\"code\": \"203\", \"desc\": \"COMMUTATION\", \"type\": \"EARN\", \"amount\": \"\", \"deduction_priority\": \"\"}, {\"code\": \"205\", \"desc\": \"RET. GRATUITY OPT- I\", \"type\": \"EARN\", \"amount\": \"\", \"deduction_priority\": \"\"}, {\"code\": \"208\", \"desc\": \"RELIEF\", \"type\": \"EARN\", \"amount\": \"\", \"deduction_priority\": \"\"}]','2026-05-27 10:55:10.332149','2026-06-03 08:23:48.267920',1,3),
(5,'44391','Mr. KASHINATH  PAUL','EMPLOYEE','33051','N','MRN/CH/1860/1276',0,'RT','2007-02-01',2007,2,'23Y 1M 1D','G','E','VI/K/89','1994-07-29',2,2007,'LIC-1177','2006-06-30',NULL,NULL,'010129','HOWRAH RLY. STN. (HRS)','01190008042','VIG/SARO/30/2006/878','2006-08-10','700001','LIC','',NULL,'','','',NULL,'NO','1',1708.00,1,1,'','N',NULL,0,0,0,0,'[{\"code\": \"200\", \"desc\": \"PENSION(RETIRING)\", \"type\": \"EARN\", \"amount\": \"\", \"deduction_priority\": \"\"}, {\"code\": \"203\", \"desc\": \"COMMUTATION\", \"type\": \"EARN\", \"amount\": \"\", \"deduction_priority\": \"\"}, {\"code\": \"205\", \"desc\": \"RET. GRATUITY OPT- I\", \"type\": \"EARN\", \"amount\": \"\", \"deduction_priority\": \"\"}, {\"code\": \"208\", \"desc\": \"RELIEF\", \"type\": \"EARN\", \"amount\": \"\", \"deduction_priority\": \"\"}]','2026-06-01 07:31:35.080196','2026-06-01 07:31:35.080196',3,NULL),
(6,'43694','Mrs. KRISHNA  MINZ','EMPLOYEE','38565','N','ABC/Test/9',0,'RT','2026-05-01',NULL,NULL,'32Y 5M 11D','G','E','X/K-45','2026-05-27',6,2026,'LIC-6504','2026-05-22',NULL,NULL,'160059','Ko.P.T. FAIRLIE PLACE BRANCH','227001000001244','VIG/26/001','2026-05-15','700001','','',NULL,'','','E',NULL,'YES','1',359.00,1,1,'','',NULL,0,0,0,0,'[{\"code\": \"200\", \"desc\": \"PENSION(RETIRING)\", \"type\": \"EARN\", \"amount\": \"\", \"deduction_priority\": \"\"}, {\"code\": \"203\", \"desc\": \"COMMUTATION\", \"type\": \"EARN\", \"amount\": \"\", \"deduction_priority\": \"\"}, {\"code\": \"205\", \"desc\": \"RET. GRATUITY OPT- I\", \"type\": \"EARN\", \"amount\": \"\", \"deduction_priority\": \"\"}, {\"code\": \"208\", \"desc\": \"RELIEF\", \"type\": \"EARN\", \"amount\": \"\", \"deduction_priority\": \"\"}]','2026-06-02 11:37:33.771683','2026-06-03 06:24:10.081122',3,3),
(7,'41783','Mr. SK.  NIZAM','EMPLOYEE','33333','N','PP/ABC/002',0,'RT','2026-07-01',NULL,NULL,'30Y 11M 5D','G','E','X/F-55','2026-06-03',7,2026,'LIC-0001','2026-06-03',NULL,NULL,'110008','NEW ALIPORE (NAL)','20032324043','VIG/26/99','2026-06-03','700001','','',NULL,'','','E',NULL,'YES','1',359.00,1,1,'','',NULL,0,0,0,0,'[{\"code\": \"200\", \"desc\": \"PENSION(RETIRING)\", \"type\": \"EARN\", \"amount\": \"\", \"deduction_priority\": \"\"}, {\"code\": \"203\", \"desc\": \"COMMUTATION\", \"type\": \"EARN\", \"amount\": \"\", \"deduction_priority\": \"\"}, {\"code\": \"205\", \"desc\": \"RET. GRATUITY OPT- I\", \"type\": \"EARN\", \"amount\": \"\", \"deduction_priority\": \"\"}, {\"code\": \"208\", \"desc\": \"RELIEF\", \"type\": \"EARN\", \"amount\": \"\", \"deduction_priority\": \"\"}]','2026-06-03 04:44:54.416448','2026-06-03 04:44:54.416448',3,NULL);

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
) ENGINE=InnoDB AUTO_INCREMENT=12 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

/*Data for the table `first_pension_pensionsummary` */

insert  into `first_pension_pensionsummary`(`id`,`total_service_years`,`total_service_months`,`total_service_days`,`tccs_years`,`tccs_months`,`tccs_days`,`tqs_years`,`tqs_months`,`tqs_days`,`pension_amount`,`commutation_amount`,`gratuity_amount`,`pension_start_date`,`created_at`,`updated_at`,`pension_case_id`) values 
(1,34,5,0,34,5,0,34,4,21,90035.00,3541184.59,2000000.00,'2026-06-01','2026-05-11 06:54:24.410189','2026-05-11 06:54:24.410189',12),
(2,38,0,6,37,11,29,37,11,19,43150.00,1697142.00,2000000.00,'2026-06-01','2026-05-11 08:12:40.510186','2026-06-02 06:34:17.198194',13),
(4,38,0,7,38,0,7,38,0,7,64200.00,2525063.04,2000000.00,'2026-06-01','2026-05-11 09:16:47.062626','2026-05-11 09:16:47.062626',15),
(5,33,4,19,33,4,19,33,4,9,41450.00,1630278.24,1879268.07,'2026-06-01','2026-05-12 09:29:23.863720','2026-05-12 09:29:23.863720',16),
(6,32,5,11,32,5,11,32,5,1,49350.00,1940995.00,2000000.00,'2026-06-01','2026-05-15 05:53:24.525710','2026-06-02 11:37:43.298050',17),
(8,32,0,21,32,0,21,32,0,21,38400.00,1510319.00,1688230.00,'2026-06-01','2026-05-21 12:24:07.680469','2026-06-02 09:48:24.009223',18),
(9,37,7,23,37,6,13,35,3,25,4240.00,166765.00,221361.00,'2005-02-01','2026-05-25 09:08:49.005510','2026-05-25 09:13:10.899733',19),
(10,23,1,1,23,0,0,22,11,26,8045.00,316420.00,254217.00,'2007-02-01','2026-06-01 07:31:52.301660','2026-06-01 07:31:52.301660',20),
(11,30,11,5,30,10,4,30,9,29,39500.00,1553583.00,1682322.00,'2026-07-01','2026-06-03 04:52:53.720686','2026-06-03 04:52:53.720686',21);

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

/*Data for the table `workflow_workflowhistory` */

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

/*Data for the table `workflow_workflowinstance` */

/*Table structure for table `workflow_workflowmaster` */

DROP TABLE IF EXISTS `workflow_workflowmaster`;

CREATE TABLE `workflow_workflowmaster` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `name` varchar(100) NOT NULL,
  `module` varchar(50) NOT NULL,
  `is_active` tinyint(1) NOT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

/*Data for the table `workflow_workflowmaster` */

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

/*Data for the table `workflow_workflowstep` */

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;
