"""
Read no-pay (NPL) leave details for an employee directly from Oracle.

Source table: FINANCE.FI_LA_TH_LVAPPL (leave applications), joined to
FINANCE.FI_LA_MH_ATTENDTYPE (leave type) and FINANCE.FI_LA_MH_LVREASON (reason).

No-pay leave is identified by the NPL attendance codes.
"""

from employee.services.oracle_service import get_oracle_connection

# NPL (No Pay Leave) attendance codes in FI_LA_MH_ATTENDTYPE.
NO_PAY_ATTEND_CODES = (4, 34)


def _fmt_date(value):
    if value is None:
        return None
    return value.strftime("%d-%m-%Y")


def get_no_pay_leave_details(emp_code):
    """
    Return all no-pay (NPL) leave applications for one employee from Oracle.

    {
        "emp_code": "46353",
        "total_applications": 149,
        "total_no_pay_days": 299,
        "details": [
            {
                "appl_no": "...",
                "attend_desc": "NPL",
                "from_date": "dd-mm-yyyy",
                "to_date": "dd-mm-yyyy",
                "no_pay_days": 3,
                "reason": "...",
                "sanctioned_by": "...",
                "sanctioned_date": "dd-mm-yyyy",
            },
            ...
        ],
    }
    """
    emp = str(emp_code).strip()
    if not emp:
        raise ValueError("emp_code is required.")

    codes_bind = ", ".join(f":c{i}" for i in range(len(NO_PAY_ATTEND_CODES)))
    binds = {"emp": emp}
    for i, code in enumerate(NO_PAY_ATTEND_CODES):
        binds[f"c{i}"] = code

    conn = get_oracle_connection()
    cur = conn.cursor()
    try:
        cur.execute(
            f"""
            SELECT l.APPL_NO,
                   a.ATTEND_DESC,
                   l.WEF_DT,
                   l.WET_DT,
                   l.LV_DAYS,
                   r.REASON_DESC,
                   l.SANC_EMP_CD,
                   l.SANC_DT
            FROM FINANCE.FI_LA_TH_LVAPPL l
            JOIN FINANCE.FI_LA_MH_ATTENDTYPE a
              ON a.ATTEND_CD = l.ATTEND_CD
            LEFT JOIN FINANCE.FI_LA_MH_LVREASON r
              ON r.REASON_CD = l.REASON_CD
            WHERE l.EMP_CD = :emp
              AND l.ATTEND_CD IN ({codes_bind})
            ORDER BY l.WEF_DT
            """,
            binds,
        )

        details = []
        total_days = 0.0
        for row in cur.fetchall():
            days = float(row[4] or 0)
            total_days += days
            details.append(
                {
                    "appl_no": row[0],
                    "attend_desc": row[1],
                    "from_date": _fmt_date(row[2]),
                    "to_date": _fmt_date(row[3]),
                    "no_pay_days": days,
                    "reason": row[5],
                    "sanctioned_by": row[6],
                    "sanctioned_date": _fmt_date(row[7]),
                }
            )

        return {
            "emp_code": emp,
            "total_applications": len(details),
            "total_no_pay_days": int(total_days) if total_days.is_integer() else total_days,
            "details": details,
        }
    finally:
        cur.close()
        conn.close()
