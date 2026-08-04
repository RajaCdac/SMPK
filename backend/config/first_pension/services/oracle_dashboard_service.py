"""Fetch dashboard retirement data from Oracle (same logic as api.views.DashboardView)."""

import calendar
from datetime import datetime

from employee.services.oracle_service import get_oracle_connection

from employee.utils.age import calculate_age
from employee.services.emp_data_service import resolve_posting_designation_display
from employee.utils.display_format import normalize_department_name
from methodology2.services.oracle_employee_service import (
    batch_fetch_scale_desc_map,
    extract_scale_cd,
    resolve_scale_display,
)


def fetch_dashboard_payload(month, year):
    """
    Returns dict matching GET /api/dashboard/ response shape (without data_source).
    """
    conn = get_oracle_connection()
    cursor = conn.cursor()

    try:
        if month == 1:
            prev_month, prev_year = 12, year - 1
        else:
            prev_month, prev_year = month - 1, year

        if month == 12:
            next_month, next_year = 1, year + 1
        else:
            next_month, next_year = month + 1, year

        cursor.execute(
            """
            SELECT COUNT(*) FROM FINANCE.FI_XX_MH_EMP_PER
            """
        )
        total = cursor.fetchone()[0]

        separation_filter = """
              AND (
                t2.SEPARATION_TYPE IS NULL
                OR UPPER(TRIM(t2.SEPARATION_TYPE)) NOT IN ('VR', 'DT')
              )
        """
        retirement_month_filter = """
              AND EXTRACT(MONTH FROM (t2.EXP_RET_DT - 1)) = :month
              AND EXTRACT(YEAR FROM (t2.EXP_RET_DT - 1)) = :year
        """

        def count_retirements(target_month, target_year):
            cursor.execute(
                f"""
                SELECT COUNT(*)
                FROM FINANCE.FI_XX_MH_EMP_ADM t2
                WHERE 1 = 1
                {retirement_month_filter}
                {separation_filter}
                """,
                {"month": target_month, "year": target_year},
            )
            return cursor.fetchone()[0]

        prev_month_count = count_retirements(prev_month, prev_year)
        retirement_count = count_retirements(month, year)
        next_month_count = count_retirements(next_month, next_year)

        cursor.execute(
            f"""
            SELECT t1.EMP_CD,
                   TRIM(t1.TITLE || ' ' || t1.FIRST_NAME || ' ' ||
                       NVL(t1.MIDDLE_NAME, '') || ' ' || t1.LAST_NAME) AS full_name,
                   t2.JOIN_DT,
                   t2.EXP_RET_DT,
                   t1.BIRTH_DT,
                   t7.DEPT_DESC,
                   t3.DESIG_DESC,
                   t6.ALLOC_DESC,
                   t4.SCALE_SL,
                   t5.BASIC_AMT,
                   t5.CLASS
            FROM FINANCE.FI_XX_MH_EMP_PER t1
            LEFT JOIN FINANCE.FI_XX_MH_EMP_ADM t2 ON t1.EMP_CD = t2.EMP_CD
            LEFT JOIN FINANCE.FI_XX_MH_DESIG t3 ON t2.DESIG_CD = t3.DESIG_CD
            LEFT JOIN FINANCE.FI_XX_MH_EMP_DATA t6 ON t1.EMP_CD = t6.EMP_CD
            LEFT JOIN FINANCE.FI_XX_MH_DEPT t7 ON t6.DEPT_CD = t7.DEPT_CD
            LEFT JOIN FINANCE.FI_XX_MH_EMP_FIN t4 ON t1.EMP_CD = t4.EMP_CD
            LEFT JOIN FINANCE.FI_XX_MH_EMP_FIN_VW t5 ON t4.EMP_CD = t5.EMP_CD
            WHERE 1 = 1
            {retirement_month_filter}
            {separation_filter}
            ORDER BY t1.EMP_CD ASC
            """,
            {"month": month, "year": year},
        )

        rows = cursor.fetchall()
        scale_desc_map = batch_fetch_scale_desc_map(
            cursor,
            [extract_scale_cd(row[8]) for row in rows],
        )
        data = []
        for r in rows:
            scale_sl = r[8]
            dept_desc = r[5]
            desig_desc = r[6]
            alloc_desc = r[7]
            data.append({
                "emp_code": r[0],
                "name": r[1],
                "joining_date": r[2].strftime("%d-%m-%Y") if r[2] else None,
                "retirement_date": r[3].strftime("%d-%m-%Y") if r[3] else None,
                "birth_date": r[4].strftime("%d-%m-%Y") if r[4] else None,
                "age_on_appointment": calculate_age(r[4], r[2]) if r[4] and r[2] else None,
                "age_on_retirement": calculate_age(r[4], r[3]) if r[4] and r[3] else None,
                "department": normalize_department_name(dept_desc),
                "designation": resolve_posting_designation_display(
                    dept_desc=dept_desc,
                    desig_desc=desig_desc,
                    alloc_desc=alloc_desc,
                ),
                "scale": resolve_scale_display(
                    scale_sl,
                    r[3],
                    scale_desc_map=scale_desc_map,
                ),
                "scale_code": str(scale_sl).strip() if scale_sl else "",
                "last_basic": r[9],
                "class": r[10],
            })

        def month_label(m, y):
            return f"{calendar.month_name[m]} {y}"

        return {
            "total_employees": total,
            "retirement_count": retirement_count,
            "retirement_list": data,
            "prev_month_count": prev_month_count,
            "next_month_count": next_month_count,
            "prev_month_label": month_label(prev_month, prev_year),
            "this_month_label": month_label(month, year),
            "next_month_label": month_label(next_month, next_year),
            "retirement_month": month,
            "retirement_year": year,
        }
    finally:
        cursor.close()
        conn.close()
