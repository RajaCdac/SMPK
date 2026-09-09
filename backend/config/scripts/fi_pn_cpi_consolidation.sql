-- Family Pension CPI consolidation (Methodology-I / class 1-2 notional basics)
-- Class 3/4: CPI in (607, 1708, 126, 198, 277, 359)
-- Class 1/2: CPI in (1708, 126, 277) — no 359
-- Used by arrear to pick era basics by EMP_CLASS / CPI

CREATE TABLE IF NOT EXISTS fi_pn_cpi_consolidation (
  CLAIM_ID       varchar(22)   NOT NULL,
  EMP_CD         varchar(5)    NOT NULL,
  CASE_NO        int           DEFAULT NULL,
  EMP_CLASS      int           DEFAULT NULL,
  CPI            int           NOT NULL,
  BASIC          int           NOT NULL,
  LAST_PAY       decimal(10,2) DEFAULT NULL,
  SEPARATION_DT  datetime      DEFAULT NULL,
  DATE_CREATED   datetime      DEFAULT NULL,
  CREATED_BY     varchar(5)    DEFAULT NULL,
  DATE_MODIFIED  datetime      DEFAULT NULL,
  MODIFIED_BY    varchar(5)    DEFAULT NULL,
  PRIMARY KEY (CLAIM_ID, CPI),
  KEY IX_CPI_CONS_EMP (EMP_CD),
  KEY IX_CPI_CONS_CASE (CASE_NO),
  CONSTRAINT FK_CPI_CONS_CLAIM
    FOREIGN KEY (CLAIM_ID) REFERENCES fi_pn_mh_fpen_caclaim (CLMCA_ID)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
