"""
Oracle first-month pension helpers.

FMPEN_ID format (production): NPEN/F/{pension_year}/{serial}
Serial from FINANCE.FI_XX_XX_M_D_FIN_CTRL where DOC_ABV = 'NPEN'.
"""

from employee.services.oracle_service import get_oracle_connection


class FirstMonthPensionOracleError(Exception):
    pass


DOC_ABV_FIRST_PENSION = "NPEN"
DOC_ABV_FIRST_MONTH_BILL = "PPN"


def _clip(value, max_len, default=""):
    if value is None:
        return default
    text = str(value).strip()
    if not text:
        return default
    return text[:max_len]


def _format_ppn_bill_no(pension_month, pension_year, serial):
    return f"PPN/{int(pension_month):02d}/{int(pension_year)}/{int(serial)}"


def _resolve_fin_year_for_month(cur, *, pension_month, pension_year):
    """
    Forms logic resolves FIN_YR by checking that the first day of the
    pension month/year falls inside the current active financial year range.
    """
    cur.execute(
        """
        SELECT FIN_YR
        FROM FINANCE.FI_XX_XX_M_H_FIN_CTRL
        WHERE FIN_STAT = 0
          AND TO_DATE('01/' || :p_mth || '/' || :p_yr, 'dd/mm/rrrr')
              BETWEEN YR_ST_DT AND YR_END_DT
        """,
        {"p_mth": int(pension_month), "p_yr": int(pension_year)},
    )
    row = cur.fetchone()
    if not row:
        raise FirstMonthPensionOracleError(
            "Active financial year not found for "
            f"{pension_month:02d}/{pension_year}."
        )
    return int(row[0])


def allocate_ppn_bill_no(*, pension_month, pension_year):
    """
    Allocate next bill number for first-month pension bill header:
    BILL_NO = PPN/MM/YYYY/serial
    where serial is controlled by FI_XX_XX_M_D_FIN_CTRL (DOC_ABV='PPN').
    """
    conn = get_oracle_connection()
    cur = conn.cursor()
    try:
        fin_yr = _resolve_fin_year_for_month(
            cur, pension_month=pension_month, pension_year=pension_year
        )
        cur.execute(
            """
            SELECT NVL(L_TRN_NO, 0)
            FROM FINANCE.FI_XX_XX_M_D_FIN_CTRL
            WHERE DOC_ABV = :doc_abv AND FIN_YR = :fin_yr
            FOR UPDATE
            """,
            {"doc_abv": DOC_ABV_FIRST_MONTH_BILL, "fin_yr": fin_yr},
        )
        row = cur.fetchone()
        if not row:
            raise FirstMonthPensionOracleError(
                f"No FIN_CTRL row for DOC_ABV={DOC_ABV_FIRST_MONTH_BILL}, "
                f"FIN_YR={fin_yr}."
            )
        serial = int(row[0]) + 1

        cur.execute(
            """
            UPDATE FINANCE.FI_XX_XX_M_D_FIN_CTRL
            SET L_TRN_NO = :serial
            WHERE DOC_ABV = :doc_abv AND FIN_YR = :fin_yr
            """,
            {"serial": serial, "doc_abv": DOC_ABV_FIRST_MONTH_BILL, "fin_yr": fin_yr},
        )
        if cur.rowcount != 1:
            raise FirstMonthPensionOracleError(
                "FIN_CTRL update for PPN did not affect exactly one row."
            )

        bill_no = _format_ppn_bill_no(pension_month, pension_year, serial)
        conn.commit()
        return {"bill_no": bill_no, "serial": serial, "fin_year": fin_yr}
    except FirstMonthPensionOracleError:
        conn.rollback()
        raise
    except Exception as exc:
        conn.rollback()
        raise FirstMonthPensionOracleError(str(exc)) from exc
    finally:
        cur.close()
        conn.close()


def generate_fmpen_id(pension_year, *, fin_year=None):
    """
    Allocate the next FMPEN_ID: NPEN/F/{pension_year}/{serial}.

    Increments L_TRN_NO on FI_XX_XX_M_D_FIN_CTRL (DOC_ABV='NPEN') for the
    active financial year, or fin_year when supplied.

    Returns:
        dict with fmpen_id, serial, fin_year, pension_year
    """
    pension_yr = int(pension_year)

    conn = get_oracle_connection()
    cur = conn.cursor()
    try:
        if fin_year is not None:
            fin_yr = int(fin_year)
            cur.execute(
                """
                SELECT NVL(L_TRN_NO, 0)
                FROM FINANCE.FI_XX_XX_M_D_FIN_CTRL
                WHERE DOC_ABV = :doc_abv AND FIN_YR = :fin_yr
                FOR UPDATE
                """,
                {"doc_abv": DOC_ABV_FIRST_PENSION, "fin_yr": fin_yr},
            )
            row = cur.fetchone()
            if not row:
                raise FirstMonthPensionOracleError(
                    f"No FIN_CTRL row for DOC_ABV={DOC_ABV_FIRST_PENSION}, "
                    f"FIN_YR={fin_yr}."
                )
            serial = int(row[0]) + 1
        else:
            cur.execute(
                """
                SELECT NVL(det.L_TRN_NO, 0), mas.FIN_YR
                FROM FINANCE.FI_XX_XX_M_D_FIN_CTRL det
                JOIN FINANCE.FI_XX_XX_M_H_FIN_CTRL mas
                  ON det.FIN_YR = mas.FIN_YR
                WHERE mas.FIN_STAT = 0
                  AND TRUNC(SYSDATE) BETWEEN mas.YR_ST_DT AND mas.YR_END_DT
                  AND det.DOC_ABV = :doc_abv
                FOR UPDATE OF det.L_TRN_NO
                """,
                {"doc_abv": DOC_ABV_FIRST_PENSION},
            )
            row = cur.fetchone()
            if not row:
                raise FirstMonthPensionOracleError(
                    "Could not resolve active financial year for "
                    f"DOC_ABV={DOC_ABV_FIRST_PENSION}."
                )
            serial = int(row[0]) + 1
            fin_yr = int(row[1])

        cur.execute(
            """
            UPDATE FINANCE.FI_XX_XX_M_D_FIN_CTRL
            SET L_TRN_NO = :serial
            WHERE DOC_ABV = :doc_abv AND FIN_YR = :fin_yr
            """,
            {
                "serial": serial,
                "doc_abv": DOC_ABV_FIRST_PENSION,
                "fin_yr": fin_yr,
            },
        )
        if cur.rowcount != 1:
            raise FirstMonthPensionOracleError(
                "FIN_CTRL update did not affect exactly one row."
            )

        fmpen_id = f"NPEN/F/{pension_yr}/{serial}"
        conn.commit()

        return {
            "fmpen_id": fmpen_id,
            "serial": serial,
            "fin_year": fin_yr,
            "pension_year": pension_yr,
        }
    except FirstMonthPensionOracleError:
        conn.rollback()
        raise
    except Exception as exc:
        conn.rollback()
        raise FirstMonthPensionOracleError(str(exc)) from exc
    finally:
        cur.close()
        conn.close()


def insert_first_month_pension_header(
    *,
    fmpen_id,
    bill_no=None,
    emp_cd,
    ca_number,
    bank_cd,
    pension_month,
    pension_year,
    pension_type="N",
    nomin_type=None,
    nomin_srl_no=None,
    created_by="A0001",
):
    """
  Insert a row into FI_PN_TH_FIRST_MONTH_PENSION (header only).

  Amount fields (ORIGINAL_FPENSION_AMT, PAYABLE_PENSION, etc.) are typically
  updated by the first-pension generation process after calculation.
    """
    conn = get_oracle_connection()
    cur = conn.cursor()
    try:
        cur.execute(
            """
            INSERT INTO FINANCE.FI_PN_TH_FIRST_MONTH_PENSION (
                FMPEN_ID,
                PENSION_TYPE,
                PENSION_MONTH,
                PENSION_YR,
                CA_NO,
                CA_DATE,
                DATE_OF_EXECUTION,
                BILL_NO,
                DATE_CREATED,
                CREATED_BY,
                EMP_CD,
                BANK_CD,
                NOMIN_TYPE,
                NOMIN_SRL_NO
            ) VALUES (
                :fmpen_id,
                :pension_type,
                :pension_month,
                :pension_yr,
                :ca_no,
                SYSDATE,
                SYSDATE,
                :bill_no,
                SYSDATE,
                :created_by,
                :emp_cd,
                :bank_cd,
                :nomin_type,
                :nomin_srl_no
            )
            """,
            {
                "fmpen_id": _clip(fmpen_id, 22),
                "pension_type": _clip(pension_type, 3, "N"),
                "pension_month": int(pension_month),
                "pension_yr": int(pension_year),
                "ca_no": _clip(ca_number, 22),
                "bill_no": _clip(bill_no, 22) or None,
                "created_by": _clip(created_by, 5, "A0001"),
                "emp_cd": _clip(emp_cd, 5),
                "bank_cd": _clip(bank_cd, 6) or None,
                "nomin_type": _clip(nomin_type, 2) or None,
                "nomin_srl_no": int(nomin_srl_no) if nomin_srl_no not in (None, "") else None,
            },
        )
        conn.commit()
        return {"fmpen_id": fmpen_id, "emp_cd": str(emp_cd).strip()}
    except Exception as exc:
        conn.rollback()
        raise FirstMonthPensionOracleError(str(exc)) from exc
    finally:
        cur.close()
        conn.close()


def allocate_fmpen_id_and_header(
    *,
    emp_cd,
    ca_number,
    bank_cd,
    pension_month,
    pension_year,
    pension_type="N",
    nomin_type=None,
    nomin_srl_no=None,
    created_by="A0001",
    fin_year=None,
):
    """Generate NPEN/F/{year}/{serial} and insert TH header in one transaction."""
    conn = get_oracle_connection()
    cur = conn.cursor()
    try:
        pension_yr = int(pension_year)

        # Bill number (PPN/MM/YYYY/serial) must be allocated for the bill month/year.
        fin_yr_for_month = _resolve_fin_year_for_month(
            cur, pension_month=pension_month, pension_year=pension_yr
        )
        cur.execute(
            """
            SELECT NVL(L_TRN_NO, 0)
            FROM FINANCE.FI_XX_XX_M_D_FIN_CTRL
            WHERE DOC_ABV = :doc_abv AND FIN_YR = :fin_yr
            FOR UPDATE
            """,
            {"doc_abv": DOC_ABV_FIRST_MONTH_BILL, "fin_yr": fin_yr_for_month},
        )
        row_ppn = cur.fetchone()
        if not row_ppn:
            raise FirstMonthPensionOracleError(
                f"No FIN_CTRL row for DOC_ABV={DOC_ABV_FIRST_MONTH_BILL}, "
                f"FIN_YR={fin_yr_for_month}."
            )
        ppn_serial = int(row_ppn[0]) + 1
        cur.execute(
            """
            UPDATE FINANCE.FI_XX_XX_M_D_FIN_CTRL
            SET L_TRN_NO = :serial
            WHERE DOC_ABV = :doc_abv AND FIN_YR = :fin_yr
            """,
            {
                "serial": ppn_serial,
                "doc_abv": DOC_ABV_FIRST_MONTH_BILL,
                "fin_yr": fin_yr_for_month,
            },
        )
        if cur.rowcount != 1:
            raise FirstMonthPensionOracleError(
                "FIN_CTRL update for PPN did not affect exactly one row."
            )
        bill_no = _format_ppn_bill_no(pension_month, pension_yr, ppn_serial)

        if fin_year is not None:
            fin_yr = int(fin_year)
            cur.execute(
                """
                SELECT NVL(L_TRN_NO, 0)
                FROM FINANCE.FI_XX_XX_M_D_FIN_CTRL
                WHERE DOC_ABV = :doc_abv AND FIN_YR = :fin_yr
                FOR UPDATE
                """,
                {"doc_abv": DOC_ABV_FIRST_PENSION, "fin_yr": fin_yr},
            )
            row = cur.fetchone()
            if not row:
                raise FirstMonthPensionOracleError(
                    f"No FIN_CTRL row for DOC_ABV={DOC_ABV_FIRST_PENSION}, "
                    f"FIN_YR={fin_yr}."
                )
            serial = int(row[0]) + 1
        else:
            cur.execute(
                """
                SELECT NVL(det.L_TRN_NO, 0), mas.FIN_YR
                FROM FINANCE.FI_XX_XX_M_D_FIN_CTRL det
                JOIN FINANCE.FI_XX_XX_M_H_FIN_CTRL mas
                  ON det.FIN_YR = mas.FIN_YR
                WHERE mas.FIN_STAT = 0
                  AND TRUNC(SYSDATE) BETWEEN mas.YR_ST_DT AND mas.YR_END_DT
                  AND det.DOC_ABV = :doc_abv
                FOR UPDATE OF det.L_TRN_NO
                """,
                {"doc_abv": DOC_ABV_FIRST_PENSION},
            )
            row = cur.fetchone()
            if not row:
                raise FirstMonthPensionOracleError(
                    "Could not resolve active financial year for "
                    f"DOC_ABV={DOC_ABV_FIRST_PENSION}."
                )
            serial = int(row[0]) + 1
            fin_yr = int(row[1])

        cur.execute(
            """
            UPDATE FINANCE.FI_XX_XX_M_D_FIN_CTRL
            SET L_TRN_NO = :serial
            WHERE DOC_ABV = :doc_abv AND FIN_YR = :fin_yr
            """,
            {
                "serial": serial,
                "doc_abv": DOC_ABV_FIRST_PENSION,
                "fin_yr": fin_yr,
            },
        )

        fmpen_id = f"NPEN/F/{pension_yr}/{serial}"

        cur.execute(
            """
            INSERT INTO FINANCE.FI_PN_TH_FIRST_MONTH_PENSION (
                FMPEN_ID,
                PENSION_TYPE,
                PENSION_MONTH,
                PENSION_YR,
                CA_NO,
                CA_DATE,
                DATE_OF_EXECUTION,
                BILL_NO,
                DATE_CREATED,
                CREATED_BY,
                EMP_CD,
                BANK_CD,
                NOMIN_TYPE,
                NOMIN_SRL_NO
            ) VALUES (
                :fmpen_id,
                :pension_type,
                :pension_month,
                :pension_yr,
                :ca_no,
                SYSDATE,
                SYSDATE,
                :bill_no,
                SYSDATE,
                :created_by,
                :emp_cd,
                :bank_cd,
                :nomin_type,
                :nomin_srl_no
            )
            """,
            {
                "fmpen_id": _clip(fmpen_id, 22),
                "pension_type": _clip(pension_type, 3, "N"),
                "pension_month": int(pension_month),
                "pension_yr": pension_yr,
                "ca_no": _clip(ca_number, 22),
                "bill_no": _clip(bill_no, 22) or None,
                "created_by": _clip(created_by, 5, "A0001"),
                "emp_cd": _clip(emp_cd, 5),
                "bank_cd": _clip(bank_cd, 6) or None,
                "nomin_type": _clip(nomin_type, 2) or None,
                "nomin_srl_no": (
                    int(nomin_srl_no) if nomin_srl_no not in (None, "") else None
                ),
            },
        )

        conn.commit()
        return {
            "fmpen_id": fmpen_id,
            "bill_no": bill_no,
            "serial": serial,
            "fin_year": fin_yr,
            "pension_year": pension_yr,
            "emp_cd": str(emp_cd).strip(),
        }
    except FirstMonthPensionOracleError:
        conn.rollback()
        raise
    except Exception as exc:
        conn.rollback()
        raise FirstMonthPensionOracleError(str(exc)) from exc
    finally:
        cur.close()
        conn.close()
