import MySQLdb

c = MySQLdb.connect(
    host="localhost", port=3307, user="root", passwd="root123", db="finance"
)
cur = c.cursor()
cur.execute(
    """
    SELECT EMP_CD, COUNT(*) n
    FROM FI_PN_TH_FIRST_MONTH_PENSION
    WHERE EMP_CD IS NOT NULL AND EMP_CD <> ''
    GROUP BY EMP_CD
    ORDER BY n DESC
    LIMIT 5
    """
)
print("top fmp emps", cur.fetchall())
cur.execute(
    """
    SELECT EMP_CD FROM FI_PN_TH_FIRST_MONTH_PENSION
    WHERE EMP_CD IS NOT NULL AND EMP_CD <> ''
    LIMIT 1
    """
)
row = cur.fetchone()
emp = row[0] if row else None
print("sample emp", emp)
if emp:
    cur.execute(
        """
        SELECT DISTINCT b.BILL_NO, b.BILL_TYPE, b.BILL_MONTH, b.BILL_YR,
               b.VOUCHER_NO, b.TOTAL_AMT_EARNED
        FROM FI_PN_TH_PENSION_BILL b
        INNER JOIN FI_PN_TH_FIRST_MONTH_PENSION h ON h.BILL_NO = b.BILL_NO
        WHERE h.EMP_CD = %s
        LIMIT 10
        """,
        (emp,),
    )
    print("bills", cur.fetchall())
    cur.execute(
        """
        SELECT VOUCHER_NO, REF_NO, TOT_AMT
        FROM FI_PN_TH_JV
        WHERE REF_NO IN (
          SELECT DISTINCT BILL_NO FROM FI_PN_TH_FIRST_MONTH_PENSION WHERE EMP_CD=%s
        )
        LIMIT 10
        """,
        (emp,),
    )
    print("jv", cur.fetchall())
    cur.execute(
        "SELECT * FROM FI_PN_MH_PENSIONER WHERE EMP_CD=%s",
        (emp,),
    )
    cols = [d[0] for d in cur.description]
    row = cur.fetchone()
    if row:
        d = dict(zip(cols, row))
        for k in [
            "ORIGINAL_PENSION_AMT",
            "PAYABLE_PENSION",
            "GRATUITY",
            "COMMUTATION_PER",
            "COMMUTED_PORTION",
            "CA_NUMBER",
        ]:
            print(k, d.get(k))
cur.close()
c.close()
