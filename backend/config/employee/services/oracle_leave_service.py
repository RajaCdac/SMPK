"""
Read no-pay (NPL) leave details for an employee from smpk_pension (MySQL).

Source tables (synced from Oracle/finance):
  fi_la_th_lvappl      — leave applications
  fi_la_mh_attendtype  — leave type
  fi_la_mh_lvreason    — reason

No-pay leave is identified by the NPL attendance codes (4, 34).
"""

from django.db import connection

# NPL (No Pay Leave) attendance codes in fi_la_mh_attendtype.
NO_PAY_ATTEND_CODES = (4, 34)


def _fmt_date(value):
    if value is None:
        return None
    if hasattr(value, "strftime"):
        return value.strftime("%d-%m-%Y")
    text = str(value).strip()
    return text[:10] if text else None


def _table_exists(cursor, table_name: str) -> bool:
    cursor.execute(
        """
        SELECT 1
        FROM information_schema.TABLES
        WHERE TABLE_SCHEMA = DATABASE()
          AND TABLE_NAME = %s
        LIMIT 1
        """,
        [table_name],
    )
    return cursor.fetchone() is not None


def get_no_pay_leave_details(emp_code):
    """
    Return all no-pay (NPL) leave applications for one employee from smpk_pension.

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

    placeholders = ", ".join(["%s"] * len(NO_PAY_ATTEND_CODES))
    params = [emp, *NO_PAY_ATTEND_CODES]

    with connection.cursor() as cur:
        required = (
            "fi_la_th_lvappl",
            "fi_la_mh_attendtype",
            "fi_la_mh_lvreason",
        )
        missing = [t for t in required if not _table_exists(cur, t)]
        if missing:
            raise RuntimeError(
                "Leave tables not found in smpk_pension: "
                + ", ".join(missing)
                + ". Sync FI_LA* from finance via Admin > Database transfer "
                "(Finance to smpk_pension)."
            )

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
            FROM fi_la_th_lvappl l
            JOIN fi_la_mh_attendtype a
              ON a.ATTEND_CD = l.ATTEND_CD
            LEFT JOIN fi_la_mh_lvreason r
              ON r.REASON_CD = l.REASON_CD
            WHERE l.EMP_CD = %s
              AND l.ATTEND_CD IN ({placeholders})
            ORDER BY l.WEF_DT
            """,
            params,
        )
        rows = cur.fetchall()

    details = []
    total_days = 0.0
    for row in rows:
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
        "source": "smpk_pension",
        "details": details,
    }
