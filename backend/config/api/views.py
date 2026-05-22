from django.shortcuts import render
from rest_framework.response import Response
from rest_framework.decorators import api_view
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework.views import APIView
from datetime import datetime
from dateutil.relativedelta import relativedelta
from employee.models import PensionCase
from employee.services.oracle_service import get_oracle_connection

class CustomTokenSerializer(TokenObtainPairSerializer):
    def validate(self, attrs):
        data = super().validate(attrs)

        user = self.user

        # get role (adjust based on your model)
        role = user.userrole_set.first().role.name if user.userrole_set.exists() else "User"

        data["user"] = {
            "username": user.username,
            "role": role
        }

        return data


class CustomTokenView(TokenObtainPairView):
    serializer_class = CustomTokenSerializer

def calculate_age(dob, other_date):
    """
    dob and other_date should be datetime.date or datetime objects
    """

    if dob is None or other_date is None:
        return None

    if other_date < dob:
        return None  # invalid case

    diff = relativedelta(other_date, dob)

    return {
        "years": diff.years,
        "months": diff.months,
        "days": diff.days
    }

class DashboardView(APIView):
    def get(self, request):
        conn = get_oracle_connection()
        cursor = conn.cursor()

        today = datetime.today()
        month = request.GET.get("month")
        year = request.GET.get("year")
        if not month or not year:
                month = today.month
                year = today.year

        # Total employees
        cursor.execute("""
            SELECT COUNT(*) FROM FINANCE.FI_XX_MH_EMP_PER
        """)
        total = cursor.fetchone()[0]

        # Retirement count
        cursor.execute("""
            SELECT COUNT(*)
            FROM FINANCE.FI_XX_MH_EMP_ADM
            WHERE EXTRACT(MONTH FROM EXP_RET_DT) = :month
              AND EXTRACT(YEAR FROM EXP_RET_DT) = :year
               AND SEPARATION_TYPE IS NULL
        """, {"month": month, "year": year})

        retirement_count = cursor.fetchone()[0]

        # Retirement list
        cursor.execute("""
            SELECT t1.EMP_CD,TRIM( t1.TITLE || ' ' || t1.FIRST_NAME || ' ' || NVL(t1.MIDDLE_NAME, '') || ' ' || t1.LAST_NAME ) AS full_name,
            t2.JOIN_DT,t2.EXP_RET_DT,t1.BIRTH_DT,t3.DESIG_DESC,
            t4.SCALE_SL,t5.BASIC_AMT,t5.CLASS
            FROM FINANCE.FI_XX_MH_EMP_PER t1
            LEFT JOIN FINANCE.FI_XX_MH_EMP_ADM t2 ON t1.EMP_CD = t2.EMP_CD
            LEFT JOIN FINANCE.FI_XX_MH_DESIG t3 ON t2.DESIG_CD = t3.DESIG_CD
            LEFT JOIN FINANCE.FI_XX_MH_EMP_FIN t4 ON t1.EMP_CD = t4.EMP_CD
            LEFT JOIN FINANCE.FI_XX_MH_EMP_FIN_vw t5 ON t4.EMP_CD= t5.EMP_CD
            
            WHERE EXTRACT(MONTH FROM (EXP_RET_DT-1)) = :month
              AND EXTRACT(YEAR FROM (EXP_RET_DT-1)) = :year
              AND t2.SEPARATION_TYPE IS NULL
            ORDER BY t1.EMP_CD ASC
        """, {"month": month, "year": year})

        rows = cursor.fetchall()
        #Calculate age (year,month,day) on appointment and retirement
        

        data = []
        for r in rows:
            data.append({
                "emp_code": r[0],
                "name": r[1],
                "joining_date": r[2].strftime("%d-%m-%Y") if r[2] else None,
                "retirement_date": r[3].strftime("%d-%m-%Y") if r[3] else None,
                "birth_date": r[4].strftime("%d-%m-%Y") if r[4] else None,
                "age_on_appointment": calculate_age(r[4], r[2]) if r[4] and r[2] else None,
                "age_on_retirement": calculate_age(r[4], r[3]) if r[4] and r[3] else None,
                "designation": r[5],
                "scale": r[6],
                "last_basic": r[7],
                "class": r[8]
            })

        cursor.close()
        conn.close()
        return Response({
            "total_employees": total,
            "retirement_count": retirement_count,
            "retirement_list": data
        })
    

class PensionProcessView(APIView):

    def post(self, request):

        data = request.data

        obj = PensionCase.objects.create(

            emp_code=data.get("emp_code"),

            name=data.get("name"),

            emp_class=data.get("class"),

            birth_date=data.get("birth_date"),

            joining_date=data.get("joining_date"),

            retirement_date=data.get("retirement_date"),

            designation=data.get("designation"),

            scale=data.get("scale"),

            last_basic=data.get("last_basic"),

            no_pay_days=data.get("no_pay_days"),

            dies_non_days=data.get("dies_non_days"),

            commutation_percent=data.get("commutation_percent"),

            commutation_reason=data.get("commutation_reason"),

        )

        return Response({
            "message": "Saved successfully",
            "case_id": obj.id
        })



