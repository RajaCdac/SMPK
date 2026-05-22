from django.shortcuts import render

# Create your views here.
from rest_framework.views import APIView
from rest_framework.response import Response
from employee.services.oracle_service import get_oracle_connection
from rest_framework import status


class EmployeeSearchAPIView(APIView):

    def get(self, request, emp_id):

        try:
            with get_oracle_connection().cursor() as cursor:

                query = """
                    SELECT t1.EMP_CD,TRIM( t1.TITLE || ' ' || t1.FIRST_NAME || ' ' || NVL(t1.MIDDLE_NAME, '') || ' ' || t1.LAST_NAME ) AS full_name,
                    t2.JOIN_DT,t2.EXP_RET_DT,t1.BIRTH_DT,t3.DESIG_DESC,
                    t4.SCALE_SL,t5.BASIC_AMT,t5.CLASS
                    FROM FINANCE.FI_XX_MH_EMP_PER t1
                    LEFT JOIN FINANCE.FI_XX_MH_EMP_ADM t2 ON t1.EMP_CD = t2.EMP_CD
                    LEFT JOIN FINANCE.FI_XX_MH_DESIG t3 ON t2.DESIG_CD = t3.DESIG_CD
                    LEFT JOIN FINANCE.FI_XX_MH_EMP_FIN t4 ON t1.EMP_CD = t4.EMP_CD
                    LEFT JOIN FINANCE.FI_XX_MH_EMP_FIN_vw t5 ON t4.EMP_CD= t5.EMP_CD
                    WHERE t1.EMP_CD = :emp_id
                """

                cursor.execute(query, {'emp_id': emp_id})

                row = cursor.fetchone()

                if row:

                    employee_data = {
                        "emp_id": row[0],
                        "name": row[1],
                        "join_date": row[2].strftime("%d-%m-%Y") if row[2] else None,
                        "expected_retirement_date": row[3].strftime("%d-%m-%Y") if row[3] else None,
                        "birth_date": row[4].strftime("%d-%m-%Y") if row[4] else None,
                        "designation": row[5],
                        "scale": row[6],
                        "basic_amount": row[7],
                        "class": row[8]
                    }

                    return Response(employee_data)

                return Response(
                    {"error": "Employee not found"},
                    status=status.HTTP_404_NOT_FOUND
                )

        except Exception as e:

            return Response(
                {"error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
