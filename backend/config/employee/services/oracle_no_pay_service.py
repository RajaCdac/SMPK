from employee.services.oracle_service import get_oracle_connection
from employee.services.oracle_commutation_service import _to_oracle_date


def upsert_fi_pn_mh_oldbill_param_from_pension_case(case):
    """
    Insert/update FINANCE.FI_PN_MH_OLDBILL_PARAM from PensionCase no-pay data.

    Column mapping:
      EMP_CD              <- emp_code
      APPOINTMENT_DT      <- joining_date
      RETIREMENT_DT       <- retirement_date
      BIRTH_DT            <- birth_date
      DNON_DAYS           <- dies_non_days
      NPAY_PRIOR_10MTH    <- no_pay_days
      SUSP_DAYS           <- suspension_days
      NPAY_MORETHAN_240_DYS <- no_pay_more_than_240_days
      BOY_SERV_DAYS         <- boys_serv_days
    """
    if not case or not case.emp_code:
        raise ValueError("Pension case with emp_code is required.")

    payload = {
        "EMP_CD": str(case.emp_code).strip(),
        "APPOINTMENT_DT": _to_oracle_date(case.joining_date),
        "RETIREMENT_DT": _to_oracle_date(case.retirement_date),
        "BIRTH_DT": _to_oracle_date(case.birth_date),
        "DNON_DAYS": int(case.dies_non_days or 0),
        "NPAY_PRIOR_10MTH": int(case.no_pay_days or 0),
        "SUSP_DAYS": int(case.suspension_days or 0),
        "NPAY_MORETHAN_240_DYS": int(case.no_pay_more_than_240_days or 0),
        "BOY_SERV_DAYS": int(case.boys_serv_days or 0),
    }

    conn = get_oracle_connection()
    cur = conn.cursor()
    try:
        lookup_bind = {"EMP_CD": payload["EMP_CD"]}
        cur.execute(
            """
            SELECT COUNT(*)
            FROM FINANCE.FI_PN_MH_OLDBILL_PARAM
            WHERE EMP_CD = :EMP_CD
            """,
            lookup_bind,
        )
        exists = cur.fetchone()[0] > 0

        if exists:
            cur.execute(
                """
                UPDATE FINANCE.FI_PN_MH_OLDBILL_PARAM
                SET APPOINTMENT_DT = :APPOINTMENT_DT,
                    RETIREMENT_DT = :RETIREMENT_DT,
                    BIRTH_DT = :BIRTH_DT,
                    DNON_DAYS = :DNON_DAYS,
                    NPAY_PRIOR_10MTH = :NPAY_PRIOR_10MTH,
                    SUSP_DAYS = :SUSP_DAYS,
                    NPAY_MORETHAN_240_DYS = :NPAY_MORETHAN_240_DYS,
                    BOY_SERV_DAYS = :BOY_SERV_DAYS
                WHERE EMP_CD = :EMP_CD
                """,
                payload,
            )
        else:
            cur.execute(
                """
                INSERT INTO FINANCE.FI_PN_MH_OLDBILL_PARAM (
                    EMP_CD,
                    APPOINTMENT_DT,
                    RETIREMENT_DT,
                    BIRTH_DT,
                    DNON_DAYS,
                    NPAY_PRIOR_10MTH,
                    SUSP_DAYS,
                    NPAY_MORETHAN_240_DYS,
                    BOY_SERV_DAYS
                ) VALUES (
                    :EMP_CD,
                    :APPOINTMENT_DT,
                    :RETIREMENT_DT,
                    :BIRTH_DT,
                    :DNON_DAYS,
                    :NPAY_PRIOR_10MTH,
                    :SUSP_DAYS,
                    :NPAY_MORETHAN_240_DYS,
                    :BOY_SERV_DAYS
                )
                """,
                payload,
            )

        if cur.rowcount == 0:
            raise ValueError(
                f"No row written in FI_PN_MH_OLDBILL_PARAM for employee {case.emp_code}."
            )

        conn.commit()
        return {"exists": exists, "emp_cd": payload["EMP_CD"]}
    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()
        conn.close()
